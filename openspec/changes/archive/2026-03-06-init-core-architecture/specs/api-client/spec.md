## ADDED Requirements

### Requirement: ShotCut API Client

系統 SHALL 提供 `ShotCutClient` class，封裝 httpx.AsyncClient，
自動帶 `Authorization: Bearer <access_token>` header，並在 401 時自動 refresh 重試。

#### Scenario: 自動帶 Token

- **WHEN** 任何 API 呼叫執行
- **THEN** request header 包含有效的 access_token

#### Scenario: Token 過期自動 Refresh

- **WHEN** API 回傳 401
- **THEN** 自動呼叫 refresh，重試原始請求一次

#### Scenario: Rate Limit 觸發

- **WHEN** API 回傳 429
- **THEN** 顯示「請求過於頻繁，請稍後再試（Retry-After: N 秒）」並退出

### Requirement: 影片 API 操作

ShotCutClient SHALL 提供以下方法：
`get_upload_url(filename, content_type)`、
`confirm_upload(video_id)`、
`get_video_status(video_id)`、
`create_mark(video_id, mark)`、
`get_config()`。

#### Scenario: 取得上傳 URL

- **WHEN** 呼叫 `get_upload_url("game.mp4", "video/mp4")`
- **THEN** 回傳 `{upload_url, video_id, key}`

#### Scenario: 查詢平台功能

- **WHEN** 呼叫 `get_config()`
- **THEN** 回傳 `{clips: bool, highlights: bool, sharing: bool}`
