'''process_text.py

Uses Gemma3 to extract keywords and definitions from text.

Note for context window sizes:
32k = 32768
64k = 65536
128k = 131072
256k = 262144
512k = 524288
1M = 1048576

Aug 2025
'''
import os
import re
import sys
import json
import time
import requests

from google import genai # query Gemini
from dotenv import load_dotenv

def query_ollama_model(paper_txt, model="gemma3:12b", verbose=False):
    ollama_url = os.getenv("OLLAMA_API")
    sys_prompt = os.getenv("OLLAMA_PROMPT_KEYWORD_1")
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": model,
        "prompt": sys_prompt + paper_txt,
        "stream": True,
        "options": {
            "num_ctx": 65536
        }
    }
    model_response = ""

    t0 = time.time()
    with requests.post(ollama_url, headers=headers, json=data, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return ""

        for line in response.iter_lines():
            if line:
                try:
                    json_data = json.loads(line.decode('utf-8'))
                    text = json_data.get("response", "")
                    model_response += text
                except json.JSONDecodeError:
                    pass

    t1 = time.time()
    if verbose:
        print(f"    == Keywords extracted in {t1-t0:.2f} seconds")
    return model_response

def get_definitions(keywords, paper_txt, model="gemma3:12b", verbose=False):
    if not keywords:
        return {}
    
    if model == "gemma3:12b":
        ollama_url = os.getenv("OLLAMA_API")
    elif model == "phi3:14b":
        ollama_url = os.getenv("OLLAMA_API")
    elif model == "llama3.3":
        ollama_url = os.getenv("OLLAMA_DAI_API")
    else:
        raise ValueError("Invalid model name: {model}. Valid options: gemma3:12b, llama3.3, phi3:14b")
    
    sys_prompt = f"{keywords}: {os.getenv('OLLAMA_PROMPT_DEFINITION_1')}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "model": model,
        "prompt": sys_prompt + paper_txt,
        "stream": True,
        "options": {
            "num_ctx": 65536
        }
    }
    model_response = ""

    t0 = time.time()
    with requests.post(ollama_url, headers=headers, json=data, stream=True) as response:
        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return ""

        for line in response.iter_lines():
            if line:
                try:
                    json_data = json.loads(line.decode('utf-8'))
                    text = json_data.get("response", "")
                    model_response += text
                except json.JSONDecodeError:
                    pass

    t1 = time.time()
    if verbose:
        print(f"    == Definitions extracted in {t1-t0:.2f} seconds")
    return model_response

def check_keywords(keywords):
    pattern = r'\[(.*?)\]'
    match = re.search(pattern, keywords, re.DOTALL)
    if match:
        list_content = match.group(1)
        keywords = re.findall(r'["\']([^"\']+)["\']', list_content)
        return keywords
    else:
        # print(f"Cannot find valid Python list in response: {keywords}")
        return []

def check_definitions(definitions):
    dict_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
    dict_match = re.search(dict_pattern, definitions, re.DOTALL)
    if dict_match:
        try:
            import ast
            definitions_dict = ast.literal_eval(dict_match.group())
            if isinstance(definitions_dict, dict):
                return definitions_dict
            else:
                # print(f"Invalid dictionary format: {definitions}")
                pass
        except (ValueError, SyntaxError) as e:
            # print(f"Failed to parse dictionary: {definitions}")
            pass
    else:
        # print(f"No dictionary found in model response: {definitions}")
        return {}

def clean_keywords(definitions):
    num_keywords_defined = len(definitions.keys())
    for word in definitions.keys():
        if definitions[word] == 'None':
            num_keywords_defined -= 1
    return num_keywords_defined
            
    
def generate_keywords_and_defs(batch_filepath, kwd_model="gemma3:12b", def_model="llama3.3", verbose=False):
    load_dotenv()
    try:
        updated_dict = {}

        num_kwds_generated = 0
        num_dict_generated = 0
        num_papers = 0
        
        with open(batch_filepath, "r") as f:
            metadata_dict = json.load(f)
            
            for i in range(len(metadata_dict.keys())): # for every paper
                num_papers += 1
                if verbose:
                    print(f"\n\n{i}: {metadata_dict[str(i)]['full_arxiv_url']}")
                    
                keywords = query_ollama_model(paper_txt=metadata_dict[str(i)]['abstract'], model=kwd_model)
                keywords = check_keywords(keywords)
                
                # if we have keywords and full paper text to search
                if keywords and (metadata_dict[str(i)]['full_text'] is not None):
                    definitions = get_definitions(keywords=keywords, paper_txt=metadata_dict[str(i)]['full_text'], model=def_model, verbose=verbose)
                    definitions = check_definitions(definitions)
                    
                    if definitions: 
                        num_dict_generated += 1
                        num_kwds_generated += clean_keywords(definitions)
                    
                    metadata_dict[str(i)]["keywords"] = keywords
                    metadata_dict[str(i)]["definitions"] = definitions
                    if verbose:
                        print(f"    == Keywords: {keywords}")
                        if definitions:
                            for key, value in definitions.items():
                                print(f"    * {key}: {value}")
                else:
                    metadata_dict[str(i)]["keywords"] = []
                    metadata_dict[str(i)]["definitions"] = {}
                    if verbose:
                        print("    == No keywords found.")
                        
                updated_dict[str(i)] = metadata_dict[str(i)]
                        
            with open(batch_filepath, "w") as f:
                json.dump(updated_dict, f, indent=2)
                
    except FileNotFoundError:
        print(f"[ERROR] File not found. Double check folder exists at: {batch_filepath}")
        return
    
    return num_papers, num_kwds_generated, num_dict_generated

def get_keywords(abstract, keywords=5):
    '''Using a Google LLM to extract keywords from a paper abstract.'''
    model = "gemini-2.5-flash-lite"
    prompt = f"For the following paper abstract, extract {keywords} keywords to describe the topic and content of the paper. Return they keywords in a Python list. Return only the Python list, no extra words. For example: ['computer science', 'RAG', 'higher education', ...]. Here is the abstrac to analyze: {abstract}"
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    response = client.models.generate_content(
        model=model, contents=prompt
    )
    return response.text

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_text.py <date>")
        sys.exit(1)
        
    load_dotenv()

    file_path = f"metadata/metadata_{sys.argv[1]}.json"
    num_papers, num_kwds, num_dicts = generate_keywords_and_defs(file_path, kwd_model="gemma3:12b", def_model="gemma3:12b", verbose=False)
    # num_papers, num_kwds, num_dicts = generate_keywords_and_defs(file_path, kwd_model="gemma3:12b", def_model="phi3:14b", verbose=False)
    print(f"[{sys.argv[1]}] {(num_kwds/(num_papers*3))*100:.2f}% keyword extraction rate | Out of {num_papers} total papers: num papers w/ definitions={num_dicts}, num keywords extracted={num_kwds}")
    
    