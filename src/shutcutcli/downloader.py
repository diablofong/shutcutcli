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
        # 清除可能的殘破檔案
        if expected_path.exists() and expected_path.stat().st_size == 0:
            expected_path.unlink(missing_ok=True)
        raise RuntimeError("yt-dlp 下載失敗，請確認網址或網路連線")

    # 找到實際產生的 mp4 檔案
    actual_path = expected_path.with_suffix(".mp4")
    if not actual_path.exists():
        # fallback：找同目錄最新建立的影片檔
        video_exts = {".mp4", ".mkv", ".webm"}
        candidates = [
            f for f in output_dir.iterdir()
            if f.suffix.lower() in video_exts
        ]
        if not candidates:
            raise RuntimeError("找不到下載後的影片檔案")
        actual_path = max(candidates, key=lambda f: f.stat().st_mtime)

    console.print(f"[green]下載完成：{actual_path}[/green]")
    return actual_path
