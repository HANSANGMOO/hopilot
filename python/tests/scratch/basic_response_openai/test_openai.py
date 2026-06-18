# test_openai.py
# Test script to verify OpenAI API connection and response format

import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

def main():
    # Resolve assets/env/api_key.env relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
    env_path = os.path.join(project_root, "assets", "env", "api_key.env")
    
    print(f"Loading environment from: {env_path}")
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)
    else:
        print(f"Warning: {env_path} not found. Attempting to load default environment.")
        load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY", "")
    
    if not api_key or api_key == "your_openai_api_key_here":
        print("[Warning] OPENAI_API_KEY is not configured in api_key.env or system environment.")
        print("Please edit assets/env/api_key.env and put your OpenAI API key.")
        return

    # REST Endpoint for OpenAI Chat Completions
    url = "https://api.openai.com/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Simple self-introduction request payload
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": "간단하게 자기소개 해주세요."
            }
        ]
    }
    
    print("Sending REST request to OpenAI API...")
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    output_path = os.path.join(script_dir, "output.json")
    
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode("utf-8")
            print(f"Received response (Status: {status_code})")
            
            # Parse raw response as JSON
            raw_json = json.loads(response_body)
            
            # Write to output.json
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(raw_json, out_f, indent=2, ensure_ascii=False)
                
            print(f"Success! Raw response written to: {output_path}")
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"[HTTP Error] {e.code} - {e.reason}")
        print(f"Response: {error_body}")
        
        try:
            raw_error = json.loads(error_body)
            with open(output_path, 'w', encoding='utf-8') as out_f:
                json.dump(raw_error, out_f, indent=2, ensure_ascii=False)
        except Exception:
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.write(error_body)
                
        print(f"Saved error response to: {output_path}")
        
    except Exception as e:
        print(f"[Error] Failed to connect or request: {e}")

if __name__ == "__main__":
    main()
