"""Side effects a processor can ask for (`ctx.action(...)`). Each type is delivered by
app.services.actions; every one is delivered at most once."""

from typing import ClassVar

from pydantic import BaseModel, Field


class ActionType(BaseModel):
    type: ClassVar[str]


class Notify(ActionType):
    """An in-app notification, also sent to Telegram when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set."""

    type: ClassVar[str] = "notify"
    title: str = Field(max_length=200)
    body: str | None = None


ACTION_TYPES: dict[str, type[ActionType]] = {cls.type: cls for cls in (Notify,)}
