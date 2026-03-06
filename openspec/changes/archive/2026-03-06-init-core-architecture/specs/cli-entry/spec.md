## ADDED Requirements

### Requirement: CLI 入口與子指令註冊

系統 SHALL 提供以 Typer 為基礎的 CLI 入口，支援以下子指令：
`login`、`logout`、`download`、`annotate`、`upload`、`run`。

#### Scenario: 顯示幫助

- **WHEN** 使用者執行 `shutcutcli --help`
- **THEN** 列出所有可用子指令與說明

#### Scenario: 執行未知指令

- **WHEN** 使用者執行不存在的子指令
- **THEN** 顯示錯誤訊息並以 exit code 2 退出

### Requirement: 錯誤處理與友善輸出

CLI SHALL 使用 Rich 輸出格式化訊息，區分成功（綠色）、警告（黃色）、錯誤（紅色）。

#### Scenario: API 連線失敗

- **WHEN** ShotCut 平台無法連線
- **THEN** 顯示清楚的錯誤訊息（非 stack trace），以 exit code 1 退出

#### Scenario: 未登入時執行受保護指令

- **WHEN** 使用者未登入即執行 `download`、`upload`、`run`
- **THEN** 提示「請先執行 shutcutcli login」並退出
