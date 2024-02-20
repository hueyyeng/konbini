from __future__ import annotations

import datetime
from typing import TypedDict, Literal


class TSgUploadedMovie(TypedDict):
    url: str
    name: str
    content_type: str
    link_type: str
    type: str
    id: int


class THumanUser(TypedDict):
    id: int
    name: str
    type: Literal["HumanUser"]


class TNoteThreadReadData(TypedDict):
    type: Literal["Note", "Attachment", "Reply"]
    id: int
    content: str
    user: THumanUser
    created_by: THumanUser
    created_at: datetime.datetime


class TNoteThreadCustomEntityFields(TypedDict):
    Note: list[str]
    Reply: list[str]
    Attachment: list[str]
