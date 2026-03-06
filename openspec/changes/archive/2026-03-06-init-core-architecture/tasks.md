# Tasks: init-core-architecture

## 1. 專案骨架

- [x] 1.1 建立 pyproject.toml（uv 專案，src layout，依賴：typer, rich, httpx, keyring, pydantic, yt-dlp）
- [x] 1.2 建立 src/shutcutcli/__init__.py
- [x] 1.3 建立 .env.example

## 2. 設定管理

- [x] 2.1 建立 src/shutcutcli/config.py（load_config / save_config，~/.shutcutcli/config.json）

## 3. 資料模型

- [x] 3.1 建立 src/shutcutcli/models.py（VideoOut, MarkCreate, MarkOut, PlayerInfo）

## 4. 認證模組

- [x] 4.1 建立 src/shutcutcli/auth.py
  - [x] 4.1.1 login()：POST /api/auth/login，存 refresh_token 至 keyring
  - [x] 4.1.2 get_access_token()：從 keyring 取 refresh_token → POST /api/auth/refresh
  - [x] 4.1.3 logout()：POST /api/auth/logout，清除 keyring
  - [x] 4.1.4 keyring fallback：不可用時存加密檔案 ~/.shutcutcli/credentials.enc

## 5. API Client

- [x] 5.1 建立 src/shutcutcli/client.py（ShotCutClient，封裝 httpx.AsyncClient）
  - [x] 5.1.1 自動帶 Authorization header
  - [x] 5.1.2 Rate Limit 429 處理
  - [x] 5.1.3 get_upload_url()
  - [x] 5.1.4 confirm_upload()
  - [x] 5.1.5 get_video_status()
  - [x] 5.1.6 create_mark()
  - [x] 5.1.7 get_config()

## 6. 影片下載

- [x] 6.1 建立 src/shutcutcli/downloader.py
  - [x] 6.1.1 download_video()：subprocess list 形式呼叫 yt-dlp
  - [x] 6.1.2 URL 驗證（限 YouTube 網域）
  - [x] 6.1.3 Rich 進度顯示

## 7. 影片上傳

- [x] 7.1 建立 src/shutcutcli/uploader.py
  - [x] 7.1.1 upload_video()：完整 Presigned URL 流程（streaming upload）
  - [x] 7.1.2 wait_for_processing()：輪詢 status 直到 completed/failed
  - [x] 7.1.3 upload_marks()：批次建立 marks
  - [x] 7.1.4 Rich progress bar

## 8. 影片標註

- [x] 8.1 建立 src/shutcutcli/annotator.py
  - [x] 8.1.1 BaseAnnotator 抽象介面（analyze(video_path) -> list[MarkCreate]）
  - [x] 8.1.2 save_marks() / load_marks()：marks.json 讀寫與 schema 驗證

## 9. CLI 指令整合

- [x] 9.1 建立 src/shutcutcli/main.py（Typer app）
  - [x] 9.1.1 `login` 指令
  - [x] 9.1.2 `logout` 指令
  - [x] 9.1.3 `download` 指令
  - [x] 9.1.4 `annotate` 指令
  - [x] 9.1.5 `upload` 指令
  - [x] 9.1.6 `run` 指令（一鍵全流程）
  - [x] 9.1.7 `videos` 指令（列表）
