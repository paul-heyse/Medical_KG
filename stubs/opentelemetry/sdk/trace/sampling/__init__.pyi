from typing import Any

class ParentBased:
    def __init__(self, delegate_sampler: Any) -> None: ...

class TraceIdRatioBased:
    def __init__(self, ratio: float) -> None: ...

