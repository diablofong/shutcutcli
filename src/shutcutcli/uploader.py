"""影片上傳：Presigned URL 流程 + 批次建立 marks。"""

import asyncio
from pathlib import Path

import httpx
from rich.console import Console
from rich.progress import BarColumn, Progress, TaskID, TextColumn, TimeRemainingColumn

from .client import ShotCutClient
from .models import MarkCreate, MarkOut, VideoOut

console = Console()

# 輪詢設定
_POLL_INTERVAL = 5        # 秒
_POLL_TIMEOUT = 600       # 10 分鐘

_VIDEO_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".webm": "video/webm",
    ".mkv": "video/x-matroska",
}


def guess_video_content_type(file_path: Path) -> str:
    """依副檔名判斷影片 Content-Type，未知格式預設 video/mp4。"""
    return _VIDEO_CONTENT_TYPES.get(file_path.suffix.lower(), "video/mp4")


async def upload_video(client: ShotCutClient, file_path: Path) -> VideoOut:
    """完整 Presigned URL 上傳流程：取得 URL → PUT S3 → confirm → 等待處理。

    Args:
        client: 已認證的 ShotCutClient
        file_path: 本地影片路徑

    Returns:
        完成處理後的 VideoOut
    """
    if not file_path.exists():
        raise FileNotFoundError(f"找不到影片檔案：{file_path}")

    filename = file_path.name
    file_size = file_path.stat().st_size
    content_type = guess_video_content_type(file_path)

    # 1. 取得 Presigned PUT URL
    console.print(f"[cyan]取得上傳 URL：{filename}[/cyan]")
    upload_info = await client.get_upload_url(filename, content_type=content_type)

    # 2. Streaming PUT 上傳至 S3
    console.print(f"[cyan]上傳影片至儲存空間（{file_size / 1024 / 1024:.1f} MB）...[/cyan]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task: TaskID = progress.add_task("上傳中", total=file_size)

        # AsyncClient 需使用 async generator 才能 streaming 上傳
        async def _iter_file():
            chunk_size = 1024 * 1024  # 1MB chunks
            with open(file_path, "rb") as f:
                while chunk := f.read(chunk_size):
                    progress.advance(task, len(chunk))
                    yield chunk

        # 明確帶 Content-Length，避免 httpx 改用 chunked 傳輸（S3 presigned PUT 不支援）
        async with httpx.AsyncClient(timeout=3600) as s3_client:
            resp = await s3_client.put(
                upload_info.upload_url,
                content=_iter_file(),
                headers={"Content-Type": content_type, "Content-Length": str(file_size)},
            )
            if resp.status_code not in (200, 204):
                raise RuntimeError(f"上傳至儲存空間失敗（HTTP {resp.status_code}）")

    # 3. 通知平台確認上傳
    console.print("[cyan]確認上傳完成...[/cyan]")
    video = await client.confirm_upload(upload_info.video_id)

    # 4. 等待後台處理（縮圖、元資料）
    video = await wait_for_processing(client, upload_info.video_id)
    return video


async def wait_for_processing(client: ShotCutClient, video_id: int) -> VideoOut:
    """輪詢影片狀態直到 completed 或 failed。"""
    console.print("[cyan]等待平台處理影片...[/cyan]")
    elapsed = 0

    while elapsed < _POLL_TIMEOUT:
        video = await client.get_video_status(video_id)

        if video.status == "completed":
            console.print(f"[green]影片處理完成（video_id={video_id}）[/green]")
            return video

        if video.status == "failed":
            raise RuntimeError(
                f"影片處理失敗：{video.error_message or '未知錯誤'}"
            )

        await asyncio.sleep(_POLL_INTERVAL)
        elapsed += _POLL_INTERVAL

    console.print(
        f"[yellow]警告：影片處理逾時（已等待 {_POLL_TIMEOUT // 60} 分鐘），"
        f"video_id={video_id} 可在平台上查看進度[/yellow]"
    )
    return video


async def upload_marks(
    client: ShotCutClient,
    video_id: int,
    marks: list[MarkCreate],
) -> tuple[list[MarkOut], list[tuple[int, str]]]:
    """批次建立 marks，回傳（成功清單, 失敗清單[(index, 錯誤訊息)]）。"""
    if not marks:
        return [], []

    console.print(f"[cyan]建立標記（共 {len(marks)} 筆）...[/cyan]")
    succeeded: list[MarkOut] = []
    failed: list[tuple[int, str]] = []

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("建立標記", total=len(marks))

        for i, mark in enumerate(marks):
            try:
                result = await client.create_mark(video_id, mark)
                succeeded.append(result)
            except Exception as e:
                failed.append((i, str(e)))
            finally:
                progress.advance(task)

    console.print(
        f"[green]標記建立完成：成功 {len(succeeded)} 筆"
        + (f"，失敗 {len(failed)} 筆" if failed else "")
        + "[/green]"
    )
    return succeeded, failed
