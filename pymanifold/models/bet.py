# generated by datamodel-codegen:
#   filename:  bet.json
#   timestamp: 2025-02-16T19:07:33+00:00

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, RootModel, confloat


class Outcome(Enum):
    YES = "YES"
    NO = "NO"


class Bet(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    contractId: str
    amount: confloat(ge=1.0)
    replyToCommentId: Optional[str] = None
    limitProb: Optional[confloat(ge=0.01, le=0.99)] = None
    expiresAt: Optional[float] = None
    outcome: Optional[Outcome] = "YES"
    answerId: Optional[str] = None
    dryRun: Optional[bool] = None
    deps: Optional[List[str]] = None
    deterministic: Optional[bool] = None


class Model(RootModel[Bet]):
    root: Bet
