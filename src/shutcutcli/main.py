"""ShutCutCLI — ShotCut 平台命令列工具。"""

import asyncio
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.table import Table

# 修正 Windows 終端 UTF-8 輸出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

app = typer.Typer(
    name="shutcutcli",
    help="ShotCut 籃球影片標記平台命令列工具",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


def _run(coro):
    """在 sync context 執行 async 函式。"""
    return asyncio.run(coro)


def _require_login() -> tuple[str, str]:
    """確認已登入，回傳 (api_url, access_token)，否則直接 exit。"""
    from .config import get_api_url
    from .auth import get_access_token

    api_url = get_api_url()
    if not api_url:
        err_console.print("[red]尚未登入，請先執行：shutcutcli login <platform_url>[/red]")
        raise typer.Exit(1)

    try:
        access_token = _run(get_access_token(api_url))
    except RuntimeError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    return api_url, access_token


# ── login ─────────────────────────────────────────────────────────────────────

@app.command()
def login(
    platform_url: Annotated[str, typer.Argument(help="ShotCut 平台 URL，例如 https://shotcut.example.com")],
    username: Annotated[Optional[str], typer.Option("--username", "-u", help="帳號")] = None,
    password: Annotated[Optional[str], typer.Option("--password", "-p", help="密碼（不建議明文傳入）")] = None,
):
    """登入 ShotCut 平台並儲存 Token。"""
    from .auth import login as auth_login
    from .config import set_api_url

    if username is None:
        username = typer.prompt("帳號")
    if password is None:
        password = typer.prompt("密碼", hide_input=True)

    try:
        _run(auth_login(platform_url, username, password))
        set_api_url(platform_url)
        console.print(f"[green]登入成功：{platform_url}[/green]")
    except ValueError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        err_console.print(f"[red]登入失敗：{e}[/red]")
        raise typer.Exit(1)


# ── logout ────────────────────────────────────────────────────────────────────

@app.command()
def logout():
    """登出並清除本地 Token。"""
    from .auth import logout as auth_logout
    from .config import get_api_url

    api_url = get_api_url()
    _run(auth_logout(api_url))
    console.print("[green]已登出[/green]")


# ── download ──────────────────────────────────────────────────────────────────

@app.command()
def download(
    url: Annotated[str, typer.Argument(help="YouTube 影片 URL")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="輸出目錄")] = None,
):
    """從 YouTube 下載影片至本地。"""
    from .downloader import download_video, validate_youtube_url

    try:
        validate_youtube_url(url)
    except ValueError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    try:
        path = download_video(url, output_dir=output)
        console.print(f"[green]儲存路徑：{path}[/green]")
    except Exception as e:
        err_console.print(f"[red]下載失敗：{e}[/red]")
        raise typer.Exit(1)


# ── annotate ──────────────────────────────────────────────────────────────────

@app.command()
def annotate(
    video_file: Annotated[Path, typer.Argument(help="本地影片路徑")],
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="marks.json 輸出路徑")] = None,
):
    """分析影片並產生標記檔（marks.json）。"""
    from .annotator import run_annotator

    if not video_file.exists():
        err_console.print(f"[red]找不到影片：{video_file}[/red]")
        raise typer.Exit(1)

    # 此處替換為實際的標注後端實例
    err_console.print("[yellow]尚未設定標注後端，請實作 BaseAnnotator 並在此處初始化。[/yellow]")
    raise typer.Exit(1)


# ── upload ────────────────────────────────────────────────────────────────────

@app.command()
def upload(
    video_file: Annotated[Path, typer.Argument(help="本地影片路徑")],
    marks: Annotated[Optional[Path], typer.Option("--marks", "-m", help="marks.json 路徑")] = None,
):
    """上傳影片（及標記）至 ShotCut 平台。"""
    from .annotator import load_marks
    from .client import ShotCutClient
    from .uploader import upload_marks, upload_video

    api_url, access_token = _require_login()

    # 驗證 marks 檔案（上傳前）
    marks_data = []
    if marks:
        try:
            marks_data = load_marks(marks)
        except (FileNotFoundError, ValueError) as e:
            err_console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

    async def _upload():
        async with ShotCutClient(api_url, access_token) as client:
            video = await upload_video(client, video_file)
            if marks_data:
                await upload_marks(client, video.id, marks_data)
            return video

    try:
        video = _run(_upload())
        console.print(f"\n[bold green]完成！video_id={video.id}[/bold green]")
    except Exception as e:
        err_console.print(f"[red]上傳失敗：{e}[/red]")
        raise typer.Exit(1)


# ── run ───────────────────────────────────────────────────────────────────────

@app.command()
def run(
    url: Annotated[str, typer.Argument(help="YouTube 影片 URL")],
    output_dir: Annotated[Optional[Path], typer.Option("--output-dir", "-o", help="下載目錄")] = None,
    marks_only: Annotated[bool, typer.Option("--marks-only", help="僅上傳標記（跳過重新下載）")] = False,
    skip_annotate: Annotated[bool, typer.Option("--skip-annotate", help="跳過標注步驟")] = False,
):
    """一鍵全流程：下載 → 標注 → 上傳至 ShotCut 平台。"""
    from .annotator import load_marks, run_annotator
    from .client import ShotCutClient
    from .downloader import download_video, validate_youtube_url
    from .uploader import upload_marks, upload_video

    try:
        validate_youtube_url(url)
    except ValueError as e:
        err_console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    api_url, access_token = _require_login()

    async def _run_pipeline():
        # Step 1: 下載
        console.rule("[bold]Step 1 / 3：下載影片[/bold]")
        video_path = download_video(url, output_dir=output_dir)

        # Step 2: 標注
        marks_data = []
        if not skip_annotate:
            console.rule("[bold]Step 2 / 3：分析標注[/bold]")
            marks_path = video_path.with_suffix(".marks.json")
            if marks_path.exists():
                console.print(f"[cyan]使用既有標記檔：{marks_path}[/cyan]")
                marks_data = load_marks(marks_path)
            else:
                console.print("[yellow]尚未設定標注後端，跳過標注步驟。[/yellow]")

        # Step 3: 上傳
        console.rule("[bold]Step 3 / 3：上傳至 ShotCut[/bold]")
        async with ShotCutClient(api_url, access_token) as client:
            video = await upload_video(client, video_path)
            if marks_data:
                await upload_marks(client, video.id, marks_data)
        return video

    try:
        video = asyncio.run(_run_pipeline())
        console.rule("[bold green]全流程完成[/bold green]")
        console.print(f"[bold green]video_id={video.id}[/bold green]")
    except Exception as e:
        err_console.print(f"[red]流程中斷：{e}[/red]")
        raise typer.Exit(1)


# ── videos（列表） ─────────────────────────────────────────────────────────────

@app.command(name="videos")
def list_videos():
    """列出 ShotCut 平台上的影片清單。"""
    from .client import ShotCutClient

    api_url, access_token = _require_login()

    async def _list():
        async with ShotCutClient(api_url, access_token) as client:
            return await client.list_videos()

    try:
        videos = _run(_list())
    except Exception as e:
        err_console.print(f"[red]取得影片列表失敗：{e}[/red]")
        raise typer.Exit(1)

    if not videos:
        console.print("[yellow]目前沒有影片[/yellow]")
        return

    table = Table(title="影片列表")
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("標題")
    table.add_column("狀態", justify="center")
    table.add_column("時長", justify="right")
    table.add_column("來源")

    for v in videos:
        duration_str = f"{v.duration:.0f}s" if v.duration else "-"
        table.add_row(
            str(v.id),
            v.title,
            v.status,
            duration_str,
            v.source_type,
        )

    console.print(table)


if __name__ == "__main__":
    app()
