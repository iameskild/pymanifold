# generated by datamodel-codegen:
#   filename:  users.json
#   timestamp: 2025-02-16T19:07:31+00:00

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, RootModel, confloat


class Users(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    limit: Optional[confloat(ge=0.0, le=1000.0)] = 500
    before: Optional[str] = None


class Model(RootModel[Users]):
    root: Users
