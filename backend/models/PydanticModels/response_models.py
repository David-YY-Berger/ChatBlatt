import logging
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.models.PydanticModels.entity_models import Entities
from backend.models.PydanticModels.pydantic_constants import (
    PERSON_PLACE_SPECIFIC_RELATIONSHIPS,
    SYMMETRIC_RELATIONSHIPS,
    max_len_summary,
    min_len_summary,
)
from backend.models.PydanticModels.relationship_models import Relationships

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    en_summary: str = Field(
        min_length=1,
        description=f"Summary in exactly {min_len_summary}-{max_len_summary} words",
    )
    heb_summary: str = Field(
        min_length=1,
        description=f"Hebrew summary in exactly {min_len_summary}-{max_len_summary} words",
    )
    passage_types: List[Literal["LAW", "STORY", "PHILOSOPHIC", "GENEALOGY", "PROPHECY"]] = Field(
        min_length=1,
        description="At least one passage type required",
    )
    Entities: Entities
    Rel: Optional[Relationships] = Field(default_factory=Relationships)

    @field_validator("en_summary", "heb_summary")
    @classmethod
    def validate_word_count(cls, v: str, info) -> str:
        """Ensure summary is mix_len_summary - max_len_summary words. Reject if out of range."""
        words = v.strip().split()
        word_count = len(words)

        if word_count < min_len_summary:
            raise ValueError(
                f"{info.field_name} must be {min_len_summary}-{max_len_summary} words, got {word_count}: '{v}'. "
                f"Model should generate complete summaries within word limit."
            )

        if word_count > max_len_summary:
            raise ValueError(
                f"{info.field_name} must be {min_len_summary}-{max_len_summary}, got {word_count}: '{v}'. "
                f"Model should generate complete summaries within word limit."
            )

        return v.strip()

    @field_validator("passage_types")
    @classmethod
    def validate_unique_passage_types(cls, v: List[str]) -> List[str]:
        """Remove duplicate passage types."""
        unique = list(dict.fromkeys(v))
        if len(unique) < len(v):
            logger.warning(f"Removed duplicate passage types: {v} -> {unique}")
        return unique

    @model_validator(mode="after")
    def filter_invalid_relationships(self):
        """Filter out invalid relationships instead of raising errors."""
        if not self.Rel:
            return self

        all_entities = self.Entities.get_all_entity_names()

        if not all_entities:
            return self

        relationship_constraints = {
            "studiedFrom": ("Person", "Person"),
            "childOfFather": ("Person", "Person"),
            "childOfMother": ("Person", "Person"),
            "spouseOf": ("Person", "Person"),
            "descendantOf": ("Person", "Person"),
            "spokeWith": [("Person", "Person"), ("Animal", "Person"), ("Person", "Animal"), ("Animal", "Animal")],
            "disagreedWith": ("Person", "Person"),
            "bornIn": ("Person", "Place"),
            "diedIn": ("Person", "Place"),
            "visited": ("Person", "Place"),
            "prayedAt": ("Person", "Place"),
            "associatedWithPlace": ("Person", "Place"),
            "personToTribeOfIsrael": ("Person", "TribeOfIsrael"),
            "personBelongsToNation": ("Person", "Nation"),
            "EnemyOf": [("Nation", "Nation"), ("Person", "Person"), ("Person", "Nation")],
            "AllyOf": [("Nation", "Nation"), ("Person", "Person"), ("Person", "Nation")],
            "placeToNation": ("Place", "Nation"),
            "prophesiedAbout": ("Person", None),
            "comparedTo": (None, None),
            "contrastedWith": (None, None),
            "AliasOf": (None, None),
        }

        invalid_count = 0
        corrected_count = 0

        for rel_type, type_constraint in relationship_constraints.items():
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            if isinstance(type_constraint, list):
                allowed_pairs = type_constraint
            else:
                allowed_pairs = [type_constraint]

            valid_relations = []

            for rel in relations:
                is_valid = True
                reason = None

                corrected_term1 = self.Entities.find_matching_entity(rel.term1)
                corrected_term2 = self.Entities.find_matching_entity(rel.term2)

                if corrected_term1 and corrected_term1 != rel.term1:
                    logger.info(f"Auto-corrected relationship term: '{rel.term1}' -> '{corrected_term1}'")
                    rel.term1 = corrected_term1
                    corrected_count += 1
                if corrected_term2 and corrected_term2 != rel.term2:
                    logger.info(f"Auto-corrected relationship term: '{rel.term2}' -> '{corrected_term2}'")
                    rel.term2 = corrected_term2
                    corrected_count += 1

                if rel.term1 == rel.term2:
                    is_valid = False
                    reason = f"Self-relationship: {rel.term1}"
                elif corrected_term1 is None:
                    is_valid = False
                    reason = f"term1 '{rel.term1}' not in entities"
                elif corrected_term2 is None:
                    is_valid = False
                    reason = f"term2 '{rel.term2}' not in entities"
                else:
                    matched = False
                    for (term1_type, term2_type) in allowed_pairs:
                        term1_ok = term1_type is None or rel.term1 in self.Entities.get_entities_by_type(term1_type)
                        term2_ok = term2_type is None or rel.term2 in self.Entities.get_entities_by_type(term2_type)
                        if term1_ok and term2_ok:
                            matched = True
                            break

                    if not matched:
                        is_valid = False
                        allowed_str = " or ".join(f"({t1 or 'Any'} -> {t2 or 'Any'})" for t1, t2 in allowed_pairs)
                        reason = (
                            f"'{rel.term1}' -> '{rel.term2}' does not match "
                            f"any allowed type pair: {allowed_str}"
                        )

                if is_valid:
                    valid_relations.append(rel)
                else:
                    invalid_count += 1
                    logger.warning(
                        f"Filtered invalid '{rel_type}' relationship: "
                        f"{rel.term1} -> {rel.term2} ({reason})"
                    )

            setattr(self.Rel, rel_type, valid_relations if valid_relations else None)

        if corrected_count > 0:
            logger.info(f"Auto-corrected {corrected_count} relationship terms to match entity names")
        if invalid_count > 0:
            logger.info(f"Filtered out {invalid_count} invalid relationships")

        for rel_type in relationship_constraints.keys():
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            seen = set()
            unique = []
            for rel in relations:
                key = (rel.term1, rel.term2)
                if key not in seen:
                    unique.append(rel)
                    seen.add(key)

            setattr(self.Rel, rel_type, unique if unique else None)

        return self

    @model_validator(mode="after")
    def deduplicate_symmetric_relationships(self):
        """Deduplicate symmetric relationships (A<->B = B<->A), keeping only one canonical form."""
        if not self.Rel:
            return self

        for rel_type in SYMMETRIC_RELATIONSHIPS:
            relations = getattr(self.Rel, rel_type, None)
            if not relations:
                continue

            seen_pairs = set()
            unique_relations = []

            for rel in relations:
                pair = tuple(sorted([rel.term1, rel.term2]))
                if pair not in seen_pairs:
                    unique_relations.append(rel)
                    seen_pairs.add(pair)
                else:
                    logger.debug(f"Deduplicated {rel_type} pair: {rel.term1} <-> {rel.term2}")

            setattr(self.Rel, rel_type, unique_relations if unique_relations else None)

        return self

    @model_validator(mode="after")
    def clean_descendant_logic(self):
        """Removes descendantOf links that are already defined as childOfFather or childOfMother."""
        if not self.Rel or not self.Rel.descendantOf:
            return self

        has_father_rels = self.Rel.childOfFather and len(self.Rel.childOfFather) > 0
        has_mother_rels = self.Rel.childOfMother and len(self.Rel.childOfMother) > 0

        if not has_father_rels and not has_mother_rels:
            return self

        direct_parents = set()
        if self.Rel.childOfFather:
            direct_parents.update((rel.term1, rel.term2) for rel in self.Rel.childOfFather)
        if self.Rel.childOfMother:
            direct_parents.update((rel.term1, rel.term2) for rel in self.Rel.childOfMother)

        original_count = len(self.Rel.descendantOf)
        self.Rel.descendantOf = [rel for rel in self.Rel.descendantOf if (rel.term1, rel.term2) not in direct_parents]

        if len(self.Rel.descendantOf) < original_count:
            logger.info("Removed redundant descendantOf links duplicated in childOfFather/childOfMother.")

        return self

    @model_validator(mode="after")
    def clean_spokewith_disagreedwith_overlap(self):
        """Removes disagreedWith links that overlap with spokeWith - a pair cannot be in both."""
        if not self.Rel or not self.Rel.spokeWith or not self.Rel.disagreedWith:
            return self

        spokewith_pairs = set()
        for rel in self.Rel.spokeWith:
            spokewith_pairs.add((rel.term1, rel.term2))
            spokewith_pairs.add((rel.term2, rel.term1))

        original_count = len(self.Rel.disagreedWith)
        self.Rel.disagreedWith = [rel for rel in self.Rel.disagreedWith if (rel.term1, rel.term2) not in spokewith_pairs]

        removed_count = original_count - len(self.Rel.disagreedWith)
        if removed_count > 0:
            logger.info(f"Removed {removed_count} disagreedWith links that overlap with spokeWith.")

        if not self.Rel.disagreedWith:
            self.Rel.disagreedWith = None

        return self

    @model_validator(mode="after")
    def clean_associated_with_place_logic(self):
        """Removes associatedWithPlace links that are already covered by specific Person->Place relationships."""
        if not self.Rel or not self.Rel.associatedWithPlace:
            return self

        covered_pairs = set()

        for rel_type in PERSON_PLACE_SPECIFIC_RELATIONSHIPS:
            relations = getattr(self.Rel, rel_type, None)
            if relations:
                covered_pairs.update((rel.term1, rel.term2) for rel in relations)

        original_count = len(self.Rel.associatedWithPlace)
        self.Rel.associatedWithPlace = [
            rel for rel in self.Rel.associatedWithPlace if (rel.term1, rel.term2) not in covered_pairs
        ]

        removed_count = original_count - len(self.Rel.associatedWithPlace)
        if removed_count > 0:
            rel_types_str = "/".join(PERSON_PLACE_SPECIFIC_RELATIONSHIPS)
            logger.info(
                f"Removed {removed_count} redundant associatedWithPlace links already covered by {rel_types_str}."
            )

        if not self.Rel.associatedWithPlace:
            self.Rel.associatedWithPlace = None

        return self


class FinalResponse(BaseModel):
    res: ExtractionResult


__all__ = ["ExtractionResult", "FinalResponse"]

