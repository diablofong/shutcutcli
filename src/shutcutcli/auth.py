"""認證管理：登入、Token Refresh、keyring 儲存（fallback 加密檔案）。"""

import base64
import json
import os
import stat
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import CONFIG_DIR, get_api_url

KEYRING_SERVICE = "shutcutcli"
CREDENTIALS_FILE = CONFIG_DIR / "credentials.enc"

# 允許 HTTP 的 host（僅開發用途）
_LOCALHOST_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _require_secure_url(api_url: str) -> None:
    """強制 HTTPS，僅 localhost 例外。"""
    parsed = urlparse(api_url)
    if parsed.scheme == "https":
        return
    if parsed.scheme == "http" and parsed.hostname in _LOCALHOST_HOSTS:
        return
    raise ValueError(
        f"安全性要求：非 localhost 環境必須使用 HTTPS，拒絕：{parsed.scheme}://{parsed.hostname}"
    )


def _set_file_owner_only(path: Path) -> None:
    """設定檔案權限為僅擁有者可讀寫（600），Windows 上為 no-op。"""
    if os.name != "nt":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


# ── Keyring 操作（帶 fallback） ─────────────────────────────────────────────

def _keyring_set(api_url: str, token: str) -> None:
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, api_url, token)
    except Exception:
        _file_set(api_url, token)


def _keyring_get(api_url: str) -> str | None:
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, api_url)
    except Exception:
        return _file_get(api_url)


def _keyring_delete(api_url: str) -> None:
    try:
        import keyring
        keyring.delete_password(KEYRING_SERVICE, api_url)
    except Exception:
        pass
    _file_delete(api_url)


# ── 加密檔案 fallback ────────────────────────────────────────────────────────

def _derive_key() -> bytes:
    """從機器指紋 + 隨機 salt 衍生加密 key（32 bytes）。

    首次執行時產生隨機 salt 儲存於 CONFIG_DIR/.salt，
    後續使用同一 salt 確保金鑰一致。
    """
    import hashlib

    salt_file = CONFIG_DIR / ".salt"
    if salt_file.exists():
        salt = salt_file.read_bytes()
    else:
        salt = os.urandom(32)
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        salt_file.write_bytes(salt)
        _set_file_owner_only(salt_file)

    machine_id = (
        os.environ.get("COMPUTERNAME", "")
        + os.environ.get("USERNAME", "")
        + str(Path.home())
    )
    return hashlib.pbkdf2_hmac("sha256", machine_id.encode(), salt, iterations=100_000)


def _file_set(api_url: str, token: str) -> None:
    from cryptography.fernet import Fernet
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    key = base64.urlsafe_b64encode(_derive_key())
    fernet = Fernet(key)
    data: dict = {}
    if CREDENTIALS_FILE.exists():
        try:
            data = json.loads(fernet.decrypt(CREDENTIALS_FILE.read_bytes()).decode())
        except Exception:
            data = {}
    data[api_url] = token
    CREDENTIALS_FILE.write_bytes(fernet.encrypt(json.dumps(data).encode()))
    _set_file_owner_only(CREDENTIALS_FILE)


def _file_get(api_url: str) -> str | None:
    if not CREDENTIALS_FILE.exists():
        return None
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_derive_key())
        fernet = Fernet(key)
        data = json.loads(fernet.decrypt(CREDENTIALS_FILE.read_bytes()).decode())
        return data.get(api_url)
    except Exception:
        return None


def _file_delete(api_url: str) -> None:
    if not CREDENTIALS_FILE.exists():
        return
    try:
        from cryptography.fernet import Fernet
        key = base64.urlsafe_b64encode(_derive_key())
        fernet = Fernet(key)
        data = json.loads(fernet.decrypt(CREDENTIALS_FILE.read_bytes()).decode())
        data.pop(api_url, None)
        CREDENTIALS_FILE.write_bytes(fernet.encrypt(json.dumps(data).encode()))
        _set_file_owner_only(CREDENTIALS_FILE)
    except Exception:
        pass


# ── 公開介面 ─────────────────────────────────────────────────────────────────

async def login(api_url: str, username: str, password: str) -> str:
    """登入 ShotCut 平台，儲存 refresh_token，回傳 access_token。"""
    _require_secure_url(api_url)

    async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        if resp.status_code == 401:
            raise ValueError("帳號或密碼錯誤")
        resp.raise_for_status()

        data = resp.json()
        access_token: str = data["access_token"]

        # refresh_token 在 httpOnly cookie 中
        refresh_token: str = resp.cookies.get("refresh_token") or ""
        if refresh_token:
            _keyring_set(api_url, refresh_token)

        return access_token


async def get_access_token(api_url: str | None = None) -> str:
    """從 keyring 取 refresh_token，換取新 access_token（Refresh Token Rotation）。"""
    if api_url is None:
        api_url = get_api_url()
    if not api_url:
        raise RuntimeError("尚未設定平台 URL，請執行 shutcutcli login")

    refresh_token = _keyring_get(api_url)
    if not refresh_token:
        raise RuntimeError("尚未登入，請執行 shutcutcli login")

    async with httpx.AsyncClient(
        base_url=api_url,
        timeout=30,
        cookies={"refresh_token": refresh_token},
    ) as client:
        resp = await client.post("/api/auth/refresh")
        if resp.status_code in (401, 403):
            raise RuntimeError("登入已過期，請重新執行 shutcutcli login")
        resp.raise_for_status()

        data = resp.json()
        access_token: str = data["access_token"]

        # 更新 refresh_token（Rotation）
        new_refresh = resp.cookies.get("refresh_token")
        if new_refresh:
            _keyring_set(api_url, new_refresh)

        return access_token


async def logout(api_url: str | None = None) -> None:
    """登出並清除 keyring 中的 token。"""
    if api_url is None:
        api_url = get_api_url()
    if not api_url:
        return

    refresh_token = _keyring_get(api_url)
    if refresh_token:
        try:
            # 先取得有效 access_token（後端 logout 需要 Authorization header）
            access_token = await get_access_token(api_url)
            async with httpx.AsyncClient(
                base_url=api_url,
                timeout=10,
                headers={"Authorization": f"Bearer {access_token}"},
                cookies={"refresh_token": refresh_token},
            ) as client:
                await client.post("/api/auth/logout")
        except Exception:
            pass  # 即使 API 失敗，仍清除本地 token

    _keyring_delete(api_url)
