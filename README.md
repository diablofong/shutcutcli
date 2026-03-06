# ShutCutCLI

ShotCut 籃球影片標記平台的命令列工具。

核心流程：從 YouTube 下載影片 → 自動分析產生標注 → 上傳影片與標注至 ShotCut 平台。

## 需求

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)（已包含在依賴中）
- ShotCut 平台實例（自建或雲端版）

## 安裝

```bash
git clone https://github.com/diablofong/shutcutcli.git
cd shutcutcli
uv sync
```

## 快速開始

### 1. 登入

```bash
uv run shutcutcli login https://your-shotcut-instance.example.com
```

互動式輸入帳號與密碼。Token 會安全儲存至 OS keyring（Windows Credential Manager / macOS Keychain / Linux Secret Service）。

### 2. 下載影片

```bash
uv run shutcutcli download "https://www.youtube.com/watch?v=VIDEO_ID"

# 指定輸出目錄
uv run shutcutcli download "https://youtu.be/VIDEO_ID" --output ./videos
```

### 3. 上傳影片

```bash
# 僅上傳影片
uv run shutcutcli upload game.mp4

# 上傳影片並附帶標注
uv run shutcutcli upload game.mp4 --marks game.marks.json
```

### 4. 一鍵全流程

```bash
# 下載 → 標注 → 上傳
uv run shutcutcli run "https://www.youtube.com/watch?v=VIDEO_ID"

# 跳過標注步驟
uv run shutcutcli run "https://youtu.be/VIDEO_ID" --skip-annotate

# 指定下載目錄
uv run shutcutcli run "https://youtu.be/VIDEO_ID" --output-dir ./videos
```

### 其他指令

```bash
# 列出平台上的影片
uv run shutcutcli videos

# 手動產生標注檔（需設定標注後端）
uv run shutcutcli annotate game.mp4 --output game.marks.json

# 登出
uv run shutcutcli logout
```

## 標注檔格式（marks.json）

```json
[
  {
    "start_time": 120.5,
    "end_time": 135.0,
    "category": "offense",
    "label": "快攻得分",
    "players": [
      { "number": 23, "name": "Jordan" }
    ]
  },
  {
    "start_time": 210.0,
    "end_time": 218.5,
    "category": "defense",
    "label": "火鍋",
    "players": [
      { "number": 6, "name": "" }
    ]
  }
]
```

| 欄位 | 類型 | 說明 |
|------|------|------|
| `start_time` | float | 片段開始時間（秒） |
| `end_time` | float | 片段結束時間（秒） |
| `category` | string | `offense` / `defense` / `turnover` / `untagged` |
| `label` | string | 自訂標籤（最多 200 字） |
| `players` | array | 球員資訊（號碼 0–999、姓名選填） |

## 指令總覽

| 指令 | 說明 |
|------|------|
| `login <url>` | 登入 ShotCut 平台並儲存 Token |
| `logout` | 登出並清除本地 Token |
| `download <url>` | 從 YouTube 下載影片 |
| `annotate <file>` | 分析影片並產生 marks.json |
| `upload <file>` | 上傳影片（可附帶 --marks） |
| `run <url>` | 一鍵全流程 |
| `videos` | 列出平台影片清單 |

## 自訂標注後端

`annotator.py` 提供 `BaseAnnotator` 抽象介面，可替換分析後端：

```python
from pathlib import Path
from shutcutcli.annotator import BaseAnnotator
from shutcutcli.models import MarkCreate

class MyAnnotator(BaseAnnotator):
    async def analyze(self, video_path: Path) -> list[MarkCreate]:
        # 實作你的分析邏輯
        return [
            MarkCreate(start_time=10.0, end_time=20.0, category="offense")
        ]
```

## 安全設計

- **Token 儲存**：refresh_token 存入 OS keyring，不落明文磁碟；keyring 不可用時 fallback 加密檔案
- **URL 驗證**：yt-dlp 僅允許 YouTube 網域，防止 SSRF
- **指令注入防護**：所有外部指令以 subprocess list 形式呼叫，不使用 `shell=True`
- **大檔案上傳**：streaming 上傳，不將整個檔案載入記憶體
- **標注驗證**：上傳前以 Pydantic v2 驗證 marks.json schema

## 開發

```bash
# 安裝含開發依賴
uv sync

# 執行測試
uv run pytest
```

## License

[MIT](LICENSE)
