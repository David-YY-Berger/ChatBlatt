# bs"d
import logging
import os
import google.generativeai as genai
from dotenv import load_dotenv
from typing_extensions import override

from BackEnd.DataPipeline.LMM_api.LmmCaller import LmmCaller
from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiLmmCaller(LmmCaller):

    def __init__(self):
        super().__init__()
        # Only configure if this is a fresh initialization
        if not hasattr(self, '_model'):
            if self._api_key:
                genai.configure(api_key=self._api_key)

            # Initialize the model
            self._model = genai.GenerativeModel(self._model_name)
            logger.info(f"Gemini model {self._model} configured")

    @override
    def _get_model_name(self) -> str:
        return "gemini-2.5-flash-lite"

    @override
    def _get_api_key(self) -> str:
        # Check if already in environment; if not, load from .env
        api_key = os.getenv('GEMINI_FREE_API_KEY')
        if not api_key:
            load_dotenv()
            api_key = os.getenv('GEMINI_FREE_API_KEY')
        return api_key

    @override
    def _get_pydantic_model_name(self):
        return 'google-gla:' + self._model_name

    def call(self, prompt: str) -> RawLmmResponse:
        """
        Make a call to the Gemini API.

        Args:
            prompt: The prompt to send to the model

        Returns:
            RawLmmResponse containing the generated text and metadata
        """
        try:
            # Configure generation parameters
            generation_config = genai.GenerationConfig(
                temperature=self._config['temperature'],
                max_output_tokens=self._config['max_tokens'],
                top_p=self._config['top_p'],
                top_k=self._config['top_k']
            )

            # Make the API call
            response = self._model.generate_content(
                prompt,
                generation_config=generation_config
            )

            # Extract response text
            response_text = response.text

            # Build metadata
            metadata = {
                'model': self._model_name,
                'config': self._config.copy(),
                'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None,
                'safety_ratings': [
                    {
                        'category': rating.category.name,
                        'probability': rating.probability.name
                    }
                    for rating in (response.candidates[0].safety_ratings if response.candidates else [])
                ]
            }

            logger.info(f"Gemini API call successful, response length: {len(response_text)}")

            return RawLmmResponse(
                success=True,
                content=response_text,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            return RawLmmResponse(
                success=False,
                error=str(e),
                metadata={'model': self._model_name, 'config': self._config.copy()}
            )
