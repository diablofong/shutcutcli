"""程式碼審查修復的回歸測試。"""

import httpx
import pytest
import respx
from pydantic import ValidationError

from shutcutcli import auth, uploader
from shutcutcli.client import ShotCutClient
from shutcutcli.downloader import _cleanup_partial_files, _find_downloaded_file
from shutcutcli.models import MarkCreate

API = "https://shotcut.test"


@pytest.fixture
def token_store(monkeypatch):
    """以 dict 取代 keyring，避免測試碰觸 OS 憑證庫。"""
    store: dict[str, str] = {}
    monkeypatch.setattr(auth, "_keyring_get", lambda url: store.get(url))
    monkeypatch.setattr(auth, "_keyring_set", lambda url, t: store.__setitem__(url, t))
    monkeypatch.setattr(auth, "_keyring_delete", lambda url: store.pop(url, None))
    return store


# ── uploader ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_upload_video_streams_with_content_length(tmp_path):
    video = tmp_path / "game.webm"
    payload = b"x" * (3 * 1024 * 1024 + 7)  # 跨多個 1MB chunk
    video.write_bytes(payload)

    respx.get(f"{API}/api/videos/upload-url").respond(
        json={"upload_url": "https://s3.test/bucket/key?sig=1", "video_id": 7, "key": "k"}
    )
    s3 = respx.put("https://s3.test/bucket/key").respond(200)
    respx.post(f"{API}/api/videos/7/confirm").respond(
        json={"id": 7, "title": "game", "source_type": "upload", "status": "processing"}
    )
    respx.get(f"{API}/api/videos/7/status").respond(
        json={"id": 7, "title": "game", "source_type": "upload", "status": "completed"}
    )

    async with ShotCutClient(API, "tok") as client:
        result = await uploader.upload_video(client, video)

    assert result.status == "completed"
    req = s3.calls.last.request
    assert req.headers["Content-Length"] == str(len(payload))
    assert "Transfer-Encoding" not in req.headers
    assert req.headers["Content-Type"] == "video/webm"
    assert req.content == payload
    upload_url_req = respx.calls[0].request
    assert upload_url_req.url.params["content_type"] == "video/webm"


def test_guess_video_content_type():
    from pathlib import Path
    assert uploader.guess_video_content_type(Path("a.MP4")) == "video/mp4"
    assert uploader.guess_video_content_type(Path("a.mkv")) == "video/x-matroska"
    assert uploader.guess_video_content_type(Path("a.xyz")) == "video/mp4"


# ── client：401 自動 refresh ──────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_client_refreshes_on_401_and_retries(monkeypatch):
    async def fake_get_access_token(api_url):
        assert api_url == API
        return "new-token"
    monkeypatch.setattr(auth, "get_access_token", fake_get_access_token)

    route = respx.get(f"{API}/api/videos").mock(side_effect=[
        httpx.Response(401),
        httpx.Response(200, json=[]),
    ])

    async with ShotCutClient(API, "old-token") as client:
        assert await client.list_videos() == []

    assert route.call_count == 2
    assert route.calls[0].request.headers["Authorization"] == "Bearer old-token"
    assert route.calls[1].request.headers["Authorization"] == "Bearer new-token"


@pytest.mark.asyncio
@respx.mock
async def test_client_gives_up_after_second_401(monkeypatch):
    async def fake_get_access_token(api_url):
        return "new-token"
    monkeypatch.setattr(auth, "get_access_token", fake_get_access_token)
    route = respx.get(f"{API}/api/videos").respond(401)

    async with ShotCutClient(API, "old-token") as client:
        with pytest.raises(RuntimeError, match="登入已過期"):
            await client.list_videos()
    assert route.call_count == 2


# ── auth ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
@respx.mock
async def test_logout_sends_rotated_refresh_token(token_store):
    token_store[API] = "rt-old"
    respx.post(f"{API}/api/auth/refresh").respond(
        json={"access_token": "at"},
        headers={"set-cookie": "refresh_token=rt-new; Path=/; HttpOnly"},
    )
    logout_route = respx.post(f"{API}/api/auth/logout").respond(200)

    await auth.logout(API)

    cookie = logout_route.calls.last.request.headers["cookie"]
    assert "refresh_token=rt-new" in cookie
    assert API not in token_store


@pytest.mark.asyncio
@respx.mock
async def test_login_without_refresh_cookie_fails(token_store):
    respx.post(f"{API}/api/auth/login").respond(json={"access_token": "at"})

    with pytest.raises(RuntimeError, match="refresh_token"):
        await auth.login(API, "u", "p")
    assert token_store == {}


@pytest.mark.asyncio
@respx.mock
async def test_login_stores_refresh_token(token_store):
    respx.post(f"{API}/api/auth/login").respond(
        json={"access_token": "at"},
        headers={"set-cookie": "refresh_token=rt1; Path=/; HttpOnly"},
    )
    assert await auth.login(API, "u", "p") == "at"
    assert token_store[API] == "rt1"


# ── models ────────────────────────────────────────────────────────────────────

def test_mark_rejects_end_before_start():
    with pytest.raises(ValidationError, match="end_time"):
        MarkCreate(start_time=10, end_time=5)
    assert MarkCreate(start_time=5, end_time=5).end_time == 5


# ── downloader ────────────────────────────────────────────────────────────────

def test_find_downloaded_file_ignores_other_videos(tmp_path):
    expected = tmp_path / "game [abc].webm"
    target = tmp_path / "game [abc].mkv"
    target.write_bytes(b"1")
    (tmp_path / "newer-other.mp4").write_bytes(b"2")  # 較新但不相干

    assert _find_downloaded_file(expected) == target


def test_find_downloaded_file_prefers_merged_mp4(tmp_path):
    expected = tmp_path / "game.webm"
    (tmp_path / "game.webm").write_bytes(b"1")
    (tmp_path / "game.mp4").write_bytes(b"2")
    assert _find_downloaded_file(expected) == tmp_path / "game.mp4"


def test_find_downloaded_file_missing(tmp_path):
    (tmp_path / "other.mp4").write_bytes(b"1")
    with pytest.raises(RuntimeError):
        _find_downloaded_file(tmp_path / "game.webm")


def test_cleanup_partial_files(tmp_path):
    expected = tmp_path / "game.webm"
    junk = [
        tmp_path / "game.f137.mp4.part",
        tmp_path / "game.webm.ytdl",
        tmp_path / "game.temp.mp4",
    ]
    for f in junk:
        f.write_bytes(b"partial")
    (tmp_path / "game.webm").write_bytes(b"")  # 空檔
    keep = [tmp_path / "game.mp4", tmp_path / "other.mp4.part"]
    for f in keep:
        f.write_bytes(b"data")

    _cleanup_partial_files(expected)

    assert not any(f.exists() for f in junk)
    assert not (tmp_path / "game.webm").exists()
    assert all(f.exists() for f in keep)
