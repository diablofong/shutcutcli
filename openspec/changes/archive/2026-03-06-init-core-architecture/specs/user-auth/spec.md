## ADDED Requirements

### Requirement: 登入與 Token 取得

系統 SHALL 呼叫 `POST /api/auth/login`，取得 access_token 與 refresh_token，
並將 refresh_token 安全儲存於 OS keyring（service="shutcutcli"，username=api_url）。

#### Scenario: 登入成功

- **WHEN** 使用者提供有效的帳號密碼
- **THEN** refresh_token 存入 keyring，顯示登入成功訊息

#### Scenario: 登入失敗（帳密錯誤）

- **WHEN** 帳號或密碼不正確
- **THEN** 顯示「帳號或密碼錯誤」，不存入任何 token

#### Scenario: 互動式輸入

- **WHEN** 使用者執行 `shutcutcli login <url>` 未帶帳密參數
- **THEN** 以互動提示輸入 username 與 password（密碼不回顯）

### Requirement: Access Token 自動 Refresh

系統 SHALL 在每次執行指令時，從 keyring 取 refresh_token，
呼叫 `POST /api/auth/refresh` 換取新 access_token（Refresh Token Rotation）。

#### Scenario: Refresh 成功

- **WHEN** refresh_token 有效
- **THEN** 取得新 access_token，存入記憶體供本次執行使用

#### Scenario: Refresh Token 已過期

- **WHEN** refresh_token 已過期或被 revoke
- **THEN** 提示「登入已過期，請重新執行 shutcutcli login」並退出

### Requirement: 登出

系統 SHALL 呼叫 `POST /api/auth/logout`，並清除 keyring 中的 refresh_token。

#### Scenario: 登出成功

- **WHEN** 使用者執行 `shutcutcli logout`
- **THEN** 呼叫 logout API，清除 keyring token，顯示登出成功

### Requirement: Keyring Fallback

當 OS keyring 不可用時（headless/CI），系統 SHALL fallback 存加密檔案
`~/.shutcutcli/credentials.enc`，key 從機器指紋衍生。

#### Scenario: Keyring 不可用

- **WHEN** keyring 套件拋出 `keyring.errors.NoKeyringError`
- **THEN** 自動改用加密檔案儲存，顯示警告訊息
