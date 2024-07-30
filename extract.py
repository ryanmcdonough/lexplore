import hashlib
import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv
from langchain.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, \
    HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, create_model
from unstract.llmwhisperer.client import LLMWhispererClient

def load_json_file(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r') as f:
        return json.load(f)

def create_pydantic_model(name: str, schema: Dict[str, Any]) -> BaseModel:
    fields = {}
    for field_name, field_info in schema.items():
        field_type = eval(field_info['type'])
        fields[field_name] = (field_type, Field(description=field_info['description']))
    return create_model(name, **fields)

def create_models_from_schema(schema: Dict[str, Any]) -> Dict[str, BaseModel]:
    models = {}
    for model_name, model_schema in schema.items():
        models[model_name] = create_pydantic_model(model_name, model_schema)
    return models

def make_llm_whisperer_call(file_path):
    print(f"Processing file:{file_path}...")
    # LLMWhisperer API key is picked up from the environment variable
    client = LLMWhispererClient()
    result = client.whisper(file_path=file_path, processing_mode="ocr", output_mode="line-printer")
    return result["extracted_text"]

def generate_cache_file_name(file_path):
    # For our use case, PDFs won't be less than 4096, practically speaking.
    if os.path.getsize(file_path) < 4096:
        error_exit("File too small to process.")
    with open(file_path, "rb") as f:
        first_block = f.read(4096)
        # seek to the last block
        f.seek(-4096, os.SEEK_END)
        f.read(4096)
        last_block = f.read(4096)

    first_md5_hash = hashlib.md5(first_block).hexdigest()
    last_md5_hash = hashlib.md5(last_block).hexdigest()
    return f"/tmp/{first_md5_hash}_{last_md5_hash}.txt"

def is_file_cached(file_path):
    cache_file_name = generate_cache_file_name(file_path)
    cache_file = Path(cache_file_name)
    if cache_file.is_file():
        return True
    else:
        return False

def extract_text(file_path):
    if is_file_cached(file_path):
        print(f"Info: File {file_path} is already cached.")
        cache_file_name = generate_cache_file_name(file_path)
        with open(cache_file_name, "r") as f:
            return f.read()
    else:
        data = make_llm_whisperer_call(file_path)
        cache_file_name = generate_cache_file_name(file_path)
        with open(cache_file_name, "w") as f:
            f.write(data)
        return data

def error_exit(error_message):
    print(error_message)
    sys.exit(1)

def show_usage_and_exit():
    error_exit("Usage: python script.py <path_to_pdf_or_directory> <schema_file_name>")

def enumerate_pdf_files(file_path):
    files_to_process = []
    # Users can pass a directory or a file name
    if os.path.isfile(file_path):
        if os.path.splitext(file_path)[1][1:].strip().lower() == 'pdf':
            files_to_process.append(file_path)
    elif os.path.isdir(file_path):
        files = os.listdir(file_path)
        for file_name in files:
            full_file_path = os.path.join(file_path, file_name)
            if os.path.isfile(full_file_path):
                if os.path.splitext(file_name)[1][1:].strip().lower() == 'pdf':
                    files_to_process.append(full_file_path)
    else:
        error_exit(f"Error. {file_path} should be a file or a directory.")

    return files_to_process

def extract_values_from_file(raw_file_data, models, prompt_config):
    system_template = prompt_config['system_message']
    human_template = prompt_config['human_message']

    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    parser = PydanticOutputParser(pydantic_object=models['ParsedNDA'])
    print(parser.get_format_instructions())

    # compile chat template
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    request = chat_prompt.format_prompt(format_instructions=parser.get_format_instructions(),
                                        raw_file_data=raw_file_data)

    model = ChatOpenAI(temperature=prompt_config['temperature'])
    print("Querying model...")
    result = model(request.to_messages())
    print("Response from model:")
    print(result.content)
    return result.content

def process_pdf_files(file_list, models, prompt_config):
    for file_path in file_list:
        raw_file_data = extract_text(file_path)
        print(f"Extracted text for file {file_path}:\n{raw_file_data}")
        extracted_json = extract_values_from_file(raw_file_data, models, prompt_config)
        json_file_path = f"{file_path}.json"
        with open(json_file_path, "w") as f:
            f.write(extracted_json)

def main():
    load_dotenv()
    if len(sys.argv) != 3:
        show_usage_and_exit()

    pdf_path = sys.argv[1]
    schema_file_name = sys.argv[2]

    # Load the schema and create models
    schema_path = os.path.join('schemas', 'definitions', schema_file_name)
    schema = load_json_file(schema_path)
    models = create_models_from_schema(schema)

    # Load the prompt configuration
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