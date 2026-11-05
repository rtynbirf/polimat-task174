#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""battery_harness.py — конституция instrument-слоя (урок P5, Task 11–12).

УРОК P5: исход пробы трёхзначен; bool-API стирает различие
«закрыт / неприменимо / вакуум». Этот харнес делает недостоверный вердикт
НЕВЫРАЗИМЫМ: CLOSED невозможен без трёх свидетелей.

МЕСТО В СЛОЯХ ПРОЕКТА (решение Task 12 «вшивать в слой, где живёт дефект»):
  runtime агента — НЕТ: refusing-семантики с именованными причинами и
    RESOLVED+revocation_history уже в фундаменте v3.4.0+; аудиторский
    инструмент не импортируется аудируемым артефактом (независимость, TCB).
  instrument-слой (proof-батареи) — ДА, ЗДЕСЬ: конституция проб.
  protocol-слой (worklog/handoff) — ДА: «закрыт» = claim, обязан нести evidence.

ВЕРДИКТЫ:
  REPRODUCED   дефект жив — самодостаточный вердикт (один бит)
  CLOSED       закрыт — ТОЛЬКО при трёх свидетелях, иначе понижение с причиной
  INAPPLICABLE статус неизвестен: преусловие не материализовалось / вакуум /
               затмение другим дефектом / отказ по чужой причине
  ERROR        проба упала вне семантического отказа (сбой прибора)

ТРИ СВИДЕТЕЛЯ CLOSED:
  W1 applicability      преусловие материализовалось (сценарий дошёл до механизма)
  W2 positive_control   тот же сценарий БЕЗ нарушения ПРИНЯТ (нет отказа-вакуума)
  W3 refusal_semantics  отказ назвал СВОЮ причину (тип исключения + маркер)

Единая эпистемология проекта: proof-carrying commits ↔ witness-carrying
closures — самодостаточен только позитивный вердикт.
"""

from dataclasses import dataclass, field
from enum import Enum


class Verdict(str, Enum):
    REPRODUCED = "REPRODUCED"
    CLOSED = "CLOSED"
    INAPPLICABLE = "INAPPLICABLE"
    ERROR = "ERROR"


# Маркеры артефактных отказов: «мир ≠ снимок наблюдения» (v3.3.2+ линейка).
# Харнес не диктует маркеры — проба передаёт СВОИ; это общий набор по умолчанию.
ARTIFACT_REFUSAL_MARKERS = (
    "WorldState mismatch",
    "REVOKED",
    "bound artifact",
    "artifact",
)


@dataclass
class Witnesses:
    """Свидетели закрытия. CLOSED валиден только при всех трёх True."""
    applicability: bool = False      # W1
    positive_control: bool = False   # W2
    refusal_semantics: bool = False  # W3
    notes: dict = field(default_factory=dict)

    def flag(self) -> str:
        return (f"W1{'ok' if self.applicability else 'x'} "
                f"W2{'ok' if self.positive_control else 'x'} "
                f"W3{'ok' if self.refusal_semantics else 'x'}")


def classify_closure(w: Witnesses) -> tuple[Verdict, str]:
    """CLOSED только при (W1 и W2 и W3); любое понижение — с причиной."""
    if not w.applicability:
        return Verdict.INAPPLICABLE, f"W1: преусловие не материализовалось {w.notes.get('w1', '')}".rstrip()
    if not w.positive_control:
        return Verdict.INAPPLICABLE, f"W2: позитивный контроль провален — отказ-вакуум/консервативная защита {w.notes.get('w2', '')}".rstrip()
    if not w.refusal_semantics:
        return Verdict.INAPPLICABLE, f"W3: отказ по чужой причине {w.notes.get('w3', '')}".rstrip()
    return Verdict.CLOSED, "свидетели W1+W2+W3"


def classify(defect_observed: bool, w: Witnesses,
             scenario_completed: bool = True) -> tuple[Verdict, str]:
    """Единая точка вердикта пробы.
    defect_observed=True  -> REPRODUCED (свидетели не требуются)
    defect_observed=False -> CLOSED при трёх свидетелях, иначе понижение."""
    if not scenario_completed:
        return Verdict.ERROR, "сценарий не завершился"
    if defect_observed:
        return Verdict.REPRODUCED, "дефект наблюдён"
    return classify_closure(w)


def as_bool(verdict: Verdict) -> bool:
    """Историческая bool-семантика батарей (zero-flip гарантия):
    REPRODUCED -> True (дефект жив), всё остальное -> False."""
    return verdict is Verdict.REPRODUCED


def refusal_is_semantic(exc: BaseException, expected_type: type,
                        markers) -> tuple[bool, str]:
    """W3: отказ должен быть НАШЕГО типа и называть СВОЮ причину."""
    if not isinstance(exc, expected_type):
        return False, f"чужой тип отказа {type(exc).__name__}: {exc}"
    msg = str(exc)
    hit = [m for m in markers if m in msg]
    if hit:
        return True, f"{msg[:160]} [маркер: {hit[0]}]"
    return False, f"{msg[:160]} [маркера нет]"


@dataclass
class ProbeReport:
    name: str
    verdict: Verdict
    detail: str = ""
    witnesses: Witnesses = field(default_factory=Witnesses)


class Battery:
    """Сборник проб с честным отчётом. «Зелёный» обязан называть неизвестные."""

    def __init__(self, title: str):
        self.title = title
        self.reports: list[ProbeReport] = []

    def add(self, report: ProbeReport) -> None:
        self.reports.append(report)

    def summary(self) -> dict:
        s = {v.value: 0 for v in Verdict}
        for r in self.reports:
            s[r.verdict.value] += 1
        return s

    def report(self) -> str:
        lines = [f"═══ {self.title} ═══"]
        for r in self.reports:
            wflag = (f" [{r.witnesses.flag()}]"
                     if r.verdict in (Verdict.CLOSED, Verdict.INAPPLICABLE) else "")
            tail = f" — {r.detail}" if r.detail else ""
            lines.append(f"[{r.verdict.value:12s}]{wflag} {r.name}{tail}")
        s = self.summary()
        lines.append(f"═══ ИТОГ: REPRODUCED={s['REPRODUCED']} CLOSED={s['CLOSED']} "
                     f"INAPPLICABLE={s['INAPPLICABLE']} ERROR={s['ERROR']} ═══")
        unknown = s["INAPPLICABLE"] + s["ERROR"]
        if s["REPRODUCED"] == 0 and unknown > 0:
            lines.append(f"ВНИМАНИЕ: зелёный НЕ полный — {unknown} проб(ы) со статусом НЕИЗВЕСТЕН")
        return "\n".join(lines)


def selftest() -> int:
    """Механическая самопроверка харнеса: понижения и bool-совместимость."""
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    w_all = Witnesses(True, True, True)
    w_none = Witnesses(False, False, False)

    # 1. Позитив самодостаточен — свидетели не требуются
    v, _ = classify(True, w_none)
    check("REPRODUCED без свидетелей", v is Verdict.REPRODUCED)

    # 2. CLOSED только при всех трёх
    v, why = classify(False, w_all)
    check("CLOSED при W1+W2+W3", v is Verdict.CLOSED)

    # 3. Каждое отсутствие свидетеля понижает до INAPPLICABLE со своей причиной
    for w_bad, tag in ((Witnesses(False, True, True), "W1"),
                       (Witnesses(True, False, True), "W2"),
                       (Witnesses(True, True, False), "W3")):
        v, why = classify(False, w_bad)
        check(f"понижение {tag}", v is Verdict.INAPPLICABLE and why.startswith(tag))

    # 4. Незавершённый сценарий — ERROR даже при полных свидетелях
    v, _ = classify(False, w_all, scenario_completed=False)
    check("ERROR при незавершённом сценарии", v is Verdict.ERROR)

    # 5. bool-совместимость с историческими батареями
    check("as_bool(REPRODUCED)=True", as_bool(Verdict.REPRODUCED) is True)
    check("as_bool(остальные)=False",
          all(not as_bool(v) for v in (Verdict.CLOSED, Verdict.INAPPLICABLE, Verdict.ERROR)))

    # 6. W3-семантика: тип + маркер
    class PCC(Exception):
        pass
    ok, why = refusal_is_semantic(PCC("COMMIT: WorldState mismatch"), PCC, ARTIFACT_REFUSAL_MARKERS)
    check("W3 наш тип+маркер", ok)
    ok, _ = refusal_is_semantic(ValueError("boom"), PCC, ARTIFACT_REFUSAL_MARKERS)
    check("W3 чужой тип отклонён", not ok)
    ok, _ = refusal_is_semantic(PCC("COMMIT: UNKNOWN"), PCC, ARTIFACT_REFUSAL_MARKERS)
    check("W3 наш тип без маркера отклонён", not ok)

    # 7. Отчёт Battery: честный «зелёный с неизвестными»
    b = Battery("самопроверка отчёта")
    b.add(ProbeReport("x", Verdict.CLOSED, witnesses=w_all))
    b.add(ProbeReport("y", Verdict.INAPPLICABLE, detail="затмение"))
    rep = b.report()
    check("отчёт содержит ВНИМАНИЕ о неизвестных",
          "ВНИМАНИЕ" in rep and "НЕИЗВЕСТЕН" in rep)
    check("итог четырёхчастный",
          "REPRODUCED=0" in rep and "CLOSED=1" in rep and "INAPPLICABLE=1" in rep)

    fails = [n for n, ok in checks if not ok]
    print(f"HARNESS SELFTEST: {len(checks) - len(fails)}/{len(checks)} PASS"
          + (f", FAIL: {fails}" if fails else ""))
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
