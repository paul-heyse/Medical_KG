from typing import Any

class FastAPIInstrumentor:
    def __call__(self, *args: Any, **kwargs: Any) -> "FastAPIInstrumentor": ...

    @classmethod
    def instrument_app(cls, app: Any) -> None: ...

    @classmethod
    def instrument(cls, *args: Any, **kwargs: Any) -> None: ...

