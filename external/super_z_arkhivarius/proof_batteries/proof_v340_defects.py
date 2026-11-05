#!/usr/bin/env python3
"""
proof_v340_defects.py — механические пробы границы ARTIFACT REVOCATION.

Атакуется следующий рубеж после CAS: изменение/удаление артефакта должно
механически инвалидировать зависимые Evidence → Claim → Derivation → Proof,
а не только блокировать один конкретный COMMIT.

Пробы (воспроизводятся на v3.3.3, закрыты в v3.4.0):
  P1  REVIVAL    write → commit → мутация → перекомпиляция → COMMIT ПРОХОДИТ:
                 перезапись глобального пина при перекомпиляции laundering'ит
                 старое evidence. Claim «файл содержит SECRET» коммитится,
                 хотя файл содержит EVIL.
  P2  READ-UNBOUND  read-evidence не имеет рёбер к артефакту: модуль не хранит
                 per-evidence binding, мутация прочитанного файла невидима.
  P3  COARSE     каскад ревокации грубый: мутация ОДНОГО артефакта отзывает
                 ВСЕ evidence/claims proof'а, включая несвязанные.
  P4  POST-COMMIT DRIFT  мутация мира ПОСЛЕ успешного коммита никем не
                 обнаруживается: закреплённое знание остаётся «VALID».
  P5  STALE LABEL  после REVOKED → восстановления артефакта → re-commit
                 запись revocation навсегда остаётся REVOKED (знание помечено
                 отозванным при валидном мире; истории нет).
  P6  DEAD FALSIFICATION  state["falsification"] не пишется никем в модуле —
                 FalsificationProbe вакуумен (мёртвая механика).

rev2: P5 получил СВИДЕТЕЛЯ НЕПРИМЕНИМОСТИ — если commit #2 по мутации ПРИНЯТ
(дыра REVIVAL/P1), преусловие P5 не материализуется, и NOT-REPRODUCED означает
«затмение P1», а НЕ «дефект закрыт». Bool-семантика всех проб не изменена.

Запуск:  python proof_v340_defects.py <path_to_agent_py>
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


def asdict(mod, proof):
    from dataclasses import asdict
    return asdict(proof)


def clean(state):
    s = dict(state)
    for k in ("proof", "commit", "epistemic_reconciliation"):
        s.pop(k, None)
    return s


def p1_revival(mod) -> bool:
    """REVIVAL: старое evidence переживает мутацию мира через перекомпиляцию."""
    with tempfile.TemporaryDirectory(prefix="p340_revival_") as td:
        art = Path(td) / "a.txt"
        art.write_text("SECRET", encoding="utf-8")
        st = {"criteria": ["capability:write_file выполнена"],
              "required_capabilities": ["write_file"],
              "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                          "obs_brief": "written", "artifact_path": str(art),
                          "artifact_sha256": mod.sha256_hex(b"SECRET")}],
              "_artifact_paths": [str(art)], "_cas_version": 0}
        p1 = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(mod, p1)
        mod.ProofCarryingGovernor.commit(st)          # честный коммит по SECRET
        art.write_text("EVIL", encoding="utf-8")      # мир изменился ПОСЛЕ evidence
        st2 = clean(st)
        p2 = mod.ProofCompiler(st2).compile()          # глобальный пин перезаписан на EVIL
        st2["proof"] = asdict(mod, p2)
        try:
            mod.ProofCarryingGovernor.commit(st2)
            return True   # ДЕФЕКТ: commit прошёл по мутации мира
        except mod.ProofCarryingCommitError:
            return False  # закрыто
        except Exception:
            return False


def p2_read_unbound(mod) -> bool:
    """READ-UNBOUND (e2e на живом runtime-контуре): read-наблюдение не биндится
    к артефакту → мутация прочитанного файла невидима COMMIT'у.
    Гоняет настоящий production-путь: MockBrain → Agent.solve → commit."""
    with tempfile.TemporaryDirectory(prefix="p340_read_") as td:
        cfg, ws = mod._fresh_cfg(td)
        Path(ws).mkdir(parents=True, exist_ok=True)
        (Path(ws) / "r.txt").write_text("ORIGINAL", encoding="utf-8")
        script = [
            {"thought": "План: проверить и прочитать.", "status": "plan",
             "success_criteria": ["r.txt содержит 'ORIGINAL'"],
             "plan": ["статистика", "чтение"]},
            {"thought": "Статистика.", "status": "act",
             "actions": [{"name": "stat_path", "args": {"path": "r.txt"}}]},
            {"thought": "Читаю.", "status": "act",
             "actions": [{"name": "read_file", "args": {"path": "r.txt"}}]},
            {"thought": "Сверено.", "status": "final", "outcome": "verified",
             "final_answer": "прочитано", "lesson": "read"},
        ]
        import json as _json
        audit = mod.AuditChain(Path(td) / "a.jsonl")
        agent = mod.Agent(cfg, mod.MockBrain(script), mod.Governor(cfg, audit), audit)
        result = agent.solve("задача чтения r.txt")
        if result["outcome"] != "verified":
            return False   # сценарий не дошёл до коммита — проба неприменима
        w = _json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
        # форма: хранит ли модуль per-evidence binding вообще?
        edges = (w.get("proof") or {}).get("artifact_edges")
        (Path(ws) / "r.txt").write_text("EVIL", encoding="utf-8")
        st2 = {k: v for k, v in w.items() if k not in ("proof", "commit", "epistemic_reconciliation")}
        p2 = mod.ProofCompiler(st2).compile()
        st2["proof"] = asdict(mod, p2)
        if not (getattr(p2, "artifact_edges", None) or edges):
            try:
                mod.ProofCarryingGovernor.commit(st2)
                return True   # ДЕФЕКТ: read-знание не привязано, мутация пережила COMMIT
            except mod.ProofCarryingCommitError:
                return False
        try:
            mod.ProofCarryingGovernor.commit(st2)
            return True   # ДЕФЕКТ: рёбра есть, но мутация прошла
        except mod.ProofCarryingCommitError:
            return False  # закрыто: read-evidence защищён


def p3_coarse_cascade(mod) -> bool:
    """COARSE: мутация одного артефакта отзывает ВСЁ знание proof'а."""
    with tempfile.TemporaryDirectory(prefix="p340_coarse_") as td:
        a1 = Path(td) / "a1.txt"; a2 = Path(td) / "a2.txt"
        a1.write_text("ONE", encoding="utf-8"); a2.write_text("TWO", encoding="utf-8")
        st = {"criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
              "required_capabilities": [],
              "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                          "obs_brief": "w1", "artifact_path": str(a1),
                          "artifact_sha256": mod.sha256_hex(b"ONE")},
                         {"step": 2, "action": "read_file", "ok": True, "kind": "read",
                          "obs_brief": "r2", "artifact_path": str(a2),
                          "artifact_sha256": mod.sha256_hex(b"TWO")}],
              "_cas_version": 0}
        p = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(mod, p)
        mod.ProofCarryingGovernor.commit(st)
        a2.write_text("MUTATED", encoding="utf-8")    # мутировал ТОЛЬКО a2
        st2 = clean(st)
        p2 = mod.ProofCompiler(st2).compile()
        st2["proof"] = asdict(mod, p2)
        try:
            mod.ProofCarryingGovernor.commit(st2)
            return True   # мутация вовсе не замечена — хуже грубости
        except mod.ProofCarryingCommitError:
            rev = st2.get("revocation") or {}
            ev = set(rev.get("evidence_ids", []))
            cl = set(rev.get("claim_ids", []))
            # грубость: отозвано несвязанное знание (evidence шага 1 / claim:1)
            if "evidence:step:1:write_file" in ev or "claim:1" in cl:
                return True   # ДЕФЕКТ: каскад грубый
            return False      # точечный — закрыто
        except Exception:
            return False


def p4_post_commit_drift(mod) -> bool:
    """POST-COMMIT DRIFT: закреплённое знание не сверяется с миром после коммита."""
    with tempfile.TemporaryDirectory(prefix="p340_drift_") as td:
        art = Path(td) / "d.txt"
        art.write_text("V1", encoding="utf-8")
        st = {"criteria": ["capability:write_file выполнена"],
              "required_capabilities": ["write_file"],
              "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                          "obs_brief": "w", "artifact_path": str(art),
                          "artifact_sha256": mod.sha256_hex(b"V1")}],
              "_artifact_paths": [str(art)], "_cas_version": 0}
        p = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(mod, p)
        mod.ProofCarryingGovernor.commit(st)
        art.write_text("V2", encoding="utf-8")
        auditor = getattr(mod, "KnowledgeAuditor", None)
        if auditor is None:
            ks = st.get("knowledge_status")
            return ks != "STALE"   # ДЕФЕКТ: нет механизма дрейфа вообще
        rep = auditor.audit(st)
        return rep.get("status") != "STALE"   # ДЕФЕКТ: дрейф не обнаружен


def p5_stale_revoked_label(mod) -> bool:
    """STALE LABEL: REVOKED не закрывается успешным re-commit (нет истории)."""
    with tempfile.TemporaryDirectory(prefix="p340_label_") as td:
        art = Path(td) / "r.txt"
        art.write_text("ORIGINAL", encoding="utf-8")
        st = {"criteria": ["capability:write_file выполнена"],
              "required_capabilities": ["write_file"],
              "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                          "obs_brief": "w", "artifact_path": str(art),
                          "artifact_sha256": mod.sha256_hex(b"ORIGINAL")}],
              "_artifact_paths": [str(art)], "_cas_version": 0}
        p = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(mod, p)
        mod.ProofCarryingGovernor.commit(st)
        art.write_text("MUTATED", encoding="utf-8")
        st2 = clean(st)
        p2 = mod.ProofCompiler(st2).compile()
        st2["proof"] = asdict(mod, p2)
        try:
            mod.ProofCarryingGovernor.commit(st2)
            print("      [P5] СВИДЕТЕЛЬ: НЕПРИМЕНИМА — commit #2 по мутации ПРИНЯТ "
                  "(дыра REVIVAL/P1 затмевает преусловие P5; NOT-REPRODUCED здесь ≠ «закрыт», "
                  "см. P1 этой же батареи)")
            return False   # ревокации не было — проба неприменима
        except mod.ProofCarryingCommitError:
            pass
        art.write_text("ORIGINAL", encoding="utf-8")   # мир восстановлен бит-в-бит
        st3 = clean(st2)
        p3 = mod.ProofCompiler(st3).compile()
        st3["proof"] = asdict(mod, p3)
        mod.ProofCarryingGovernor.commit(st3)          # успешный re-commit
        rev = st3.get("revocation") or {}
        if rev.get("status") == "REVOKED":
            return True    # ДЕФЕКТ: знание навсегда помечено REVOKED при валидном мире
        hist = st3.get("revocation_history")
        if rev.get("status") == "RESOLVED" and hist:
            return False   # закрыто: RESOLVED + история
        return True        # статус не приведён в порядок — дефект консистентности


def p6_dead_falsification(mod) -> bool:
    """DEAD FALSIFICATION: state["falsification"] не пишется никем — probe вакуумен.
    Поведенческая форма: verify-fail, назвавший критерий ПОСЛЕ evidence,
    не блокирует COMMIT."""
    st = {"criteria": ["capability:write_file выполнена"],
          "required_capabilities": ["write_file"],
          "ledger": [{"step": 1, "action": "write_file", "ok": True, "kind": "write",
                      "obs_brief": "created"},
                     {"step": 2, "action": "(verify-fail)", "ok": False, "kind": "verify",
                      "obs_brief": "VERIFIED ОТКЛОНЁН Контролёром: критерии не подтверждены "
                                   "ни одним успешным наблюдением в журнале: "
                                   "capability:write_file выполнена"}],
          "_cas_version": 0}
    p = mod.ProofCompiler(st).compile()
    if p.status != "verified":
        return False   # сценарий не собрался
    st["proof"] = asdict(mod, p)
    try:
        mod.ProofCarryingGovernor.commit(st)
        return True    # ДЕФЕКТ: противоречие журнала не дошло до falsification-гейта
    except mod.ProofCarryingCommitError as e:
        return "falsification" not in str(e).lower()


PROBES = [
    ("P1 REVIVAL: перекомпиляция launder'ит старое evidence", p1_revival),
    ("P2 READ-UNBOUND: read-evidence без рёбер к артефакту", p2_read_unbound),
    ("P3 COARSE: каскад отзывает несвязанное знание", p3_coarse_cascade),
    ("P4 POST-COMMIT DRIFT: закреплённое знание не сверяется", p4_post_commit_drift),
    ("P5 STALE LABEL: REVOKED не закрывается re-commit'ом", p5_stale_revoked_label),
    ("P6 DEAD FALSIFICATION: противоречия журнала не captured", p6_dead_falsification),
]


def main():
    if len(sys.argv) < 2:
        print("использование: proof_v340_defects.py <path_to_agent_py>")
        return 2
    mod = load_module(sys.argv[1])
    print(f"═══ ПРОБЫ против {sys.argv[1]} ═══")
    hits = 0
    for name, fn in PROBES:
        try:
            hit = fn(mod)
        except Exception as e:
            print(f"[ERROR]           {name}: {e!r}")
            continue
        tag = "[REPRODUCED]" if hit else "[NOT-REPRODUCED]"
        hits += 1 if hit else 0
        print(f"{tag:17s} {name}")
    print(f"═══ Итог: {hits}/{len(PROBES)} дефектов ВОСПРОИЗВЕЛИСЬ ═══")
    return 0


if __name__ == "__main__":
    sys.exit(main())
