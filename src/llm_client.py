from openai import OpenAI
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

class LLMClient:
    def __init__(self):
        load_dotenv(override=True)
        
        self.api_key = os.environ.get("LITELLM_API_KEY")
        
        if not self.api_key or "PLACEHOLDER" in self.api_key:
             raise ValueError("LITELLM_API_KEY is not set correctly in .env file.")

        self.base_url = "http://3.110.18.218"
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        self.default_model = "gemini-2.5-flash"

    def get_completion(self, messages: List[Dict[str, str]], model: str = None, json_mode: bool = False) -> str:
        try:
            target_model = model if model else self.default_model
            
            response = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.0
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise e

llm_client = LLMClient()
