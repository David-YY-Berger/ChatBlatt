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
  - Number            : heb_unit, heb_context — vowel-less Hebrew, same word order/
                        direction as the corresponding English en_unit / en_context.
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

from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent, ModelSettings
from pydantic_ai.usage import RunUsage

from backend.models_db.Enums import PlaceType, RoleType, SymbolType, TimePeriod
from backend_pipeline.data_pipeline.llm_api.ModelConfig import ModelConfig

logger = logging.getLogger(__name__)

_ROLE_VALUES = [r.value for r in RoleType]
_TIME_PERIOD_VALUES = [t.value for t in TimePeriod]
_PLACE_TYPE_VALUES = [p.value for p in PlaceType]
_SYMBOL_TYPE_VALUES = [s.value for s in SymbolType]


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

    display_heb_name: Optional[str] = Field(
        default=None,
        description=(
            "ALL entity types. The normalized Hebrew display name for this entity, "
            "taken almost verbatim from the Hebrew text of the passage. "
            "Must NOT contain niqqud (vowel points)."
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
        default=None, description="Person only. True if the person is explicitly non-Jewish."
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
    heb_context: Optional[str] = Field(
        default=None,
        description=(
            "Number only. Hebrew translation of the entity's existing en_context — "
            "no niqqud, same word order/direction as the English context."
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

    def __init__(self):
        ModelConfig.ensure_api_key_in_env()

        model_str = ModelConfig.get_pydantic_model()
        is_thinking = ModelConfig.is_thinking_enabled()
        logger.info(f"Initializing EntityEnrichmentCaller with model: {model_str}, thinking={is_thinking}")

        if is_thinking:
            settings = ModelSettings(
                temperature=0.3,
                extra_body={"thinkingConfig": {"thinkingBudget": 4096}},
            )
        else:
            settings = ModelSettings(temperature=0.3)

        self.agent = Agent(
            model=model_str,
            output_type=EnrichmentResponse,
            model_settings=settings,
            system_prompt=(
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
                "Return one entry per entity you can enrich, with 'key' copied EXACTLY "
                "(same string) from the matching input entity. Only set the fields relevant "
                "to that entity's entityType; leave every other field unset.\n\n"

                "=== FOR EVERY ENTITY (any entityType) ===\n"
                "- display_heb_name: the Hebrew name for this entity, taken almost verbatim "
                "from the Hebrew text in the passage (correct for grammatical prefixes like "
                "ה/ו/ב/ל/מ only if they are not part of the proper name). NEVER include niqqud "
                "(vowel points) — strip all vowel diacritics.\n\n"

                "=== IF entityType == 'Person' ===\n"
                f"- timePeriod: one of: {', '.join(_TIME_PERIOD_VALUES)}.\n"
                "    Tanach = biblical period; Tanaim = Mishnaic sages (≈10–220 CE); "
                "Amoraim = Talmudic sages (≈220–500 CE). Omit if genuinely uncertain.\n"
                "- isWoman: true only if the person is clearly female.\n"
                "- isNonJew: true only if the person is explicitly non-Jewish.\n"
                "- isGroup: true only if the name refers to a group (e.g. 'Children of Israel', "
                "'The Sanhedrin').\n"
                f"- roles: applicable roles from: {', '.join(_ROLE_VALUES)}. "
                "Only include roles clearly evidenced in the passage.\n\n"

                "=== IF entityType == 'Number' ===\n"
                "- heb_unit: Hebrew translation of the entity's existing 'en_unit' value — "
                "a normalized singular noun, no niqqud, written in the SAME word order/direction "
                "as the English unit (do not reverse word order just because Hebrew is RTL).\n"
                "- heb_context: Hebrew translation of the entity's existing 'en_context' value — "
                "no niqqud, same word order/direction as the English context.\n\n"

                "=== IF entityType == 'Place' ===\n"
                f"- placeType: one of: {', '.join(_PLACE_TYPE_VALUES)}.\n\n"

                "=== IF entityType == 'Symbol' ===\n"
                f"- symbolType: one of: {', '.join(_SYMBOL_TYPE_VALUES)}.\n\n"

                "=== RULES ===\n"
                "- Only enrich entities that appear in the ENTITIES list you were given.\n"
                "- Omit fields that are unclear or not evidenced by the passage — do not guess.\n"
                "- Omit empty lists entirely.\n"
                "- If nothing can be determined for an entity, omit it from the response.\n"
                "- If no entities can be enriched at all, return an empty response."
            ),
            retries=0,
        )

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
            result = await self.agent.run(user_prompt)

            json_str = result.output.model_dump_json(
                indent=2,
                exclude_unset=True,
                exclude_none=True,
            )

            usage = result.usage()
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
        pricing = ModelConfig.get_cost_per_million()
        input_cost = (usage.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
