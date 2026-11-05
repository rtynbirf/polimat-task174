#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Механическое доказательство дефектов v3.1.0 (фундамент).

  D4  «Мёртвая механика свежести»: EvidenceContract.max_age_seconds существует,
      но ProofCompiler.contracts() никогда его не выставляет → evidence с любой
      датой наблюдения (годы назад) закрывает claim. I28 TEMPORAL_VALIDITY —
      декларация, а не механика. Следствие: stale-и-unknown сливаются —
      честная диагностика невозможна.
  D5  «Отсутствие политики циклов»: эпистемические циклы зависимостей
      (A↔B) не отклоняются; циркулярная поддержка получает status=verified
      и проходит Proof-Carrying COMMIT. Нарушение I27 PROOF_CLOSURE
      (в v2.9.0-ветке TMS-линии циклы отклонялись механически).

Запуск: python proof_v310_defects.py <polymath_agent.py>
"""
import importlib.util
import sys


def load(path):
    spec = importlib.util.spec_from_file_location("poly_target", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    if len(sys.argv) < 2:
        print("usage: proof_v310_defects.py <polymath_agent.py>")
        return 2
    mod = load(sys.argv[1])
    pc = mod.ProofCompiler
    results = []

    # ------------- D4: stale evidence закрывает claim (свежесть мертва) -------------
    st = {
        "criteria": ["capability:write_file выполнена"],
        "required_capabilities": ["write_file"],
        "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                    "obs_brief": "created", "ts": "2020-01-01T00:00:00+00:00"}],
    }
    p = pc(st).compile()
    stale_reason = any(x.endswith(":stale_evidence") for x in p.unknowns)
    results.append(("D4", "evidence 6-летней давности даёт status=verified (свежесть не участвует)",
                    p.status == "verified" and not stale_reason,
                    f"status={p.status}, unknowns={p.unknowns}"))

    # ------------- D5: эпистемический цикл не отклоняется -------------
    st2 = {
        "criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
        "required_capabilities": [],
        "claim_dependencies": {"claim:1": ["claim:2"], "claim:2": ["claim:1"]},
        "ledger": [
            {"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "ok1"},
            {"step": 2, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"},
        ],
    }
    p2 = pc(st2).compile()
    cycles_recorded = bool(st2.get("claim_dependency_cycles"))
    results.append(("D5", "цикл зависимостей claim:1↔claim:2 не мешает status=verified",
                    p2.status == "verified" and not cycles_recorded,
                    f"status={p2.status}, unknowns={p2.unknowns}, cycles={st2.get('claim_dependency_cycles')}"))

    print("=" * 78)
    print("МЕХАНИЧЕСКАЯ ПРОВЕРКА ДЕФЕКТОВ ФУНДАМЕНТА:", sys.argv[1])
    print("=" * 78)
    n_bad = 0
    for code, descr, reproduced, detail in results:
        verdict = "ВОСПРОИЗВЁДСЯ" if reproduced else "не воспроизвёлся"
        if reproduced:
            n_bad += 1
        print(f"[{code}] {descr}")
        print(f"      {verdict}: {detail}")
    print("-" * 78)
    print(f"Дефектов воспроизвелось: {n_bad} / {len(results)}")
    return 0 if n_bad else 1


if __name__ == "__main__":
    sys.exit(main())
