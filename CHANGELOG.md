# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/) 与
[Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## [Unreleased]

### Added
- P2 商业基石落地：Apache-2.0 LICENSE、requirements.txt（零第三方依赖）、
  README 客户化重写、CONTRIBUTING、SECURITY.md。
- 工程化规范：semver 版本号（`__version__`）、pytest 原生测试风格（去 sys.exit）。

### Fixed
- 测试层重构：`tests/test_runtime.py` 由自研 `check()/expect_raises()+sys.exit`
  改为 pytest 原生 `assert + pytest.raises`，`python3 -m pytest` 不再 INTERNALERROR。

## [0.1.0] - 2026-08-17

### Added （M1-3 运行时骨架 + M2-1 / M3 里程碑）
- Harness 统一运行时载体：状态容器 + 任务调度 + 追溯日志 + 治理闸门。
- Skills 接入层：`loadSkill` / `listSkills`（vetted 冻结区 + MANIFEST + SHA 逐字节校验）。
- 记忆接入层：`loadMemory` / `writeInsight`（CMD-MEM 七段模板，零重建，默认 dry-run）。
- 自我改进接入层：`collectExperience` / `applyImprovement`（默认 reject，须显式确认）。
- 三条治理闸门：G1 数据不出服务器 / G2 信号非投资建议 / G3 不自动改系统提示安全策略。
- P1 去硬编码化：全路径常量锚定包安装根，零 `~/.openclaw` 绝对路径，干净环境可跑通。

### Changed
- G1 token 正则收紧为赋值形态（`token\s*[=:]`），消除对合法量化技能
  （如 strategy-protocol 提及「Tushare Pro Token」）的误拦截。
  （质量事件 2026-08-17，契约测试 26→32 固化防回归断言。）

### Fixed
- 修正 G1 裸 token 正则误伤问题（见 Changed）。

[Unreleased]: https://github.com/cwiouxpp/harness-hub/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/cwiouxpp/harness-hub/releases/tag/v0.1.0
