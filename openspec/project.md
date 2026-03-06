# Project Context

## Purpose

ShutCutCLI 是 ShotCut 籃球影片標記平台的命令列工具。
核心流程：從 YouTube 下載影片 → 自動分析產生標註（marks.json）→ 上傳影片與標註到 ShotCut 平台。

## Tech Stack

- **語言**：Python 3.11+
- **套件管理**：uv（直接 `uv run` 執行，不打包）
- **CLI 框架**：Typer + Rich（互動提示、進度條）
- **HTTP Client**：httpx（async，streaming upload）
- **影片下載**：yt-dlp（subprocess list 形式呼叫，防 injection）
- **Token 儲存**：keyring（OS 原生），fallback 加密檔案
- **資料模型**：Pydantic v2
- **分析後端**：初期實驗性（可抽換介面），長期替換為 YOLO + 籃球訓練模型

## Project Conventions

### Code Style
- 繁體中文：所有回應、程式碼註解、文件
- Python type hints 全覆蓋
- async/await 優先（httpx async client）
- 不使用 `shell=True`（防 command injection）
- 不在 log/stderr 輸出 token 或密碼

### Architecture Patterns
- CLI 入口：`src/shutcutcli/main.py`（Typer app）
- 各功能模組獨立：config / auth / client / downloader / annotator / uploader
- 設定檔：`~/.shutcutcli/config.json`（明文，非敏感）
- Token：keyring 存 refresh_token，每次執行 refresh 換新 access_token
- 上傳走 ShotCut Presigned URL 流程（不直傳 backend）

### Testing Strategy
- pytest + pytest-asyncio
- 使用 httpx.MockTransport 模擬 ShotCut API
- 不在測試中使用真實 keyring（mock 替代）

### Git Workflow
- 分支：main（主線）
- commit 訊息：繁體中文，簡潔描述變更
- **不加 AI 簽署**（Co-Authored-By 等）
- 遵循 OpenSpec：實作前必須有通過 validate 的 change proposal

## Domain Context

### ShotCut 平台 API

**認證**
- `POST /api/auth/login` → access_token (15min) + refresh_token cookie (7day)
- `POST /api/auth/refresh` → Refresh Token Rotation（舊 token 被 revoke）
- `POST /api/auth/logout` → 清除 token

**影片上傳（Presigned URL 流程）**
1. `GET /api/videos/upload-url?filename=xxx&content_type=video/mp4` → `{upload_url, video_id, key}`
2. `PUT upload_url`（直傳 S3，httpx streaming）
3. `POST /api/videos/{video_id}/confirm`
4. 輪詢 `GET /api/videos/{video_id}/status` 等待 `status: completed`

**標記**
- `POST /api/videos/{video_id}/marks`
- Body: `{ start_time, end_time, category, label, players: [{number, name}] }`
- category: `offense | defense | turnover | untagged`

**平台功能查詢**
- `GET /api/config` → `{ clips: bool, highlights: bool, sharing: bool }`

### Rate Limiting
| 端點 | 限制 |
|------|------|
| upload-url | 10/hour |
| confirm | 20/hour |
| download (YouTube) | 10/hour |
| login | 5/minute |

## Important Constraints

- 與 ShotCut API 通訊強制 HTTPS（localhost 開發除外）
- yt-dlp URL 驗證：限制 YouTube 網域（防 SSRF）
- Token 不得落明文磁碟
- 標註 JSON 上傳前驗證 schema（防注入惡意資料）
- 大檔案上傳使用 streaming（不全載入記憶體）
- annotator 介面設計需可抽換分析後端（長期換 YOLO 模型）

## External Dependencies

| 服務/套件 | 用途 |
|-----------|------|
| ShotCut Platform API | 影片管理、標記、認證 |
| Cloudflare R2 / S3-compatible | 影片實際存放（Presigned URL 直傳） |
| yt-dlp | YouTube 影片下載 |
| keyring | OS 原生 token 儲存 |
| httpx | async HTTP client（含 streaming upload） |
| typer + rich | CLI 框架與終端美化 |
| pydantic v2 | 資料驗證與模型 |
