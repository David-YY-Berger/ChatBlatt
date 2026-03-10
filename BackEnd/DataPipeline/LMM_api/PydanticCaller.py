import os
from typing import Tuple
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.usage import RunUsage
from pydantic import ValidationError
from BackEnd.DataObjects.PydanticModels.PydanticClasses import (
    FinalResponse,
    TRIBES_OF_ISRAEL,
    ENTITY_CATEGORIES,        # Re-exported for convenience
    SYMMETRIC_RELATIONSHIPS,  # Re-exported for convenience
    min_len_summary,
    max_len_summary
)

TRIBES_LIST_STR = ', '.join(sorted([t.title() for t in TRIBES_OF_ISRAEL]))

class PydanticCaller:
    def __init__(self, api_key: str, model_name: str):
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key

        self.agent = Agent(
            model=model_name,
            output_type=FinalResponse,
            model_settings=ModelSettings(
                temperature=0.5  # Lower temp for consistent structured extraction
            ),
            system_prompt=(
                "Extract entities and relationships from the text.\n\n"
                
                "=== SUMMARY REQUIREMENTS ===\n"
                f"- en_summary: EXACTLY {min_len_summary}-{max_len_summary} complete words in English. No partial sentences.\n"
                f"- heb_summary: EXACTLY {min_len_summary}-{max_len_summary} complete words in Hebrew. No partial sentences.\n"
                "- Count words BEFORE responding. Rephrase if needed to fit the limit.\n\n"
                
                "=== ENTITY TYPES ===\n"
                "- Person: Named individuals AND groups (proper nouns only).\n"
                "  Includes: humans, angels, idols/gods, talking animals.\n"
                "  Groups: 'The 70 Elders', 'Children Of Israel', 'The Sanhedrin', 'The Spies'.\n"
                "  Examples: Moses, David, Sarah, Gabriel, Balaam's Donkey.\n"
                "  NOT generic terms: priest, king, prophet, man, woman.\n"
                "  Extract even if mentioned incidentally or as possessives.\n\n"
                
                "- Place: Named geographic locations (proper nouns).\n"
                "  Includes: cities, regions, rivers, mountains, countries as locations.\n"
                "  Also non-literal: 'World To Come', 'Garden of Eden', 'Gehenna'.\n"
                "  Examples: Jerusalem, Egypt, Jordan River, Mount Sinai.\n\n"
                
                f"- TribeOfIsrael: ONLY these 14 tribes: {TRIBES_LIST_STR}.\n"
                "  Always classify tribe names as TribeOfIsrael.\n\n"
                
                "- Nation: Named nations/peoples (proper nouns only).\n"
                "  Use singular form: Egypt (not Egyptians), Moab (not Moabites).\n"
                "  Examples: Egypt, Moab, Assyria, Babylon, Philistia, Edom.\n"
                "  NOT generic terms: nation, people, enemy, kingdom.\n\n"
                
                "- Symbol: Symbolic objects, concepts, or items with significance.\n"
                "  Examples: Ark of the Covenant, Menorah, Tablets, Burning Bush.\n\n"
                
                "=== ENTITY PRIORITY RULES ===\n"
                "- If entity is both Person AND TribeOfIsrael → include in BOTH lists.\n"
                "- If entity is both Place AND Nation → include in BOTH lists.\n\n"
                
                "=== RELATIONSHIP TYPES ===\n"
                "Person ↔ Person:\n"
                "- studiedFrom: Sage transmitting teaching ('X said in name of Y', 'X said that Y said').\n"
                "- childOf: Explicit parent-child only.\n"
                "- descendantOf: Non-adjacent ancestry (grandparent+). NOT if childOf exists.\n"
                "- spouseOf: Married couples.\n"
                "- spokeWith: Direct conversation or dialogue in the text.\n\n"
                
                "Person → Place:\n"
                "- bornIn: Person's birthplace.\n"
                "- diedIn: Place of death.\n"
                "- visited: Person traveled to or was present at location.\n\n"
                
                "Person → TribeOfIsrael:\n"
                "- personToTribeOfIsrael: Person belongs to or is associated with a tribe.\n\n"
                
                "Person → Nation:\n"
                "- personBelongsToNation: Person is a member of a nation.\n\n"
                
                "Nation/Person ↔ Nation/Person:\n"
                "- EnemyOf: Hostile relationship between nations OR between persons.\n"
                "- AllyOf: Alliance or friendly relationship between nations OR persons.\n\n"
                
                "Place → Nation:\n"
                "- placeToNation: Place belongs to or is associated with a nation.\n\n"
                
                "Person → Any Entity:\n"
                "- prophesiedAbout: Prophet making prediction about any entity.\n\n"
                
                "Any Entity ↔ Any Entity:\n"
                "- comparedTo: Similarity or likeness drawn between entities.\n"
                "- contrastedWith: Difference or opposition drawn between entities.\n"
                "- AliasOf: Two names for the SAME entity. Only if text EXPLICITLY states they are the same.\n"
                "  Examples: 'Hadassa, who is Esther', 'Jacob, who is Israel'.\n"
                "  NOT for similar entities or comparisons - only explicit identity.\n\n"
                
                "=== OPTIMIZATION ===\n"
                "- Omit empty lists/objects entirely.\n"
                "- All relationship terms MUST reference extracted entities.\n"
                "- Return only populated data."
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
        output_cost = (usage.output_tokens / 1_000_000) * 0.30  # Fixed: was using input_tokens
        return input_cost + output_cost

    async def extract_graph_from_passage(self, passage: str) -> Tuple[str, RunUsage, float]:
        """
                Raises:
                    ValidationError: If the model output doesn't pass validation
                    Exception: For any other errors during extraction
                """
        try:
            # TODO this 'await' prevents any parrallelity... must fix
            result = await self._extract(passage)

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