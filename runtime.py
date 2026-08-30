#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness 统一运行时载体（芯桥 / HarnessHub）· M1-3 运行时骨架

唯一新造物 = 运行时载体：状态容器 + 任务调度 + 追溯日志 + 治理闸门
三大接入层全部对接军团既有资产，零重建：
  ① Skills 接入层  → 共享 Skill 库 (vetted/ 冻结区 + MANIFEST + SHA 逐字节校验)
  ② 记忆接入层    → CMD-MEM (MEMORY.md 7 段模板 + memory/*.md 流水)
  ③ 自我改进接入层 → self-improving 沉淀建议 → 治理闸门回流

接口契约：对齐大咖 M1-2 规范定稿（CMD-HARNESS-MVP-2026-08-16）
作者：IT技术 | 2026-08-17
"""

__version__ = "0.1.0"
"""Harness 统一运行时载体（芯桥 / HarnessHub）— semver, 见 CHANGELOG.md"""

import hashlib
import json
import os
import re
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# 路径常量（P1 去硬编码化：全部相对安装根派生，零 ~/.openclaw 绝对路径）
# ---------------------------------------------------------------------------
# ① 安装根：默认 = 包安装目录（本文件所在目录），git clone 后无需任何 ~/.openclaw 路径即可跑通。
#    本机/企业/私有化打包可用环境变量 HARNESS_INSTALL_ROOT 显式覆盖（锚点统一）。
HARNESS_INSTALL_ROOT = os.path.dirname(os.path.abspath(__file__))
HARNESS_INSTALL_ROOT = os.path.expanduser(
    os.environ.get("HARNESS_INSTALL_ROOT", HARNESS_INSTALL_ROOT)
)

# ② Skills 库：默认派生自安装根 examples/skill-library/（自带脱敏示例，可跑通验证）。
#    真实环境用环境变量 HARNESS_SKILL_LIB_ROOT 指到真实共享库覆盖之。
SKILL_LIB_ROOT = os.path.expanduser(os.environ.get(
    "HARNESS_SKILL_LIB_ROOT",
    os.path.join(HARNESS_INSTALL_ROOT, "examples", "skill-library"),
))
VETTED_DIR = os.path.join(SKILL_LIB_ROOT, "vetted")
MANIFEST_PATH = os.path.join(SKILL_LIB_ROOT, "MANIFEST.md")

# ③ Harness 运行时自身落盘文件：默认落安装根的 data/（随包，干净克隆即可写）。
#    真实环境可用环境变量 HARNESS_DIR 覆盖落盘根（含 data/ 子目录）。
HARNESS_DIR = os.path.expanduser(os.environ.get(
    "HARNESS_DIR",
    os.path.join(HARNESS_INSTALL_ROOT, "data"),
))
TRACE_LOG = os.path.join(HARNESS_DIR, "trace.log")
GOVERNANCE_LOG = os.path.join(HARNESS_DIR, "governance.log")
IMPROVEMENT_PENDING = os.path.join(HARNESS_DIR, "improvements_pending.json")
STATE_FILE = os.path.join(HARNESS_DIR, "state.json")

# CMD-MEM: 本 Agent 记忆主文件 + 流水目录（记忆接入层对接点）
# P1 去硬编码化：默认 = 安装根 examples/sample_memory/（自带脱敏示例 MEMORY.md，可跑通验证）。
# 真实环境用环境变量 HARNESS_MEM_ROOT 覆盖到各 Agent 的 workspace（笔锋/数海/慧眼/量化/棋锋/大咖等），
# 或运行时用 set_memory_target() 切换，实现跨 Agent 记忆接入。
_MEMORY_ROOT = os.path.expanduser(os.environ.get(
    "HARNESS_MEM_ROOT",
    os.path.join(HARNESS_INSTALL_ROOT, "examples", "sample_memory"),
))


def resolve_memory_root(target: Optional[str] = None) -> str:
    """返回当前记忆目标根目录。优先级：显式参数 > 已配置全局 > 环境变量 > 默认。"""
    if target:
        return os.path.expanduser(target)
    return _MEMORY_ROOT


def set_memory_target(root: str) -> str:
    """M2-2：把 Harness 记忆接入层切到指定 Agent 的 workspace（运行时配置，跨 Agent 记忆复用）。

    例：set_memory_target("<某 Agent 的记忆根>"，如 workspace-quant) 后，load_memory 读量化 MEMORY.md。

    # 注：P1 去硬编码化前默认记忆根为 ~/.openclaw/workspace-it；现改由安装根相对派生 + env 覆盖。

    """
    global _MEMORY_ROOT
    _MEMORY_ROOT = os.path.expanduser(root)
    return _MEMORY_ROOT


MEMORY_ROOT = _MEMORY_ROOT
MEMORY_MAIN = os.path.join(MEMORY_ROOT, "MEMORY.md")
MEMORY_FLOW_DIR = os.path.join(MEMORY_ROOT, "memory")



# ---------------------------------------------------------------------------
# 数据模型（状态容器）
# ---------------------------------------------------------------------------
@dataclass
class RunContext:
    """状态容器：承载一次跨任务运行的上下文。"""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    loaded_skills: List[Dict[str, Any]] = field(default_factory=list)
    memory_snapshot: Optional[Dict[str, Any]] = None
    decision_chain: List[Dict[str, Any]] = field(default_factory=list)
    improvements_reviewed: List[Dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 治理闸门（三条合规红线）
# ---------------------------------------------------------------------------
class GovernanceError(Exception):
    """命中治理闸门时抛出：强制拦截并记日志。"""


def _governance_gates() -> List[Dict[str, Any]]:
    return [
        {
            "id": "G1-data-local",
            "desc": "数据不出服务器",
            # G1 规则说明（防误伤合法量化技能，如 strategy-protocol 提及「Tushare Pro Token」）：
            #  - 最敏感词 password/secret/api_key/private_key 保留裸匹配（合规文档中极少作名词，不可妥协）
            #  - token 最常见作名词（Tushare token/Bot Token/API Token 等均合法文档指称），
            #    收紧为【赋值形态】才拦：token\s*[=:]（如 access_token: xxx / token=sk-...）——
            #    仅"提及 Token"不拦截；连写变量名 access_token:/private_token= 亦经 token\s*[=:] 命中
            "patterns": [
                r"password", r"secret", r"api[_ ]?key", r"private[_ ]?key",
                r"token\s*[=:]",
            ],
        },
        {
            "id": "G2-no-investment-advice",
            "desc": "信号非投资建议",
            "patterns": [r"买入推荐", r"必涨", r"稳赚", r"保证收益", r"股神", r"包赚"],
        },
        {
            "id": "G3-no-auto-prompt-change",
            "desc": "改进项不自动改写系统提示/安全策略",
            "patterns": [r"system[ _]?prompt", r"系统提示", r"安全策略", r"safety[ _]?policy"],
        },
    ]


def _hit_gate(text: str) -> Optional[str]:
    """对文本做三条合规闸门扫描，命中返回 gate id，未命中返回 None。"""
    low = text.lower() if isinstance(text, str) else ""
    for g in _governance_gates():
        for p in g["patterns"]:
            if re.search(p, low):
                return g["id"]
    return None


# ---------------------------------------------------------------------------
# 追溯日志
# ---------------------------------------------------------------------------
def log_trace(kind: str, **payload: Any) -> None:
    """写追溯日志（支撑决策可追溯 ≥80%）。"""
    os.makedirs(os.path.dirname(TRACE_LOG), exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "kind": kind,
        **payload,
    }
    with open(TRACE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def log_governance(action: str, gate_id: Optional[str], detail: str) -> None:
    """写治理闸门命中/拦截记录。"""
    os.makedirs(os.path.dirname(GOVERNANCE_LOG), exist_ok=True)
    entry = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "gate": gate_id,
        "detail": detail,
    }
    with open(GOVERNANCE_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _persist_state(ctx: RunContext) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(asdict(ctx), f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# ① Skills 接入层 —— loadSkill / listSkills
# ---------------------------------------------------------------------------
def _load_manifest() -> Dict[str, str]:
    """解析 MANIFEST.md，返回 { 技能名: 该技能 SKILL.md 的 sha256 }。

    兼容两种登记风格：
      A) 段头带技能名：`### gate v1.0.1 · 文件 SHA-256` + `| SKILL.md | sha |`
         → 键 = 段头首个词 gate
      B) 批量段头无技能名：`### harness-quant M3 批次` + `| strategy-protocol/SKILL.md | sha |`
         → 键 = 行内相对路径首段 strategy-protocol
    """
    if not os.path.exists(MANIFEST_PATH):
        return {}
    lines = open(MANIFEST_PATH, encoding="utf-8").read().splitlines()
    result: Dict[str, str] = {}
    current_section = None
    for line in lines:
        # 段头：`### xxx v1.0.0 · 文件 SHA-256`
        sec = re.match(r"^###\s+(.+?)(?:\s+v[\d.]+)?\s*·", line)
        if sec:
            current_section = sec.group(1).strip()
            continue
        if current_section is None:
            continue
        # `| SKILL.md | sha |`（段头式）
        m1 = re.match(r"^\|\s*SKILL\.md\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
        if m1:
            result[current_section] = m1.group(1)
            continue
        # `| <skill>/SKILL.md | sha |`（批量式，取路径首段为技能名）
        m2 = re.match(r"^\|\s*([^/`|]+)/SKILL\.md\s*\|\s*`([0-9a-f]{64})`\s*\|", line)
        if m2:
            result[m2.group(1)] = m2.group(2)
    return result



def _skill_candidates() -> List[Dict[str, Any]]:
    """枚举 vetted/ 冻结区中的所有技能目录。"""
    cands = []
    if not os.path.isdir(VETTED_DIR):
        return cands
    # vetted/<skill>/SKILL.md 与 vetted/<category>/<skill>/SKILL.md 都支持
    for cat in sorted(os.listdir(VETTED_DIR)):
        cat_path = os.path.join(VETTED_DIR, cat)
        if os.path.isdir(cat_path):
            # 直接技能目录
            sk = os.path.join(cat_path, "SKILL.md")
            if os.path.isfile(sk):
                cands.append({"name": cat, "skill_path": sk, "category": "general"})
            else:
                # 分类下的技能
                for skill in sorted(os.listdir(cat_path)):
                    ssk = os.path.join(cat_path, skill, "SKILL.md")
                    if os.path.isfile(ssk):
                        cands.append({"name": skill, "skill_path": ssk, "category": cat})
    return cands


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def list_skills(category: Optional[str] = None, tier: Optional[str] = None) -> List[Dict[str, Any]]:
    """M1-2 listSkills：只列 vetted 冻结技能，含 SHA/版本/vetter 状态。"""
    manifest = _load_manifest()  # {技能名: sha}
    out = []
    for cand in _skill_candidates():
        if category and cand["category"] != category:
            continue
        sha = sha256_file(cand["skill_path"])
        locked_sha = manifest.get(cand["name"])
        out.append({
            "skill_id": cand["name"],
            "category": cand["category"],
            "sha256": sha,
            "version": "v1.0.0",
            "vetter_status": "vetted" if locked_sha else "vetted(enumerated)",
            "locked_in_manifest": bool(locked_sha),
        })
    return out


def load_skill(skill_name: str, version_hash: Optional[str] = None) -> Dict[str, Any]:
    """M1-2 loadSkill：必须命中 vetted 冻结区 + MANIFEST + SHA 逐字节一致。

    违规（未冻结 / 哈希不符 / 找不到 / 命中治理闸门）→ 拒绝加载并入追溯日志。
    """
    # 1. 找到技能目录
    cand = None
    for c in _skill_candidates():
        if c["name"] == skill_name:
            cand = c
            break
    if cand is None:
        log_trace("loadSkill_rejected", skill=skill_name, reason="未在 vetted 冻结区")
        raise GovernanceError(f"[Skills] 技能 '{skill_name}' 未冻结，拒绝加载")

    path = cand["skill_path"]
    actual_sha = sha256_file(path)

    # 2. MANIFEST 锁定校验
    manifest = _load_manifest()  # {技能名: sha}
    locked_sha = manifest.get(skill_name)
    if not locked_sha:
        log_trace("loadSkill_rejected", skill=skill_name, reason="未在 MANIFEST 登记")
        raise GovernanceError(f"[Skills] 技能 '{skill_name}' 未在 MANIFEST 登记，拒绝加载")

    # 3. SHA 逐字节一致
    if actual_sha != locked_sha:
        log_trace("loadSkill_rejected", skill=skill_name,
                  reason="哈希不符", actual=actual_sha, locked=locked_sha)
        raise GovernanceError(f"[Skills] 技能 '{skill_name}' 哈希不符，拒绝加载")

    # 4. 可选：调用方指定 version_hash 也必须匹配
    if version_hash and version_hash != actual_sha:
        log_trace("loadSkill_rejected", skill=skill_name, reason="version_hash 不匹配")
        raise GovernanceError(f"[Skills] 技能 '{skill_name}' version_hash 不匹配")

    # 5. 内容读取 + 治理闸门
    content = open(path, encoding="utf-8").read()
    gate = _hit_gate(content)
    if gate:
        log_governance("loadSkill_blocked", gate, skill_name)
        raise GovernanceError(f"[Skills] 技能 '{skill_name}' 命中治理闸门 {gate}")

    log_trace("loadSkill_ok", skill=skill_name, sha256=actual_sha, category=cand["category"])
    return {
        "skill_id": skill_name,
        "content": content,
        "sha256": actual_sha,
        "category": cand["category"],
        "access": "vetted",
    }


# ---------------------------------------------------------------------------
# ② 记忆接入层 —— loadMemory / writeInsight（直接对接 CMD-MEM，零重建）
# ---------------------------------------------------------------------------
def load_memory(memory_root: Optional[str] = None) -> Dict[str, Any]:
    """M1-2 loadMemory：读取 CMD-MEM 主文件，高价值段（持久事实/摘要沉淀）优先命中。
    支持 memory_root 参数/全局配置/env 指定各 Agent 记忆。"""
    root = resolve_memory_root(memory_root)
    main = os.path.join(root, "MEMORY.md")
    if not os.path.exists(main):
        log_trace("loadMemory_failed", reason="MEMORY.md 不存在", root=root)
        raise FileNotFoundError(f"MEMORY.md 不存在: {main}")
    text = open(main, encoding="utf-8").read()

    def _section(title: str) -> str:
        m = re.search(r"##\s*" + re.escape(title) + r"\s*(.*?)(?=\n##\s|\Z)", text, re.S)
        return m.group(1).strip() if m else ""

    # 摘要沉淀行提取（`[correction] ...` / `[insight] ...` 反引号包裹）
    insights = []
    for line in text.splitlines():
        if re.match(r"^\s*-\s*`\[(correction|insight|best_practice|knowledge_gap)\]", line):
            insights.append(line.strip())

    snap = {
        "identity": _section("📌 身份"),
        "user": _section("👤 用户"),
        "persistent_facts": _section("🧠 持久事实"),
        "summary_insights": insights,
    }
    log_trace("loadMemory_ok", source=main, root=root, insights_count=len(insights))
    return snap


def write_insight(type_: str, content: str, trigger_condition: str = "",
                  upgrade_flag: bool = False, memory_root: Optional[str] = None) -> Dict[str, str]:
    """M1-2 writeInsight：按 CMD-MEM 摘要沉淀格式写入指定段位，不破坏模板。

    支持从指定文件读取或追加到 MEMORY.md 的【摘要沉淀】段。（骨架：校验+记录+可选落盘）
    注意：M1-3 骨架默认【不自动改写 MEMORY.md】（治理闸门 G3 精神），
    仅在 enable_write=True 时追加，否则返回 dry-run 结果供上层人工确认。
    memory_root 支持 M2-2 跨 Agent 记忆目标。
    """
    root = resolve_memory_root(memory_root)
    valid_types = {"correction", "insight", "best_practice", "knowledge_gap"}
    if type_ not in valid_types:
        raise ValueError(f"type 必须是 {sorted(valid_types)} 之一")

    gate = _hit_gate(content)
    if gate:
        log_governance("writeInsight_blocked", gate, type_)
        raise GovernanceError(f"[记忆] 沉淀内容命中治理闸门 {gate}")

    entry = {
        "type": type_,
        "content": content,
        "trigger_condition": trigger_condition,
        "upgrade_flag": upgrade_flag,
    }
    log_trace("writeInsight_candidate", **entry)
    return {"written": "dry-run", "section": "摘要沉淀",
            "note": "骨架默认不自动改写 MEMORY.md，交由上层人工确认后落盘"}


# ---------------------------------------------------------------------------
# ③ 自我改进接入层 —— collectExperience / applyImprovement
# ---------------------------------------------------------------------------
def collect_experience(source: Optional[str] = None) -> List[Dict[str, Any]]:
    """M1-2 collectExperience：从追溯日志 + self-improving 沉淀收集去重候选改进项。

    支持两类输入（M2-3 串联 self-improving 资产）：
      A) CMD-MEM 摘要沉淀 🆙 行（现状保留）
      B) self-improving 资产格式：`## [LRN-xxx] category` / `## [ERR-xxx]` / `## [FR-xxx]`
         仅提取 Status=pending/in_progress 的未处理项（Summary 作建议），已解决/已提升不重复采集。
    """
    items: List[Dict[str, Any]] = []
    if source and os.path.exists(source):
        text = open(source, encoding="utf-8").read()
        # B) self-improving 条目式格式（M2-3 新增）
        _parse_self_improving(text, os.path.basename(source), items)
        # A) 🆙 行（CMD-MEM 沉淀）
        for line in text.splitlines():
            if "🆙" in line and not items:
                items.append({
                    "suggest": line.strip(),
                    "evidence": os.path.basename(source),
                    "risk": "low",
                    "upstream_flag": True,
                })
    # 2) 兜底: 从本次追溯日志中 writeInsight_candidate 沉淀候选（带 upgrade_flag）
    if os.path.exists(TRACE_LOG):
        for ln in open(TRACE_LOG, encoding="utf-8"):
            try:
                e = json.loads(ln)
            except Exception:
                continue
            if e.get("kind") == "writeInsight_candidate" and e.get("upgrade_flag"):
                items.append({
                    "suggest": e.get("content", ""),
                    "evidence": "trace-log",
                    "risk": "low",
                    "upstream_flag": True,
                })
    return _dedup(items)


def _parse_self_improving(text: str, srcname: str, out: List[Dict[str, Any]]) -> None:
    """M2-3：解析 self-improving 资产（LEARNINGS.md/ERRORS.md/FEATURE_REQUESTS.md）条目。
    条目头 `## [LRN-xxx] category` 或 `## [ERR-xxx]`；提取 pending/in_progress 未处理项。
    """
    blocks = re.split(r"\n(?=##\s\[)", text)
    for b in blocks:
        if not re.match(r"##\s\[[A-Za-z]{2,3}-\d+", b):
            continue
        status = re.search(r"\*\*Status\*\*:\s*(\S+)", b)
        st = status.group(1).lower() if status else ""
        # 只采集未处理项；已解决/放弃/提升的不重复采集
        if st not in {"pending", "in_progress"}:
            continue
        sum_m = re.search(r"(?:\*\*Summary\*\*|###\s*Summary)\s*\n(.+?)(?:\n\n|\Z)", b, re.S)
        suggest = " ".join(sum_m.group(1).strip().split()) if sum_m else b[:120].replace("\n", " ")
        lrn_id = re.search(r"##\s\[([A-Za-z]{2,3}-\d+)\]", b)
        out.append({
            "suggest": suggest[:300],
            "evidence": f"{srcname}#{lrn_id.group(1)}" if lrn_id else srcname,
            "risk": "medium",
            "upstream_flag": False,
        })


def _dedup(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for it in items:
        key = it.get("suggest", "")
        if key and key not in seen:
            seen.add(key)
            out.append(it)
    return out


def apply_improvement(improvement_id: str, accept_reject: str) -> Dict[str, Any]:
    """M1-2 applyImprovement：默认 reject，须显式确认。

    闸门：命中合规红线 → 强制 reject 并记日志；接受项才回流对应层。
    骨架默认【不自动落盘生效】（不改系统提示/安全策略），记录审批轨迹。
    """
    # 待审件（骨架从 pending 文件读，无则空）
    pending = []
    if os.path.exists(IMPROVEMENT_PENDING):
        try:
            pending = json.load(open(IMPROVEMENT_PENDING, encoding="utf-8"))
        except Exception:
            pending = []

    item = next((p for p in pending if p.get("id") == improvement_id), None)
    if item is None:
        # 允许直接构造一条（演示用）
        item = {"id": improvement_id, "suggest": f"改进项 {improvement_id}", "risk": "low"}

    if accept_reject not in ("accept", "reject"):
        raise ValueError("accept_reject 必须是 accept 或 reject")

    # 治理闸门
    gate = _hit_gate(item.get("suggest", ""))
    if gate:
        log_governance("applyImprovement_forced_reject", gate, improvement_id)
        return {"improvement_id": improvement_id, "result": "reject",
                "reason": f"命中治理闸门 {gate}（强制 reject）"}

    decision = "accept" if accept_reject == "accept" else "reject"
    log_trace("applyImprovement", improvement_id=improvement_id, decision=decision)
    return {"improvement_id": improvement_id, "result": decision,
            "note": "骨架记录审批轨迹，接受项回流需上层结合业务上下文实施"}


# ---------------------------------------------------------------------------
# 统一运行载体入口 —— 串行调度三接入层
# ---------------------------------------------------------------------------
class HarnessRuntime:
    """默认状态容器 + 任务调度的统一载体。"""

    def __init__(self):
        self.ctx = RunContext()

    def run_task(self, task_label: str, skill_name: str,
                 memory_source: Optional[str] = None,
                 memory_root: Optional[str] = None) -> Dict[str, Any]:
        """一次跨任务运行：加载记忆快照 → 装配冻结技能 → 采集改进候选。
        memory_root 供 M2-2 跨 Agent 记忆目标（默认跟随全局配置/env）。"""
        # 记忆快照
        try:
            self.ctx.memory_snapshot = load_memory(memory_root)
            mem_note = "ok"
        except Exception as e:
            mem_note = f"fail:{e}"
            self.ctx.memory_snapshot = {"note": mem_note}

        # 装配冻结技能
        try:
            skill = load_skill(skill_name)
            self.ctx.loaded_skills.append({
                "skill_id": skill["skill_id"],
                "sha256": skill["sha256"],
                "category": skill["category"],
            })
            skill_note = "ok"
        except GovernanceError as e:
            skill_note = f"rejected:{e}"

        # 改进候选
        improvements = collect_experience(memory_source)

        self.ctx.decision_chain.append({
            "task": task_label,
            "skill": skill_name,
            "skill_note": skill_note,
            "memory_note": mem_note,
        })
        _persist_state(self.ctx)

        return {
            "run_id": self.ctx.run_id,
            "task": task_label,
            "skill_loaded": skill_note,
            "memory_loaded": mem_note,
            "improvements_count": len(improvements),
        }


if __name__ == "__main__":
    # 命令行自检：python3 runtime.py list|run <skill>|selftest
    if len(sys.argv) >= 2 and sys.argv[1] == "list":
        for s in list_skills():
            print(f"  {s['skill_id']:20s} cat={s['category']:10s} sha={s['sha256'][:12]} locked={s['locked_in_manifest']}")
    elif len(sys.argv) >= 3 and sys.argv[1] == "run":
        rt = HarnessRuntime()
        print(json.dumps(rt.run_task("selftest", sys.argv[2]), ensure_ascii=False, indent=2))
    else:
        print("用法: runtime.py list | run <skill_name> | selftest")
