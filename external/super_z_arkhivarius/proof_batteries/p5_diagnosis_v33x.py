#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""p5_diagnosis_v33x.py — дискриминация наблюдения «P5 (N-ART) не воспроизводится
на v3.3.x»: это честный фикс ветки (фича) или слабость пробы (вакуумный отказ COMMIT)?

Проба P5 (proof_v330_defects.p5_artifact_mutation_invisible) не различает:
  (a) COMMIT сверил мир с снимком наблюдения и ОТКАЗАЛ из-за мутации  → фича ветки;
  (b) COMMIT отказывает ВСЕГДА (сломан/перестраховывается)            → проба слепа.
Оба случая дают NOT-REPRODUCED.

Матрица сценариев на каждой ветке (production-формы: ProofCompiler + Governor.commit):
  A POSITIVE-CONTROL : наблюдение → proof → БЕЗ мутации → COMMIT
                       (здоровая ветка: ПРИНЯТ; «отказ всему» — отказ)
  B P5-ТОЧНО         : наблюдение → proof → мутация диска → COMMIT
                       (v3.3.2/3.3.3: отказ; v3.3.0: принят = дефект)
  C REVIVAL (N-REV1) : наблюдение → proof → мутация → ПЕРЕкомпиляция → COMMIT
                       (известная дыра ветки v3.3.x: перезапись пина launder'ит;
                        v3.4.0+ : отказ)
  D SNAPSHOT-ТЕСТ    : мутация ДО наблюдения → proof → COMMIT
                       (честная snapshot-семантика: ПРИНЯТ — проверяется
                        diff «мир против снимка наблюдения», а не «файл неизменен вообще»)

Плюс интроспекция: пишет ли ProofCompiler ветки снимок хешей в state
(st["artifact_hashes"]) — где берётся эталон для сверки.
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

BRANCHES = [
    ("JOHNSON_v3.3.0", "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.0.py"),
    ("JOHNSON_v3.3.2", "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.2.py"),
    ("JOHNSON_v3.3.3", "/home/z/my-project/upload/polymath_agent_JOHNSON_v3.3.3.py"),
    ("MY_v3.3.1", "/home/z/my-project/download/polymath_agent_v3.3.1.py"),
    ("MY_v3.8.0", "/home/z/my-project/download/polymath_agent_v3.8.0.py"),
]

EVIL = "EVIL — мир изменился"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def make_state(art_path):
    return {
        "criteria": ["capability:write_file выполнена"],
        "required_capabilities": ["write_file"],
        "ledger": [{"step": 1, "action": "write_file", "ok": True,
                    "kind": "write", "obs_brief": "created"}],
        "_artifact_paths": [str(art_path)],
        "_cas_version": 0,
    }


def commit_outcome(mod, st):
    """('ACCEPTED', '') | ('ProofCarryingCommitError', msg) | (ExcName, msg)"""
    try:
        mod.ProofCarryingGovernor.commit(st)
        return ("ACCEPTED", "")
    except mod.ProofCarryingCommitError as e:
        return ("ProofCarryingCommitError", str(e)[:200])
    except Exception as e:  # noqa: BLE001 — фиксируем ЛЮБОЙ чужой отказ
        return (type(e).__name__, f"{type(e).__name__}: {e}"[:200])


def scenario(mod, *, mutate_before_compile=False, mutate_after_compile=False,
             recompile=False, introspect=False):
    d = tempfile.mkdtemp()
    art = Path(d) / "art.txt"
    art.write_text("ORIGINAL", encoding="utf-8")
    if mutate_before_compile:
        art.write_text(EVIL, encoding="utf-8")
    st = make_state(art)
    p = mod.ProofCompiler(st).compile()
    st["proof"] = mod.asdict(p)
    snap = None
    if introspect:
        snap = st.get("artifact_hashes", "<ОТСУТСТВУЕТ>")
    if mutate_after_compile:
        art.write_text(EVIL, encoding="utf-8")
    if recompile:
        p2 = mod.ProofCompiler(st).compile()
        st["proof"] = mod.asdict(p2)
    outcome = commit_outcome(mod, st)
    return outcome, snap


def fmt(outcome):
    kind, msg = outcome
    if kind == "ACCEPTED":
        return "ПРИНЯТ"
    if kind == "ProofCarryingCommitError":
        return f"ОТКАЗ(PCC): {msg}"
    return f"ОТКАЗ(ЧУЖОЙ!): {msg}"


def main():
    print("=" * 100)
    print("МАТРИЦА ДИСКРИМИНАЦИИ P5/N-ART: фикс ветки или слабость пробы?")
    print("=" * 100)
    for label, path in BRANCHES:
        mod = load(f"tgt_{label}", path)
        (a, _), (b, _), (c, _), (d_out, _) = (
            scenario(mod),
            scenario(mod, mutate_after_compile=True),
            scenario(mod, mutate_after_compile=True, recompile=True),
            scenario(mod, mutate_before_compile=True),
        )
        (_, snap) = scenario(mod, introspect=True)
        print(f"\n─── {label}  ({path})")
        print(f"  A positive-control (без мутации)          : {fmt(a)}")
        print(f"  B P5-точно        (мутация после proof)   : {fmt(b)}")
        print(f"  C revival         (+перекомпиляция)       : {fmt(c)}")
        print(f"  D snapshot-тест   (мутация ДО наблюдения) : {fmt(d_out)}")
        if snap == "<ОТСУТСТВУЕТ>":
            print("  интроспекция: ProofCompiler НЕ пишет state['artifact_hashes']")
        elif snap is None:
            print("  интроспекция: state['artifact_hashes'] присутствует, но пуст")
        else:
            shown = {k: v[:16] + "…" for k, v in snap.items()} if isinstance(snap, dict) else snap
            print(f"  интроспекция: state['artifact_hashes'] после compile = {shown}")
    print("\n" + "=" * 100)
    print("ИНТЕРПРЕТАЦИЯ:")
    print("  ФИКС ЧЕСТНЫЙ  = A ПРИНЯТ + B ОТКАЗ(PCC, причина про артефакт/хеш) + D ПРИНЯТ")
    print("  ОТКАЗ-ВАКУУМ  = A ОТКАЗ (проба слепа: 'закрыт' == 'сломан')")
    print("  ФИКС ЧАСТИЧНЫЙ= C ПРИНЯТ на v3.3.x (revival-дыра N-REV1 жива) при честных A/B/D")
    return 0


if __name__ == "__main__":
    sys.exit(main())
