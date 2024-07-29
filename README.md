Extracting Structured JSON from NDAs with Langchain and Pydantic
============================================================================

This repository contains code for extracting structured data from multi-party Non-Disclosure Agreements (NDAs) using Large Language Models (LLMs). We use Langchain to create prompts and Pydantic to ensure the extracted data conforms to our defined schema.

Based on https://github.com/Zipstack/structured-extraction


Supported operating systems
---------------------------

This code should run on Linux or macOS. 

Windows is not currently supported - however you can try this branch: https://github.com/ryanmcdonough/nda-extraction/tree/windows-support which is untested but should work fine on windows.

Required API Keys
-----------------

You'll need API keys for OpenAI and [LLMWhisperer](https://unstract.com/llmwhisperer/). You can obtain free keys for both services. Once you have the keys, add them to the `.env.example` file in the root of the project - then rename to `.env`

Running the code
----------------

1.  Clone this repository and navigate to the project directory.
2.  Create and activate a Python virtual environment:

    bash

    Copy

    `python3 -m venv .venv
    source .venv/bin/activate`

3.  Install the required dependencies:

    bash

    Copy

    `pip install -r requirements.txt`

4.  Run the script:

    bash

    Copy

    `python extract.py <path to NDA PDF or directory with PDFs>`

How it works
------------

The script processes PDF files containing NDAs, extracts the text content, and uses a language model to parse the information into a structured format. It handles multi-party NDAs, extracting comprehensive information about all aspects of the agreement.

Output
------

For each processed NDA, the script generates a JSON file containing the extracted information, including:

-   List of all parties involved, with their names, addresses, and roles
-   Effective date of the NDA
-   Term or duration of the NDA
-   Confidentiality provisions, including exceptions and duration
-   Governing law
-   Purpose of the NDA
-   Permitted use of confidential information
-   Presence of non-solicitation and non-compete clauses
-   Intellectual property provisions
-   Requirements for returning or destroying confidential information
-   Dispute resolution procedures
-   Amendment provisions
-   Presence of a severability clause

Customization
-------------

You can modify the `ParsedNDA` class in the script to adjust the structure of the extracted data according to your specific needs. The current implementation extracts a wide range of information, but you may want to add or remove fields based on your particular use case.

Limitations
-----------

-   The accuracy of the extraction depends on the quality of the input PDFs and the capabilities of the language model.
-   Very complex or non-standard NDAs may not be parsed correctly.
-   The script currently doesn't handle attachments or exhibits that might be part of the NDA.
-   Some nuanced legal concepts may not be fully captured, and the tool should not be considered a substitute for legal review.

Contributing
------------

Contributions to improve the script or extend its capabilities are welcome. Please submit a pull request or open an issue to discuss proposed changes.

License
-------

MIT

Disclaimer
----------

This tool is for informational purposes only and should not be considered as legal advice. While it aims to extract a comprehensive set of information from NDAs, it may not capture all nuances or legal implications. Always consult with a qualified legal professional for interpretation, application, and advice regarding NDAs.
