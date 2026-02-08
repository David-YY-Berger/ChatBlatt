# from dataclasses import dataclass, field
# from typing import List, Dict, Union
#
# from BackEnd.DataObjects.EntityObjects.EPerson import EPerson
# from BackEnd.DataObjects.EntityObjects.EPlace import EPlace
# from BackEnd.DataObjects.EntityObjects.ETribeOfIsrael import ETribeOfIsrael
# from BackEnd.DataObjects.EntityObjects.ENation import ENation
# from BackEnd.DataObjects.EntityObjects.ESymbol import ESymbol
# from BackEnd.DataObjects.Enums import PassageType, EntityType, RelType
# from BackEnd.DataObjects.Rel import Rel
#
#
# @dataclass
# class AnalyzedSourceResponse:
#     summary_en: str
#     summary_heb: str
#     e_passage_types: List[PassageType] = field(default_factory=list)
#
#     # Entities stored as a map
#     entities: Dict[EntityType, List[Union[EPerson, EPlace, ETribeOfIsrael, ENation, ESymbol]]] = field(
#         default_factory=lambda: {
#             EntityType.EPerson: [],
#             EntityType.EPlace: [],
#             EntityType.ETribeOfIsrael: [],
#             EntityType.ENation: [],
#             EntityType.ESymbol: [],
#         }
#     )
#
#     # Relationships stored as a map by RelType
#     relationships: Dict[RelType, List[Rel]] = field(
#         default_factory=lambda: {rel_type: [] for rel_type in RelType}
#     )
#
#     # Helper methods for adding entities
#     def add_person(self, person: EPerson) -> None:
#         """Add a person entity."""
#         self.entities[EntityType.EPerson].append(person)
#
#     def add_place(self, place: EPlace) -> None:
#         """Add a place entity."""
#         self.entities[EntityType.EPlace].append(place)
#
#     def add_tribe_of_israel(self, tribe: ETribeOfIsrael) -> None:
#         """Add a tribe entity."""
#         self.entities[EntityType.ETribeOfIsrael].append(tribe)
#
#     def add_nation(self, nation: ENation) -> None:
#         """Add a nation entity."""
#         self.entities[EntityType.ENation].append(nation)
#
#     def add_symbol(self, symbol: ESymbol) -> None:
#         """Add a symbol entity."""
#         self.entities[EntityType.ESymbol].append(symbol)
#
#     # Helper method for adding relationships
#     def add_relationship(self, rel: Rel) -> None:
#         """Add a relationship to the appropriate RelType bucket."""
#         self.relationships[rel.rel_type].append(rel)
#
#     # Convenience getters
#     def get_persons(self) -> List[EPerson]:
#         """Get all person entities."""
#         return self.entities[EntityType.EPerson]
#
#     def get_places(self) -> List[EPlace]:
#         """Get all place entities."""
#         return self.entities[EntityType.EPlace]
#
#     def get_tribeOfIsraels(self) -> List[ETribeOfIsrael]:
#         """Get all tribe entities."""
#         return self.entities[EntityType.ETribeOfIsrael]
#
#     def get_nations(self) -> List[ENation]:
#         """Get all nation entities."""
#         return self.entities[EntityType.ENation]
#
#     def get_symbols(self) -> List[ESymbol]:
#         """Get all symbol entities."""
#         return self.entities[EntityType.ESymbol]
#
#     def get_relationships_by_type(self, rel_type: RelType) -> List[Rel]:
#         """Get all relationships of a specific type."""
#         return self.relationships[rel_type]
#
#     def get_all_relationships(self) -> List[Rel]:
#         """Get all relationships as a flat list."""
#         all_rels = []
#         for rels in self.relationships.values():
#             all_rels.extend(rels)
#         return all_rels
#
#     def get_entity_map(self) -> Dict[EntityType, List]:
#         """
#         Returns a dictionary mapping EntityType to the corresponding entity lists.
#         """
#         return self.entities