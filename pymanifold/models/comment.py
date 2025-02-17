# generated by datamodel-codegen:
#   filename:  comment.json
#   timestamp: 2025-02-16T19:07:31+00:00

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, RootModel


class Mark(BaseModel):
    type: str
    attrs: Optional[Dict[str, Any]] = None


class Content(BaseModel):
    type: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None
    content: Optional[List[Content]] = None
    marks: Optional[List[Mark]] = None
    text: Optional[str] = None


class ContentModel(BaseModel):
    type: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None
    content: Optional[List[Content]] = None
    marks: Optional[List[Mark]] = None
    text: Optional[str] = None


class Comment(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    contractId: str
    content: Optional[ContentModel] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    replyToCommentId: Optional[str] = None
    replyToAnswerId: Optional[str] = None
    replyToBetId: Optional[str] = None


class Model(RootModel[Comment]):
    root: Comment


Content.model_rebuild()
