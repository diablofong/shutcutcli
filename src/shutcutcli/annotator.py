"""影片標註介面：BaseAnnotator 抽象介面，可抽換分析後端。"""

import json
from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import ValidationError
from rich.console import Console

from .models import MarkCreate

console = Console()


class BaseAnnotator(ABC):
    """標註後端抽象介面，所有分析後端必須實作此介面。"""

    @abstractmethod
    async def analyze(self, video_path: Path) -> list[MarkCreate]:
        """分析影片，回傳標記清單。

        Args:
            video_path: 本地影片路徑

        Returns:
            符合 MarkCreate schema 的標記清單
        """
        ...


# ── Marks JSON 讀寫 ───────────────────────────────────────────────────────────

def save_marks(marks: list[MarkCreate], output_path: Path) -> None:
    """將標記清單儲存為 JSON 檔案。"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [m.model_dump() for m in marks]
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]標記已儲存：{output_path}（共 {len(marks)} 筆）[/green]")


def load_marks(marks_path: Path) -> list[MarkCreate]:
    """讀取 marks.json 並驗證 schema。

    Raises:
        FileNotFoundError: 檔案不存在
        ValueError: JSON 格式或 schema 驗證失敗
    """
    if not marks_path.exists():
        raise FileNotFoundError(f"找不到標記檔案：{marks_path}")

    try:
        raw = json.loads(marks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"標記檔案 JSON 格式錯誤：{e}") from e

    if not isinstance(raw, list):
        raise ValueError("標記檔案必須是 JSON 陣列")

    marks: list[MarkCreate] = []
    errors: list[str] = []

    for i, item in enumerate(raw):
        try:
            marks.append(MarkCreate.model_validate(item))
        except ValidationError as e:
            errors.append(f"第 {i + 1} 筆：{e.error_count()} 個錯誤 — {e.errors()[0]['msg']}")

    if errors:
        raise ValueError("標記 schema 驗證失敗：\n" + "\n".join(errors))

    return marks


async def run_annotator(
    annotator: BaseAnnotator,
    video_path: Path,
    output_path: Path | None = None,
) -> list[MarkCreate]:
    """執行標註流程並儲存結果。

    Args:
        annotator: 分析後端實例
        video_path: 本地影片路徑
        output_path: marks.json 輸出路徑（預設與影片同目錄）

    Returns:
        產生的標記清單
    """
    if not video_path.exists():
        raise FileNotFoundError(f"找不到影片：{video_path}")

    if output_path is None:
        output_path = video_path.with_suffix(".marks.json")

    console.print(f"[cyan]分析影片：{video_path.name}[/cyan]")
    marks = await annotator.analyze(video_path)

    save_marks(marks, output_path)
    return marks
