# Extracting Structured JSON from NDAs with Langchain and Pydantic

This repository contains code for extracting structured data from multi-party Non-Disclosure Agreements (NDAs) using Large Language Models (LLMs). We use Langchain to create prompts and Pydantic to ensure the extracted data conforms to our defined schema.

Based on https://github.com/Zipstack/structured-extraction

## Supported operating systems

This code should run on Linux, macOS. Windows is untested, however work is on to solved this.

## Required API Keys

You'll need API keys for OpenAI and [LLMWhisperer](https://unstract.com/llmwhisperer/). Once you have the keys, add them to the `.env.example` file in the root of the project - then rename to `.env`

## Project Structure

```
project_root/
├── nda_extractor.py
├── schemas/
│   ├── definitions/
│   │   └── nda.json
│   └── prompts/
│       └── nda.json
├── .env
├── requirements.txt
└── README.md
```

## Running the code

1. Clone this repository and navigate to the project directory.
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the script:
   ```bash
   python extract.py <path_to_pdf_or_directory> <schema_file_name>
   ```
   For example:
   ```bash
   python extract.py ./example/nda.pdf nda.json
   ```

## How it works

The script processes PDF files containing NDAs, extracts the text content, and uses a language model to parse the information into a structured format. It handles multi-party NDAs, extracting comprehensive information about all aspects of the agreement.

The script now uses customisable schema and prompt configurations, which are loaded from JSON files in the `schemas/definitions/` and `schemas/prompts/` directories, respectively.

## Output

For each processed NDA, the script generates a JSON file containing the extracted information. The structure of this information is defined in the schema file (`schemas/definitions/nda.json`).

## Customisation

You can customise both the data structure and the prompts used for extraction:

1. To modify the structure of the extracted data, edit the `schemas/definitions/nda.json` file.
2. To adjust the prompts used by the language model, edit the `schemas/prompts/nda.json` file.

You can create multiple schema and prompt configurations for different types of documents by adding new JSON files to these directories and specifying the file name when running the script.

## Limitations

- The accuracy of the extraction depends on the quality of the input PDFs and the capabilities of the language model.
- Very complex or non-standard NDAs may not be parsed correctly.
- Some nuanced legal concepts may not be fully captured, and the tool should not be considered a substitute for legal review.

## Contributing

Contributions to improve the script or extend its capabilities are welcome. Please submit a pull request or open an issue to discuss proposed changes.

## Licence

MIT

## Disclaimer

This tool is for informational purposes only and should not be considered as legal advice. While it aims to extract a comprehensive set of information from NDAs, it may not capture all nuances or legal implications. Always consult with a qualified legal professional for interpretation, application, and advice regarding NDAs.