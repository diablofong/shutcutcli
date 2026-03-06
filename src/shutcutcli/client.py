"""ShotCut 平台 API client（httpx async，自動帶 token 與 refresh）。"""

from __future__ import annotations

import httpx

from .models import AppConfig, MarkCreate, MarkOut, UploadUrlResponse, VideoOut


class ShotCutClient:
    """封裝 ShotCut API 的 async HTTP client。

    使用方式：
        async with ShotCutClient(api_url, access_token) as client:
            videos = await client.list_videos()
    """

    def __init__(self, api_url: str, access_token: str) -> None:
        self._api_url = api_url.rstrip("/")
        self._access_token = access_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> ShotCutClient:
        self._client = httpx.AsyncClient(
            base_url=self._api_url,
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=60,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._client:
            await self._client.aclose()

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("請使用 async with ShotCutClient(...) as client")
        return self._http_client

    @property
    def _http_client(self) -> httpx.AsyncClient:
        assert self._client is not None
        return self._client

    async def _request(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        resp = await self._http_client.request(method, path, **kwargs)
        if resp.status_code == 429:
            retry_after = resp.headers.get("Retry-After", "?")
            raise RuntimeError(f"請求過於頻繁，請 {retry_after} 秒後再試")
        if resp.status_code == 403:
            raise PermissionError("無權存取此資源")
        if resp.status_code == 404:
            raise FileNotFoundError(f"資源不存在：{path}")
        resp.raise_for_status()
        return resp

    # ── 影片 ─────────────────────────────────────────────────────────────────

    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[VideoOut]:
        resp = await self._request("GET", "/api/videos", params={"limit": limit, "offset": offset})
        return [VideoOut.model_validate(v) for v in resp.json()]

    async def get_upload_url(self, filename: str, content_type: str = "video/mp4") -> UploadUrlResponse:
        resp = await self._request(
            "GET", "/api/videos/upload-url",
            params={"filename": filename, "content_type": content_type},
        )
        return UploadUrlResponse.model_validate(resp.json())

    async def confirm_upload(self, video_id: int) -> VideoOut:
        resp = await self._request("POST", f"/api/videos/{video_id}/confirm")
        return VideoOut.model_validate(resp.json())

    async def get_video_status(self, video_id: int) -> VideoOut:
        resp = await self._request("GET", f"/api/videos/{video_id}/status")
        return VideoOut.model_validate(resp.json())

    async def delete_video(self, video_id: int) -> None:
        await self._request("DELETE", f"/api/videos/{video_id}")

    # ── 標記 ─────────────────────────────────────────────────────────────────

    async def create_mark(self, video_id: int, mark: MarkCreate) -> MarkOut:
        resp = await self._request(
            "POST", f"/api/videos/{video_id}/marks",
            json=mark.model_dump(),
        )
        return MarkOut.model_validate(resp.json())

    async def list_marks(self, video_id: int) -> list[MarkOut]:
        resp = await self._request("GET", f"/api/videos/{video_id}/marks")
        return [MarkOut.model_validate(m) for m in resp.json()]

    # ── 平台設定 ─────────────────────────────────────────────────────────────

    async def get_config(self) -> AppConfig:
        try:
            resp = await self._request("GET", "/api/config")
            return AppConfig.model_validate(resp.json())
        except Exception:
            # 舊版平台沒有 /api/config，回傳預設值
            return AppConfig()
