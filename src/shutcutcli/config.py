"""設定管理：非敏感設定存於 ~/.shutcutcli/config.json"""

import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".shutcutcli"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """讀取設定檔，不存在時回傳空 dict。"""
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(data: dict) -> None:
    """寫入設定檔，自動建立目錄。"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_api_url() -> str | None:
    """取得已儲存的平台 URL。"""
    return load_config().get("api_url")


def set_api_url(api_url: str) -> None:
    """儲存平台 URL。"""
    config = load_config()
    config["api_url"] = api_url.rstrip("/")
    save_config(config)
