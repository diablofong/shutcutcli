## ADDED Requirements

### Requirement: YouTube 影片下載

系統 SHALL 使用 yt-dlp 下載 YouTube 影片至本地，
以 subprocess list 形式呼叫（禁止 shell=True），並在下載期間顯示 Rich 進度條。

#### Scenario: 下載成功

- **WHEN** 使用者執行 `shutcutcli download <youtube_url>`
- **THEN** 影片下載至指定路徑（預設當前目錄），顯示下載進度

#### Scenario: 非 YouTube URL 被拒絕

- **WHEN** 傳入非 YouTube 網域的 URL
- **THEN** 顯示「僅支援 YouTube 網址」並拒絕下載（防 SSRF）

#### Scenario: 指定輸出路徑

- **WHEN** 使用者帶 `--output <path>` 參數
- **THEN** 影片下載至指定路徑

#### Scenario: 下載失敗

- **WHEN** yt-dlp 回傳非零 exit code
- **THEN** 顯示錯誤訊息，不留下殘破檔案
