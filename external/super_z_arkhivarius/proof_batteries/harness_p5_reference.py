#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harness_p5_reference.py — эталонный перенос обеих проб P5 на конституцию
battery_harness (Task 12). Показывает механическую классификацию на живых
ветках и zero-flip регрессию против исторической bool-матрицы Task 11.

Сценарии те же, что в proof_v330_defects.p5_artifact_mutation_invisible и
proof_v340_defects.p5_stale_revoked_label, но вердикт теперь четырёхзначный,
а «закрыт» требует трёх свидетелей.

Прогон: python3 harness_p5_reference.py
"""
import importlib.util
import sys
import tempfile
from dataclasses import asdict as dc_asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from battery_harness import (Verdict, Witnesses, classify, as_bool,
                             refusal_is_semantic, ARTIFACT_REFUSAL_MARKERS,
                             ProbeReport, Battery)

BRANCHES = [
    ("v3.3.0",   "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.0.py"),
    ("v3.3.1",   "/home/z/my-project/download/polymath_agent_v3.3.1.py"),
    ("v3.3.2",   "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.2.py"),
    ("v3.3.3",   "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.3.py"),
    ("v3.4.0",   "/home/z/my-project/download/polymath_agent_v3.4.0.py"),
    ("v3.6.0td", "/home/z/my-project/audit_v360_root/trust_domain/polymath_agent_JOHNSON_v3.6.0.py"),
    ("v3.6.0rt", "/home/z/my-project/audit_v360_root/root_trust/polymath_agent_JOHNSON_v3.6.0.py"),
    ("v3.7.0",   "/home/z/my-project/download/polymath_agent_v3.7.0.py"),
    ("v3.8.0",   "/home/z/my-project/download/polymath_agent_v3.8.0.py"),
]

# Историческая bool-матрица (Task 11, rev2-батареи): True = дефект воспроизводился.
# None = исторически [ERROR] (v340-P5 на v3.3.1) — bool не существовал.
HISTORICAL_BOOL = {
    "v3.3.0":   {"nart": True,  "stale": False},
    "v3.3.1":   {"nart": False, "stale": None},
    "v3.3.2":   {"nart": False, "stale": False},
    "v3.3.3":   {"nart": False, "stale": False},
    "v3.4.0":   {"nart": False, "stale": False},
    "v3.6.0td": {"nart": False, "stale": False},
    "v3.6.0rt": {"nart": False, "stale": False},
    "v3.7.0":   {"nart": False, "stale": False},
    "v3.8.0":   {"nart": False, "stale": False},
}


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def clean(state: dict) -> dict:
    return {k: v for k, v in state.items()
            if k not in ("proof", "commit", "epistemic_reconciliation")}


# ─────────────────────────── P5/N-ART (v330) через харнес ───────────────────
def p5_nart(mod) -> ProbeReport:
    NAME = "P5/N-ART (v330): мутация артефакта невидима COMMIT'у"
    try:
        art = Path(tempfile.mkdtemp()) / "art.txt"
        art.write_text("ORIGINAL", encoding="utf-8")

        def fresh_state():
            return {"criteria": ["capability:write_file выполнена"],
                    "required_capabilities": ["write_file"],
                    "ledger": [{"step": 1, "action": "write_file", "ok": True,
                                "kind": "write", "obs_brief": "created"}],
                    "_artifact_paths": [str(art)], "_cas_version": 0}

        # W2: позитивный контроль — тот же сценарий БЕЗ мутации обязан быть принят
        st_ctl = fresh_state()
        st_ctl["proof"] = dc_asdict(mod.ProofCompiler(st_ctl).compile())
        control_ok = True
        try:
            mod.ProofCarryingGovernor.commit(st_ctl)
        except mod.ProofCarryingCommitError:
            control_ok = False

        # боевой сценарий: мутация мира ПОСЛЕ наблюдения
        st = fresh_state()
        st["proof"] = dc_asdict(mod.ProofCompiler(st).compile())
        art.write_text("EVIL — мир изменился после наблюдения", encoding="utf-8")
        try:
            mod.ProofCarryingGovernor.commit(st)
            return ProbeReport(NAME, Verdict.REPRODUCED,
                               detail="COMMIT прошёл мимо мутации мира")
        except Exception as e:  # noqa: BLE001
            w3ok, w3why = refusal_is_semantic(
                e, mod.ProofCarryingCommitError, ARTIFACT_REFUSAL_MARKERS)
            w = Witnesses(applicability=True, positive_control=control_ok,
                          refusal_semantics=w3ok,
                          notes={"w2": "" if control_ok else "— честный COMMIT отклонён",
                                 "w3": w3why})
            verdict, why = classify(False, w)
            return ProbeReport(NAME, verdict, detail=f"{why} | отказ: {w3why}", witnesses=w)
    except Exception as e:  # noqa: BLE001 — сбой прибора
        return ProbeReport(NAME, Verdict.ERROR, detail=f"{type(e).__name__}: {e}")


# ─────────────────────────── P5/STALE (v340) через харнес ───────────────────
def p5_stale(mod) -> ProbeReport:
    NAME = "P5/STALE (v340): REVOKED не закрывается re-commit'ом"
    try:
        art = Path(tempfile.mkdtemp()) / "r.txt"
        art.write_text("ORIGINAL", encoding="utf-8")

        def fresh_state():
            return {"criteria": ["capability:write_file выполнена"],
                    "required_capabilities": ["write_file"],
                    "ledger": [{"step": 1, "action": "write_file", "ok": True,
                                "kind": "write", "obs_brief": "w",
                                "artifact_path": str(art),
                                "artifact_sha256": mod.sha256_hex(b"ORIGINAL")}],
                    "_artifact_paths": [str(art)], "_cas_version": 0}

        # Шаг 1: честный коммит — преусловие всей пробы (W1)
        st = fresh_state()
        st["proof"] = dc_asdict(mod.ProofCompiler(st).compile())
        try:
            mod.ProofCarryingGovernor.commit(st)
        except mod.ProofCarryingCommitError as e:
            w = Witnesses(notes={"w1": f"— честный COMMIT #1 отклонён: {e}"})
            verdict, why = classify(False, w)
            return ProbeReport(NAME, verdict, detail=why, witnesses=w)

        # Шаг 2: мутация → перекомпиляция → commit #2 (материализация ревокации)
        art.write_text("MUTATED", encoding="utf-8")
        st2 = clean(st)
        st2["proof"] = dc_asdict(mod.ProofCompiler(st2).compile())
        try:
            mod.ProofCarryingGovernor.commit(st2)
            # затмение: ревокации не было — преусловие P5 не материализовалось
            w = Witnesses(notes={"w1": "— commit #2 по мутации ПРИНЯТ "
                                       "(затмение P1 REVIVAL, см. proof_v340 P1)"})
            verdict, why = classify(False, w)
            return ProbeReport(NAME, verdict, detail=why, witnesses=w)
        except mod.ProofCarryingCommitError as e2:
            refusal2 = e2

        # Шаг 3: мир восстановлен бит-в-бит → успешный re-commit
        art.write_text("ORIGINAL", encoding="utf-8")
        st3 = clean(st2)
        st3["proof"] = dc_asdict(mod.ProofCompiler(st3).compile())
        try:
            mod.ProofCarryingGovernor.commit(st3)
        except Exception as e:  # noqa: BLE001
            return ProbeReport(NAME, Verdict.ERROR,
                               detail=f"re-commit после восстановления упал: {e}")

        rev = st3.get("revocation") or {}
        if rev.get("status") == "REVOKED":
            return ProbeReport(NAME, Verdict.REPRODUCED,
                               detail="знание навсегда REVOKED при валидном мире (истории нет)")
        if rev.get("status") == "RESOLVED" and st3.get("revocation_history"):
            # CLOSED: W1 ревокация материализовалась (commit #2 отказал);
            #         W2 честные #1 и #3 приняты;
            #         W3 закрытие несёт свою семантику: RESOLVED + revocation_history,
            #            отказ #2 — нашего типа ProofCarryingCommitError
            w3ok, _ = refusal_is_semantic(
                refusal2, mod.ProofCarryingCommitError, ARTIFACT_REFUSAL_MARKERS)
            w = Witnesses(applicability=True, positive_control=True,
                          refusal_semantics=w3ok,
                          notes={"w3": f"commit #2: {refusal2}"})
            verdict, why = classify(False, w)
            return ProbeReport(NAME, verdict, detail=why, witnesses=w)
        w = Witnesses(applicability=True, positive_control=True, refusal_semantics=False,
                      notes={"w3": f"— статус после re-commit не приведён в порядок: {rev}"})
        verdict, why = classify(False, w)
        return ProbeReport(NAME, verdict, detail=why, witnesses=w)
    except Exception as e:  # noqa: BLE001 — сбой прибора
        return ProbeReport(NAME, Verdict.ERROR, detail=f"{type(e).__name__}: {e}")


def main() -> int:
    flips = []
    rows = []
    for key, path in BRANCHES:
        mod = load(f"ref_{key}", path)
        b = Battery(f"харнес-классификация vs {key}")
        r_nart = p5_nart(mod)
        r_stale = p5_stale(mod)
        b.add(r_nart)
        b.add(r_stale)
        print(b.report())
        # zero-flip: as_bool(харнес) обязан совпасть с историческим bool
        for probe, rep in (("nart", r_nart), ("stale", r_stale)):
            hist = HISTORICAL_BOOL[key][probe]
            actual = as_bool(rep.verdict)
            if hist is None:
                ok = rep.verdict in (Verdict.INAPPLICABLE, Verdict.ERROR)
                rows.append((key, probe, str(rep.verdict.value), "истор. ERROR → формализован"))
                if not ok:
                    flips.append((key, probe, hist, actual))
            else:
                rows.append((key, probe, str(rep.verdict.value), f"hist={hist}"))
                if actual != hist:
                    flips.append((key, probe, hist, actual))
        print()

    print("═══ СВОДКА ПО ВЕТКАМ ═══")
    for key, probe, verdict, note in rows:
        print(f"  {key:9s} {probe:5s} → {verdict:12s} ({note})")
    print("═══ ZERO-FLIP РЕГРЕССИЯ ═══")
    if flips:
        for f in flips:
            print(f"  ПЕРЕКЛЮЧЕНИЕ: {f}")
        print("  РЕЗУЛЬТАТ: ЕСТЬ ПЕРЕКЛЮЧЕНИЯ — СТОП, разбираться")
        return 1
    print("  НОЛЬ ПЕРЕКЛЮЧЕНИЙ против исторической bool-матрицы Task 11 (9 веток × 2 пробы)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
