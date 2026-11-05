#!/usr/bin/env python3
"""
proof_v330_defects.py — механические пробы дефектов v3.3.0 (JOHNSON).

Каждая проба загружает целевой модуль, строит состояние ProofCompiler
и утверждает ФОРМУ дефекта. Воспроизвелась = дефект жив; не воспроизвелась = закрыт.

Пробы:
  P1  R-D1   двойной префикс "claim:claim:1:derivation_missing" + пустая атрибуция
             epistemic_blockers (регресс v3.1.0 D1)
  P2  R-D4   evidence 2020 года даёт status=verified — свежесть выброшена
             (регресс v3.2.0 D4 / I28)
  P3  R-D5   эпистемический цикл claim:1↔claim:2 с покрытием даёт verified
             (регресс v3.2.0 D5 / I27)
  P4  R-D2   висячая зависимость (claim:99) не блокирует: END-TO-END
             ProofCarryingGovernor.commit пропускает (регресс v3.1.0 D2 / I24)
  P5  N-ART  мутация артефакта на диске после наблюдения НЕ видна COMMIT'у:
             artifact_hashes никогда не заполняется в runtime → reconcile вакуумный
  P6  N-CLM  чужие claim_ids в proof проходят Governor.validate (класс тампер-батареи)
  P7  R-D3   деривация зависимого claim остаётся valid=True при недоказанной
             предпосылке (регресс v3.1.0 D3 / TMS)
  P8  N-CLS  ProofClosureError не наследник ProofCarryingCommitError — отказ COMMIT
             по замыканию/времени вырывается из runtime-контракта (краш run-loop)

rev2: P5 получил ПОЗИТИВНЫЙ КОНТРОЛЬ — вердикт «закрыт» валиден только при
принятом no-mutation контроле; при проваленном контроле печатается свидетель
(отказ-вакуум ≠ сверка мира). Bool-семантика всех проб не изменена.

Запуск:  python proof_v330_defects.py <path_to_agent_py>
"""
import importlib.util
import sys
import tempfile
from pathlib import Path


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("target_agent", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["target_agent"] = mod
    spec.loader.exec_module(mod)
    return mod


# ─────────────────────────────────────────────────────────────────────────────
def p1_double_prefix_and_blockers(mod) -> bool:
    """R-D1: канонические id сломаны, блокеры не атрибутируются."""
    st = {"criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
          "required_capabilities": [],
          "claim_dependencies": {"claim:2": ["claim:1"]},
          "ledger": [{"step": 1, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"}]}
    p = mod.ProofCompiler(st).compile()
    double = [x for x in p.unknowns if x.startswith("claim:claim:")]
    blockers = st.get("epistemic_blockers", {})
    # дефект: двойной префикс И блокеры пусты при живой зависимости claim:2→claim:1
    return bool(double) and blockers == {}


def p2_stale_evidence_verifies(mod) -> bool:
    """R-D4: протухшее evidence (2020 год) даёт verified."""
    st = {"criteria": ["capability:write_file выполнена"], "required_capabilities": ["write_file"],
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                      "obs_brief": "created", "ts": "2020-01-01T00:00:00+00:00"}]}
    p = mod.ProofCompiler(st).compile()
    # дефект: verified вместо unknown с ":stale_evidence"
    return p.status == "verified" and not any(":stale_evidence" in x for x in p.unknowns)


def p3_dependency_cycle_verifies(mod) -> bool:
    """R-D5: циркулярная поддержка проходит как замыкание."""
    st = {"criteria": ["capability:write_file выполнена", "capability:read_file выполнена",
                       "capability:read_file завершена"],
          "required_capabilities": [],
          "claim_dependencies": {"claim:1": ["claim:2"], "claim:2": ["claim:1"], "claim:3": ["claim:2"]},
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "ok1"},
                     {"step": 2, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"},
                     {"step": 3, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok3"}]}
    p = mod.ProofCompiler(st).compile()
    # дефект: verified, цикл не обнаружен
    return p.status == "verified" and not any(":dependency_cycle" in x for x in p.unknowns)


def p4_dangling_dependency_commits(mod) -> bool:
    """R-D2: висячая зависимость доходит до COMMIT (end-to-end)."""
    st = {"criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
          "required_capabilities": [],
          "claim_dependencies": {"claim:2": ["claim:99"]},
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "ok1"},
                     {"step": 2, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"}],
          "_cas_version": 0}
    p = mod.ProofCompiler(st).compile()
    if p.status != "verified":
        return False  # компилятор ещё блокирует — дефект не в этой точке
    st["proof"] = mod.asdict(p)
    try:
        mod.ProofCarryingGovernor.commit(st)
    except mod.ProofCarryingCommitError:
        return False  # governor отклонил — дефект закрыт
    return True  # дефект: COMMIT принят


def p5_artifact_mutation_invisible(mod) -> bool:
    """N-ART: мутация артефакта на диске после наблюдения переживает COMMIT.

    rev2: добавлен ПОЗИТИВНЫЙ КОНТРОЛЬ. Отказ COMMIT'а сам по себе не доказывает
    «дефект закрыт»: отказ-вакуум (COMMIT отказывает всему подряд) выглядит для
    пробы так же. Валидный вердикт «закрыт» = боевой сценарий отклонён ПРИ
    ПРИНЯТОМ позитивном контроле (тот же сценарий БЕЗ мутации — принят).
    Семантика возврата не изменена: True/False решает только боевой сценарий;
    контроль лишь добавляет печатного свидетеля недостоверности."""
    d = tempfile.mkdtemp()
    art = Path(d) / "art.txt"
    art.write_text("ORIGINAL", encoding="utf-8")
    # ПОЗИТИВНЫЙ КОНТРОЛЬ: тот же state, БЕЗ мутации — COMMIT обязан принять
    st_ctl = {"criteria": ["capability:write_file выполнена"], "required_capabilities": ["write_file"],
              "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "created"}],
              "_artifact_paths": [str(art)], "_cas_version": 0}
    p_ctl = mod.ProofCompiler(st_ctl).compile()
    st_ctl["proof"] = mod.asdict(p_ctl)
    control_ok = True
    try:
        mod.ProofCarryingGovernor.commit(st_ctl)
    except mod.ProofCarryingCommitError:
        control_ok = False
    # runtime-форма: _artifact_paths заполняется, artifact_hashes — НИКОГДА
    st = {"criteria": ["capability:write_file выполнена"], "required_capabilities": ["write_file"],
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "created"}],
          "_artifact_paths": [str(art)], "_cas_version": 0}
    p = mod.ProofCompiler(st).compile()
    st["proof"] = mod.asdict(p)
    art.write_text("EVIL — мир изменился после наблюдения", encoding="utf-8")
    try:
        mod.ProofCarryingGovernor.commit(st)
        return True  # дефект: COMMIT прошёл мимо мутации мира
    except mod.ProofCarryingCommitError:
        if not control_ok:
            print("      [P5] СВИДЕТЕЛЬ: позитивный контроль ПРОВАЛЕН — COMMIT отказывает "
                  "и БЕЗ мутации; «закрыт» недостоверен (отказ-вакуум/консервативная защита), "
                  "см. матрицу p5_diagnosis_v33x.py A/B/C/D")
        return False  # мутация поймана — дефект закрыт (валидно лишь при control_ok)
    return True  # дефект: COMMIT прошёл мимо мутации мира


def p6_foreign_claim_ids_pass(mod) -> bool:
    """N-CLM: чужие claim_ids в замкнутом proof проходят validate."""
    st = {"criteria": ["capability:write_file выполнена"], "required_capabilities": ["write_file"],
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write", "obs_brief": "created"}],
          "_cas_version": 0}
    p = mod.ProofCompiler(st).compile()
    assert p.status == "verified"
    import copy as _copy
    tampered = _copy.deepcopy(mod.asdict(p))
    tampered["claim_ids"] = ["claim:9"]  # proof ≠ fingerprint-материал → CAS молчит
    st["proof"] = tampered
    try:
        mod.ProofCarryingGovernor.commit(st)
    except mod.ProofCarryingCommitError:
        return False  # отклонён — закрыт
    return True  # дефект: тамперинг прошёл


def p7_no_tms_invalidation(mod) -> bool:
    """R-D3: деривация зависимого claim остаётся valid при UNKNOWN-предпосылке."""
    st = {"criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
          "required_capabilities": [],
          "claim_dependencies": {"claim:2": ["claim:1"]},
          "ledger": [{"step": 1, "action": "read_file", "ok": True, "kind": "read", "obs_brief": "ok2"}]}
    mod.ProofCompiler(st).compile()
    derivs = [d for d in st.get("derivations", []) if d["claim_id"] == "claim:2"]
    # дефект: деривация жива, хотя её предпосылка claim:1 недоказана
    return bool(derivs) and derivs[0]["valid"] is True


def p8_closure_error_escapes_commit_contract(mod) -> bool:
    """N-CLS: ProofClosureError не наследник ProofCarryingCommitError — отказ COMMIT
    по замыканию/временной валидности вырывается из runtime-контракта
    `except ProofCarryingCommitError` (краш run-loop вместо честного verify-fail)."""
    import datetime as _dt
    future = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(days=2)).isoformat()
    st = {"criteria": ["capability:write_file выполнена"], "required_capabilities": ["write_file"],
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                      "obs_brief": "created", "ts": future}],
          "_cas_version": 0}
    p = mod.ProofCompiler(st).compile()
    st["proof"] = mod.asdict(p)
    try:
        mod.ProofCarryingGovernor.commit(st)
    except mod.ProofCarryingCommitError:
        return False  # отказ пойман контрактом — дефект закрыт
    except Exception:
        return True   # отказ ВЫРВАЛСЯ из контракта — дефект
    return False      # commit прошёл — другой случай, не эта проба


PROBES = [
    ("P1 R-D1 double-prefix + пустая атрибуция блокеров", p1_double_prefix_and_blockers),
    ("P2 R-D4 stale evidence даёт verified", p2_stale_evidence_verifies),
    ("P3 R-D5 эпистемический цикл даёт verified", p3_dependency_cycle_verifies),
    ("P4 R-D2 висячая зависимость доходит до COMMIT", p4_dangling_dependency_commits),
    ("P5 N-ART мутация артефакта невидима COMMIT'у", p5_artifact_mutation_invisible),
    ("P6 N-CLM чужие claim_ids проходят validate", p6_foreign_claim_ids_pass),
    ("P7 R-D3 нет TMS-инвалидации дериваций", p7_no_tms_invalidation),
    ("P8 N-CLS отказ COMMIT вырывается из runtime-контракта", p8_closure_error_escapes_commit_contract),
]


def main():
    if len(sys.argv) < 2:
        print("usage: proof_v330_defects.py <agent.py>")
        return 2
    mod = load_module(sys.argv[1])
    hit = 0
    print(f"═══ ПРОБЫ против {sys.argv[1]} ═══")
    for name, fn in PROBES:
        try:
            reproduced = fn(mod)
        except Exception as e:
            reproduced = False
            print(f"[NOT-REPRODUCED] {name}  (исключение: {type(e).__name__}: {e})")
            continue
        if reproduced:
            hit += 1
            print(f"[REPRODUCED]     {name}")
        else:
            print(f"[NOT-REPRODUCED] {name}")
    print(f"═══ Итог: {hit}/{len(PROBES)} дефектов ВОСПРОИЗВЕЛИСЬ ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
