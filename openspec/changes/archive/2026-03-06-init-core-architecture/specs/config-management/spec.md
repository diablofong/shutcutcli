## ADDED Requirements

### Requirement: 設定檔管理

系統 SHALL 將非敏感設定（api_url）存於 `~/.shutcutcli/config.json`，以明文 JSON 格式儲存。

#### Scenario: 儲存設定

- **WHEN** 使用者執行 `login <url>`
- **THEN** api_url 寫入 `~/.shutcutcli/config.json`

#### Scenario: 讀取設定

- **WHEN** 任何指令執行時需要 api_url
- **THEN** 從 `~/.shutcutcli/config.json` 讀取

#### Scenario: 設定檔不存在

- **WHEN** `~/.shutcutcli/config.json` 不存在
- **THEN** 提示使用者執行 `shutcutcli login` 並退出
