#!/usr/bin/env python3
"""
proof_v360_root_trust_defects.py — механические пробы ROOT TRUST слоя
ветки JOHNSON v3.6.0 ROOT_TRUST (sha256 0a950025…), закрываемые в v3.8.0.

Урок series (worklog Task 5–8): тест на соседний механизм ≠ покрытие production
path нужного инварианта. Ветка ROOT_TRUST проходит 98/98 selftest, НО:

  N-RT3 DEAD-WIRING     RootTrustAuthority/RootEpoch упоминаются ТОЛЬКО в
                        selftest (_root_hardening_tests) — ноль вызовов из
                        Agent/Governor/commit-пути. CHANGELOG заявляет
                        «in-runtime trust-history layer» — production COMMIT
                        не несёт ни эпохи, ни отпечатка корня.
  N-RT1 TRUNCATION      verify_history проверяет e.epoch==i — усечение ХВОСТА
                        истории проходит; тест T97 ветки проверяет лишь
                        «digest differs», а не отклонение усечённой истории.
                        Без внешнего пина дайджеста усечение НЕОБНАРУЖИМО —
                        и пина на production-пути нет.
  N-RT2 DOUBLE-REVOKE   revoke_current от уже отозванного корня принимается
                        молча (повторная «ревокация» — инвариант нарушен).
  N-RT4 EXCEPTION       RootTrustError(Exception) — НЕ наследник
                        KnowledgeLedgerError: при вшивании в COMMIT отказ
                        вырвался бы из except-контракта runtime (класс
                        дефекта N-CLS из Task 6).

Пробы гоняют production-формы (Agent e2e / COMMIT-гейт), а не hand-made
состояния. Запуск: python proof_v360_root_trust_defects.py <agent_py>
"""
import importlib.util
import json as _json
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("target_agent", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["target_agent"] = mod
    spec.loader.exec_module(mod)
    return mod


def _chain_cls(mod):
    """Класс истории корневых эпох: v3.8.0 → RootEpochChain; ветка ROOT_TRUST →
    RootTrustAuthority; ветка TRUST_DOMAIN → нет (проба неприменима)."""
    for name in ("RootEpochChain", "RootTrustAuthority"):
        cls = getattr(mod, name, None)
        if cls is not None and hasattr(cls, "genesis") and hasattr(cls, "revoke_current"):
            return cls
    return None


def p1_dead_wiring(mod) -> bool:
    """N-RT3: живой runtime COMMIT не вшивает корневую эпоху никуда."""
    with tempfile.TemporaryDirectory(prefix="prt_wiring_") as td:
        cfg, ws = mod._fresh_cfg(td)
        Path(ws).mkdir(parents=True, exist_ok=True)
        script = [
            {"thought": "План.", "status": "plan",
             "success_criteria": ["hello.txt содержит 'final'"],
             "plan": ["запись"]},
            {"thought": "Пишу.", "status": "act",
             "actions": [{"name": "write_file", "args": {"path": "hello.txt", "content": "final"}}]},
            {"thought": "Готово.", "status": "final", "outcome": "verified",
             "final_answer": "готово", "lesson": "wiring"},
        ]
        audit = mod.AuditChain(Path(td) / "a.jsonl")
        agent = mod.Agent(cfg, mod.MockBrain(script), mod.Governor(cfg, audit), audit)
        result = agent.solve("создай hello.txt со строкой final")
        if result["outcome"] != "verified":
            raise RuntimeError("сценарий не дошёл до verified — проба неприменима")
        w = _json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
        chain = w.get("root_epoch_chain")
        proof_epoch = (w.get("proof") or {}).get("root_epoch", -1)
        commit_epoch = (w.get("commit") or {}).get("root_epoch", -1)
        led_epoch = None
        led_path = w.get("_knowledge_ledger_path")
        if led_path and Path(led_path).exists():
            rows = [r for r in mod.ImmutableKnowledgeLedger(Path(led_path))._rows()
                    if r.get("event") == "COMMIT"]
            if rows:
                led_epoch = rows[0]["payload"].get("root_epoch", -1)
        # ДЕФЕКТ: ни цепи в состоянии, ни эпохи в proof/commit/ledger
        return not chain or proof_epoch < 0 or commit_epoch < 0 or (led_epoch is not None and led_epoch < 0)


def p2_truncation_undetected(mod) -> bool:
    """N-RT1: усечение хвоста корневой истории доходит до COMMIT необнаруженным."""
    cls = _chain_cls(mod)
    if cls is None:
        return False  # слоя нет — проба неприменима к TRUST_DOMAIN
    with tempfile.TemporaryDirectory(prefix="prt_trunc_") as td:
        st = {"_cas_version": 0,
              "criteria": ["capability:write_file выполнена"],
              "required_capabilities": ["write_file"],
              "ledger": [{"step": 1, "action": "write_file", "ok": True,
                          "kind": "write", "obs_brief": "created"}]}
        h = [cls.genesis("ROOT-A", "t0")]
        h = cls.rotate(h, "ROOT-B", "t1")
        h = cls.rotate(h, "ROOT-C", "t2")
        pin = cls.history_digest(h) if hasattr(cls, "history_digest") else "0" * 64
        # Тампер: пин от ПОЛНОЙ истории, в состоянии — УСЕЧЁННАЯ (хвост снят)
        st["root_epoch_chain"] = [asdict(e) for e in h[:2]]
        st["root_epoch_chain_pin"] = pin
        p = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(p)
        try:
            mod.ProofCarryingGovernor.commit(st)
        except Exception:
            return False  # COMMIT отклонён — усечение обнаружено (здоровое поведение)
        return True      # ДЕФЕКТ: COMMIT прошёл при усечённой истории


def p3_double_revoke(mod) -> bool:
    """N-RT2: повторный revoke того же корня принимается молча."""
    cls = _chain_cls(mod)
    if cls is None:
        return False
    h = [cls.genesis("A", "t0")]
    h1 = cls.revoke_current(h)
    try:
        cls.revoke_current(h1)
    except Exception:
        return False  # отклонён (здоровое поведение)
    return True       # ДЕФЕКТ: двойной revoke принят


def p4_exception_contract(mod) -> bool:
    """N-RT4: RootTrustError вне ledger-контракта исключений."""
    err = getattr(mod, "RootTrustError", None)
    base = getattr(mod, "KnowledgeLedgerError", None)
    if err is None or base is None:
        return False  # неприменимо
    return not issubclass(err, base)  # ДЕФЕКТ: не наследник


def main(target: str) -> int:
    mod = load_module(target)
    print(f"═══ ПРОБЫ против {target} ═══")
    probes = [
        ("P1 N-RT3 DEAD-WIRING: корневая эпоха не вшивается в COMMIT", p1_dead_wiring),
        ("P2 N-RT1 TRUNCATION: усечение истории проходит COMMIT", p2_truncation_undetected),
        ("P3 N-RT2 DOUBLE-REVOKE: повторный revoke принят", p3_double_revoke),
        ("P4 N-RT4 EXCEPTION: RootTrustError вне ledger-контракта", p4_exception_contract),
    ]
    reproduced = 0
    for name, fn in probes:
        try:
            ok = fn(mod)
            print(f"[{'REPRODUCED' if ok else 'NOT-REPRODUCED'}]  {name}")
            reproduced += bool(ok)
        except Exception as exc:
            print(f"[N/A] {name} :: {type(exc).__name__}: {exc}")
    print(f"═══ Итог: {reproduced}/{len(probes)} дефектов ВОСПРОИЗВЕЛИСЬ ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
