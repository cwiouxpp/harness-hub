---
name: buildguard
description: 构建期防线：只读文本扫描禁用硬编码，拒部署带有禁用引用的产物。
version: 1.0.0
author: 示例库（脱敏）
source: 自研 · 干净环境演示
---

# 🧱 buildguard — 构建期防线（示例脱敏版）

## 定位
在 build 产物上跑"构建期防线"：断言文本内容不含禁用引用（默认本机开发地址），命中即拒部署。

## 能力
- 递归扫描 build 目录的文本类文件（js/css/html/json/txt 等）
- token 可配置（`--token`），只读扫描，零命令执行、零网络、零写

## 用法
`python3 buildguard.py <build_dir> [--token <t>]` — 0=通过 / 1=拒部署 / 2=用法错误。

## 安全边界（示例）
纯文件读取 + 正则，不读身份/凭据文件，不执行外部命令。分级 🟢 可入库。
