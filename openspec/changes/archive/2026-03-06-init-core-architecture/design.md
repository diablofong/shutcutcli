# Design: ShutCutCLI 核心架構

## Context

ShutCutCLI 需對接 ShotCut 平台（FastAPI + S3-compatible storage），主要挑戰：
1. Presigned URL 上傳流程（不直傳 backend）
2. Refresh Token Rotation（舊 token 被 revoke，需原子性更新）
3. 大檔案 streaming upload（不全載入記憶體）
4. 分析後端可抽換（初期實驗性，長期換 YOLO 模型）

## Goals / Non-Goals

- Goals:
  - 完整 CLI 流程（download → annotate → upload）
  - 安全 token 儲存（keyring 優先）
  - 大檔案 streaming 上傳
  - annotator 介面可抽換
- Non-Goals:
  - GUI 介面
  - 影片剪輯功能（由 ShotCut 平台處理）
  - 打包成單一執行檔（uv run 即可）

## Decisions

- **CLI 框架**：Typer + Rich。type hint 驅動，自動 help，搭配 rich 有漂亮進度條。
- **HTTP Client**：httpx AsyncClient。支援 streaming upload、timeout、自動 retry。
- **Token 儲存**：keyring（OS 原生）為主，~/.shutcutcli/credentials.enc 為 fallback。refresh_token 存 keyring，access_token 只存記憶體，每次執行重新 refresh。
- **上傳流程**：GET upload-url → PUT presigned（httpx streaming） → POST confirm → 輪詢 status。
- **annotator 介面**：`BaseAnnotator` 抽象介面，`analyze(video_path) -> list[MarkCreate]`。實驗階段實作可替換。
- **專案 layout**：`src/shutcutcli/` src layout，配合 uv 的 editable install。

## Risks / Trade-offs

- keyring 在 headless/CI 環境可能不可用 → fallback 加密檔案
- Presigned URL 有效期 15min，大檔案上傳需在時限內完成 → streaming 上傳邊傳邊送
- Rate limiting（upload-url: 10/hr）→ CLI 顯示明確錯誤訊息

## Open Questions

- annotator 實驗性後端細節（不在本次 scope 實作）
