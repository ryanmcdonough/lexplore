import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv
from langchain.prompts import SystemMessagePromptTemplate, ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from unstract.llmwhisperer.client import LLMWhispererClient


class PartyInfo(BaseModel):
    name: str = Field(description="Name of the party")
    address: str = Field(description="Full address of the party")
    role: str = Field(description="Role of the party in the NDA (e.g., 'Disclosing Party', 'Receiving Party', or 'Both')")


class NDATerm(BaseModel):
    start_date: datetime = Field(description="The start date of the NDA")
    end_date: datetime = Field(description="The end date of the NDA, if specified")
    duration: str = Field(description="The duration of the NDA, if specified instead of an end date")


class ConfidentialityProvision(BaseModel):
    description: str = Field(description="Description of what is considered confidential information")
    exceptions: List[str] = Field(description="List of exceptions to confidential information")
    duration: str = Field(description="Duration for which the confidentiality obligations last")

class DisputeResolution(BaseModel):
    method: str = Field(description="Method of dispute resolution (e.g., arbitration, litigation)")
    venue: str = Field(description="Location or jurisdiction for dispute resolution")

class ParsedNDA(BaseModel):
    parties: List[PartyInfo] = Field(description="List of all parties involved in the NDA")
    effective_date: datetime = Field(description="The effective date of the NDA")
    nda_term: NDATerm = Field(description="The term or duration of the NDA")
    confidentiality_provision: ConfidentialityProvision = Field(description="Details about the confidentiality clause")
    governing_law: str = Field(description="The governing law or jurisdiction for the NDA")
    purpose: str = Field(description="The purpose or context of the NDA")
    permitted_use: str = Field(description="Specific allowed uses of confidential information")
    non_solicitation: bool = Field(description="Whether the NDA includes a non-solicitation clause")
    non_compete: bool = Field(description="Whether the NDA includes a non-compete clause")
    intellectual_property: str = Field(description="Provisions related to intellectual property rights")
    return_of_information: str = Field(description="Requirements for returning or destroying confidential information")
    dispute_resolution: DisputeResolution = Field(description="Details about dispute resolution procedures")
    amendments: str = Field(description="Provisions for making amendments to the agreement")
    severability: bool = Field(description="Whether the NDA includes a severability clause")

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
    error_exit("Please pass name of directory or file to process.")


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


def extract_values_from_file(raw_file_data):
    preamble = ("\n"
                "Your task is to accurately extract and summarize key information from Non-Disclosure Agreements (NDAs), "
                "including multi-party NDAs. Pay close attention to the NDA's language, structure, and any cross-references "
                "to ensure a comprehensive and precise extraction of information. Identify all parties involved, their roles, "
                "and any specific terms that apply to each party. Do not use prior knowledge or information from outside the "
                "context to answer the questions. Only use the information provided in the context to answer the questions.\n")
    postamble = "Do not include any explanation in the reply. Only include the extracted information in the reply."
    system_template = "{preamble}"
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)
    human_template = "{format_instructions}\n{raw_file_data}\n{postamble}"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    parser = PydanticOutputParser(pydantic_object=ParsedNDA)
    print(parser.get_format_instructions())

    # compile chat template
    chat_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    request = chat_prompt.format_prompt(preamble=preamble,
                                        format_instructions=parser.get_format_instructions(),
                                        raw_file_data=raw_file_data,
                                        postamble=postamble).to_messages()
    model = ChatOpenAI()
    print("Querying model...")
    result = model(request, temperature=0)
    print("Response from model:")
    print(result.content)
    return result.content


def process_pdf_files(file_list):
    for file_path in file_list:
        raw_file_data = extract_text(file_path)
        print(f"Extracted text for file {file_path}:\n{raw_file_data}")
        extracted_json = extract_values_from_file(raw_file_data)
        json_file_path = f"{file_path}.json"
        with open(json_file_path, "w") as f:
            f.write(extracted_json)


def main():
    load_dotenv()
    if len(sys.argv) < 2:
        show_usage_and_exit()

    print(f"Processing path {sys.argv[1]}...")
    file_list = enumerate_pdf_files(sys.argv[1])
    print(f"Processing {len(file_list)} files...")
    print(f"Processing first file: {file_list[0]}...")
    process_pdf_files(file_list)


if __name__ == '__main__':
    main()
