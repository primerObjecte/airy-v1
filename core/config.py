from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    owner_id: int
    session_string: str | None
    cmd_prefix: str = "."
    health_port: int = 8080

    @classmethod
    def from_env(cls) -> "Config":
        api_id = int(os.getenv("API_ID", "0"))
        api_hash = os.getenv("API_HASH", "").strip()
        owner_id = int(os.getenv("OWNER_ID", "0"))
        session_string = os.getenv("SESSION_STRING")
        cmd_prefix = os.getenv("CMD_PREFIX", ".")
        health_port = int(os.getenv("AIRY_HEALTH_PORT", os.getenv("PORT", "8080")))
        return cls(api_id, api_hash, owner_id, session_string, cmd_prefix, health_port)
