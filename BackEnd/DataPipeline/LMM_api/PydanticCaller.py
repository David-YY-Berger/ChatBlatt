import os
import asyncio
from typing import Tuple
from pydantic_ai import Agent
from pydantic_ai.usage import RunUsage
from BackEnd.DataObjects.PydanticModels.PydanticClasses import FinalResponse


class PydanticCaller:
    def __init__(self, api_key: str, model_name: str):
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key

        self.agent = Agent(
            model=model_name,
            output_type=FinalResponse,
            system_prompt=(
                "Extract entities and relationships from the text. "
                "Optimization: Do not include keys for lists or objects that are empty. "
                "Only return populated data to save tokens."
            )
        )

    async def _extract(self, passage: str):
        """Internal async call."""
        return await self.agent.run(passage)

    def extract_graph_from_passage(self, passage: str) -> Tuple[str, RunUsage]:
        """
        Runs extraction and returns a tuple:
        (JSON String, Usage Object)
        """
        result = asyncio.run(self._extract(passage))

        formatted_json = result.output.model_dump_json(
            indent=2,
            exclude_unset=True, # ensures empty Optional fields aren't in the JSON string
            exclude_none=True
        )

        return formatted_json, result.usage()
