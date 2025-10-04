from typing import Any

class _TraceAPI:
    def set_tracer_provider(self, provider: Any) -> None: ...


def get_tracer_provider() -> Any: ...

def set_tracer_provider(provider: Any) -> None: ...

