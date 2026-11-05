# -*- coding: utf-8 -*-
"""
ЯДРО ИСПОЛНЯЕМОЙ МОДЕЛИ «СУБЪЕКТ»
Формализация документа «ПЕРЕНОС РАБОЧЕГО СОСТОЯНИЯ» (§3, §6-§10, §13, §15-§22).
Все конструкции — реализации, не фундамент (§23).
"""
import json, copy, hashlib, random
from dataclasses import dataclass, field, asdict
from typing import Optional, List

# ============================================================
# §20. УРОВНИ УСПЕХА (запрещено сворачивать в success=true)
# ============================================================
LEVELS = ["PROPOSED", "AUTHORIZED", "EXECUTED", "OBSERVED",
          "VERIFIED", "COMMITTED", "GOAL_VERIFIED"]

class LevelJump(Exception):
    """Попытка перескочить уровень или заявить факт без доказательств (§15, §20)."""

GATE_REQUIREMENT = {
    "PROPOSED":   lambda r: r.hypothesis is not None,
    "AUTHORIZED": lambda r: r.conditions is not None,
    "EXECUTED":   lambda r: r.action is not None and r.actually_executed,
    "OBSERVED":   lambda r: r.observation is not None,
    "VERIFIED":   lambda r: r.verification in ("PASS", "FAIL"),
    "COMMITTED":  lambda r: True,
}

def advance(rec, to: str) -> str:
    """ГЕЙТ: уровень растёт только на +1 и только при наличии доказательств."""
    if to not in LEVELS:
        raise LevelJump(f"неизвестный уровень {to}")
    cur, nxt = LEVELS.index(rec.level), LEVELS.index(to)
    if nxt == cur:
        return rec.level
    if nxt != cur + 1:
        raise LevelJump(f"перескок {rec.level} → {to} запрещён (§20)")
    if to in GATE_REQUIREMENT and not GATE_REQUIREMENT[to](rec):
        raise LevelJump(f"нет доказательств для уровня {to} (§16)")
    rec.level = to
    return to

# ============================================================
# §3. ЗАПИСЬ ПЕРЕХОДА: S0 → [C] → P → A → O → V → S1
# ============================================================
def content_id(obj) -> str:
    """Хеш содержимого — РЕАЛИЗАЦИЯ неизменяемости (§23: не фундамент)."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()[:12]

def state_str(d) -> str:
    return json.dumps(d, sort_keys=True, ensure_ascii=False) if d else "UNKNOWN"

@dataclass
class Rec:
    """Одна попытка перехода. Поля остаются разделимыми (§26)."""
    seq: int
    s0: Optional[str] = None
    conditions: Optional[dict] = None
    hypothesis: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    verification: Optional[str] = None
    s1: Optional[str] = None
    level: str = "PROPOSED"
    attribution: dict = field(default_factory=dict)
    error: Optional[dict] = None
    rejected: Optional[str] = None
    actually_executed: bool = False

    def cid(self) -> str:
        return content_id(asdict(self))

# ============================================================
# МИР: контейнер с замком. Цель: locked == False.
# ============================================================
class LockWorld:
    def __init__(self, rusted=False):
        self.locked = True
        self.has_key = True
        self.oiled = False
        self.rusted = rusted

    def observe(self) -> dict:
        return {"locked": self.locked, "has_key": self.has_key,
                "oiled": self.oiled, "rusted": self.rusted}

    def act(self, a: str) -> str:
        if a == "turn_key":
            if self.rusted and not self.oiled:
                return "STUCK"                       # R' != R
            if self.locked and self.has_key:
                self.locked = False
                return "OPENED"
            return "NOOP" if not self.locked else "FAILED"
        if a == "oil":
            if self.rusted:
                self.oiled = True
                return "OILED"
            return "NOTHING"
        if a == "inspect":
            return f"rusted={self.rusted}"
        return "UNKNOWN_ACTION"

# ============================================================
# §6/§8/§9. КЛАССИФИКАТОР ОТКЛОНЕНИЙ
# ============================================================
def classify_error(expected, observed, c_prev, c_now,
                   executed_as_planned=True, plan_repr="P"):
    """Различает: другой результат / другой алгоритм / изменённые условия /
    отсутствие данных / неопределённость / ошибку (§6)."""
    if observed is None:
        return {"type": "NO_DATA", "status": "UNKNOWN",
                "rule": "§1/§29: наблюдения нет — вывод невозможен"}
    if expected is None:
        return {"type": "NO_HYPOTHESIS", "status": "ERROR_UNDEFINED",
                "rule": "§6: нет ожидаемого R — ошибка не определима"}
    if observed == expected:
        return None
    if c_prev is not None and c_now is not None and c_prev != c_now:
        return {"type": "CONDITION_CHANGED", "status": "HYPOTHESIS",
                "rule": "§6/§9: C изменилась — не ошибка P относительно старой C"}
    if not executed_as_planned:
        return {"type": "EXECUTION_DEVIATION", "status": "HYPOTHESIS",
                "rule": "§6: исполнено не по P"}
    return {"type": "ERROR_P", "status": "LOCALIZED_CANDIDATE",
            "label": f"ERROR({plan_repr} | C → R)",
            "rule": "§6: C сохранено, P исполнено, R'≠R — ошибка процедуры"}

def diagnose(belief: dict, observation: str) -> dict:
    """§7: LOCALIZE DEVIATION → IDENTIFY CONDITION."""
    if observation == "STUCK":
        if belief.get("rusted") and not belief.get("oiled"):
            return {"condition": "rusted_and_not_oiled", "evidence": "belief/inspect"}
        return {"condition": "UNKNOWN", "evidence": None}
    return {"condition": "UNKNOWN", "evidence": None}

# ============================================================
# §21. СУБЪЕКТ: 11-ШАГОВЫЙ ЦИКЛ С АМПУТАЦИОННЫМИ ФЛАГАМИ
# ============================================================
STEPS = ["OBSERVE", "HYPOTHESIZE", "CHECK", "SELECT", "ACT", "OBSERVE_RESULT",
         "VERIFY", "COMMIT", "RECORD_ERROR", "UPDATE", "CONTINUE"]

DEFAULT_PROCEDURE = {
    "plan": ["turn_key"],
    "expect": {"turn_key": "OPENED", "oil": "OILED", "inspect": "*"},
    "known_requirements": {"turn_key": ["has_key", "locked"], "oil": [], "inspect": []},
}

class Subject:
    def __init__(self, name, world, procedure=None, use=None, rng=None, c_prev=None):
        self.name = name
        self.world = world
        self.proc = copy.deepcopy(procedure or DEFAULT_PROCEDURE)
        self.use = {s: True for s in STEPS}
        if use:
            self.use.update(use)
        self.log: List[Rec] = []          # append-only (§17)
        self.hashes: List[str] = []
        self.belief = {}                  # модель мира (обновляется только OBSERVE-шагами)
        self.c_prev = copy.deepcopy(c_prev)   # предыдущая модель условий (§9)
        self.seq = 0
        self.rng = rng or random.Random(7)
        self.initial_plan = list(self.proc["plan"])
        self.updates_done = 0

    def cycle(self) -> Rec:
        u = self.use
        rec = Rec(seq=self.seq)
        rec.attribution["who"] = self.name

        # 1 OBSERVE — исходное состояние должно быть различимым (§3)
        if u["OBSERVE"]:
            self.belief = self.world.observe()
        rec.s0 = state_str(self.belief)

        plan = self.proc["plan"]
        cand = plan[0] if plan else None

        # 2 HYPOTHESIZE — ожидаемый R (без него ошибка неопределима, §6)
        if u["HYPOTHESIZE"]:
            rec.hypothesis = self.proc["expect"].get(cand, "*") if cand else None

        # 3 CHECK — проверка известных условий применимости (§9, §19)
        if u["CHECK"] and cand is not None:
            reqs = self.proc["known_requirements"].get(cand, [])
            rec.conditions = {k: self.belief.get(k) for k in reqs}
            ok = (not reqs) or all(rec.conditions.values())
        else:
            rec.conditions = None
            ok = False

        # 4 SELECT — выбор действия; выбор должен иметь носителя (§18)
        if u["SELECT"]:
            action = cand
            rec.attribution["selector"] = self.name
        else:
            action = self.rng.choice(["turn_key", "oil", "inspect"])
            rec.attribution["selector"] = "RANDOM_НЕАТРИБУТИРОВАНО"
        rec.action = action

        # ГЕЙТ: PROPOSED требует гипотезы, AUTHORIZED — проверенных условий (§19)
        if rec.hypothesis is None:
            rec.rejected = "нет гипотезы → уровень PROPOSED недостижим (§2/§20)"
        else:
            try: advance(rec, "PROPOSED")
            except LevelJump as e: rec.rejected = str(e)
        if rec.rejected is None:
            if ok:
                try: advance(rec, "AUTHORIZED")
                except LevelJump as e: rec.rejected = str(e)
            else:
                rec.rejected = "условия не проверены/не выполнены → AUTHORIZED запрещён (§19)"

        # 5 ACT — единственный элемент, меняющий внешний мир (§15)
        obs_result = None
        if rec.rejected is None:
            if u["ACT"]:
                obs_result = self.world.act(rec.action)
                rec.actually_executed = True
                try: advance(rec, "EXECUTED")
                except LevelJump as e: rec.rejected = str(e)
            else:
                rec.rejected = "ACT отключён → переход не может состояться (§15)"

        # 6 OBSERVE_RESULT — EXECUTED ≠ OBSERVED (§20)
        if rec.rejected is None:
            if u["OBSERVE_RESULT"]:
                rec.observation = obs_result
                self.belief = self.world.observe()   # свежая информация
                try: advance(rec, "OBSERVED")
                except LevelJump as e: rec.rejected = str(e)
            else:
                rec.rejected = "OBSERVE_RESULT отключён → EXECUTED не станет OBSERVED"

        # 7 VERIFY — сравнение O с ожидаемым R; NOT_PERFORMED ≠ PASS (§16, §24)
        if rec.hypothesis not in (None, "*") and rec.observation is not None and u["VERIFY"]:
            rec.verification = "PASS" if rec.observation == rec.hypothesis else "FAIL"
        else:
            rec.verification = "NOT_PERFORMED"
        if rec.rejected is None and rec.verification in ("PASS", "FAIL"):
            try: advance(rec, "VERIFIED")
            except LevelJump as e: rec.rejected = str(e)

        rec.s1 = state_str(self.belief) if rec.actually_executed else rec.s0

        # 9 RECORD_ERROR — классификация ДО фиксации (запись уходит полной)
        if rec.verification == "FAIL":
            if u["RECORD_ERROR"]:
                rec.error = classify_error(rec.hypothesis, rec.observation,
                                           self.c_prev, self.belief,
                                           executed_as_planned=(rec.action == cand),
                                           plan_repr=str(self.proc["plan"]))
                if rec.error:
                    rec.error["diagnosis"] = diagnose(self.belief, rec.observation)
            else:
                rec.error = None   # ошибка утрачена

        # 8 COMMIT — фиксация в append-only журнале (§17)
        if u["COMMIT"]:
            if rec.rejected is None:
                try: advance(rec, "COMMITTED")
                except LevelJump as e: rec.rejected = str(e)
            self.seq += 1
            self.log.append(rec)
            self.hashes.append(rec.cid())
        # (COMMIT отключён → попытка исчезает бесследно — см. E4)

        # 10 UPDATE — ошибка становится знанием только здесь (§7)
        if rec.error and u["UPDATE"]:
            if self.apply_update(rec):
                self.updates_done += 1

        # Потребление плана: выполненный по плану шаг уходит из очереди
        # (найдено экспериментом: без этого субъект повторяет первый шаг вечно)
        if rec.verification == "PASS" and rec.action == cand and self.proc["plan"]:
            self.proc["plan"].pop(0)

        # c_prev обновляется ПОСЛЕ цикла (§9: сравнение моделей условий)
        self.c_prev = dict(self.belief) if self.belief else self.c_prev

        # 11 CONTINUE — реализуется внешним циклом носителя (см. E3: свойство субстрата)
        return rec

    def apply_update(self, rec) -> bool:
        """§7: ошибка → наблюдение → классификация → причина → ограничение → P'."""
        d = (rec.error or {}).get("diagnosis", {}).get("condition")
        if d == "rusted_and_not_oiled" and "oil" not in self.proc["plan"]:
            self.proc["plan"] = ["oil"] + self.proc["plan"]
            self.proc["expect"]["oil"] = "OILED"
            self.proc["known_requirements"]["oil"] = []
            return True
        return False

# ============================================================
# E3. СЛИТАЯ РЕАЛИЗАЦИЯ: 6 ПРИМИТИВОВ вместо 11 именованных шагов
# OBSERVE, PREDICT(гипотеза+выбор), EVALUATE(проверка+верификация),
# ACT(действие+наблюдение результата), APPEND(фиксация+ошибка), UPDATE
# ============================================================
class Subject6:
    def __init__(self, name, world, procedure=None):
        self.name = name
        self.world = world
        self.proc = copy.deepcopy(procedure or DEFAULT_PROCEDURE)
        self.log: List[Rec] = []
        self.hashes: List[str] = []
        self.belief = {}
        self.seq = 0
        self.initial_plan = list(self.proc["plan"])
        self.updates_done = 0

    def cycle(self) -> Rec:
        rec = Rec(seq=self.seq)
        rec.attribution = {"who": self.name, "selector": self.name}
        self.belief = self.world.observe()                          # OBSERVE
        rec.s0 = state_str(self.belief)
        plan = self.proc["plan"]
        act = plan[0] if plan else None                             # PREDICT
        rec.hypothesis = self.proc["expect"].get(act, "*") if act else None
        rec.conditions = ({k: self.belief.get(k)
                           for k in self.proc["known_requirements"].get(act, [])}
                          if act else None)
        rec.action = act
        if act is None:
            rec.rejected = "план пуст → PROPOSED недостижим (§2)"
        elif rec.conditions and not all(rec.conditions.values()):   # EVALUATE#1
            rec.rejected = "условия не выполнены (§19)"
        else:
            o = self.world.act(act)                                 # ACT
            rec.actually_executed = True
            rec.observation = o
            self.belief = self.world.observe()
            rec.s1 = state_str(self.belief)
            rec.verification = ("PASS" if o == rec.hypothesis else "FAIL"
                                if rec.hypothesis not in (None, "*")
                                else "NOT_PERFORMED")               # EVALUATE#2
            if rec.verification == "FAIL":
                rec.error = classify_error(rec.hypothesis, o, None, self.belief,
                                           True, str(self.proc["plan"]))
                if rec.error:
                    rec.error["diagnosis"] = diagnose(self.belief, o)
                d = (rec.error or {}).get("diagnosis", {}).get("condition")  # UPDATE
                if d == "rusted_and_not_oiled" and "oil" not in self.proc["plan"]:
                    self.proc["plan"] = ["oil"] + self.proc["plan"]
                    self.proc["expect"]["oil"] = "OILED"
                    self.proc["known_requirements"]["oil"] = []
                    self.updates_done += 1
            if rec.verification == "PASS" and self.proc["plan"]:   # потребление плана
                self.proc["plan"].pop(0)
            try:
                for lvl in ("PROPOSED", "AUTHORIZED", "EXECUTED",
                            "OBSERVED", "VERIFIED", "COMMITTED"):
                    if lvl == "PROPOSED" and rec.hypothesis is None:
                        raise LevelJump("нет гипотезы")
                    advance(rec, lvl)
            except LevelJump as e:
                rec.rejected = str(e)
        self.seq += 1
        self.log.append(rec)                                        # APPEND
        self.hashes.append(rec.cid())
        return rec

# ============================================================
# ПРОВЕРКИ СВОЙСТВ P1-P6 (§22: минимальность = что ломается при удалении)
# ============================================================
def goal_reached(log) -> bool:
    for r in log:
        if r.verification == "PASS" and r.s1 and r.s1 != "UNKNOWN":
            try:
                if json.loads(r.s1).get("locked") is False:
                    return True
            except Exception:
                pass
    return False

def properties(s, world) -> dict:
    log = s.log
    p = {}
    seqs = [r.seq for r in log]
    p["P1_последовательность"] = (seqs == sorted(seqs) and len(set(seqs)) == len(seqs)) if log else None
    p["P2_различимость_состояний"] = (all(r.s0 != "UNKNOWN" and r.s1 != "UNKNOWN" for r in log)
                                      if log else None)
    p["P3_легальность_уровней"] = all(
        (r.level != "VERIFIED" or r.verification in ("PASS", "FAIL")) and
        (r.level != "OBSERVED" or r.observation is not None) and
        (r.level != "EXECUTED" or (r.action is not None and r.actually_executed))
        for r in log) if log else None
    # P4a: неизменность зафиксированного прошлого (§17)
    p["P4a_неизменность_журнала"] = ([r.cid() for r in log] == s.hashes) if log else None
    # P4b: воспроизведение — журнал достаточен для восстановления итога мира
    w = LockWorld(rusted=world.rusted)
    for r in log:
        if r.actually_executed and r.action:
            w.act(r.action)
    p["P4b_воспроизведение"] = (w.observe() == world.observe())
    # P5: атрибуция выбора и носителя (§18)
    p["P5_атрибуция"] = all(
        r.attribution.get("who") and
        (r.rejected is not None or r.attribution.get("selector") not in (None, "RANDOM_НЕАТРИБУТИРОВАНО"))
        for r in log) if log else None
    # P6: ошибка → знание (§7) — поведенчески
    errors = [r for r in log if r.error]
    unrecorded = sum(1 for r in log if r.verification == "FAIL" and r.error is None)
    if errors:
        p["P6_ошибка_становится_знанием"] = (getattr(s, "updates_done", 0) > 0) and goal_reached(log)
    elif unrecorded:
        p["P6_ошибка_становится_знанием"] = False   # ошибка произошла, но утрачена
    else:
        p["P6_ошибка_становится_знанием"] = None    # материала нет — N/A, не PASS
    p["GOAL_VERIFIED"] = goal_reached(log)
    p["ошибок_зафиксировано"] = len(errors)
    p["циклов"] = len(log)
    return p

def run_scenario(name, world_kwargs=None, use=None, procedure=None,
                 max_cycles=8, seed=7, c_prev=None, world=None):
    world = world if world is not None else LockWorld(**(world_kwargs or {}))
    s = Subject("S:" + name, world, procedure=procedure, use=use,
                rng=random.Random(seed), c_prev=c_prev)
    for i in range(max_cycles):
        if use and use.get("CONTINUE") is False and i >= 1:
            break                                    # 11 CONTINUE отключён
        s.cycle()
        if goal_reached(s.log):
            break
    return {"name": name, "world": world, "subject": s,
            "props": properties(s, world), "log": s.log}
