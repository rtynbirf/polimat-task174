#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Сборка polymath_agent_v3.10.0.py «C5 GATE ANTI-VACUUM» из v3.9.0 (ea1e9001…, 133/133).

Приоритет Р-01 из ревизии приборного слоя (аудит REV1, CH5):
  Анти-вакуумное правило гейтов (C5) вшивается в РАНТАЙМ.
  Принцип v3.9.0 («каждый отказной гейт → парный тест «честный путь принят»
  + assertion на именованную причину») становится законом v3.10.0:
    1. GateAntiVacuum.refuse(gate, reason) — единственный законный способ
       отказа гейта COMMIT-контура: отказ без именованной причины сам
       поднимается как VacuousRefusalError (вакуумный отказ невыразим).
    2. GATE_REGISTRY — явный реестр отказных гейтов COMMIT-контура
       (11 семейств) с именованными причинами и парными свидетелями
       самопроверки (honest + refusal).
    3. GateAntiVacuum.audit() — механическая сверка реестра.
    4. T140 — мета-гейт: реестр непротиворечив, ВСЕ парные свидетели
       реально исполнены и зелёные (удаление парного теста роняет самопроверку).
    5. T141 — невыразимость вакуумного отказа (позитивный контроль refuse()).
    6. Усиление refusal-проб T64/T65/T115/T117/T120: голый факт исключения
       больше не свидетель — ассертируется ИМЕНОВАННАЯ причина.

Методология: сплайсы по уникальным якорям, assert count==1 (эталон build_v390.py).
Ни одно сообщение отказа не меняется байт-в-байт (zero-flip по текстам причин).
"""
import hashlib
import sys
from pathlib import Path

SRC = Path("/home/z/my-project/scripts/handoff_rev5_build/02_version_chain/polymath_agent_v3.9.0.py")
OUT = Path("/home/z/my-project/download/polymath/v3.10.0_release/polymath_agent_v3.10.0.py")


def main() -> int:
    src = SRC.read_text(encoding="utf-8")
    baseline_sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    assert baseline_sha == "ea1e9001d53a646a4def4930f4e17ec4ca5d63512d37284cbd466bd314fda2b3", \
        f"бейзлайн v3.9.0 не совпал: {baseline_sha}"

    def splice(old: str, new: str, n: int = 1) -> None:
        nonlocal src
        c = src.count(old)
        assert c == n, f"якорь неуникален ({c}x, ожидалось {n}): {old[:90]!r}"
        src = src.replace(old, new)

    # ── Сплайс 1: заголовок-версия ──────────────────────────────────────────
    splice(
        "+ v3.8.0 ROOT EPOCH CHAIN + v3.9.0 HMAC DOMAIN BINDING (восстановлено из базы v2",
        "+ v3.8.0 ROOT EPOCH CHAIN + v3.9.0 HMAC DOMAIN BINDING + v3.10.0 C5 GATE ANTI-VACUUM (восстановлено из базы v2",
    )

    # ── Сплайс 2: VacuousRefusalError + GateAntiVacuum + GATE_REGISTRY ──────
    anchor2 = '''class ProofClosureError(ProofCarryingCommitError):
    """v3.7.0 N-CLS: отказ замыкания — часть runtime-контракта COMMIT
    (ловится except ProofCarryingCommitError, а не рвёт run-loop)."""

class ProofClosure:'''
    block2 = '''class ProofClosureError(ProofCarryingCommitError):
    """v3.7.0 N-CLS: отказ замыкания — часть runtime-контракта COMMIT
    (ловится except ProofCarryingCommitError, а не рвёт run-loop)."""

class VacuousRefusalError(PolicyViolation):
    """v3.10.0 C5 GATE ANTI-VACUUM: отказной гейт отказал без именованной причины.

    Отказ без причины недействителен: он неотличим от поломки прибора и не может
    быть ассертирован refusal-пробой (урок P5/N-ART: отказ-вакуум стирает различие
    «закрыт / неприменимо»). Сам отказ поднимается как нарушение политики.
    """

class GateAntiVacuum:
    """v3.10.0 C5 — анти-вакуумное правило гейтов, вшитое в рантайм (Р-01).

    Принцип v3.9.0 («каждый отказной гейт → парный тест «честный путь принят»
    + assertion на именованную причину») становится механикой:

      refuse(gate, reason) — единственный законный способ отказа гейта
        COMMIT-контура: сообщение гарантированно несёт namespaced-причину
        "<gate>: <reason>"; голый отказ без причины/гейта невыразим —
        refuse() сам поднимает VacuousRefusalError.
      GATE_REGISTRY — явный реестр отказных гейтов COMMIT-контура: каждое
        семейство несёт именованные причины отказа и ПАРНЫХ свидетелей
        самопроверки (honest_witnesses — «честный путь принят»;
        refusal_witnesses — «отказ по своей причине»).
      audit() — механическая сверка реестра: пустые/безымянные причины,
        отсутствующие свидетели = нарушение C5.

    Мета-гейт T140 сверяет реестр с фактом исполнения проб самопроверки:
    удаление или обесточивание парного теста роняет --selftest. Гейты Тела
    (изоляция путей, SSRF, схемный валидатор, гейты процедур и плана) уже
    несут парные пробы «отказ + честный путь» в каждой паре (T01, T02, T09,
    T11, T14, T15, T17, T19, T21); их включение в реестр — при ревизии Тела.
    """
    MIN_REASON = 4

    @staticmethod
    def refuse(gate: str, reason: str) -> ProofCarryingCommitError:
        if not isinstance(gate, str) or not gate.strip():
            raise VacuousRefusalError("C5: отказ без имени гейта — вакуумный отказ")
        if (not isinstance(reason, str) or len(reason.strip()) < GateAntiVacuum.MIN_REASON
                or not reason.strip()):
            raise VacuousRefusalError(
                f"C5: гейт {gate!r} отказал без именованной причины: {reason!r}")
        return ProofCarryingCommitError(f"{gate}: {reason}")

    @staticmethod
    def audit() -> List[str]:
        bad: List[str] = []
        for g in GATE_REGISTRY:
            gid = g.get("gate", "")
            if not gid:
                bad.append("C5: строка реестра без имени гейта")
                continue
            reasons = g.get("reasons") or []
            if not reasons or any(not isinstance(r, str) or len(r.strip()) < GateAntiVacuum.MIN_REASON
                                  for r in reasons):
                bad.append(f"C5: {gid}: безымянная причина отказа")
            if not (g.get("honest_witnesses") or []):
                bad.append(f"C5: {gid}: honest-свидетель отсутствует")
            if not (g.get("refusal_witnesses") or []):
                bad.append(f"C5: {gid}: refusal-свидетель отсутствует")
        return bad

GATE_REGISTRY: List[Dict[str, Any]] = [
    {"gate": "COMMIT/ProofCarryingGovernor",
     "reasons": ["COMMIT: отсутствует полный ProofObject", "COMMIT: UNKNOWN",
                 "COMMIT: неполное покрытие", "COMMIT: falsification=",
                 "COMMIT: proof missing CAS source state", "COMMIT: CAS conflict",
                 "COMMIT: REVOKED", "COMMIT: WorldState mismatch", "COMMIT: ROOT TRUST:"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T64 commit requires proof", "T65 commit rejects unknown proof",
                           "T104 CAS changed state (renumbered; was duplicate T73 in v3.6.0)",
                           "T119 falsification contested (unit)",
                           "T77 artifact mutation reconciliation",
                           "T122 truncated root history blocks COMMIT",
                           "T123 revoked root blocks COMMIT"]},
    {"gate": "PROOF_CLOSURE/ProofClosure.validate",
     "reasons": ["PROOF_CLOSURE:"],
     "honest_witnesses": ["T116 proof closure closed (unit)"],
     "refusal_witnesses": ["T115 proof closure dangling (unit)",
                           "T118 proof closure cycle (unit)"]},
    {"gate": "TEMPORAL/TemporalValidity.validate",
     "reasons": ["TEMPORAL_VALIDITY:"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T117 temporal future (unit)",
                           "T120 temporal future evidence (unit)"]},
    {"gate": "CAS/StateCAS.assert_unchanged",
     "reasons": ["COMMIT: CAS conflict"],
     "honest_witnesses": ["T74 CAS unchanged state"],
     "refusal_witnesses": ["T104 CAS changed state (renumbered; was duplicate T73 in v3.6.0)"]},
    {"gate": "FALSIFICATION/FalsificationProbe.probe",
     "reasons": ["COMMIT: falsification=CONTESTED"],
     "honest_witnesses": ["T66 commit accepts closed proof"],
     "refusal_witnesses": ["T119 falsification contested (unit)"]},
    {"gate": "ROOT_TRUST_GATE/RootEpochChain.require_active_from_state",
     "reasons": ["COMMIT: ROOT TRUST:"],
     "honest_witnesses": ["T121 runtime root epoch bound to COMMIT"],
     "refusal_witnesses": ["T122 truncated root history blocks COMMIT",
                           "T123 revoked root blocks COMMIT",
                           "T125 replay root-epoch rollback"]},
    {"gate": "ROOT_AUTH/RootTrustAuthority.authorize+verify",
     "reasons": ["invalid root authorization envelope", "root authorization MAC failure",
                 "authorization not bound to a root epoch",
                 "authorization root epoch rotated/revoked", "signing key epoch rollback"],
     "honest_witnesses": ["T137 signing-key authorization bound to active root (A1.2)"],
     "refusal_witnesses": ["T95 root substitution", "T96 key-epoch rollback",
                           "T100 key-history fork", "T103 root authorization tamper",
                           "T134 root authorization tamper (port)",
                           "T138 root rotation invalidates unconfirmed authorization (A1.2)",
                           "T139 root revocation invalidates unconfirmed authorization (A1.2)"]},
    {"gate": "SIGNING/SigningTrustDomain.install+sign+verify",
     "reasons": ["root-authorized key fingerprint mismatch", "signing epoch replay/rollback",
                 "unknown/revoked signing key", "invalid signing checkpoint envelope",
                 "signing epoch mismatch", "checkpoint MAC failure",
                 "cannot revoke active signing key"],
     "honest_witnesses": ["T94 trust-domain separation"],
     "refusal_witnesses": ["T97 old-key resurrection", "T99 root envelope in signing domain",
                           "T101 checkpoint epoch tamper", "T102 revoked epoch checkpoint",
                           "T129 old-root resurrection (port)",
                           "T132 root/signing domain confusion (port)",
                           "T136 active checkpoint fingerprint mismatch (port)"]},
    {"gate": "ANCHOR/LedgerTrustAnchor.verify",
     "reasons": ["trust anchor mismatch"],
     "honest_witnesses": ["T90 trust anchor exact checkpoint"],
     "refusal_witnesses": ["T91 trust anchor rollback", "T92 trust anchor fork",
                           "T93 trust anchor substitution"]},
    {"gate": "LEDGER/ImmutableKnowledgeLedger.append+replay",
     "reasons": ["ledger verification failed", "replay fork:", "replay error:"],
     "honest_witnesses": ["T84 knowledge ledger chain+replay"],
     "refusal_witnesses": ["T85 knowledge ledger tamper", "T86 knowledge ledger fork/replay",
                           "T88 replay distinguishes truncation", "T89 replay proof binding",
                           "T114 replay rejects duplicate commit"]},
    {"gate": "GOVERNOR/_confine+SSRF-фильтр",
     "reasons": ["path обязателен и должен быть строкой", "SSRF-фильтр:",
                 "Отказ Конституции:"],
     "honest_witnesses": ["T10 сквозной цикл на MockBrain"],
     "refusal_witnesses": ["T01 изоляция путей", "T09 SSRF-фильтр http_get"]},
]

class ProofClosure:'''
    splice(anchor2, block2)

    # ── Сплайсы 3–13: все отказы COMMIT-контура через GateAntiVacuum.refuse ──
    # Сообщения сохраняются байт-в-байт: refuse(gate, reason) = f"{gate}: {reason}"
    splice('raise ProofCarryingCommitError("COMMIT: отсутствует полный ProofObject")',
           'raise GateAntiVacuum.refuse("COMMIT", "отсутствует полный ProofObject")')
    splice('if proof.unknowns: raise ProofCarryingCommitError("COMMIT: UNKNOWN")',
           'if proof.unknowns: raise GateAntiVacuum.refuse("COMMIT", "UNKNOWN")')
    splice('raise ProofCarryingCommitError("COMMIT: неполное покрытие")',
           'raise GateAntiVacuum.refuse("COMMIT", "неполное покрытие")')
    splice('raise ProofCarryingCommitError(f"COMMIT: falsification={fals[\'status\']}")',
           'raise GateAntiVacuum.refuse("COMMIT", f"falsification={fals[\'status\']}")')
    splice('raise ProofCarryingCommitError("COMMIT: proof missing CAS source state")',
           'raise GateAntiVacuum.refuse("COMMIT", "proof missing CAS source state")')
    splice('raise ProofCarryingCommitError("COMMIT: REVOKED — evidence-bound artifact mutation: "+", ".join(sorted({d[\'artifact\'] for d in drift})))',
           'raise GateAntiVacuum.refuse("COMMIT", "REVOKED — evidence-bound artifact mutation: "+", ".join(sorted({d[\'artifact\'] for d in drift})))')
    splice('raise ProofCarryingCommitError("COMMIT: REVOKED — bound artifact mutation")',
           'raise GateAntiVacuum.refuse("COMMIT", "REVOKED — bound artifact mutation")')
    splice('raise ProofCarryingCommitError("COMMIT: WorldState mismatch")',
           'raise GateAntiVacuum.refuse("COMMIT", "WorldState mismatch")')
    splice('raise ProofCarryingCommitError(f"COMMIT: ROOT TRUST: {_rte}") from _rte',
           'raise GateAntiVacuum.refuse("COMMIT", f"ROOT TRUST: {_rte}") from _rte')
    splice('raise ProofCarryingCommitError("COMMIT: CAS conflict — state changed after proof compilation")',
           'raise GateAntiVacuum.refuse("COMMIT", "CAS conflict — state changed after proof compilation")')

    # ── Сплайсы 14–18: усиление refusal-проб — ассерт именованной причины ───
    splice('''        except ProofCarryingCommitError:
            return "COMMIT без ProofObject блокируется"''',
           '''        except ProofCarryingCommitError as e:
            msg = str(e)
            assert msg.startswith("COMMIT:") and "отсутствует полный ProofObject" in msg, \\
                f"C5: отказ без именованной причины: {msg!r}"
            return "COMMIT без ProofObject блокируется (именованная причина ассертируется)"''')
    splice('''        except ProofCarryingCommitError:
            return "COMMIT с UNKNOWN блокируется"''',
           '''        except ProofCarryingCommitError as e:
            assert "COMMIT: UNKNOWN" in str(e), f"C5: отказ без именованной причины: {str(e)!r}"
            return "COMMIT с UNKNOWN блокируется (именованная причина ассертируется)"''')
    splice('''        try: ProofClosure.validate(p)
        except ProofClosureError: return "dangling input блокируется"
        raise AssertionError("dangling input accepted")''',
           '''        try: ProofClosure.validate(p)
        except ProofClosureError as e:
            assert str(e) == "PROOF_CLOSURE: dangling input", \\
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "dangling input блокируется (именованная причина ассертируется)"
        raise AssertionError("dangling input accepted")''')
    splice('''        try: TemporalValidity.validate(p)
        except ProofClosureError: return "future proof блокируется"
        raise AssertionError("future proof accepted")''',
           '''        try: TemporalValidity.validate(p)
        except ProofClosureError as e:
            assert str(e) == "TEMPORAL_VALIDITY: future-dated proof", \\
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "future proof блокируется (именованная причина ассертируется)"
        raise AssertionError("future proof accepted")''')
    splice('''        try: TemporalValidity.validate(p, "2026-01-02T00:00:00+00:00")
        except ProofClosureError: return "future evidence блокируется"
        raise AssertionError("future evidence accepted")''',
           '''        try: TemporalValidity.validate(p, "2026-01-02T00:00:00+00:00")
        except ProofClosureError as e:
            assert "TEMPORAL_VALIDITY: future evidence" in str(e), \\
                f"C5: отказ без именованной причины: {str(e)!r}"
            return "future evidence блокируется (именованная причина ассертируется)"
        raise AssertionError("future evidence accepted")''')

    # ── Сплайс 19: T141 + T140 — новые пробы C5, регистрируются последними ──
    anchor19 = '''    check("T139 root revocation invalidates unconfirmed authorization (A1.2)", t_hmac_binding_revocation_invalidates)'''
    block19 = '''    check("T139 root revocation invalidates unconfirmed authorization (A1.2)", t_hmac_binding_revocation_invalidates)

    # ═══ v3.10.0 C5 GATE ANTI-VACUUM: невыразимость вакуумного отказа + мета-гейт ═══
    def t_c5_vacuous_refusal() -> str:
        exc = GateAntiVacuum.refuse("COMMIT", "CAS conflict — сплайс-проба C5")
        assert isinstance(exc, ProofCarryingCommitError) and str(exc).startswith("COMMIT: "), \\
            "refuse() не вернул отказ с namespaced-причиной"
        for bad in [("", "reason"), ("COMMIT", ""), ("COMMIT", "   "), ("COMMIT", "x")]:
            try:
                GateAntiVacuum.refuse(*bad)
                raise AssertionError(f"C5: вакуумный отказ выразим: {bad!r}")
            except VacuousRefusalError:
                pass
        return "вакуумный отказ невыразим: refuse() без гейта/причины сам поднимает VacuousRefusalError"

    def t_c5_meta_gate() -> str:
        bad = GateAntiVacuum.audit()
        assert not bad, f"C5: нарушения реестра: {bad}"
        executed = {name: ok for name, ok, _ in results}
        for g in GATE_REGISTRY:
            for w in g["honest_witnesses"]:
                assert w in executed, f"C5: honest-свидетель {w!r} гейта {g['gate']} не исполнен"
                assert executed[w], f"C5: honest-свидетель {w!r} гейта {g['gate']} провален"
            for w in g["refusal_witnesses"]:
                assert w in executed, f"C5: refusal-свидетель {w!r} гейта {g['gate']} не исполнен"
                assert executed[w], f"C5: refusal-свидетель {w!r} гейта {g['gate']} провален"
        assert len(GATE_REGISTRY) >= 11, "C5: реестр гейтов сжался ниже аудиторского пола"
        total_w = sum(len(g["honest_witnesses"]) + len(g["refusal_witnesses"]) for g in GATE_REGISTRY)
        return (f"анти-вакуумная сверка {len(GATE_REGISTRY)} гейтов COMMIT-контура: "
                f"причины именованы, все {total_w} парных свидетелей исполнены и зелёные")

    check("T141 vacuous refusal is inexpressible (C5)", t_c5_vacuous_refusal)
    check("T140 C5 gate anti-vacuum meta-gate", t_c5_meta_gate)'''
    splice(anchor19, block19)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(src, encoding="utf-8")
    out_sha = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"OK: {OUT}")
    print(f"строк: {src.count(chr(10)) + 1}")
    print(f"sha256: {out_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
