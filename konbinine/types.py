from typing import TypedDict


class TSgUploadedMovie(TypedDict):
    url: str
    name: str
    content_type: str
    link_type: str
    type: str
    id: int
