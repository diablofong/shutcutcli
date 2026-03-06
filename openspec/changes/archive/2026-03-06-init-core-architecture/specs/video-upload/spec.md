## ADDED Requirements

### Requirement: Presigned URL 影片上傳

系統 SHALL 遵循 ShotCut 平台的 Presigned URL 上傳流程：
1. GET /api/videos/upload-url
2. PUT presigned URL（httpx streaming，不全載入記憶體）
3. POST /api/videos/{id}/confirm
4. 輪詢 GET /api/videos/{id}/status 直到 completed 或 failed

#### Scenario: 上傳成功

- **WHEN** 使用者執行 `shutcutcli upload <video_file>`
- **THEN** 依序完成四步驟，顯示 Rich 進度條，最終輸出 video_id

#### Scenario: 大檔案上傳

- **WHEN** 影片檔案超過 100MB
- **THEN** 使用 streaming 上傳，記憶體使用量不因檔案大小線性增長

#### Scenario: 上傳後處理逾時

- **WHEN** 輪詢超過 10 分鐘仍未 completed
- **THEN** 顯示警告訊息，回傳 video_id 供使用者自行追蹤

### Requirement: 批次建立 Marks

系統 SHALL 讀取 marks.json，逐一呼叫 `POST /api/videos/{id}/marks` 建立標記，
顯示建立進度（N/Total）。

#### Scenario: 建立 Marks 成功

- **WHEN** 使用者執行 `shutcutcli upload <video_file> --marks marks.json`
- **THEN** 影片上傳完成後，依序建立所有 marks，顯示成功筆數

#### Scenario: Marks JSON 格式錯誤

- **WHEN** marks.json 不符合 schema
- **THEN** 顯示具體錯誤欄位，拒絕上傳

#### Scenario: 部分 Mark 建立失敗

- **WHEN** 個別 mark 建立失敗（如 API 錯誤）
- **THEN** 記錄失敗項目並繼續，最終顯示成功/失敗統計
