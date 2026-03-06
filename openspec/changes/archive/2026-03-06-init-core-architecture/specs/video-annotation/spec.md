## ADDED Requirements

### Requirement: 標註介面（可抽換後端）

系統 SHALL 提供 `BaseAnnotator` 抽象介面，方法簽章為
`analyze(video_path: Path) -> list[MarkCreate]`，
供不同分析後端實作（初期實驗性後端、長期 YOLO 模型）。

#### Scenario: 分析成功

- **WHEN** 呼叫 annotator 分析影片
- **THEN** 回傳符合 MarkCreate schema 的標記清單

#### Scenario: 切換後端

- **WHEN** 替換 BaseAnnotator 實作
- **THEN** 上層介面（CLI 指令、uploader）不需修改

### Requirement: Marks JSON 讀寫

系統 SHALL 提供 `save_marks(marks, path)` 與 `load_marks(path) -> list[MarkCreate]`，
存取 marks.json 並驗證 schema。

#### Scenario: 儲存 Marks

- **WHEN** 標註完成
- **THEN** marks 以 JSON 格式存至指定路徑，可被 `shutcutcli upload --marks` 使用

#### Scenario: 載入 Marks 格式驗證

- **WHEN** 載入 marks.json
- **THEN** 以 Pydantic v2 驗證每筆 mark，不符 schema 者拋出明確錯誤

### Requirement: Annotate CLI 指令

系統 SHALL 提供 `shutcutcli annotate <video_file> [--output marks.json]` 指令。

#### Scenario: 執行標註

- **WHEN** 使用者執行 `shutcutcli annotate game.mp4`
- **THEN** 分析影片並將結果存至 marks.json（預設同目錄）

#### Scenario: 指定輸出路徑

- **WHEN** 使用者帶 `--output <path>` 參數
- **THEN** marks.json 存至指定路徑
