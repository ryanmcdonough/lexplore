import hashlib
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Union
import requests
from dotenv import load_dotenv
from langchain.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, create_model
from unstract.llmwhisperer.client import LLMWhispererClient
 
def load_json_file(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r') as f:
        return json.load(f)

def create_pydantic_model(name: str, schema: Dict[str, Any], models: Dict[str, Any]) -> BaseModel:
    fields = {}
    for field_name, field_info in schema.items():
        field_type = parse_field_type(field_info['type'], models)
        fields[field_name] = (field_type, Field(description=field_info['description']))
    return create_model(name, **fields)

def parse_field_type(type_str: str, models: Dict[str, Any]) -> Any:
    if type_str.startswith('List['):
        inner_type = type_str[5:-1]  # Remove 'List[' and ']'
        return List[parse_field_type(inner_type, models)]
    elif type_str in ['str', 'int', 'float', 'bool', 'datetime']:
        return eval(type_str)
    elif type_str in models:
        return models[type_str]
    else:
        raise ValueError(f"Unknown type: {type_str}")

def create_models_from_schema(schema: Dict[str, Any]) -> Dict[str, BaseModel]:
    models = {}
    # First pass: create placeholder classes
    for model_name in schema.keys():
        models[model_name] = type(model_name, (BaseModel,), {})
    
    # Second pass: create actual models with fields
    for model_name, model_schema in schema.items():
        models[model_name] = create_pydantic_model(model_name, model_schema, models)
    
    return models

def generate_cache_file_name(file_path: str) -> str:
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return os.path.join(os.environ.get('TEMP', '/tmp'), f"{hasher.hexdigest()}.txt")

def extract_text(file_path: str) -> str:
    cache_file_name = generate_cache_file_name(file_path)
    if os.path.exists(cache_file_name):
        print(f"Info: Using cached content for {file_path}")
        with open(cache_file_name, "r", encoding='utf-8') as f:
            return f.read()
    else:
        print(f"Processing file: {file_path}...")
        client = LLMWhispererClient()
        result = client.whisper(file_path=file_path, processing_mode="ocr", output_mode="line-printer")
        extracted_text = result["extracted_text"]
        with open(cache_file_name, "w", encoding='utf-8') as f:
            f.write(extracted_text)
        return extracted_text

def error_exit(error_message: str) -> None:
    print(error_message)
    sys.exit(1)

def show_usage_and_exit() -> None:
    error_exit("Usage: python extract.py <path_to_pdf_or_directory> <schema_file_name>")

def enumerate_pdf_files(file_path: str) -> List[str]:
    files_to_process = []
    if os.path.isfile(file_path):
        if Path(file_path).suffix.lower() == '.pdf':
            files_to_process.append(file_path)
    elif os.path.isdir(file_path):
        for file_name in os.listdir(file_path):
            full_file_path = os.path.join(file_path, file_name)
            if os.path.isfile(full_file_path) and Path(full_file_path).suffix.lower() == '.pdf':
                files_to_process.append(full_file_path)
    else:
        error_exit(f"Error. {file_path} should be a file or a directory.")

    return files_to_process

def extract_values_from_file(raw_file_data: str, models: Dict[str, BaseModel], prompt_config: Dict[str, Any]) -> str:
    system_template = prompt_config['system_message']
    human_template = prompt_config['human_message']

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    parser = PydanticOutputParser(pydantic_object=models['ParsedNDA'])
    print(parser.get_format_instructions())

    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    request = chat_prompt.format_prompt(format_instructions=parser.get_format_instructions(),
                                        raw_file_data=raw_file_data)

    model = ChatOpenAI(temperature=prompt_config['temperature'])
    print("Querying model...")
    result = model(request.to_messages())
    print("Response from model:")
    print(result.content)
    return result.content

def process_pdf_files(file_list: List[str], models: Dict[str, BaseModel], prompt_config: Dict[str, Any]) -> None:
    for file_path in file_list:
        raw_file_data = extract_text(file_path)
        print(f"Extracted text for file {file_path}:\n{raw_file_data}")
        extracted_json = extract_values_from_file(raw_file_data, models, prompt_config)
        json_file_path = f"{file_path}.json"
        with open(json_file_path, "w", encoding='utf-8') as f:
            f.write(extracted_json)

def main() -> None:
    load_dotenv()
    if len(sys.argv) != 3:
        show_usage_and_exit()

    pdf_path = sys.argv[1]
    schema_file_name = sys.argv[2]

    schema_path = os.path.join('schemas', 'definitions', schema_file_name)
    schema = load_json_file(schema_path)
    models = create_models_from_schema(schema)

    prompt_config_path = os.path.join('schemas', 'prompts', schema_file_name)
    prompt_config = load_json_file(prompt_config_path)

    print(f"Processing path {pdf_path}...")
    file_list = enumerate_pdf_files(pdf_path)
    print(f"Processing {len(file_list)} files...")
    if file_list:
        print(f"Processing first file: {file_list[0]}...")
        process_pdf_files(file_list, models, prompt_config)
    else:
        print("No PDF files found to process.")

if __name__ == '__main__':
    main()