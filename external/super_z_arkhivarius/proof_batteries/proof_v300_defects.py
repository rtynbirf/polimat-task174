#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Механическое доказательство дефектов загруженной ветки v2.9.0/v3.0.0.

Проверяются три подозрения:
  D1  «Двойной префикс id missing-claim»: ProofCompiler.compile() формирует
      "claim:claim:1:derivation_missing" и при извлечении даёт "claim:claim:1",
      который НЕ совпадает с узлами claim_dependencies ("claim:1").
      Следствие: propagation по зависимостям не срабатывает, epistemic_blockers
      пуст — заявленная диагностика v2.9.0 («система сохраняет конкретных
      блокеров») не работает в реальном контуре ProofCompiler.
  D2  «Висячая зависимость не блокирует»: все claims покрыты evidence, но
      claim:2 зависит от claim:99, которого не существует и который никогда
      не будет доказан. Статус = verified, UNKNOWN не распространяется.
      Нарушение инварианта Unknown(x) ∧ Depends(y,x) ⇒ ¬Certain(y).
  D3  «Covered claim с непокрытой зависимостью сохраняет valid derivation»:
      claim:2 покрыт своим evidence, но его предпосылка claim:1 UNKNOWN —
      в state["derivations"] деривация claim:2 остаётся valid=True.

Запуск: python proof_v300_defects.py <path_to_polymath_agent.py>
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
        print("usage: proof_v300_defects.py <polymath_agent.py>")
        return 2
    mod = load(sys.argv[1])
    pc = mod.ProofCompiler
    edg = mod.EpistemicDependencyGraph

    results = []

    # ---------------- D1: double prefix + пустые epistemic_blockers ----------------
    st = {
        "criteria": [
            "capability:write_file выполнена",     # claim:1 — НЕТ evidence
            "capability:read_file выполнена",      # claim:2 — покрыт, зависит от claim:1
            "capability:read_file завершена",      # claim:3 — покрыт, зависит от claim:2
        ],
        "required_capabilities": [],
        "claim_dependencies": {"claim:2": ["claim:1"], "claim:3": ["claim:2"]},
        "ledger": [
            {"step": 1, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"},
            {"step": 2, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok3"},
        ],
    }
    proof = pc(st).compile()
    raw_missing = [x for x in proof.unknowns if x.endswith(":derivation_missing")]
    blockers = st.get("epistemic_blockers", {})
    dep_unknowns = [x for x in proof.unknowns if x.endswith(":dependency_unknown")]

    d1_prefix_broken = any(not x.startswith("claim:claim:") or x.count("claim:") != 2 for x in [])  # placeholder
    # Форма исходного missing-claim в unknowns:
    double_prefixed_raw = bool(raw_missing) and all(x.startswith("claim:claim:") for x in raw_missing)
    # Блокеры, которых МЫ ожидаем по семантике v2.9.0:
    expect_blockers = {"claim:2": ["claim:1"], "claim:3": ["claim:2", "claim:1"]}
    blockers_ok = blockers == expect_blockers
    # Dependency-unknown для зависимых покрытых claims:
    dep2_marked = any(x in ("claim:2:dependency_unknown",) for x in dep_unknowns)
    dep3_marked = any(x in ("claim:3:dependency_unknown",) for x in dep_unknowns)

    results.append(("D1a", "missing-claim id двойным префиксом в unknowns",
                    double_prefixed_raw,
                    f"unknowns={raw_missing}"))
    results.append(("D1b", "epistemic_blockers пуст вместо конкретных блокеров",
                    blockers_ok is False and blockers == {},
                    f"epistemic_blockers={blockers} (ожидалось {expect_blockers})"))
    results.append(("D1c", "claim:2/claim:3 не помечены dependency_unknown (точная форма id)",
                    (not dep2_marked) or (not dep3_marked),
                    f"dep_unknowns={dep_unknowns}"))

    # ---------------- D2: dangling dependency не блокирует verified ----------------
    st2 = {
        "criteria": [
            "capability:write_file выполнена",     # claim:1 — покрыт
            "capability:read_file выполнена",      # claim:2 — покрыт, зависит от несуществующего claim:99
        ],
        "required_capabilities": [],
        "claim_dependencies": {"claim:2": ["claim:99"]},
        "ledger": [
            {"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "ok1"},
            {"step": 2, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"},
        ],
    }
    proof2 = pc(st2).compile()
    results.append(("D2", "висячая зависимость claim:99 не мешает status=verified",
                    proof2.status == "verified",
                    f"status={proof2.status}, unknowns={proof2.unknowns}"))

    # ---------------- D3: covered claim с UNKNOWN-предпосылкой держит valid=True ----------------
    st3 = {
        "criteria": [
            "capability:write_file выполнена",     # claim:1 — НЕТ evidence (корень UNKNOWN)
            "capability:read_file выполнена",      # claim:2 — покрыт, зависит от claim:1
        ],
        "required_capabilities": [],
        "claim_dependencies": {"claim:2": ["claim:1"]},
        "ledger": [
            {"step": 1, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"},
        ],
    }
    pc(st3).compile()
    derivs = st3.get("derivations", [])
    d2 = [d for d in derivs if d.get("claim_id") == "claim:2"]
    results.append(("D3", "деривация зависимого claim:2 остаётся valid=True при UNKNOWN-предпосылке",
                    bool(d2) and d2[0].get("valid") is True,
                    f"derivation(claim:2)={d2}"))

    # ---------------- Вердикт ----------------
    print("=" * 78)
    print("МЕХАНИЧЕСКАЯ ПРОВЕРКА ДЕФЕКТОВ:", sys.argv[1])
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
