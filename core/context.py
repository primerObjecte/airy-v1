from dataclasses import dataclass
from typing import Any


@dataclass
class CommandContext:
    runtime: Any
    event: Any
    storage: Any
    reply: Any
    sender_id: int | None = None
