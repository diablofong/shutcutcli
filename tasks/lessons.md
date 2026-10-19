# Lessons

## 2026-10-19：開發流程走 /pdw，不走 OpenSpec
- **情境**：修 bug 前先去查 OpenSpec 是否需要 proposal，並在回報中以 OpenSpec 規範作為依據
- **規則**：本專案開發一律走使用者定義的 `/pdw` 模式；不建立 OpenSpec proposal/change、不跑 `openspec validate`
- `openspec/specs/` 只當作既有行為參考，不作為流程依據
- 已同步更新專案 `CLAUDE.md` 的開發規範

## 2026-10-19：本專案 git 身分
- commit 身分為 `diablofong <diablofong@gmail.com>`（已設定於 repo local config）
- commit 前先確認 `git config --local user.name` / `user.email`
