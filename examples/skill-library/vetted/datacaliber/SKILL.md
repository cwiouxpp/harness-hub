---
name: datacaliber
description: 数据口径校验：纯只读声明式校验，无命令执行，复用 gate 引擎。
version: 1.0.0
author: 示例库（脱敏）
source: 自研 · 干净环境演示
---

# 📏 datacaliber — 数据口径校验（示例脱敏版）

## 定位
对各 Agent 数据资产做完整性机器化验收，纯数据校验，**无命令执行**，复用 gate 引擎按 manifest 断言。

## 能力
- 断言关键字段存在与取值范围
- 无命令执行、无网络、无写操作，最低风险形态

## 使用
`gate.sh --conf datacaliber.manifest.json` — 本地只读校验，返回码 0/1/2。

## 安全边界（示例）
纯只读文本与 JSON 校验，不读身份/凭据文件，不执行外部命令。分级 🟢 可入库。
