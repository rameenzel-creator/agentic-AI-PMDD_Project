"""
Centralized LLM Handler — wraps NVIDIA Gemma API
with retry, temperature control, and JSON-mode parsing.
"""

import os
import json
import re
import time
import random
import requests
from pathlib import Path
from dotenv import load_dotenv

# Always load from the .env next to this file's parent (pmdd root)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env", override=True)


def get_api_key() -> str:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not set in .env")
    return api_key


def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 4096,
    expect_json: bool = True,
    retries: int = 3,
) -> str | dict:
    """
    Calls NVIDIA Gemma API and returns parsed JSON or raw text.
    Implements retry with randomized exponential backoff (jitter).
    """
    api_key = get_api_key()
    invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    # NVIDIA API expects a standard chat payload
    # For JSON response, we can append instruction to the system prompt
    sys_content = system_prompt
    if expect_json:
        sys_content += "\n\nIMPORTANT: Return ONLY a valid JSON object or array. Do not include markdown formatting or extra text."

    payload = {
        "model": "google/gemma-3n-e4b-it",
        "messages": [
            {"role": "system", "content": sys_content},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.70,
        "stream": False
    }

    print(f"\n[LLM] Starting API call to Gemma (expect_json={expect_json})")

    for attempt in range(retries):
        try:
            print(f"[LLM] Attempt {attempt + 1}/{retries}...")
            response = requests.post(invoke_url, headers=headers, json=payload)
            response.raise_for_status()  # raise HTTP errors
            
            data = response.json()
            raw = data["choices"][0]["message"]["content"].strip()
            print("[LLM] Success! Received response.")

            if expect_json:
                # Strip markdown code fences if present
                cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
                cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
                cleaned = cleaned.strip()
                try:
                    res = json.loads(cleaned)
                    return res
                except json.JSONDecodeError:
                    if attempt == retries - 1:
                        print("[LLM] ERROR: Failed to parse JSON on final attempt.")
                        return {"error": "JSON parse failed", "raw": raw}
                    print("[LLM] WARNING: JSON parse failed, retrying...")
            else:
                return raw

        except Exception as e:
            error_str = str(e)
            if attempt < retries - 1:
                # Small exponential backoff with random jitter: (1, 2, 4...) * random(0.5 to 1.5)
                base_delay = 2 ** attempt
                jitter = random.uniform(0.5, 1.5)
                sleep_time = round(base_delay * jitter, 2)
                
                if "429" in error_str or "Rate limit" in error_str:
                    print(f"[LLM] RATE LIMIT HIT! Waiting {sleep_time}s before retry...")
                else:
                    print(f"[LLM] ERROR: {error_str}. Waiting {sleep_time}s before retry...")
                
                time.sleep(sleep_time)
            else:
                print(f"[LLM] FAILED after {retries} attempts.")
                raise RuntimeError(f"LLM call failed after {retries} attempts: {e}")

    print("[LLM] Returning error fallback.")
    return {"error": "All retries failed", "raw": ""}
