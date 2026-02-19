"""
Ollama AI Client.

Uses the official Ollama Python library to communicate with local models.
Handles structured JSON extraction and asynchronous communication.
"""

import ollama
import json
import logging
import re
from typing import Dict, Any, Optional, List

class OllamaClient:
    """
    Handles communication with the local Ollama server.
    """

    def __init__(self, model_name: str = "llama3.2"):
        self.model_name = model_name
        # Reuse the same client instance for better performance
        #self._client = ollama.AsyncClient()
        self._client = None

    def reset_session(self):
        """Re-initializes the async client for the current event loop."""
        self._client = ollama.AsyncClient()

    async def generate_breakdown(self, prompt: str, options: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Sends the prompt to Ollama and returns the structured JSON data.

        Args:
            prompt: The full instruction text for the AI.
            options: LLM parameters like temperature.

        Returns:
            Optional[Dict]: The parsed JSON response or None if the call fails.
        """
        if self._client is None:
            self.reset_session()

        llm_options = options or {}
            
        try:
            response = await self._client.generate(
                model=self.model_name,
                prompt=prompt,
                format="json",
                options=llm_options
            )
            
            raw_content = response.get('response', '')
            if not raw_content:
                return None

            return self._safe_json_parse(raw_content)
            
        except Exception as e:
            logging.error(f"Ollama Communication Error: {e}")
            return None

    def _safe_json_parse(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to parse JSON, with a fallback for common LLM formatting errors.
        """
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Surgical Cleanup: Remove potential leading/trailing markdown backticks
            # which AI sometimes includes even when asked for 'format=json'
            cleaned_text = re.sub(r'^```json\s*|```$', '', text.strip(), flags=re.MULTILINE)
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logging.error(f"Critical JSON Parse Failure: {e}")
                return None

    def update_model(self, new_model_name: str):
        """Allows the GUI to change the active model without restarting."""
        self.model_name = new_model_name

    def get_local_models(self) -> List[str]:
        """Fetches the list of all models currently downloaded in Ollama."""
        try:
            response = ollama.list()
            model_names = []
            for m in response.get('models', []):
                name = getattr(m, 'model', None) or m.get('name') or m.get('model')
                if name:
                    model_names.append(name)
            return model_names if model_names else ["llama3.1:8b"]
        except Exception as e:
            logging.error(f"Failed to fetch local Ollama models: {e}")
            return ["llama3.1:8b"]