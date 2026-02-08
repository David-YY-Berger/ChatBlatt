import os
import asyncio
from typing import Tuple
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage
from pydantic import ValidationError
from BackEnd.DataObjects.PydanticModels.PydanticClasses import FinalResponse, TRIBES_OF_ISRAEL

TRIBES_LIST_STR = ', '.join(sorted([t.title() for t in TRIBES_OF_ISRAEL]))

class PydanticCaller:
    def __init__(self, api_key: str, model_name: str):
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key

        self.agent = Agent(
            model=model_name,
            output_type=FinalResponse,
            system_prompt=(
                "Extract entities and relationships from the text. "
                "CRITICAL SUMMARY REQUIREMENTS: "
                "- en_summary: MUST be EXACTLY 4-10 complete words. Do NOT generate partial sentences. "
                "- heb_summary: MUST be EXACTLY 4-10 complete words in Hebrew. Do NOT generate partial sentences. "
                "- Count your words BEFORE responding. If a summary would exceed 10 words, rephrase it to be shorter. "
                "ENTITY CLASSIFICATION RULES: "
                "- Person: ONLY specific named individuals (proper nouns). "
                "  Examples: Moses, David, Sarah. "
                "  NOT generic terms: priest, king, prophet, man, woman. "
                "- Nation: ONLY specific named nations/peoples (proper nouns). "
                "  Examples: Egypt (for 'Egyptians'), Moab (for 'Moabites'), Assyria. "
                "  Use the proper noun form (Egypt, not Egyptians; Moab, not Moabites). "
                "  NOT generic terms: nation, people, enemy, kingdom. "
                f"- TribeOfIsrael: The 14 tribes are: {TRIBES_LIST_STR}. "
                "  Always classify these as TribeOfIsrael. "
                "Optimization: Do not include keys for lists or objects that are empty. "
                "Only return populated data to save tokens. "
                "Ensure all relationship terms reference actual entities extracted."
            ),
            retries=0,
        )

    async def _extract(self, passage: str):
        """Internal async call with single attempt."""
        try:
            # Single extraction attempt - no retries
            result = await self.agent.run(passage)
            return result
        except ValidationError as e:
            # Log validation error but don't retry
            print(f"Validation failed on first attempt: {e}")
            raise  # Re-raise to handle in calling code
        except Exception as e:
            # Any other error - don't retry
            print(f"Extraction failed: {e}")
            raise

    @staticmethod
    def _calculate_cost(usage: RunUsage) -> float:
        """Estimates cost in USD for Gemini 1.5 Flash."""
        input_cost = (usage.input_tokens / 1_000_000) * 0.075
        output_cost = (usage.input_tokens / 1_000_000) * 0.30
        return input_cost + output_cost

    def extract_graph_from_passage(self, passage: str) -> Tuple[str, RunUsage, float]:
        """
        Raises:
            ValidationError: If the model output doesn't pass validation
            Exception: For any other errors during extraction
        """
        try:
            result = asyncio.run(self._extract(passage))

            formatted_json = result.output.model_dump_json(
                indent=2,
                exclude_unset=True,  # ensures empty Optional fields aren't in the JSON string
                exclude_none=True
            )

            usage = result.usage()
            cost = self._calculate_cost(usage)

            return formatted_json, usage, cost

        except ValidationError as e:
            # Validation failed - return error info without retrying
            print(f"VALIDATION ERROR: {e}")
            print("No retry attempted to preserve token budget.")
            raise
        except Exception as e:
            print(f"EXTRACTION ERROR: {e}")
            raise