"""Pydantic 資料模型，對齊 ShotCut 平台 API schema。"""

from typing import Literal

from pydantic import BaseModel, Field

CategoryType = Literal["offense", "defense", "turnover", "untagged"]


class PlayerInfo(BaseModel):
    number: int = Field(ge=0, le=999)
    name: str = Field(default="", max_length=100)


class MarkCreate(BaseModel):
    start_time: float = Field(ge=0, description="片段開始時間（秒）")
    end_time: float = Field(ge=0, description="片段結束時間（秒）")
    category: CategoryType = Field(default="untagged")
    label: str = Field(default="", max_length=200)
    players: list[PlayerInfo] = Field(default_factory=list)

    model_config = {"json_schema_extra": {"example": {
        "start_time": 120.5,
        "end_time": 135.0,
        "category": "offense",
        "label": "快攻得分",
        "players": [{"number": 23, "name": "Jordan"}],
    }}}


class MarkOut(BaseModel):
    id: int
    video_id: int
    start_time: float
    end_time: float
    category: str
    label: str
    players: list[PlayerInfo] = []

    model_config = {"from_attributes": True}


class VideoOut(BaseModel):
    id: int
    title: str
    source_type: str
    source_url: str | None = None
    status: str
    duration: float | None = None
    file_size: int | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class AppConfig(BaseModel):
    clips: bool = True
    highlights: bool = True
    sharing: bool = True


class UploadUrlResponse(BaseModel):
    upload_url: str
    video_id: int
    key: str
