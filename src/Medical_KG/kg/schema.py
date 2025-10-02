from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class Constraint:
    statement: str
    description: str


@dataclass(slots=True)
class Index:
    statement: str
    description: str


@dataclass(slots=True)
class CDKOSchema:
    constraints: List[Constraint] = field(default_factory=list)
    indexes: List[Index] = field(default_factory=list)

    @classmethod
    def default(cls) -> "CDKOSchema":
        constraints = [
            Constraint("CREATE CONSTRAINT doc_uri_unique IF NOT EXISTS FOR (d:Document) REQUIRE d.uri IS UNIQUE", "Unique document URIs"),
            Constraint("CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE", "Chunk id uniqueness"),
            Constraint("CREATE CONSTRAINT study_nct_unique IF NOT EXISTS FOR (s:Study) REQUIRE s.nct_id IS UNIQUE", "Study id uniqueness"),
            Constraint("CREATE CONSTRAINT drug_rxcui_unique IF NOT EXISTS FOR (d:Drug) REQUIRE d.rxcui IS UNIQUE", "Drug RxCUI uniqueness"),
            Constraint("CREATE CONSTRAINT device_udi_unique IF NOT EXISTS FOR (x:Device) REQUIRE x.udi_di IS UNIQUE", "Device UDI uniqueness"),
        ]
        indexes = [
            Index("CREATE VECTOR INDEX chunk_qwen_idx IF NOT EXISTS FOR (c:Chunk) ON (c.embedding_qwen) OPTIONS {indexConfig: {`vector.dimensions`: 4096, `vector.similarity_function`: 'cosine'}}", "Chunk embedding vector index"),
            Index("CREATE FULLTEXT INDEX chunk_text_ft IF NOT EXISTS FOR (n:Chunk) ON EACH [n.text] OPTIONS {analyzer: 'english'}", "Chunk full text index"),
        ]
        return cls(constraints=constraints, indexes=indexes)

    def as_statements(self) -> Dict[str, List[str]]:
        return {
            "constraints": [c.statement for c in self.constraints],
            "indexes": [i.statement for i in self.indexes],
        }
