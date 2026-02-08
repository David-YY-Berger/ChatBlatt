import os
from pydantic_ai import Agent
from BackEnd.DataObjects.PydanticModels.PydanticClasses import FinalResponse


class PydanticCaller:
    def __init__(self, api_key: str, model_name: str):
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key

        self.agent = Agent(
            model=model_name,
            output_type=FinalResponse,
            system_prompt="Your prompt here..."
        )

    async def extract(self, passage: str) -> FinalResponse:
        result = await self.agent.run(passage,)
        return result.output
