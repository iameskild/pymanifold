# generated by datamodel-codegen:
#   filename:  lite.json
#   timestamp: 2025-02-16T19:07:35+00:00

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class UserUsernameLite(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    username: str


class Model(RootModel[UserUsernameLite]):
    root: UserUsernameLite
