#!/usr/bin/env python3
"""
proof_v360_defects.py — механические пробы ПРОИЗВОДСТВЕННОГО WIRING ветки v3.6.0
(TRUST DOMAIN ARCHIVE, sha256 79e512e3…).

Урок прошлых ударов (worklog Task 5–7): тест на соседний механизм ≠ покрытие
production path нужного инварианта. v3.6.0 проходит 98/98 selftest и батареи
v310/v340 частично, НО все новые механики (KnowledgeLedger, RevocationIndex,
TrustAnchor, точная ревокация) существуют ТОЛЬКО в selftest-сценариях с
руками сконструированными state. Пробы ниже гоняют ПРОИЗВОДСТВЕННЫЕ формы.

Пробы (воспроизводятся на v3.6.0):
  N1  FP-REFS-NO-ATTRIBUTION  production run-loop пишет в ledger
      "artifact": <16-hex fingerprint> (Governor.run, только WRITE). Компилятор
      кладёт эти префиксы в evidence_artifact_refs как будто это пути →
      RevocationCascade.apply не может сопоставить их с мутировавшими путями →
      каскад ревокации НЕ АТРИБУТИРУЕТ ни одного evidence/claim.
  N2  LEDGER-VACUUM  runtime Agent никогда не выставляет
      _knowledge_ledger_path / _knowledge_revocation_index_path / _proof_anchor_path
      → ImmutableKnowledgeLedger/KnowledgeRevocationIndex/ProofAnchorLedger
      молчат на каждом production COMMIT (вся машинерия v3.5.x–3.6.0 мертва
      вне selftest).
  N3  REPLAY-DUP-COMMIT  ImmutableKnowledgeLedger.replay отклоняет
      commit-after-revoke, но молча принимает ПОВТОРНЫЙ COMMIT того же
      proof_id (двойная запись знания; политика форков неполна).
  N4  NO-POST-COMMIT-RECONCILE  в теле класса Agent нет ни одного вызова
      KnowledgeRevocationIndex.reconcile / KnowledgeAuditor: мутация мира
      ПОСЛЕ коммита не сверяется никем в runtime (закреплённое знание
      остаётся VALID навсегда).

Запуск:  python proof_v360_defects.py <path_to_agent_py>
"""
import importlib.util
import inspect
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


def clean(state):
    s = dict(state)
    for k in ("proof", "commit", "epistemic_reconciliation"):
        s.pop(k, None)
    return s


def n1_fp_refs_no_attribution(mod) -> bool:
    """N1: production-форма ledger-строк → каскад обязан АТРИБУТИРОВАТЬ точечно.
    Форма строк — ровно та, что пишет исправленный runtime (artifact_path +
    artifact_sha256 для write/read/verify, "artifact": fp для совместимости)."""
    with tempfile.TemporaryDirectory(prefix="p360_fprefs_") as td:
        a = Path(td) / "a.txt"; b = Path(td) / "b.txt"
        a.write_text("AAA", encoding="utf-8"); b.write_text("BBB", encoding="utf-8")
        fp_a = mod.sha256_hex(a.read_bytes())[:16]
        st = {"_cas_version": 0,
              "criteria": ["capability:write_file выполнена", "capability:read_file выполнена"],
              "required_capabilities": [],
              "claim_dependencies": {},
              "ledger": [
                  {"step": 1, "action": "write_file", "ok": True, "kind": "write",
                   "obs_brief": "создано", "artifact": fp_a,
                   "artifact_path": str(a), "artifact_sha256": mod.sha256_hex(a.read_bytes())},
                  {"step": 2, "action": "read_file", "ok": True, "kind": "read",
                   "obs_brief": "прочитано",
                   "artifact_path": str(b), "artifact_sha256": mod.sha256_hex(b.read_bytes())},
              ],
              "_artifact_paths": [str(a), str(b)]}
        p = mod.ProofCompiler(st).compile()
        st["proof"] = asdict(p)
        a.write_text("EVIL", encoding="utf-8")
        mod.RevocationCascade.apply(st, p)
        revoked_ev = st.get("revoked_evidence_ids", [])
        revoked_cl = st.get("revoked_claim_ids", [])
        # Ожидание: write-evidence шага 1 (и его claim) отозваны ТОЧНО,
        # read-знание шага 2 (claim:2) не задето.
        if revoked_ev == ["evidence:step:1:write_file"] and revoked_cl == ["claim:1"]:
            return False   # закрыто: атрибуция точная
        return True        # ДЕФЕКТ: каскад в production-форме не атрибутирует знание


def n2_ledger_vacuum(mod) -> bool:
    """N2: e2e COMMIT в живом runtime не оставляет следа в knowledge ledger/индексе."""
    with tempfile.TemporaryDirectory(prefix="p360_ledger_") as td:
        cfg, ws = mod._fresh_cfg(td)
        Path(ws).mkdir(parents=True, exist_ok=True)
        (Path(ws) / "hello.txt").write_text("stale", encoding="utf-8")
        script = [
            {"thought": "План.", "status": "plan",
             "success_criteria": ["hello.txt содержит 'final'"],
             "plan": ["запись", "чтение"]},
            {"thought": "Пишу.", "status": "act",
             "actions": [{"name": "write_file", "args": {"path": "hello.txt", "content": "final"}}]},
            {"thought": "Читаю.", "status": "act",
             "actions": [{"name": "read_file", "args": {"path": "hello.txt"}}]},
            {"thought": "Сверено.", "status": "final", "outcome": "verified",
             "final_answer": "готово", "lesson": "e2e"},
        ]
        audit = mod.AuditChain(Path(td) / "a.jsonl")
        agent = mod.Agent(cfg, mod.MockBrain(script), mod.Governor(cfg, audit), audit)
        result = agent.solve("создай hello.txt со строкой final и проверь")
        if result["outcome"] != "verified":
            return False   # сценарий не дошёл до коммита — проба неприменима
        w = _json.loads((Path(cfg.data_dir) / "working.json").read_text(encoding="utf-8"))
        led_path = w.get("_knowledge_ledger_path")
        idx_path = w.get("_knowledge_revocation_index_path")
        if not led_path or not idx_path:
            return True    # ДЕФЕКТ: knowledge ledger/индекс мертвы в production COMMIT
        led = mod.ImmutableKnowledgeLedger(Path(led_path))
        ok, bad = led.verify()
        rows = led._rows()
        commit_rows = [r for r in rows if r.get("event") == "COMMIT"]
        idx_rows = mod.KnowledgeRevocationIndex._load(Path(idx_path))
        if not ok or not commit_rows or not idx_rows:
            return True    # ДЕФЕКТ: пути есть, но COMMIT не записан/не зарегистрирован
        return False       # закрыто: COMMIT материализован в ledger + индекс


def n3_replay_duplicate_commit(mod) -> bool:
    """N3: replay молча принимает повторный COMMIT того же proof_id."""
    with tempfile.TemporaryDirectory(prefix="p360_dup_") as td:
        led = mod.ImmutableKnowledgeLedger(Path(td) / "k.jsonl")
        payload = {"proof_id": "proof:DUP1", "claim_ids": ["claim:1"],
                   "evidence_ids": ["evidence:1"], "artifact_hashes": {},
                   "proof_hash": "0" * 64}
        led.append("COMMIT", payload)
        led.append("COMMIT", dict(payload))     # та же связь знания второй раз
        ok, _bad = led.verify()
        if not ok:
            return False   # цепь сломана иначе — проба неприменима
        try:
            led.replay()
        except mod.KnowledgeLedgerError:
            return False   # закрыто: дубликат COMMIT отклонён
        return True        # ДЕФЕКТ: дубликат COMMIT принят молча


def n4_no_post_commit_reconcile(mod) -> bool:
    """N4: в production-классе Agent нет ни одного вызова reconciliation/аудита."""
    src = inspect.getsource(mod.Agent)
    wired = ("KnowledgeRevocationIndex.reconcile" in src) or ("KnowledgeAuditor" in src)
    if wired:
        return False   # закрыто: reconciliation присутствует в run-loop
    return True        # ДЕФЕКТ: post-commit reconciliation отсутствует в runtime


PROBES = [
    ("N1 FP-REFS: production-каскад без атрибуции знания", n1_fp_refs_no_attribution),
    ("N2 LEDGER-VACUUM: COMMIT не материализуется в knowledge ledger", n2_ledger_vacuum),
    ("N3 REPLAY-DUP-COMMIT: дубликат COMMIT принимается молча", n3_replay_duplicate_commit),
    ("N4 NO-POST-COMMIT-RECONCILE: сверка мира после коммита отсутствует", n4_no_post_commit_reconcile),
]


def main():
    if len(sys.argv) != 2:
        print("usage: proof_v360_defects.py <agent.py>"); sys.exit(2)
    mod = load_module(sys.argv[1])
    print(f"═══ ПРОБЫ против {Path(sys.argv[1]).name} ═══")
    repro = 0
    for name, fn in PROBES:
        try:
            hit = fn(mod)
        except Exception as e:
            hit = None
            print(f"[ERROR]           {name}: {type(e).__name__}: {e}")
            continue
        if hit:
            repro += 1
            print(f"[REPRODUCED]      {name}")
        else:
            print(f"[NOT-REPRODUCED]  {name}")
    print(f"═══ Итог: {repro}/{len(PROBES)} дефектов ВОСПРОИЗВЕЛИСЬ ═══")
    sys.exit(1 if repro else 0)


if __name__ == "__main__":
    main()
