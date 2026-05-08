from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum

class RoomRole(str, Enum):
    business = "business"
    lilly = "lilly"
    james = "james"
    family_mediator = "family_mediator"

class RoomConfig(BaseModel):
    token: str
    name: str
    role: RoomRole = RoomRole.business
    level: int = Field(default=2, ge=1, le=4)
    memory_file: str = ""
    enabled: bool = True
    urgent_capable: bool = False
    model: Optional[str] = None
    system_prompt_override: Optional[str] = None

class NextcloudConfig(BaseModel):
    url: str = ""
    user: str = ""
    pass_: str = Field(default="", alias="pass")
    model_config = {"populate_by_name": True}

class AnthropicConfig(BaseModel):
    api_key: str = ""
    default_model: str = "claude-haiku-4-5"

class TelegramConfig(BaseModel):
    bot_token: str = ""
    chat_id: str = ""

class PollingConfig(BaseModel):
    tick: int = 15
    level_intervals: dict = Field(default={"1": 120, "2": 900, "3": 3600, "4": 86400})
    urgent_poll_interval: int = 15
    urgent_calm_timeout: int = 600
    urgent_trigger_words: List[str] = ["urgent", "panic", "help me", "spiral"]
    urgent_calm_words: List[str] = ["ok", "calm", "better", "thanks", "thank you", "good", "sorted"]
    history_limit: int = 20

class WebuiConfig(BaseModel):
    port: int = 7861
    password_hash: str = ""
    auth_enabled: bool = True

class AppConfig(BaseModel):
    nextcloud: NextcloudConfig = Field(default_factory=NextcloudConfig)
    anthropic: AnthropicConfig = Field(default_factory=AnthropicConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    polling: PollingConfig = Field(default_factory=PollingConfig)
    rooms: List[RoomConfig] = Field(default_factory=list)
    webui: WebuiConfig = Field(default_factory=WebuiConfig)
    backup_retention_days: int = 30
    safety_keywords: List[str] = Field(default_factory=lambda: [
        "kill myself", "end my life", "want to die", "wish i was dead", "suicide",
        "self harm", "self-harm", "cut myself", "hurt myself", "not want to be here",
        "don't want to be here", "nobody cares", "no one cares", "abuse",
        "touched me", "hurting me", "hitting me", "he hurt", "she hurt", "they hurt",
        "being hit", "being hurt", "being abused"
    ])
