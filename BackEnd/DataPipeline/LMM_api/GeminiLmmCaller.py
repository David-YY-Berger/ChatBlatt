# bs"d
import logging
from typing import Optional
import requests

from BackEnd.DataPipeline.LMM_api.LmmCaller import LmmCaller
from BackEnd.DataPipeline.LMM_api.LmmResponses.RawLmmResponse import RawLmmResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiLmmCaller(LmmCaller):

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-pro"):
        super().__init__(api_key)
        if not hasattr(self, 'model'):
            self.model = model
            logger.info(f"GeminiLmmCaller configured with model: {model}")

    def call(self, prompt: str, **kwargs) -> RawLmmResponse:
        """
        Call Gemini API with the given prompt.

        Args:
            prompt: The text prompt to send
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LmmResponse object with the result
        """
        if not self.api_key:
            logger.error("API key not provided")
            return RawLmmResponse(
                success=False,
                error="API key not provided"
            )

        if not prompt or not prompt.strip():
            logger.error("Empty prompt provided")
            return RawLmmResponse(
                success=False,
                error="Prompt cannot be empty"
            )

        try:
            url = f"{self.BASE_URL}/{self.model}:generateContent"
            headers = {"Content-Type": "application/json"}

            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }

            # Add optional parameters
            if kwargs:
                generation_config = {}
                if "temperature" in kwargs:
                    generation_config["temperature"] = kwargs["temperature"]
                if "max_tokens" in kwargs:
                    generation_config["maxOutputTokens"] = kwargs["max_tokens"]
                if generation_config:
                    payload["generationConfig"] = generation_config

            logger.info(f"Sending request to Gemini API (model: {self.model})")

            response = requests.post(
                url,
                params={"key": self.api_key},
                headers=headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()

                # Extract content from Gemini response structure
                try:
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info("Successfully received response from Gemini API")
                    return RawLmmResponse(
                        success=True,
                        content=content,
                        metadata={"model": self.model, "status_code": 200}
                    )
                except (KeyError, IndexError) as e:
                    logger.error(f"Failed to parse Gemini response: {e}")
                    return RawLmmResponse(
                        success=False,
                        error=f"Invalid response structure: {e}",
                        metadata={"raw_response": data}
                    )

            elif response.status_code == 401:
                logger.error("Authentication failed - invalid API key")
                return RawLmmResponse(
                    success=False,
                    error="Authentication failed: Invalid API key"
                )

            elif response.status_code == 429:
                logger.warning("Rate limit exceeded")
                return RawLmmResponse(
                    success=False,
                    error="Rate limit exceeded. Please try again later."
                )

            elif response.status_code == 400:
                logger.error(f"Bad request: {response.text}")
                return RawLmmResponse(
                    success=False,
                    error=f"Bad request: {response.text}"
                )

            else:
                logger.error(f"API request failed with status {response.status_code}")
                return RawLmmResponse(
                    success=False,
                    error=f"API error: {response.status_code} - {response.text}"
                )

        except requests.exceptions.Timeout:
            logger.error("Request timed out")
            return RawLmmResponse(
                success=False,
                error="Request timed out after 30 seconds"
            )

        except requests.exceptions.ConnectionError:
            logger.error("Connection error occurred")
            return RawLmmResponse(
                success=False,
                error="Failed to connect to Gemini API"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            return RawLmmResponse(
                success=False,
                error=f"Request failed: {str(e)}"
            )

        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return RawLmmResponse(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )


# Example usage
if __name__ == "__main__":
    # Singleton pattern demonstration
    caller1 = GeminiLmmCaller(api_key="your-api-key-here")
    caller2 = GeminiLmmCaller(api_key="different-key")  # Will reuse same instance

    print(f"Same instance? {caller1 is caller2}")  # True

    # Make a call
    response = caller1.call("What is the capital of France?")
    print(response)

    if response.success:
        print(f"Response: {response.content}")
    else:
        print(f"Error: {response.error}")

