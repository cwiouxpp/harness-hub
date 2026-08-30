# Contributing · 贡献指南

感谢你愿意为 **芯桥（HarnessHub）** 贡献力量。请先阅读本指南与
[README](README.md)、[LICENSE](LICENSE)。

---

## 快速开始

```bash
git clone <repo> && cd harness-runtime
# 零第三方依赖，直接跑测试
python3 -m pytest tests/ -q      # 期望 24 passed，无 INTERNALERROR
```

所有 PR 提交前请确保本机测试全绿（判定标准见下）。

---

## 无第三方依赖纪律

- 本项目**零第三方依赖**（仅 Python ≥3.9 标准库）。
- 新增代码不得引入第三方包；若确需，请先在 issue 讨论并说明理由（会触发复审）。
- `requirements.txt` 仅作版本/环境声明，不含真实依赖。

---

## PR 提交流程（强制门禁）

所有 PR **必须**经过以下两道自动门禁，否则不予合并：

1. **skill-vetter 合规审查**：变更涉及技能/规则/协议时，须按
   `skill-vetter` 流程校验——冻结技能 SHA 与 MANIFEST 一致性、内容合规
   （G1/G2/G3 三闸门）、风险分级、红名单/命令执行能力标注。
2. **防投毒扫描（buildguard）**：递归扫描变更产物，断言不含禁用硬编码
   （默认 `localhost:3000`，可追加 token；`--p1-openclaw` 追加禁用
   `~/.openclaw/` 本机私有安装路径）。命中即拒部署/拒合并。

```bash
# 提交前自查（以 buildguard 为例）
python3 examples/../skill-library/vetted/buildguard/scripts/buildguard.py <build 目录>
```

---

## 测试要求

- 修改运行时（`runtime.py`）或新增能力：**必须**补/改 pytest 用例，
  `python3 -m pytest tests/ -q` 全绿（当前 24 passed）。
- 测试风格：pytest 原生 `assert` + `pytest.raises`，**不要**用
  `sys.exit`/脚本式自研断言（P2-6 已是基线）。

---

## 提交约定

- 分支：`feature/<描述>` / `fix/<描述>`（小步快跑）。
- 语义化版本：遵循 [SemVer](https://semver.org/lang/zh-CN/)，变更记入
  [CHANGELOG.md](CHANGELOG.md)（Keep a Changelog 风格）。
- Commit message 简明，说明"为什么改"而非仅"改了什么"。
- 大改动拆小 PR，每 PR 聚焦一件事。

---

## 代码规范

- 遵循 [PEP 8](https://peps.python.org/pep-0008/)，type hints 尽可能完整。
- 所有对外函数需 docstring（参数/返回/异常）。
- 涉及敏感词/治理闸门改动，必须在注释说明"为何如此正则"并固化防回归断言
  （参考 G1 token 赋值形态的历史教训，见 README FAQ）。

---

## 问题 / 讨论

- Bug / 需求 → 提 issue（附复现步骤 + Python 版本 + 完整输出）。
- 安全漏洞 → **不要**走公开 issue，按 [SECURITY.md](SECURITY.md) 上报。

---

*维护：HarnessHub 核心维护者｜版本 v0.1.0*
