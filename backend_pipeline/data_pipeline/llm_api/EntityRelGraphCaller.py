# bs"d
"""
EntityRelGraphCaller - Extracts structured data from passages using LLMs.

Usage:
    from backend.data_pipeline.llm_api.EntityRelGraphCaller import EntityRelGraphCaller
    from backend.data_pipeline.llm_api.ModelConfig import ModelConfig, ModelProvider

    # Optional: Switch to OpenAI (default is Gemini)
    ModelConfig.set_provider(ModelProvider.OPENAI)

    # Create caller (uses current ModelConfig settings)
    caller = EntityRelGraphCaller()

    # Extract graph from passage
    json_str, usage, cost = await caller.extract_graph_from_passage(passage)
"""

import asyncio
import logging
import random
from typing import Optional, Tuple
from pydantic_ai import Agent, ModelSettings, NativeOutput
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import RunUsage
from pydantic import ValidationError
from google.genai.types import CreateCachedContentConfig

from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig
from backend.models_db.Enums import NumberCategory
from backend_pipeline.data_pipeline.PydanticModels.PydanticClasses import (
    FinalResponse,
    TRIBES_OF_ISRAEL,
    min_len_summary,
    max_len_summary
)

logger = logging.getLogger(__name__)

# Retried ONLY for transient rate-limit/server errors (429/500/503) - not for
# ValidationError, where a retry would just burn tokens on output the model already
# got wrong once. Backoff is deliberately long (rate-limit windows are per-minute).
_RATE_LIMIT_RETRYABLE_STATUS_CODES = {429, 500, 503}
_RATE_LIMIT_MAX_ATTEMPTS = 6
_RATE_LIMIT_BASE_DELAY_SECONDS = 10.0

# Gemini explicit context caching (see control_docs/pipeline/llm_context_caching.md) - the
# system prompt is identical on every call for a given run (only the passage text varies),
# so it's cached once per `EntityRelGraphCaller` instance and reused for every source in the
# run. TTL is kept short-ish and refreshed on a 404 mid-run rather than sized to cover an
# entire run up front, so a short/test run isn't paying cache storage for far longer than
# it's actually used.
_CONTEXT_CACHE_TTL_SECONDS = 3600  # 1 hour
_CONTEXT_CACHE_NOT_FOUND_STATUS = 404
_CONTEXT_CACHE_MAX_REFRESH_ATTEMPTS = 2

# Gemini's cached-input rate has consistently been ~10% of the standard input rate across the
# Flash/Flash-Lite tiers (checked against https://ai.google.dev/gemini-api/docs/pricing, Oct
# 2026) - used only to adjust the cost ESTIMATE in _calculate_cost below. Revisit if Google's
# pricing page ever shows a different ratio.
_CACHE_DISCOUNT_FACTOR = 0.1

TRIBES_LIST_STR = ', '.join(sorted([t.title() for t in TRIBES_OF_ISRAEL]))
NUMBER_CATEGORIES_STR = ', '.join(e.value for e in NumberCategory)


class EntityRelGraphCaller:
    """
    Extracts structured entity/relationship graphs from text passages using LLMs.

    Uses ModelConfig to determine which provider (Gemini/OpenAI) to use.
    Change provider with: ModelConfig.set_provider(ModelProvider.GEMINI_FREE)
    """

    def __init__(self, use_context_cache: bool = True):
        """
        Initialize with current ModelConfig settings.

        Args:
            use_context_cache: On Gemini providers, cache the (large, call-invariant) system
                prompt below as a Gemini context-cache resource and reuse it for every call
                this instance makes, instead of resending it with every request. Falls back
                to the original uncached behavior for non-Gemini providers, or if cache
                creation fails for any reason. See
                control_docs/pipeline/llm_context_caching.md for the mechanism/tradeoffs.
        """
        ModelConfig.ensure_api_key_in_env()

        model_str = ModelConfig.get_pydantic_model()
        self._model_name = ModelConfig.get_model_name()
        is_thinking = ModelConfig.is_thinking_enabled()
        logger.info(f"Initializing EntityRelGraphCaller with model: {model_str}, thinking={is_thinking}")

        # Configure model settings based on thinking mode
        if is_thinking:
            # Enable thinking with a budget (tokens allocated for internal reasoning)
            # Higher budget = more thorough reasoning but more tokens used
            self._model_settings = ModelSettings(
                temperature=0.5,
                extra_body={
                    "thinkingConfig": {
                        "thinkingBudget": 8192  # Tokens for internal reasoning (1024-24576)
                    }
                }
            )
        else:
            self._model_settings = ModelSettings(
                temperature=0.5  # Lower temp for consistent structured extraction
            )

        self._system_prompt = (
                "Extract entities and relationships from the text.\n\n"
                
                "=== SUMMARY REQUIREMENTS ===\n"
                f"- en_summary: EXACTLY {min_len_summary}-{max_len_summary-2} complete words in English. No partial sentences.\n"
                f"- heb_summary: EXACTLY {min_len_summary}-{max_len_summary-2} complete words in Hebrew. No partial sentences.\n"
                "- Count words BEFORE responding. Rephrase if needed to fit the limit.\n\n"

                "=== PASSAGE TYPES ===\n"
                "Classify the passage with at least one of: LAW, STORY_TANACH, STORY_SAGES, PHILOSOPHIC, GENEALOGY, PROPHECY.\n"
                "- LAW: Halakhic rulings, legal discussion/debate.\n"
                "- STORY_TANACH: A narrative about Tanach-era people or events (Avraham, Moshe, the Kings, etc).\n"
                "  A passage FROM the Tanach itself is ALWAYS STORY_TANACH if it is a narrative at all —\n"
                "  Mishnaic/Talmudic sages did not yet exist, so Tanach text can never be STORY_SAGES.\n"
                "- STORY_SAGES: A narrative about the Mishnaic/Talmudic sages themselves (a Tanna or Amora\n"
                "  doing/experiencing something, an anecdote about Rabbis). If a Talmudic passage instead\n"
                "  retells/discusses a story about Tanach-era people, classify it as STORY_TANACH, not STORY_SAGES.\n"
                "- PHILOSOPHIC: Ethical, theological, or conceptual discussion (not a narrative, not a ruling).\n"
                "- GENEALOGY: Lineage/ancestry listings.\n"
                "- PROPHECY: A prophetic statement/vision.\n\n"
                
                "=== ENTITY TYPES ===\n"
                "- Person: Named individuals AND groups (proper nouns only).\n"
                "  Includes: humans, angels, idols/gods.\n"
                "  Groups: 'The 70 Elders', 'Children Of Israel', 'The Sanhedrin', 'The Spies'.\n"
                "  Examples: Moses, David, Sarah, Gabriel.\n"
                "  NOT: Generic roles (king, priest), anonymous descriptions (survivors, rulers),\n"
                "  NOT: possessive phrases (my people, his servants), indefinite references (he who, those who),\n"
                "  NOT: or talking animals (use Animal category for those).\n"
                "  Extract even if mentioned incidentally or as possessives.\n"
                "  Strip titles/epithets from en_name - use the BARE proper name only, never prefixed with a\n"
                "  role/title. 'King Ahaz' → 'Ahaz', 'Queen Esther' → 'Esther', 'Rabbi Akiva' → 'Akiva',\n"
                "  'the prophet Elijah' → 'Elijah'. The title itself is never part of en_name.\n\n"
                "  If same name appears with truly different spelling, extract as separate entities with Alias"
                
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
                "  NOT: 'a', 'an', 'one', 'each' unless it's an explicit count.\n"
                "  NOT: Ordinal numbers — SKIP 'first', 'second', 'third', '1st', '2nd', '3rd', etc.\n"
                "  Ordinals indicate order/rank, not a countable quantity. Do NOT extract them.\n\n"
                
                "  Each Number entity requires THREE additional fields:\n\n"
                
                f"  1) number_category — MUST be exactly one of these values: {NUMBER_CATEGORIES_STR}.\n"
                "     Use 'Misc' ONLY if no other category fits.\n"
                "     Gematria is ONLY for the numeric value of an ENTIRE word/name (e.g. 'the gematria of\n"
                "     [word] is 358'), NOT for a number attached to an individual letter.\n"
                "     Examples:\n"
                "       '7 bulls' → Sacrifice | '40 years' → Time | '100 silver' → Money\n"
                "       '600,000 men' → People | '10 cubits' → Measurement\n"
                "       '613 mitzvot' → Obligation | 'gematria of 358' → Gematria\n\n"
                
                "  2) en_unit — a NORMALIZED, SINGULAR, LOWERCASE noun describing what the number counts or measures.\n"
                "     This must be ONE word, always singular, always lowercase, always English.\n"
                "     The goal is deterministic matching — use the same word every time for the same concept.\n"
                "     Examples:\n"
                "       Sacrifice: bull, ram, goat, lamb, sheep, flour, oil, frankincense, dove, offering\n"
                "       Time: year, month, week, day, hour\n"
                "       Money: shekel, silver, gold, talent, gerah\n"
                "       People: man, woman, person, soldier, elder, priest\n"
                "       Measurement: cubit, span, bath, hin, ephah, kor, seah\n"
                "       Obligation: mitzvah, commandment, prohibition\n"
                "       Gematria: word (always 'word' — the value of the entire word/name, never a single letter)\n"
                "     WRONG: 'bulls' (plural), 'years old' (phrase), 'Silver Shekels' (capitalized/multi-word).\n\n"
                
                "  3) en_context — a 1-6 word lowercase topic summary so this number is understandable outside the original passage.\n"
                "     Someone seeing this entry in a totally different place should immediately understand what this number is about.\n"
                "     Describe the GENERAL SUBJECT being discussed, not the number itself.\n"
                "     Examples:\n"
                "       '7 bulls offered on the altar' → en_context: 'korbanot on sukkot'\n"
                "       '40 years wandering' → en_context: 'wilderness punishment'\n"
                "       '100 shekels of silver' → en_context: 'bride price for slander'\n"
                "       '30 cubits high' → en_context: 'tabernacle construction'\n"
                "       '600,000 men' → en_context: 'census in wilderness'\n"
                "       '120 years old' → en_context: 'moshe lifespan'\n"
                "       '10 generations' → en_context: 'genealogy adam to noah'\n"
                "       'gematria of 358 for mashiach' → en_context: 'gematria of mashiach'.\n\n"
                
                "=== ENTITY PRIORITY RULES ===\n"
                "- If entity is both Person AND TribeOfIsrael → include in BOTH lists.\n"
                "- If entity is both Place AND Nation → include in BOTH lists.\n"
                "- If entity is both Food AND Plant (e.g., Apple) → include in BOTH lists with SAME name.\n"
                "- If entity is both Food AND Animal (e.g., Quail) → include in BOTH lists with SAME name.\n"
                "- If entity appears in Animal, Food, or Plant → do NOT include in Symbol.\n\n"
                
                "=== RELATIONSHIP TYPES ===\n"
                "Person ↔ Person:\n"
                "- studiedFrom: Sage transmitting teaching ('X said in name of Y', 'X said that Y said').\n"
                " A PERSON CAN ONLY STUDY FROM A SAGE; if Y is not a Sage, use spokeWith instead.\n"
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
                
                "Person → Place:\n"
                "- associatedWithPlace: Any significant connection between a Person and a Place\n"
                "  NOT covered by bornIn, diedIn, visited, or prayedAt. Use ONLY if no other Person→Place relationship applies.\n"
                "  Examples: 'Moses' → 'Mount Sinai' (if not visited).\n"
                "  NOT for Symbols or Nations - use other relationships for those.\n\n"

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
                "- prophesiedAbout: ONLY PROPHETS (not sages) making prophetic statements about any entity.\n"
                "  God, or angels, are not prophets. A prophet is only a person"
                
                "Any Entity ↔ Any Entity:\n"
                "- comparedTo: EXPLICIT simile/comparison ('like', 'as', 'resembles').\n"
                "- contrastedWith: EXPLICIT contrast or opposition.\n"
                "  NOTE: contrastedWith is for literary/symbolic contrasts, NOT for halakhic disagreements.\n"
                "  Use disagreedWith for disputes between persons, not contrastedWith.\n"
                "- AliasOf: Two names for the SAME entity. Only if text EXPLICITLY states they are the same, and it is LITERAL (not figurative).\n"
                "  Examples: 'Hadassa, who is Esther', 'Jacob, who is Israel'.\n"
                "  NOT for similar entities or comparisons - only explicit identity.\n\n"
                
                "=== OPTIMIZATION ===\n"
                "- Omit empty lists/objects entirely.\n"
                "- All relationship terms MUST use the EXACT SAME spelling as the extracted entity names.\n"
                "- Return only populated data."
        )

        self._google_provider: Optional[GoogleProvider] = None
        self._context_cache_name: Optional[str] = None
        output_type = FinalResponse

        if use_context_cache and ModelConfig.is_gemini_provider():
            try:
                self._google_provider = GoogleProvider()
                self._context_cache_name = self._create_context_cache()
                self._model_settings["google_cached_content"] = self._context_cache_name
                # `google_cached_content` strips `tools`/`tool_config`/`system_instruction` from
                # every request (the cache resource owns them) - FinalResponse's tool-based
                # output (pydantic-ai's default structured-output mode for Gemini) would
                # silently stop working, so switch to Gemini's native JSON-schema output mode,
                # which isn't affected, instead.
                output_type = NativeOutput(FinalResponse)
                logger.info(f"Gemini context cache active: {self._context_cache_name}")
            except Exception as e:
                logger.warning(f"Gemini context cache unavailable ({e}); falling back to uncached calls.")
                self._google_provider = None
                self._context_cache_name = None

        agent_kwargs = dict(
            model=model_str,
            output_type=output_type,
            model_settings=self._model_settings,
            retries=0,
        )
        if self._context_cache_name is None:
            # Not cached (non-Gemini provider, or cache creation failed) - send the system
            # prompt with every call, same as before this feature existed.
            agent_kwargs["system_prompt"] = self._system_prompt

        self.agent = Agent(**agent_kwargs)

    def _create_context_cache(self) -> str:
        """
        Creates (or recreates, e.g. after expiry mid-run - see `_extract`) the Gemini cache
        resource holding `self._system_prompt`, returning its resource name. Raises on
        failure; callers decide how to handle that (initial creation in __init__ falls back
        to uncached calls, a mid-run recreation in `_extract` surfaces the error after
        exhausting its own retry budget).
        """
        cache = self._google_provider.client.caches.create(
            model=self._model_name,
            config=CreateCachedContentConfig(
                system_instruction=self._system_prompt,
                ttl=f"{_CONTEXT_CACHE_TTL_SECONDS}s",
                display_name="entity_rel_graph_system_prompt",
            ),
        )
        return cache.name

    def close(self) -> None:
        """
        Deletes the Gemini context-cache resource (if any), so its storage isn't billed past
        the end of this run rather than waiting out its TTL. Safe to call even if no cache was
        ever created, or if it already expired/was already deleted.
        """
        if self._context_cache_name and self._google_provider:
            try:
                self._google_provider.client.caches.delete(name=self._context_cache_name)
                logger.info(f"Gemini context cache deleted: {self._context_cache_name}")
            except Exception as e:
                logger.warning(f"Failed to delete Gemini context cache {self._context_cache_name}: {e}")
            finally:
                self._context_cache_name = None

    async def _extract(self, passage: str):
        """
        Internal async call. Rate-limit/server errors (HTTP 429/500/503) are retried
        with exponential backoff - these are transient and cost nothing extra to retry.
        A 404 while a context cache is active means the cache resource expired or otherwise
        vanished mid-run (e.g. a run spanning longer than its TTL) - it's recreated and the
        call retried immediately, bounded by its own small attempt budget (separate from the
        rate-limit one above, since the failure mode and fix are different).
        ValidationError and any other error are NOT retried (single attempt), since
        retrying a bad output just burns tokens for the same mistake.
        """
        attempt = 0
        cache_refresh_attempts = 0
        while True:
            try:
                result = await self.agent.run(passage, model_settings=self._model_settings)
                return result
            except ValidationError as e:
                # Log validation error but don't retry
                print(f"Validation failed on first attempt: {e}")
                raise  # Re-raise to handle in calling code
            except ModelHTTPError as e:
                if (
                    self._context_cache_name
                    and e.status_code == _CONTEXT_CACHE_NOT_FOUND_STATUS
                    and cache_refresh_attempts < _CONTEXT_CACHE_MAX_REFRESH_ATTEMPTS
                ):
                    cache_refresh_attempts += 1
                    print(f"Gemini context cache {self._context_cache_name} not found (expired?); "
                          f"recreating (attempt {cache_refresh_attempts}/{_CONTEXT_CACHE_MAX_REFRESH_ATTEMPTS})...")
                    self._context_cache_name = self._create_context_cache()
                    self._model_settings["google_cached_content"] = self._context_cache_name
                    continue
                attempt += 1
                if e.status_code not in _RATE_LIMIT_RETRYABLE_STATUS_CODES or attempt >= _RATE_LIMIT_MAX_ATTEMPTS:
                    print(f"Extraction failed (HTTP {e.status_code}), giving up after {attempt} attempt(s): {e}")
                    raise
                delay = _RATE_LIMIT_BASE_DELAY_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 5)
                print(f"Rate/server limited (HTTP {e.status_code}), attempt {attempt}/{_RATE_LIMIT_MAX_ATTEMPTS}, "
                      f"retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            except Exception as e:
                # Any other error - don't retry
                print(f"Extraction failed: {e}")
                raise

    def _calculate_cost(self, usage: RunUsage) -> float:
        """
        Estimates cost in USD based on current provider's pricing. Tokens served from the
        Gemini context cache (usage.details['cached_content_tokens'], populated only when
        google_cached_content is active - see __init__) are billed at _CACHE_DISCOUNT_FACTOR
        of the standard input rate instead of the full rate.
        """
        pricing = ModelConfig.get_cost_per_million()

        cached_tokens = usage.details.get('cached_content_tokens', 0)
        standard_input_tokens = usage.input_tokens - cached_tokens

        input_cost = (standard_input_tokens / 1_000_000) * pricing["input"]
        cached_input_cost = (cached_tokens / 1_000_000) * pricing["input"] * _CACHE_DISCOUNT_FACTOR
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + cached_input_cost + output_cost

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

            usage = result.usage
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