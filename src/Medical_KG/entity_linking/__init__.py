"""Entity linking package."""

from .candidates import Candidate, CandidateGenerator, DenseClient, DictionaryClient, SparseClient
from .decision import DecisionEngine, LinkingDecision
from .detectors import DeterministicDetectors, IdentifierCandidate
from .llm import AdjudicationResult, LlmAdjudicator, LlmClient
from .ner import Mention, NerPipeline
from .service import EntityLinkingService, KnowledgeGraphWriter, LinkingResult

__all__ = [
    "DeterministicDetectors",
    "IdentifierCandidate",
    "NerPipeline",
    "Mention",
    "CandidateGenerator",
    "Candidate",
    "DictionaryClient",
    "SparseClient",
    "DenseClient",
    "LlmAdjudicator",
    "LlmClient",
    "AdjudicationResult",
    "DecisionEngine",
    "LinkingDecision",
    "EntityLinkingService",
    "LinkingResult",
    "KnowledgeGraphWriter",
]
