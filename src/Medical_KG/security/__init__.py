"""Security and compliance utilities."""

from .audit import AuditEvent, AuditLogger
from .licenses import LicenseRegistry, LicenseRegistryError, LicenseSession, LicenseTier
from .provenance import ExtractionActivity, ProvenanceStore
from .rbac import RBACEngine, Role, ScopeEnforcer, ScopeError
from .retention import PurgePipeline, RetentionPolicy, RetentionRecord, RetentionResult
from .shacl import (
    ShaclIssue,
    compose_shapes,
    load_shapes,
    validate_on_write,
    validate_shacl,
)

__all__ = [
    "AuditEvent",
    "AuditLogger",
    "LicenseRegistry",
    "LicenseRegistryError",
    "LicenseTier",
    "LicenseSession",
    "ScopeEnforcer",
    "ScopeError",
    "RBACEngine",
    "Role",
    "ProvenanceStore",
    "ExtractionActivity",
    "PurgePipeline",
    "RetentionPolicy",
    "RetentionRecord",
    "RetentionResult",
    "validate_shacl",
    "validate_on_write",
    "load_shapes",
    "compose_shapes",
    "ShaclIssue",
]
