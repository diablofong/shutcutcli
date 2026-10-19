# ShutCutCLI 專案指南

## 最高注意事項（CRITICAL）

### 語言設定
- **一律使用繁體中文回應**
- **即使自動清除 cache 後，仍必須使用繁體中文回應**
- 所有對話、註解、文件都使用繁體中文

### Git 提交規範
- **提交訊息不得包含任何 Claude Code 或 AI 的簽署**
- 不要加入 "Co-Authored-By: Claude" 或任何類似簽名
- 提交訊息必須簡潔明確，只描述變更內容

### 開發規範
- **開發一律採用 `/pdw` 模式，不走 OpenSpec 流程**（不建立 proposal / change、不執行 `openspec validate`）
- Bug fix / 新功能 → `/pdw dev`；緊急修復 → `/pdw hotfix`；討論 → `/pdw talk`
- 分支紀錄存放於 `.claude/records/`（不 commit）
- `openspec/specs/` 僅作為既有行為的參考文件

## 專案說明

ShutCutCLI 是 ShotCut 籃球影片標記平台的命令列工具。
功能：本地下載影片 → 分析產生標註 → 上傳影片與標註到 ShotCut 平台。

## 技術架構

- 語言：Python 3.11+
- 套件管理：uv
- CLI 框架：Typer + Rich
- HTTP Client：httpx (async)
- 影片下載：yt-dlp
- Token 儲存：keyring（OS 原生），fallback 加密檔案
- 資料模型：Pydantic v2

## 專案結構

```
shutcutcli/
├── pyproject.toml
├── .env.example
├── src/
│   └── shutcutcli/
│       ├── __init__.py
│       ├── main.py         # Typer CLI 入口
│       ├── config.py       # 設定管理（平台 URL 存 ~/.shutcutcli/config.json）
│       ├── auth.py         # 登入 + JWT token 管理（keyring 儲存 refresh_token）
│       ├── client.py       # ShotCut API client (httpx async)
│       ├── downloader.py   # yt-dlp wrapper
│       ├── annotator.py    # 影片分析 → marks.json（實驗階段用 Claude API）
│       ├── uploader.py     # Presigned URL 上傳 + confirm + 建立 marks
│       └── models.py       # Pydantic 資料模型
```

## ShotCut 平台 API 對接規格

### 認證流程
- POST /api/auth/login → 取得 access_token + refresh_token (httpOnly cookie)
- POST /api/auth/refresh → 用 refresh_token 換新 access_token（Refresh Token Rotation，舊 token 會被 revoke）
- CLI Token 策略：refresh_token 存 keyring，每次執行用 refresh 取新 access_token

### 影片上傳流程（Presigned URL）
1. GET /api/videos/upload-url?filename=xxx&content_type=video/mp4
   → 回傳 {upload_url, video_id, key}
2. PUT upload_url（直傳 S3，不經 backend，用 httpx streaming upload）
3. POST /api/videos/{video_id}/confirm
4. 輪詢 GET /api/videos/{video_id}/status 等待 status: completed

### 標記建立
- POST /api/videos/{video_id}/marks
- Body: { start_time, end_time, category, label, players: [{number, name}] }
- category: "offense" | "defense" | "turnover" | "untagged"

### Rate Limiting（CLI 需配合）
- upload-url: 10/hour
- confirm: 20/hour
- download: 10/hour
- login: 5/minute

### 平台功能查詢
- GET /api/config → 回傳啟用的功能（clips, highlights, sharing）

## CLI 指令設計

```bash
# 登入
shutcutcli login <platform_url>
# 例：shutcutcli login https://shotcut.example.com

# 登出（清除 keyring 中的 token）
shutcutcli logout

# 下載影片
shutcutcli download <youtube_url> [--output <path>]

# 分析影片產生標註
shutcutcli annotate <video_file> [--output marks.json]

# 上傳影片 + 標註
shutcutcli upload <video_file> [--marks marks.json]

# 一鍵全流程
shutcutcli run <youtube_url> [--marks-only]
```

## 實作計畫（依序執行）

### Phase 1：專案骨架
1. 建立 pyproject.toml（uv 專案，定義依賴：typer, rich, httpx, keyring, pydantic）
2. 建立 src/shutcutcli/__init__.py
3. 建立 src/shutcutcli/main.py — Typer app 骨架，註冊所有子指令（先空實作）
4. 建立 .env.example

### Phase 2：設定與認證
5. 建立 src/shutcutcli/config.py
   - 設定檔路徑：~/.shutcutcli/config.json
   - 儲存：api_url（明文）
   - load_config() / save_config()
6. 建立 src/shutcutcli/auth.py
   - login(api_url, username, password) → 呼叫 POST /api/auth/login
   - refresh_token 存入 keyring（service="shutcutcli", username=api_url）
   - get_access_token() → 從 keyring 取 refresh_token → POST /api/auth/refresh → 回傳 access_token
   - logout() → 清除 keyring
   - fallback：若 keyring 不可用，存加密檔案到 ~/.shutcutcli/credentials.enc

### Phase 3：API Client
7. 建立 src/shutcutcli/models.py
   - VideoOut, MarkCreate, MarkOut, PlayerInfo 等 Pydantic model
   - 對齊 ShotCut 平台的 API schema
8. 建立 src/shutcutcli/client.py
   - ShotCutClient class（封裝 httpx.AsyncClient）
   - 自動帶 Authorization header
   - Token 過期自動 refresh
   - 方法：login(), list_videos(), get_upload_url(), confirm_upload(),
     create_mark(), get_video_status(), get_config()

### Phase 4：影片下載
9. 建立 src/shutcutcli/downloader.py
   - download_video(url, output_path) → 呼叫 yt-dlp
   - subprocess list 形式（不用 shell=True）
   - 進度回調（yt-dlp --progress-template）
   - URL 驗證：限制 YouTube 網域（防 SSRF）

### Phase 5：影片上傳
10. 建立 src/shutcutcli/uploader.py
    - upload_video(client, file_path) → 完整 presigned URL 流程
    - 大檔案 streaming upload（httpx stream）
    - upload_marks(client, video_id, marks_file) → 批次建立 marks
    - 進度顯示（rich progress bar）

### Phase 6：影片分析（實驗性）
11. 建立 src/shutcutcli/annotator.py
    - annotate(video_path) → 產生 marks.json
    - 實驗階段：使用 Claude API 分析影片
    - 長期計畫：替換為 YOLO + 籃球訓練模型（此階段不實作）
    - 介面設計要能輕易替換分析後端

### Phase 7：整合指令
12. 完善 main.py 中各子指令的實作
    - login：互動式輸入 URL/帳密 → 呼叫 auth.login
    - logout：清除 token
    - download：呼叫 downloader
    - annotate：呼叫 annotator
    - upload：呼叫 uploader（影片 + marks）
    - run：串接 download → annotate → upload

## 安全注意事項

- Token 不落明文磁碟（keyring 或加密檔案）
- yt-dlp 指令用 subprocess list 形式，防 command injection
- URL 驗證限制 YouTube 網域
- 與 ShotCut API 通訊強制 HTTPS（除 localhost 開發）
- 標註檔上傳前驗證 JSON schema
- 不在 log 中輸出 token 或密碼
