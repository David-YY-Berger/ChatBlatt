# bs"d
"""
EntityEnrichmentCaller - Extracts entity-attribute enrichments from passages using LLMs.

Given a passage (containing BOTH the clean English text AND the clean Hebrew text,
without vowels/niqqud, of the same source) plus a list of DB entities associated with
that passage that have not yet been enriched, asks the LLM to fill in the fields the
DB layer could not derive on its own:

  - ALL entity types : display_heb_name — normalized, vowel-less Hebrew display name,
                        taken almost verbatim from the Hebrew text in the passage.
  - Person            : timePeriod, isWoman, isNonJew, isGroup, roles.
  - Number            : heb_unit, contexts[].heb_context — vowel-less Hebrew, same word
                        order/direction as the corresponding English en_unit / en_context.
  - Place             : placeType.
  - Symbol            : symbolType.

Enum-typed fields (timePeriod, roles, placeType, symbolType) are validated against
their Python Enum definitions (backend.models_db.Enums); unrecognized values are
dropped (and logged) rather than failing the whole response — the same approach used
by DBPopulateEntityRelGraph._parse_passage_types.

Usage:
    caller = EntityEnrichmentCaller()
    json_str, usage, cost = await caller.extract_from_passage(passage, entity_json_list)
"""

import logging
from typing import List, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_ai import Agent, ModelSettings, NativeOutput
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import RunUsage
from google.genai.types import CreateCachedContentConfig

from backend.models_db.Enums import PlaceType, RoleType, SymbolType, TimePeriod
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig

logger = logging.getLogger(__name__)

# Gemini explicit context caching - see control_docs/pipeline/llm_context_caching.md for the
# mechanism (shared with EntityRelGraphCaller). Unlike that caller, a cache-expiry 404 here is
# NOT recreated/retried mid-call - consistent with this class's existing "no retries" design
# (see module docstring): it just becomes one failed source via extract_from_passage's
# existing try/except, picked up by the usual failed-keys/REMINDER flow (DBPopulateLlmBase),
# and resolved by re-running - which builds a fresh instance and a fresh cache.
_CONTEXT_CACHE_TTL_SECONDS = 3600  # 1 hour
_CACHE_DISCOUNT_FACTOR = 0.1  # see EntityRelGraphCaller._calculate_cost for the rationale

_ROLE_VALUES = [r.value for r in RoleType]
_TIME_PERIOD_VALUES = [t.value for t in TimePeriod]
_PLACE_TYPE_VALUES = [p.value for p in PlaceType]
_SYMBOL_TYPE_VALUES = [s.value for s in SymbolType]

# Legal type-specific fields per entityType; unlisted types get none.
_TYPE_SPECIFIC_FIELDS_BY_ENTITY_TYPE = {
    "Person": {"timePeriod", "isWoman", "isNonJew", "isGroup", "roles"},
    "Number": {"heb_unit", "contexts"},
    "Place": {"placeType"},
    "Symbol": {"symbolType"},
}
_ALL_TYPE_SPECIFIC_FIELDS = set().union(*_TYPE_SPECIFIC_FIELDS_BY_ENTITY_TYPE.values())


def _match_enum_value(raw: Optional[str], enum_cls, field_name: str) -> Optional[str]:
    """
    Validate *raw* against enum_cls's values (exact match, then case-insensitive).
    Returns the canonical enum value string, or None (after logging a warning)
    if it doesn't match any member — mirrors the filtering approach used in
    DBPopulateEntityRelGraph._parse_passage_types.
    """
    if raw is None:
        return None
    for member in enum_cls:
        if member.value == raw:
            return raw
    for member in enum_cls:
        if member.value.lower() == raw.lower():
            return member.value
    logger.warning(f"Unknown {field_name} '{raw}' received from LLM — dropping.")
    print(f"  WARNING: Unknown {field_name} '{raw}' received from LLM, dropping.")
    return None


# ─── Pydantic output models ───────────────────────────────────────────────────

class NumberContextEnrichment(BaseModel):
    """Hebrew translation of one of a Number entity's existing contexts."""

    en_context: str = Field(
        min_length=1,
        description="Exact 'en_context' value copied from one of the input Number entity's 'contexts'.",
    )
    heb_context: str = Field(
        min_length=1,
        description=(
            "Hebrew translation of that en_context — no niqqud, same word order/direction "
            "as the English context."
        ),
    )


class EntityEnrichment(BaseModel):
    """
    Enrichment fields for a single entity extracted from a passage.

    `key` MUST exactly match the `key` field of one of the input entities (from
    entity_json_list) so results can be matched back to the correct DB entity.
    Only the fields relevant to that entity's entityType should be filled in;
    all others should be left unset/None.
    """

    key: str = Field(
        min_length=1,
        description="Exact 'key' value copied from the corresponding input entity JSON.",
    )

    entityType: str = Field(
        description="Exact 'entityType' value copied from the corresponding input entity JSON.",
    )

    display_heb_name: Optional[str] = Field(
        default=None,
        description=(
            "ALL entity types EXCEPT Number. The normalized Hebrew display name for this "
            "entity, taken almost verbatim from the Hebrew text of the passage. "
            "Must NOT contain niqqud (vowel points). Number entities must NEVER receive a "
            "display_heb_name — leave this unset for them (use heb_unit/contexts instead)."
        ),
    )

    # --- Person-only fields ---
    timePeriod: Optional[str] = Field(
        default=None,
        description=f"Person only. One of: {', '.join(_TIME_PERIOD_VALUES)}. Omit if unclear.",
    )
    isWoman: Optional[bool] = Field(
        default=None, description="Person only. True if the person is clearly female."
    )
    isNonJew: Optional[bool] = Field(
        default=None,
        description=(
            "Person only. True if the person is explicitly non-Jewish. Every forefather of "
            "the Jewish people — from Abraham onward (Abraham, Isaac, Jacob, and Jacob's "
            "children/the twelve tribes, or any of their wives/Matriarchs (Sara, Rebecca, etc.) — must be considered Jewish (isNonJew=False), "
            "even though they lived before the giving of the Torah."
        ),
    )
    isGroup: Optional[bool] = Field(
        default=None, description="Person only. True if the name refers to a group rather than an individual."
    )
    roles: Optional[List[str]] = Field(
        default=None,
        description=f"Person only. Each item one of: {', '.join(_ROLE_VALUES)}. Omit if none clearly apply.",
    )

    # --- Number-only fields ---
    heb_unit: Optional[str] = Field(
        default=None,
        description=(
            "Number only. Hebrew translation of the entity's existing en_unit — "
            "normalized, singular, no niqqud, same word order/direction as the English unit."
        ),
    )
    contexts: Optional[List[NumberContextEnrichment]] = Field(
        default=None,
        description=(
            "Number only. One entry per item of the entity's existing 'contexts' list that has "
            "no heb_context yet: its en_context (copied exactly) and its Hebrew translation."
        ),
    )

    # --- Place-only field ---
    placeType: Optional[str] = Field(
        default=None,
        description=f"Place only. One of: {', '.join(_PLACE_TYPE_VALUES)}.",
    )

    # --- Symbol-only field ---
    symbolType: Optional[str] = Field(
        default=None,
        description=f"Symbol only. One of: {', '.join(_SYMBOL_TYPE_VALUES)}.",
    )

    @field_validator("timePeriod", mode="after")
    @classmethod
    def _validate_time_period(cls, v: Optional[str]) -> Optional[str]:
        return _match_enum_value(v, TimePeriod, "timePeriod")

    @field_validator("placeType", mode="after")
    @classmethod
    def _validate_place_type(cls, v: Optional[str]) -> Optional[str]:
        return _match_enum_value(v, PlaceType, "placeType")

    @field_validator("symbolType", mode="after")
    @classmethod
    def _validate_symbol_type(cls, v: Optional[str]) -> Optional[str]:
        return _match_enum_value(v, SymbolType, "symbolType")

    @field_validator("roles", mode="after")
    @classmethod
    def _validate_roles(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if not v:
            return v
        filtered = [
            matched
            for matched in (_match_enum_value(role, RoleType, "roles") for role in v)
            if matched is not None
        ]
        return filtered or None

    @model_validator(mode="after")
    def _drop_fields_not_valid_for_entity_type(self) -> "EntityEnrichment":
        """
        Guard against the LLM attaching another entityType's fields to this entity
        (e.g. setting placeType on a 'Nation' entity just because it shares a name
        with a 'Place' entity, as with "Shinar"). Any type-specific field not valid
        for self.entityType is forced back to None/empty, with a warning logged.
        """
        allowed_fields = _TYPE_SPECIFIC_FIELDS_BY_ENTITY_TYPE.get(self.entityType, set())
        for field_name in _ALL_TYPE_SPECIFIC_FIELDS - allowed_fields:
            if getattr(self, field_name, None) not in (None, []):
                logger.warning(
                    f"Entity '{self.key}' has entityType '{self.entityType}' but the LLM set "
                    f"'{field_name}' (only valid for {', '.join(sorted(t for t, fs in _TYPE_SPECIFIC_FIELDS_BY_ENTITY_TYPE.items() if field_name in fs))}) — dropping."
                )
                print(f"  WARNING: entity '{self.key}' ({self.entityType}) had invalid field '{field_name}' dropped.")
                setattr(self, field_name, None)
        return self


class EnrichmentResponse(BaseModel):
    """Top-level output type returned by the LLM for entity enrichment."""

    entities: Optional[List[EntityEnrichment]] = Field(
        default=None,
        description="One entry per input entity that could be enriched from the passage.",
    )


# ─── Caller ───────────────────────────────────────────────────────────────────

class EntityEnrichmentCaller:
    """
    Extracts entity-attribute enrichments from text passages using an LLM.

    Uses ModelConfig to determine which provider to use.
    Single call per passage — no retries.
    """

    def __init__(self, use_context_cache: bool = True):
        """
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
        logger.info(f"Initializing EntityEnrichmentCaller with model: {model_str}, thinking={is_thinking}")

        if is_thinking:
            self._model_settings = ModelSettings(
                temperature=0.3,
                extra_body={"thinkingConfig": {"thinkingBudget": 4096}},
            )
        else:
            self._model_settings = ModelSettings(temperature=0.3)

        self._system_prompt = (
                "You will receive a PASSAGE and a JSON list of ENTITIES that need enrichment.\n"
                "Your job is to fill in additional fields for those entities using ONLY "
                "information present in the passage — never invent facts.\n\n"

                "=== INPUT FORMAT ===\n"
                "- The passage contains the English text of a source followed by its Hebrew "
                "text (the Hebrew has no niqqud/vowel points).\n"
                "- The entities are a JSON array; each entity has at least 'key', "
                "'display_en_name', and 'entityType' (one of: Person, Number, Place, Symbol, "
                "and possibly other types that need no enrichment here).\n\n"

                "=== OUTPUT FORMAT ===\n"
                "Return one entry per entity you can enrich, with 'key' AND 'entityType' both "
                "copied EXACTLY from the matching input entity. Only set fields relevant to "
                "that entity's OWN entityType; never set a field belonging to a different "
                "entityType.\n\n"

                "=== FOR EVERY ENTITY EXCEPT entityType == 'Number' ===\n"
                "- display_heb_name: the Hebrew name for this entity, taken almost verbatim "
                "from the Hebrew text in the passage (correct for grammatical prefixes like "
                "ה/ו/ב/ל/מ only if they are not part of the proper name). NEVER include niqqud "
                "(vowel points) — strip all vowel diacritics.\n"
                "- NEVER set display_heb_name for an entity whose entityType is 'Number' — "
                "numbers have no Hebrew display name; use heb_unit/contexts for them instead.\n\n"

                "=== IF entityType == 'Person' ===\n"
                f"- timePeriod: one of: {', '.join(_TIME_PERIOD_VALUES)}.\n"
                "    Tanach = biblical period; Tanaim = Mishnaic sages (≈10–220 CE); "
                "Amoraim = Talmudic sages (≈220–500 CE). Omit if genuinely uncertain.\n"
                "- isWoman: true only if the person is clearly female.\n"
                "- isNonJew: true only if the person is explicitly non-Jewish. Every forefather "
                "of the Jewish people, from Abraham and on (Abraham, Isaac, Jacob, Jacob's "
                "children/the twelve tribes, and their descendants), must be treated as Jewish "
                "(isNonJew=false) even though this precedes the giving of the Torah. If not clear, omit the field.\n"
                "- isGroup: true only if the name refers to a group (e.g. 'Children of Israel', "
                "'The Sanhedrin').\n"
                f"- roles: applicable roles from: {', '.join(_ROLE_VALUES)}. "
                "Only include roles clearly evidenced in the passage.\n\n"

                "=== IF entityType == 'Number' ===\n"
                "- heb_unit: Hebrew translation of the entity's existing 'en_unit' value — "
                "a normalized singular noun, no niqqud, written in the SAME word order/direction "
                "as the English unit (do not reverse word order just because Hebrew is RTL).\n"
                "- contexts: the entity has a 'contexts' list; for EACH item that has no "
                "'heb_context' yet, return {en_context, heb_context}: 'en_context' copied EXACTLY "
                "from that item, and 'heb_context' its Hebrew translation — no niqqud, same word "
                "order/direction as the English context.\n\n"

                "=== IF entityType == 'Place' ===\n"
                f"- placeType: one of: {', '.join(_PLACE_TYPE_VALUES)}.\n\n"

                "=== IF entityType == 'Symbol' ===\n"
                f"- symbolType: one of: {', '.join(_SYMBOL_TYPE_VALUES)}.\n\n"

                "=== ANY OTHER entityType ===\n"
                "- Only display_heb_name applies; no other field.\n\n"

                "=== RULES ===\n"
                "- Only enrich entities that appear in the ENTITIES list you were given.\n"
                "- Omit fields that are unclear or not evidenced by the passage — do not guess.\n"
                "- Omit empty lists entirely.\n"
                "- If nothing can be determined for an entity, omit it from the response.\n"
                "- If no entities can be enriched at all, return an empty response."
        )

        self._google_provider: Optional[GoogleProvider] = None
        self._context_cache_name: Optional[str] = None
        output_type = EnrichmentResponse

        if use_context_cache and ModelConfig.is_gemini_provider():
            try:
                self._google_provider = GoogleProvider()
                self._context_cache_name = self._create_context_cache()
                self._model_settings["google_cached_content"] = self._context_cache_name
                # `google_cached_content` strips `tools`/`tool_config`/`system_instruction` from
                # every request (the cache resource owns them) - EnrichmentResponse's tool-based
                # output (pydantic-ai's default structured-output mode for Gemini) would
                # silently stop working, so switch to Gemini's native JSON-schema output mode,
                # which isn't affected, instead.
                output_type = NativeOutput(EnrichmentResponse)
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
        Creates the Gemini cache resource holding `self._system_prompt`, returning its
        resource name. Raises on failure - __init__ falls back to uncached calls.

        Unlike EntityRelGraphCaller, a mid-run cache expiry here is NOT recreated/retried -
        see the module-level note above for why a plain failed-source + re-run is enough.
        """
        cache = self._google_provider.client.caches.create(
            model=self._model_name,
            config=CreateCachedContentConfig(
                system_instruction=self._system_prompt,
                ttl=f"{_CONTEXT_CACHE_TTL_SECONDS}s",
                display_name="entity_enrichment_system_prompt",
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

    async def extract_from_passage(
        self, passage: str, entity_json_list: Optional[List[str]] = None
    ) -> Tuple[str, RunUsage, float]:
        """
        Extract enrichment data from a passage for the given entities.

        Args:
            passage: Combined clean English + clean Hebrew (no vowels) text of the source.
            entity_json_list: Optional list of JSON strings, one per DB entity associated
                with this passage that has not yet been enriched with metadata.

        Returns:
            (json_str, usage, cost_usd)

        Raises:
            Exception: For any error during extraction (no retries).
        """
        user_prompt = self._build_user_prompt(passage, entity_json_list)
        try:
            result = await self.agent.run(user_prompt, model_settings=self._model_settings)

            json_str = result.output.model_dump_json(
                indent=2,
                exclude_unset=True,
                exclude_none=True,
            )

            usage = result.usage
            cost = self._calculate_cost(usage)
            return json_str, usage, cost

        except Exception as e:
            logger.error(f"Enrichment extraction failed: {e}")
            raise

    @staticmethod
    def _build_user_prompt(passage: str, entity_json_list: Optional[List[str]]) -> str:
        """Combine the passage and the entities-to-enrich into a single user prompt."""
        entities_block = "[]"
        if entity_json_list:
            entities_block = "[\n" + ",\n".join(entity_json_list) + "\n]"

        return (
            "=== PASSAGE (English + Hebrew) ===\n"
            f"{passage}\n\n"
            "=== ENTITIES TO ENRICH (JSON) ===\n"
            f"{entities_block}\n"
        )

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
