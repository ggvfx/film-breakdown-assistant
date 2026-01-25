"""
Ollama AI Client.

Uses the official Ollama Python library to communicate with local models.
"""

import ollama
import json
import logging
from typing import Dict, Any, Optional

class OllamaClient:
    """
    Handles communication with the local Ollama server.
    """

    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name

    async def generate_breakdown(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Sends the prompt to Ollama and returns the structured JSON data.
        """
        try:
            # We use 'async_client' so the UI doesn't freeze while the AI thinks
            client = ollama.AsyncClient()
            
            response = await client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json"  # This is the "magic" that keeps the AI in line!
            )
            
            # The response is a string, so we turn it into a Python dictionary
            return json.loads(response['response'])
            
        except Exception as e:
            logging.error(f"AI Extraction Error: {e}")
            return None