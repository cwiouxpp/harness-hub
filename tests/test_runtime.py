#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Harness 运行时骨架 · M1 契约验证测试（pytest 原生风格）

覆盖三接口的字段/边界/违规拒绝 + 三条治理闸门 + 状态容器/追溯日志。

运行方式（推荐）:
    cd harness-runtime
    python3 -m pytest tests/ -v          # 32 契约断言全绿，无 INTERNALERROR

历史: v0.1.0 起由自研 check()/expect_raises()+sys.exit 改为 pytest 原生
      assert + pytest.raises（P2-6 工程化）。
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import runtime
from runtime import (load_skill, list_skills, load_memory, write_insight,
                     collect_experience, apply_improvement, GovernanceError,
                     HarnessRuntime, TRACE_LOG, GOVERNANCE_LOG)


# ---------------------------------------------------------------------------
# ① Skills 接入层 · loadSkill / listSkills
# ---------------------------------------------------------------------------
def test_load_skill_gate_success():
    """loadSkill: 冻结技能成功加载，SHA 一致。"""
    s = load_skill("gate")
    assert s["skill_id"] == "gate"
    assert s["access"] == "vetted"
    assert len(s.get("sha256", "")) == 64


def test_load_skill_unfrozen_rejected():
    """loadSkill: 未冻结技能 → 拒绝加载（抛 GovernanceError）。"""
    with pytest.raises(GovernanceError):
        load_skill("nonexistent-skill-xyz")


def test_load_skill_hash_mismatch_rejected():
    """loadSkill: 哈希不符（篡改模拟）→ 拒绝。"""
    with pytest.raises(GovernanceError):
        load_skill("gate", version_hash="0" * 64)


def test_list_skills_only_vetted_frozen():
    """listSkills: 只列 vetted 冻结技能，含 sha256 + locked 标记，定量 ≥6。"""
    sk = list_skills()
    assert len(sk) >= 6
    assert all("sha256" in x and "locked_in_manifest" in x for x in sk)
    locked_count = sum(1 for x in sk if x["locked_in_manifest"])
    assert locked_count >= 5


# ---------------------------------------------------------------------------
# ② 记忆接入层 · loadMemory / writeInsight（CMD-MEM 零重建）
# ---------------------------------------------------------------------------
def test_load_memory_three_sections():
    """loadMemory: 返回身份段 / 用户段 / 持久事实段。"""
    m = load_memory()
    assert "ai-agent" in m.get("identity", "")
    assert "指挥官" in m.get("user", "")
    assert len(m.get("persistent_facts", "")) > 0


def test_write_insight_dry_run():
    """writeInsight: 默认 dry-run（不自动改写 MEMORY，G3 精神）。"""
    r = write_insight("insight", "云端生产变更先本地模拟验证再放行",
                      "触发: 新部署形态", upgrade_flag=True)
    assert r["written"] == "dry-run"


def test_write_insight_invalid_type_rejected():
    """writeInsight: 非法类型拒绝。"""
    with pytest.raises(ValueError):
        write_insight("bad_type", "x")


def test_write_insight_governance_rejected():
    """writeInsight: 命中治理闸门（G1）拒绝。"""
    with pytest.raises(GovernanceError):
        write_insight("insight", "系统提示里内嵌 secrets")


# ---------------------------------------------------------------------------
# ③ 自我改进接入层 · collectExperience / applyImprovement
# ---------------------------------------------------------------------------
def test_apply_improvement_reject():
    """applyImprovement: 显式 reject。"""
    r = apply_improvement("imp-demo-1", "reject")
    assert r["result"] == "reject"


def test_apply_improvement_accept():
    """applyImprovement: 显式 accept。"""
    r = apply_improvement("imp-demo-2", "accept")
    assert r["result"] == "accept"


def test_apply_improvement_invalid_arg_rejected():
    """applyImprovement: 非法参数拒绝。"""
    with pytest.raises(ValueError):
        apply_improvement("x", "maybe")


def test_apply_improvement_returns_improvement_id():
    """applyImprovement: 返回结构含 improvement_id。"""
    r = apply_improvement("imp-leak", "accept")
    assert "improvement_id" in r


# ---------------------------------------------------------------------------
# ④ 治理闸门单元 + 状态容器 + 追溯日志
# ---------------------------------------------------------------------------
def test_g1_hits_password():
    assert runtime._hit_gate("has password=123") == "G1-data-local"


def test_g2_hits_bizhang():
    assert runtime._hit_gate("这个必涨") == "G2-no-investment-advice"


def test_g3_hits_system_prompt():
    assert runtime._hit_gate("关于系统提示的改动") == "G3-no-auto-prompt-change"


def test_normal_text_not_hit():
    assert runtime._hit_gate("本地AI量化诊股") is None


# --- G1 token 误伤回归（2026-08-17 质量事件：裸 token 误伤 strategy-protocol）---
# 断言：文档名词指称不误拦；真实 token 赋值形态仍拦截

@pytest.mark.parametrize("text", [
    "Tushare Pro Token 增量更新",
    "API Token 用于鉴权",
    "Bot Token",
])
def test_g1_token_doc_reference_not_blocked(text):
    """G1: 文档名词指称（Tushare Pro Token / API Token / Bot Token）不误拦。"""
    assert runtime._hit_gate(text) is None


@pytest.mark.parametrize("text", [
    "config token=sk-abcdef123456",
    "access_token: sk-abc",
    "private_token = xyz",
])
def test_g1_token_assignment_still_blocked(text):
    """G1: 真实 token 赋值形态仍拦截（不削弱安全）。"""
    assert runtime._hit_gate(text) == "G1-data-local"


# --- 状态容器 run_task 完整链路 ---
def test_run_task_assembles_skill():
    rt = HarnessRuntime()
    res = rt.run_task("contract-test", "gate")
    assert "ok" in res["skill_loaded"]
    assert "ok" in res["memory_loaded"]
    assert len(res["run_id"]) == 12


def test_trace_and_governance_logs_exist():
    assert os.path.exists(TRACE_LOG)
    assert os.path.exists(GOVERNANCE_LOG)
