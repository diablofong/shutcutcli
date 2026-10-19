"""影片下載：yt-dlp wrapper，僅允許 YouTube 網域（防 SSRF）。"""

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TransferSpeedColumn

console = Console()

# 允許的 YouTube 網域白名單
_YOUTUBE_DOMAINS = re.compile(
    r"^https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/"
)


def _sanitize_url_for_display(url: str) -> str:
    """移除 URL 中可能的嵌入式認證資訊（user:pass@）。"""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        sanitized = parsed._replace(netloc=parsed.hostname or "")
        return urlunparse(sanitized)
    return url


def validate_youtube_url(url: str) -> None:
    """驗證 URL 是否為 YouTube 網域，否則拋出 ValueError。"""
    if not _YOUTUBE_DOMAINS.match(url):
        safe_url = _sanitize_url_for_display(url)
        raise ValueError(f"僅支援 YouTube 網址，拒絕：{safe_url}")


_VIDEO_EXTS = {".mp4", ".mkv", ".webm"}


def _find_downloaded_file(expected_path: Path) -> Path:
    """找出下載完成的影片檔。

    yt-dlp 合併格式後副檔名可能改變（如 .webm → .mp4），
    因此只比對同檔名（stem）的影片檔，避免誤抓目錄中的其他影片。
    """
    mp4_path = expected_path.with_suffix(".mp4")
    if mp4_path.exists():
        return mp4_path
    candidates = [
        f for f in expected_path.parent.iterdir()
        if f.stem == expected_path.stem and f.suffix.lower() in _VIDEO_EXTS
    ]
    if not candidates:
        raise RuntimeError("找不到下載後的影片檔案")
    return max(candidates, key=lambda f: f.stat().st_mtime)


def _cleanup_partial_files(expected_path: Path) -> None:
    """清除下載失敗留下的殘破檔案（.part / .ytdl / .temp 等暫存檔與空檔）。"""
    if not expected_path.parent.exists():
        return
    prefix = expected_path.stem + "."
    for f in expected_path.parent.iterdir():
        if not f.is_file() or not f.name.startswith(prefix):
            continue
        is_temp = f.name.endswith((".part", ".ytdl")) or ".temp." in f.name
        if is_temp or f.stat().st_size == 0:
            f.unlink(missing_ok=True)


def download_video(url: str, output_dir: Path | None = None) -> Path:
    """下載 YouTube 影片，回傳本地檔案路徑。

    Args:
        url: YouTube 影片 URL
        output_dir: 輸出目錄，預設為當前目錄

    Returns:
        下載完成的本地檔案路徑
    """
    validate_youtube_url(url)

    output_dir = output_dir or Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)

    # output template：%(title)s.%(ext)s
    output_template = str(output_dir / "%(title)s.%(ext)s")

    # 先取得檔案名稱（--print filename）
    get_filename_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--print", "filename",
        "-o", output_template,
        url,
    ]

    console.print(f"[cyan]取得影片資訊：{url}[/cyan]")

    filename_result = subprocess.run(
        get_filename_cmd,
        capture_output=True,
        text=True,
    )
    if filename_result.returncode != 0:
        raise RuntimeError(f"無法取得影片資訊：{filename_result.stderr.strip()}")

    expected_path = Path(filename_result.stdout.strip())

    # 實際下載
    download_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--merge-output-format", "mp4",
        "-o", output_template,
        "--newline",          # 每行輸出進度（便於解析）
        url,
    ]

    console.print("[cyan]開始下載...[/cyan]")

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("下載影片", total=None)

        proc = subprocess.Popen(
            download_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            # 解析 yt-dlp 進度行：[download]  42.3% of  123.45MiB
            if line.startswith("[download]") and "%" in line:
                match = re.search(r"(\d+\.?\d*)%", line)
                if match:
                    pct = float(match.group(1))
                    progress.update(task, completed=pct, total=100)

        proc.wait()

    if proc.returncode != 0:
        _cleanup_partial_files(expected_path)
        raise RuntimeError("yt-dlp 下載失敗，請確認網址或網路連線")

    actual_path = _find_downloaded_file(expected_path)

    console.print(f"[green]下載完成：{actual_path}[/green]")
    return actual_path
