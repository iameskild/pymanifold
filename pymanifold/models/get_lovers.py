# generated by datamodel-codegen:
#   filename:  get-lovers.json
#   timestamp: 2025-02-16T19:07:33+00:00

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, RootModel


class GetLovers(BaseModel):
    pass
    model_config = ConfigDict(
        extra="forbid",
    )


class Model(RootModel[GetLovers]):
    root: GetLovers
