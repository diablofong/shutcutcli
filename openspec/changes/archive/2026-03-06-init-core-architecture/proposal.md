# Change: 建立 ShutCutCLI 核心架構

## Why

ShutCutCLI 是全新專案，需要從零建立完整的 CLI 骨架，涵蓋認證、影片下載、標註產生、上傳至 ShotCut 平台等核心流程。

## What Changes

- 建立 Python uv 專案骨架（pyproject.toml、src layout）
- 新增 `cli-entry`：Typer CLI 入口，註冊所有子指令
- 新增 `config-management`：設定檔管理（~/.shutcutcli/config.json）
- 新增 `user-auth`：JWT 認證、Refresh Token Rotation、keyring 儲存
- 新增 `api-client`：ShotCut 平台 HTTP client（httpx async）
- 新增 `video-download`：yt-dlp wrapper，支援 YouTube 下載
- 新增 `video-upload`：Presigned URL 上傳流程 + 批次建立 marks
- 新增 `video-annotation`：影片分析介面，產生 marks.json（可抽換後端）

## Impact

- Affected specs: cli-entry, config-management, user-auth, api-client, video-download, video-upload, video-annotation
- Affected code: 全新專案，無既有程式碼衝突
