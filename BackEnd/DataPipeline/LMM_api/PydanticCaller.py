# bs"d
"""
PydanticCaller - Extracts structured data from passages using LLMs.

Usage:
    from BackEnd.DataPipeline.LMM_api.PydanticCaller import PydanticCaller
    from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider

    # Optional: Switch to OpenAI (default is Gemini)
    ModelConfig.set_provider(ModelProvider.OPENAI)

    # Create caller (uses current ModelConfig settings)
    caller = PydanticCaller()

    # Extract graph from passage
    json_str, usage, cost = await caller.extract_graph_from_passage(passage)
"""

import logging
from typing import Tuple
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.usage import RunUsage
from pydantic import ValidationError

from BackEnd.DataPipeline.LMM_api.ModelConfig import ModelConfig, ModelProvider
from BackEnd.DataObjects.PydanticModels.PydanticClasses import (
    FinalResponse,
    TRIBES_OF_ISRAEL,
    ENTITY_CATEGORIES,
    SYMMETRIC_RELATIONSHIPS,
    PERSON_PLACE_SPECIFIC_RELATIONSHIPS,
    min_len_summary,
    max_len_summary
)

logger = logging.getLogger(__name__)

TRIBES_LIST_STR = ', '.join(sorted([t.title() for t in TRIBES_OF_ISRAEL]))


class PydanticCaller:
    """
    Extracts structured entity/relationship graphs from text passages using LLMs.

    Uses ModelConfig to determine which provider (Gemini/OpenAI) to use.
    Change provider with: ModelConfig.set_provider(ModelProvider.GEMINI_FREE)
    """

    def __init__(self):
        """Initialize with current ModelConfig settings."""
        ModelConfig.ensure_api_key_in_env()

        model_str = ModelConfig.get_pydantic_model()
        is_thinking = ModelConfig.is_thinking_enabled()
        logger.info(f"Initializing PydanticCaller with model: {model_str}, thinking={is_thinking}")

        # Configure model settings based on thinking mode
        if is_thinking:
            # Enable thinking with a budget (tokens allocated for internal reasoning)
            # Higher budget = more thorough reasoning but more tokens used
            settings = ModelSettings(
                temperature=0.5,
                extra_body={
                    "thinkingConfig": {
                        "thinkingBudget": 8192  # Tokens for internal reasoning (1024-24576)
                    }
                }
            )
        else:
            settings = ModelSettings(
                temperature=0.5  # Lower temp for consistent structured extraction
            )

        self.agent = Agent(
            model=model_str,
            output_type=FinalResponse,
            model_settings=settings,
            system_prompt=(
                "Extract entities and relationships from the text.\n\n"
                
                "=== SUMMARY REQUIREMENTS ===\n"
                f"- en_summary: EXACTLY {min_len_summary}-{max_len_summary-2} complete words in English. No partial sentences.\n"
                f"- heb_summary: EXACTLY {min_len_summary}-{max_len_summary-2} complete words in Hebrew. No partial sentences.\n"
                "- Count words BEFORE responding. Rephrase if needed to fit the limit.\n\n"
                
                "=== ENTITY TYPES ===\n"
                "- Person: Named individuals AND groups (proper nouns only).\n"
                "  Includes: humans, angels, idols/gods.\n"
                "  Groups: 'The 70 Elders', 'Children Of Israel', 'The Sanhedrin', 'The Spies'.\n"
                "  Examples: Moses, David, Sarah, Gabriel.\n"
                "  NOT: Generic roles (king, priest), anonymous descriptions (survivors, rulers),\n"
                "  possessive phrases (my people, his servants), indefinite references (he who, those who),\n"
                "  or talking animals (use Animal category for those).\n"
                "  Extract even if mentioned incidentally or as possessives.\n\n"
                
                "- Animal: Named real or mythical animals (proper nouns or specific types).\n"
                "  Includes: Real animals (Lion, Eagle, Serpent, Ox, Dove, Quail).\n"
                "  Includes: Mythical creatures (Leviathan, Behemoth, Phoenix).\n"
                "  Includes: Talking animals (Balaam's Donkey, The Serpent in Eden).\n"
                "  Use the most normalized (singular), specific form.\n"
                "  If an animal is also a food (e.g., Quail), include in BOTH Animal and Food.\n"
                "  NOT: Generic animal references.\n\n"
                
                "- Food: Food items that act as food in context of the passage.\n"
                "  Use the most normalized (singular), specific form.\n"
                "  Examples: Bread, Manna, Wine, Grape, Apple, Olive, Quail, Fig.\n"
                "  If something is both Food and Plant (e.g., Apple, Grape), include in BOTH.\n"
                "  If something is both Food and Animal (e.g., Quail), include in BOTH.\n"
                "  NOT: Generic food references.\n\n"
                
                "- Plant: Plants (edible and inedible) with specific names.\n"
                "  Use the most normalized (singular), specific form.\n"
                "  'Grape vine', 'Grape tree', 'Grape' → all become 'Grape'.\n"
                "  'Apple tree' → 'Apple'.\n"
                "  Examples: Grape, Fig, Cedar, Hyssop, Apple, Wheat, Olive, Pomegranate.\n"
                "  If something is both Plant and Food (e.g., Apple), include in BOTH.\n"
                "  NOT: Generic plant references.\n\n"
                
                "- Place: Named geographic locations (proper nouns).\n"
                "  Includes: cities, regions, rivers, mountains, countries as locations.\n"
                "  Also non-literal: 'World To Come', 'Garden of Eden', 'Gehenna'.\n"
                "  Examples: Jerusalem, Egypt, Jordan River, Mount Sinai.\n\n"
                
                f"- TribeOfIsrael: ONLY these 14 tribes: {TRIBES_LIST_STR}.\n"
                "  Always classify tribe names as TribeOfIsrael.\n\n"
                
                "- Nation: Named nations/peoples (proper nouns only).\n"
                "  ALWAYS use the nation/place NAME, NOT the demonym (people's adjective).\n"
                "  Convert demonyms to nation names: Aramean→Aram, Egyptian→Egypt, Moabite→Moab.\n"
                "  Use singular form: Egypt (not Egyptians), Moab (not Moabites), Aram (not Aramean/Arameans).\n"
                "  Examples: Egypt, Moab, Assyria, Babylon, Philistia, Edom, Aram, Persia, Greece.\n"
                "  NOT generic terms: nation, people, enemy, kingdom.\n\n"
                
                "- Symbol: Specific Symbolic objects, concepts, or items with high significance.\n"
                "  especially if used in comparison or contrastingly. Proper nouns or clearly defined concepts.\n"
                "  Examples: Ark of the Covenant, Menorah, Tablets, Burning Bush, Crown, Throne.\n"
                "  IMPORTANT: Do NOT include animals, plants, or food items as Symbols.\n"
                "  If something is an animal, plant, or food, use those categories instead.\n"
                "  NOT: Generic objects used in imagery (sword, ox, garden, booth) unless they have a\n"
                "       specific proper name. Most passages have few or no Symbols. \n\n"
                
                "- Number: EXPLICIT numeric values mentioned in the text (including fractions).\n"
                "  ALWAYS provide numbers as NUMERIC VALUES, not words.\n"
                "  Convert written numbers to digits: 'thirty seven' → '37', 'three and a half' → '3.5'.\n"
                "  Examples: '7', '40', '12', '70', '3.5', '613'.\n"
                "  NOT: 'a', 'an', 'one', 'each' unless it's an explicit count.\n\n"
                
                "=== ENTITY PRIORITY RULES ===\n"
                "- If entity is both Person AND TribeOfIsrael → include in BOTH lists.\n"
                "- If entity is both Place AND Nation → include in BOTH lists.\n"
                "- If entity is both Food AND Plant (e.g., Apple) → include in BOTH lists with SAME name.\n"
                "- If entity is both Food AND Animal (e.g., Quail) → include in BOTH lists with SAME name.\n"
                "- If entity appears in Animal, Food, or Plant → do NOT include in Symbol.\n\n"
                
                "=== RELATIONSHIP TYPES ===\n"
                "Person ↔ Person:\n"
                "- studiedFrom: Sage transmitting teaching ('X said in name of Y', 'X said that Y said').\n"
                "- childOfFather: term1 is the child, term2 is the MALE parent (father).\n"
                "  IMPORTANT: 'son of Y' or 'daughter of Y' does NOT automatically mean Y is the father!\n"
                "  Use childOfFather ONLY if Y is a MAN. Examples: 'Solomon son of David' → David is male → childOfFather.\n"
                "- childOfMother: term1 is the child, term2 is the FEMALE parent (mother).\n"
                "  Use childOfMother when Y is a WOMAN. Examples: 'Adonijah son of Haggith' → Haggith is female → childOfMother.\n"
                "  Biblical naming 'X son of Y' where Y is female = childOfMother (mother's name patronymic).\n"
                "- descendantOf: Non-adjacent ancestry (grandparent+). NOT if childOfFather/childOfMother exists for that pair.\n"
                "- spouseOf: Married couples.\n"
                "- disagreedWith: Halakhic or ideological dispute between persons.\n\n"
                
                "Person/Animal ↔ Person/Animal (spokeWith ONLY):\n"
                "- spokeWith: Direct conversation or dialogue in the text.\n"
                "  This is the ONLY relationship that includes Animals.\n"
                "  Allows: Person↔Person, Person↔Animal, Animal↔Person, Animal↔Animal.\n"
                "  IMPORTANT: A pair cannot appear in BOTH spokeWith and disagreedWith.\n"
                "  If they disagreed, use disagreedWith. If they merely conversed, use spokeWith.\n\n"
                
                "Person → Place:\n"
                "- bornIn: Person's birthplace.\n"
                "- diedIn: Place of death.\n"
                "- visited: Person traveled to or was present at location.\n"
                "- prayedAt: Person prayed at a specific location.\n"
                "  IMPORTANT FOR ALL Person→Place RELATIONSHIPS: The place name may NOT appear directly next to the event.\n"
                "  Read the ENTIRE passage holistically and use narrative context to infer where events occurred.\n"
                "  If passage discusses a person's action and separately mentions a location in the same narrative, make the connection.\n"
                "  Don't require explicit co-occurrence in the same sentence.\n\n"
                
                "Person/Symbol → Place:\n"
                "- associatedWithPlace: Any significant connection between a Person or Symbol and a Place\n"
                "  NOT covered by bornIn, diedIn, visited, or prayedAt. Use ONLY if no other Person→Place relationship applies.\n"
                "  Examples: 'The Ark of the Covenant' → 'Jerusalem', 'Moses' → 'Mount Sinai' (if not visited).\n"
                "  NOT for Nations - use placeToNation instead.\n\n"

                "Person → TribeOfIsrael:\n"
                "- personToTribeOfIsrael: Person belongs to or is associated with a tribe.\n\n"

                "Person → Nation:\n"
                "- personBelongsToNation: Person is a member of a nation.\n\n"

                "Nation/Person ↔ Nation/Person:\n"
                "- EnemyOf: Hostile relationship between nations, between persons, or person against a nation.\n"
                "- AllyOf: Alliance or friendly relationship between nations, persons, or person with a nation.\n\n"
                
                "Place → Nation:\n"
                "- placeToNation: Place belongs to or is associated with a nation.\n\n"

                "Person → Any Entity:\n"
                "- prophesiedAbout: ONLY PROPHETS (not sages) making prophetic statements about any entity.\n\n"
                
                "Any Entity ↔ Any Entity:\n"
                "- comparedTo: EXPLICIT simile/comparison ('like', 'as', 'resembles').\n"
                "- contrastedWith: EXPLICIT contrast or opposition.\n"
                "  NOTE: contrastedWith is for literary/symbolic contrasts, NOT for halakhic disagreements.\n"
                "  Use disagreedWith for disputes between persons, not contrastedWith.\n"
                "- AliasOf: Two names for the SAME entity. Only if text EXPLICITLY states they are the same.\n"
                "  Examples: 'Hadassa, who is Esther', 'Jacob, who is Israel'.\n"
                "  NOT for similar entities or comparisons - only explicit identity.\n\n"
                
                "=== OPTIMIZATION ===\n"
                "- Omit empty lists/objects entirely.\n"
                "- All relationship terms MUST use the EXACT SAME spelling as the extracted entity names.\n"
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

    def _calculate_cost(self, usage: RunUsage) -> float:
        """Estimates cost in USD based on current provider's pricing."""
        pricing = ModelConfig.get_cost_per_million()

        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
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