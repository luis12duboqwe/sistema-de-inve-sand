from typing import Any, Callable, Sequence

class AsyncIOScheduler:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    def add_job(
        self,
        func: Callable[..., Any],
        trigger: Any,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...

    def start(self) -> None: ...
