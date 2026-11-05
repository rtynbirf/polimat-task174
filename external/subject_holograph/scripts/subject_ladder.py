# -*- coding: utf-8 -*-
"""
ЛЕСТНИЦА МОДЕЛЕЙ СУБЪЕКТНОСТИ (спич 3-х ИИ -> исполнение 4-м участником)
M0  = STATE + TRANSITION                       (просто последовательность)
M1  = + ATTRIBUTION (поле owner)               (атрибутированная последовательность)
M2  = + CONTINUITY (связный лог с ID)          (атрибутированная траектория)
M2' = ИНКАПСУЛИРОВАННЫЙ СУБЪЕКТ:               (источник переходов)
      INTERNAL_STATE + TRANSITION_FUNCTION + CAUSAL_PROOF(сжатая непрерывность)
M3l = M2' + VERIFICATION без UPDATE            (запертый верификатор)

Хеши/приватность — РЕАЛИЗАЦИИ (§23), не фундамент.
Приватность в песочнице имитируется конвенцией "_": закрытость в реальной
системе требует TCB — это остаётся UNKNOWN (см. спичи).
"""
import hashlib

def H(*parts) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]

# ============================================================
# ЛОГОВЫЕ МОДЕЛИ: субъектность = свойство представления в журнале
# ============================================================
def rec(s0, action, s1, owner=None, ref=None, prev=None):
    return {"s0": s0, "action": action, "s1": s1,
            "owner": owner, "ref": ref, "prev": prev}

def recognize_M0(log):
    """M0: любая непустая последовательность неразличима от чужой."""
    return len(log) > 0

def recognize_M1(log):
    """M1: все записи несут один и тот же owner (проверить нечего кроме поля)."""
    return bool(log) and all(r["owner"] == log[0]["owner"] for r in log)

def chain_linked(log):
    for i in range(1, len(log)):
        if log[i]["prev"] != log[i-1]["ref"]:
            return False
    return len({r["ref"] for r in log}) == len(log)

def recognize_M2(log):
    """M2: owner единый + цепочка связна (внутренняя когерентность лога)."""
    return recognize_M1(log) and chain_linked(log)

class LogSubject:
    """Носитель логовой модели: пишет переходы в журнал."""
    def __init__(self, owner, model="M2"):
        self.owner = owner
        self.model = model
        self.log = []
        self._refc = 0
    def write(self, s0, action, s1):
        self._refc += 1
        r = rec(s0, action, s1, owner=self.owner,
                ref=f"{self.owner}#{self._refc}",
                prev=self.log[-1]["ref"] if self.log else "GENESIS")
        self.log.append(r)
        return r

# ============================================================
# M2' ИНКАПСУЛИРОВАННЫЙ СУБЪЕКТ
# ============================================================
class M2pSubject:
    """
    S = <identity, value, proof> (закрыто) + transition_function (закрыто).
    Публичны: label (произвольный ярлык) и public_log (для наблюдаемости).
    Субъектность — в способности ПОРОЖДАТЬ переходы из внутреннего состояния,
    а не в наличии записей.
    """
    def __init__(self, identity, initial_value, func):
        self._identity = identity          # внутренняя идентичность (нагружена в цепи)
        self._value = initial_value        # внутреннее состояние
        self._func = func                  # ПРИЧИНА переходов; None = мёртв
        self._proof = H("GENESIS", identity, initial_value)   # постулат genesis
        self.public_label = identity       # внешний ярлык (может менять кто угодно)
        self.public_log = []               # наблюдаемость, НЕ источник субъектности
        self.discrepancies = []            # для M3-locked
        self.expected = None               # для M3-locked (верификация без обновления)

    # --- внутренний акт перехода ---
    def transition(self, action):
        if self._func is None:
            return {"status": "BLOCKED_DEAD"}          # мёртвый субъект (A7)
        new_value = self._func(self._value, action)
        if new_value == self._value:
            return {"status": "NO_TRANSITION"}         # S0 == S1: перехода нет
        new_proof = H(self._proof, self._identity, action, new_value)
        r = {"seq": len(self.public_log), "s0": self._value, "action": action,
             "s1": new_value, "proof": new_proof, "label": self.public_label}
        self._proof, self._value = new_proof, new_value
        self.public_log.append(r)
        # M3-locked: верификация без права обновления функции
        if self.expected is not None:
            ok = (new_value == self.expected)
            r["verification"] = "PASS" if ok else "FAIL"
            if not ok:
                self.discrepancies.append(r["seq"])    # UPDATE FORBIDDEN
        return {"status": "OK", "record": r}

    # --- способность продолжить последовательность (дискриминатор подделки) ---
    def can_continue(self):
        """Субъект способен породить СЛЕДУЮЩИЙ переход из внутреннего состояния.
        Подделка без функции — не способна: ей нечем продолжить цепь."""
        return self._func is not None

    # --- самосверка: публичный лог воспроизводим из genesis функцией? ---
    def self_check(self, log=None):
        log = self.public_log if log is None else log
        v, p = None, None
        # восстановить genesis из первой записи невозможно в общем случае,
        # поэтому сверяем с конца внутренней цепи: субъект знает (value, proof) до лога
        v, p = self._value, self._proof
        for r in reversed(log):
            if r["s1"] != v or r["label"] != self.public_label:
                return False
            # обратный шаг: proof был H(prev_proof, identity, action, v)
            # перебор невозможен — сверяем только по структуре и значению состояния
            v = r["s0"]
        return True

    def replay_check(self, genesis_value, log=None):
        """Полная проверка лога: воспроизвести всю цепь от genesis.
        Доступна только носителю (знает функцию и genesis)."""
        log = self.public_log if log is None else log
        v = genesis_value
        p = H("GENESIS", self._identity, genesis_value)
        for r in log:
            if r["s0"] != v:
                return False, f"разрыв в seq={r['seq']}: ожидалось s0={v}"
            nv = self._func(v, r["action"]) if self._func else None
            if nv != r["s1"]:
                return False, f"подделка в seq={r['seq']}: функция не воспроизводит переход"
            np = H(p, self._identity, r["action"], r["s1"])
            if np != r["proof"]:
                return False, f"подделка proof в seq={r['seq']}"
            v, p = nv, np
        return True, "цепь воспроизводима от genesis"

    def tamper_detected(self, genesis_value, tampered_log):
        ok, why = self.replay_check(genesis_value, tampered_log)
        return not ok, why

# ============================================================
# M3-LOCKED (верифицирующий агент без права обновления)
# ============================================================
def make_m3_locked(identity, value, func, expected):
    s = M2pSubject(identity, value, func)
    s.expected = expected
    return s

# ============================================================
# A8: ДАТЧИК vs АГЕНТ — контрфактический тест источника
# ============================================================
class WorldAuto:
    """Автономный мир: значение меняется само (логическое время)."""
    def __init__(self, v0=0):
        self.v = v0
        self.t = 0
    def tick(self):
        self.t += 1
        self.v += 1
        return self.v

class Sensor:
    """Регистратор: его 'переходы' — зеркала переходов мира."""
    def __init__(self, world, name="Sensor_1"):
        self.world = world
        self.name = name
        self.readings = []
    def step(self):
        self.readings.append(self.world.v)
        return self.readings[-1]

class AgentSrc:
    """Источник: его переходы порождаются ЕГО функцией и меняют мир."""
    def __init__(self, world, name="Agent_1"):
        self.world = world
        self.name = name
        self.acts = []
        self.alive = True
    def step(self):
        if not self.alive:
            return None
        before = self.world.v
        self.world.v += 10          # действие агента: только он так меняет мир
        self.acts.append((before, self.world.v))
        return self.world.v
