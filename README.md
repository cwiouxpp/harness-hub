# Harness Hub · 统一运行时载体

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-%E2%89%A53.9-3776AB.svg)](requirements.txt)
[![Tests](https://img.shields.io/badge/tests-24%20passed-green.svg)](tests/)

> **芯桥（HarnessHub）** 是一个把「技能 + 记忆 + 治理」装进一个可运行载体的轻量微内核。
> 零第三方依赖，Python 标准库即可跑；冻结技能逐字节校验、记忆零重建、三闸门强制合规。
> 面向多 Agent 工程团队：跨会话复用冻结技能、读共享记忆、沉淀经验、治理闸门拦截违规。

---

## 🚀 30 秒快速开始

```bash
# 1) 拿到包（无任何第三方依赖，无需 pip install）
git clone <repo-url> && cd harness-runtime

# 2) 直接跑通契约测试（判定：全部通过、无 INTERNALERROR）
python3 -m pytest tests/ -v

# 3) 30 秒交互 Demo：加载冻结技能 + 读共享记忆 + 全链路装配
python3 - <<'PY'
import runtime
from runtime import HarnessRuntime

# 三接口各跑一次（最小 Demo 闭环）
s  = runtime.load_skill("gate")                 # ① 加载冻结技能（校验SHA）
sk = runtime.list_skills()                      #    冻结技能清单
m  = runtime.load_memory()                      # ② 读共享记忆（CMD-MEM，零重建）
rt = HarnessRuntime()
res = rt.run_task("demo", "gate")               # ③ 状态容器全链路装配
print("skill:", res["skill_loaded"])
print("memory:", res["memory_loaded"])
print("run_id:", res["run_id"])                 # 决策可追溯
PY
```

> ✅ 陌生客户按上述步骤，30 分钟内即可跑通完整 Demo（含自带的 `examples/skill-library/` 脱敏示例库）。

---

## 🏗 架构

```
                     ┌────────────────────────────────────────────┐
        Apps / Agents│            Harness 运行时 (runtime.py)      │
                     │                                             │
   loadSkill/list ──▶│ ① Skills 接入层                            │
        vetted 冻结区│    vetted/ + MANIFEST + SHA 逐字节校验      │
   loadMemory ──────▶│ ② 记忆接入层                                │
        CMD-MEM     │    MEMORY.md 四段(身份/用户/持久事实/沉淀)    │
   collect/apply ──▶│ ③ 自我改进层                                 │
        dry-run     │    collectExperience / applyImprovement      │
                     │                                             │
   writeInsight ───▶│ ④ 治理闸门  G1 数据不出 │ G2 信号非投资建议   │
   applyImprovement │            G3 不改系统提示/安全策略           │
                     └──────────┬───────────────┬─────────────────┘
                                │ trace.log     │ governance.log
                                ▼               ▼
                          决策可追溯日志      合规拦截留痕
```

**依赖关系**（全部可选，零强制）：
| 数据源 | 默认（包自带示例） | 真实环境（env 覆盖） |
|--------|-------------------|----------------------|
| 技能库 | `examples/skill-library/` | `HARNESS_SKILL_LIB_ROOT` |
| 记忆 | `examples/sample_memory/` | `HARNESS_MEM_ROOT` |
| 落盘目录 | `data/` | `HARNESS_DIR` |

---

## 📦 安装 / 环境

- **Python ≥ 3.9**（f-string、dataclass、类型注解均可用）
- **零第三方依赖**：仅标准库 `hashlib/json/os/re/sys/time/uuid/typing`
- 无需 `pip install`、无需 Docker、无需数据库

```bash
python3 -c "import runtime; print(runtime.__version__)"   # → 0.1.0
```

---

## 🔌 API 速览

### ① Skills 接入层
```python
import runtime
s  = runtime.load_skill("gate")                # 加载冻结技能（SHA 逐字节校验）
sk = runtime.list_skills()                     # 冻结技能清单（仅 vetted）
```
| 函数 | 说明 | 违规行为 |
|------|------|---------|
| `load_skill(name, version_hash?)` | 加载 vetted 冻结技能 | 未冻结/哈希不符 → `GovernanceError` |
| `list_skills(category?, tier?)` | 列出冻结技能 | — |

### ② 记忆接入层
```python
m = runtime.load_memory()                      # 读共享记忆（CMD-MEM 四段）
r = runtime.write_insight("insight", "内容", "触发")   # 默认 dry-run，不自动落盘
```
| 函数 | 说明 | 违规行为 |
|------|------|---------|
| `load_memory(memory_root?)` | 读取身份/用户/持久事实/沉淀四段 | — |
| `write_insight(type, content, trigger, upgrade?)` | 沉淀建议（**默认 dry-run**） | 非法 type → `ValueError`；命中闸门 → `GovernanceError` |

### ③ 自我改进接入层
```python
exp = runtime.collect_experience()             # 从 trace + 沉淀收集经验
r   = runtime.apply_improvement(id, "accept")  # 显式确认才生效，默认 reject
```
| 函数 | 说明 | 违规行为 |
|------|------|---------|
| `collect_experience(source?)` | 收集去重经验 | — |
| `apply_improvement(id, accept_reject)` | 接受/拒绝改进（**默认 reject**） | 非法参数 → `ValueError`；命中红线 → 强制 reject |

### 状态容器
```python
from runtime import HarnessRuntime
res = HarnessRuntime().run_task("label", "skill")
# → {"run_id": <12位>, "skill_loaded": ..., "memory_loaded": ...}
```

---

## 🛡 治理（三条合规红线）

命中任一闸门 → 强制拦截 + 写入 `governance.log`，**不自动放行**：

| 闸门 | 名称 | 拦截内容 |
|------|------|---------|
| **G1** | 数据不出服务器 | `password` / `secret` / `api_key` / `private_key`（裸匹配）+ token **赋值形态**（`token:` / `token=`，防误伤文档名词指称如 "Tushare Pro Token"） |
| **G2** | 信号非投资建议 | `买入推荐` / `必涨` / `稳赚` / `保证收益` / `股神` / `包赚` |
| **G3** | 不自动改系统提示/安全策略 | `system prompt` / `系统提示` / `安全策略` / `safety_policy` |

---

## ❓ FAQ

**Q1：需要安装多少依赖？**
零第三方依赖。仅 Python 3.9+ 标准库，无需 pip install、无需 Docker。

**Q2：跑不起来 / 报 INTERNALERROR？**
先确认 ≥ Python 3.9 且有 `pytest`；然后 `python3 -m pytest tests/ -q`。若用包自带示例库仍失败，请提 issue 附完整输出。

**Q3：技能和记忆从哪来？**
默认用包内 `examples/` 脱敏示例（干净克隆即可跑通）。真实环境用环境变量
`HARNESS_SKILL_LIB_ROOT` / `HARNESS_MEM_ROOT` 指向你自己的共享库与 workspace，零重建复用。

**Q4：为什么 writeInsight 默认不写入？**
合规优先（G3 精神）：沉淀建议默认 `dry-run` 返回，交由人工确认后才真正落盘，防止自动改写记忆。

**Q5：治理闸门会不会误杀正常内容？**
G1 的 token 已收紧为**赋值形态**才拦（`token:` / `token=`），仅"提及 Token"（如文档里写 "Tushare Pro Token"）不拦截；password/secret/api_key/private_key 等最敏感词保留裸匹配不妥协。契约测试含 6 条防回归断言。

**Q6：如何贡献 / 报告安全漏洞？**
见 [CONTRIBUTING.md](CONTRIBUTING.md) 与 [SECURITY.md](SECURITY.md)。

---

## 📄 许可

本项目基于 **Apache License 2.0** 开源，详见 [LICENSE](LICENSE)。
Copyright © 2026 HarnessHub Contributors

---
*维护：HarnessHub 核心维护者｜版本 v0.1.0｜变更见 [CHANGELOG.md](CHANGELOG.md)*
