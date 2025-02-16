# generated by datamodel-codegen:
#   filename:  positions.json
#   timestamp: 2025-02-16T19:07:36+00:00

from __future__ import annotations

from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, ConfigDict, RootModel


class Order(Enum):
    shares = "shares"
    profit = "profit"


class MarketIdPositions(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    id: str
    userId: Optional[str] = None
    answerId: Optional[str] = None
    summaryOnly: Optional[bool] = None
    top: Optional[Union[Any, float]] = None
    bottom: Optional[Union[Any, float]] = None
    order: Optional[Order] = None


class Model(RootModel[MarketIdPositions]):
    root: MarketIdPositions
