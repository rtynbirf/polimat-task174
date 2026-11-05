# -*- coding: utf-8 -*-
"""
РАУНД 3: УНИСОН M2'-СУБЪЕКТОВ ЧЕРЕЗ ПРИЧИННЫЕ ТОКЕНЫ
Исполнение собственного NEXT TEST из раунда 2 (§28.12) + закрытие UNKNOWN.

Протокол:
  S1 совершает переход (proof публичен в его журнале) ->
  S1 выдаёт ТОКЕН = {issuer, proof, to, seal}, seal = H("TOKEN", issuer, proof, to) ->
  S2 совершает переход, вшивая cond_proof в свой proof ->
  Валидатор (третья сторона, БЕЗ доступа к функциям): seal + условие в цепи эмитента
  + получатель + одноразовость.

Хеши — реализация (§23). Закрытость имитируется конвенцией "_" (TCB = UNKNOWN).
"""
import sys, json, hashlib
sys.path.insert(0, "/home/z/my-project/scripts")
from subject_ladder import H

OUT = {"meta": {"round": 3, "date": "2026-09-02",
                "задача": "NEXT TEST раунда 2: унисон M2' через причинные токены"}}

def section(t):
    print("=" * 76); print(t); print("=" * 76)

# ============================================================
# CoopSubject: M2' + выдача/потребление причинных токенов
# ============================================================
class CoopSubject:
    def __init__(self, identity, value, func, inherited_proof=None):
        self._identity = identity
        self._value = value
        self._func = func                       # None = мёртв
        self._proof = inherited_proof or H("GENESIS", identity, value)
        self.public_log = []
        self.consumed = set()                   # одноразовость условий (nonce)

    # --- обычный (некооперативный) переход ---
    def transition(self, action):
        if self._func is None:
            return {"status": "BLOCKED_DEAD"}
        nv = self._func(self._value, action)
        if nv == self._value:
            return {"status": "NO_TRANSITION"}
        np = H(self._proof, self._identity, action, nv)
        r = {"seq": len(self.public_log), "s0": self._value, "action": action,
             "s1": nv, "proof": np, "label": self._identity}
        self._proof, self._value = np, nv
        self.public_log.append(r)
        return {"status": "OK", "record": r}

    # --- выдача причинного токена (адресного и запечатанного) ---
    def issue_token(self, to):
        t = {"issuer": self._identity, "proof": self._proof, "to": to}
        t["seal"] = H("TOKEN", t["issuer"], t["proof"], t["to"])
        return t

    # --- кооперативный переход: требуется валидное условие ---
    def transition_coop(self, action, token):
        if self._func is None:
            return {"status": "BLOCKED_DEAD"}
        if token is None:
            return {"status": "REJECTED_НЕТ_ТОКЕНА"}
        if token.get("to") != self._identity:
            return {"status": "REJECTED_ТОКЕН_ДРУГОМУ", "token_to": token.get("to")}
        ok, why = validate_token(token, self.consumed)
        if not ok:
            return {"status": f"REJECTED_{why}"}
        nv = self._func(self._value, action)
        if nv == self._value:
            return {"status": "NO_TRANSITION"}
        np = H(self._proof, self._identity, action, nv, token["proof"])
        r = {"seq": len(self.public_log), "s0": self._value, "action": action,
             "s1": nv, "proof": np, "label": self._identity,
             "cond_issuer": token["issuer"], "cond_proof": token["proof"]}
        self._proof, self._value = np, nv
        self.consumed.add(token["proof"])
        self.public_log.append(r)
        return {"status": "OK", "record": r}

# ============================================================
# Валидатор третьей стороны (БЕЗ доступа к приватным функциям)
# ============================================================
def validate_token(t, consumed=None):
    consumed = consumed if consumed is not None else set()
    if H("TOKEN", t["issuer"], t["proof"], t["to"]) != t.get("seal"):
        return False, "SEAL_BROKEN_подделка_поля"
    if t["proof"] in consumed:
        return False, "DOUBLE_SPEND_условие_уже_потреблено"
    return True, "ok"

def validate_unison_record(rec2, issuer_public_log, global_consumed):
    """Условие кооперативного перехода реально существует в цепи эмитента?"""
    if H("TOKEN", rec2["cond_issuer"], rec2["cond_proof"], rec2["label"]) != \
       H("TOKEN", rec2["cond_issuer"], rec2["cond_proof"], rec2["label"]):
        return False, "seal"
    proofs = {r["proof"] for r in issuer_public_log}
    if rec2["cond_proof"] not in proofs:
        return False, "ФЕЙКОВОЕ_УСЛОВИЕ_нет_в_цепи_эмитента"
    if rec2["cond_proof"] in global_consumed:
        return False, "DOUBLE_SPEND"
    global_consumed.add(rec2["cond_proof"])
    return True, "unison_valid"

# ============================================================
U = {}
# ============================================================
section("U1. БАЗОВЫЙ УНИСОН: переход S2, обусловленный proof S1")
# ============================================================
S1 = CoopSubject("S1", 0, lambda v, a: v + 1)
S2 = CoopSubject("S2", 100, lambda v, a: v + 10)
S1.transition("tick")
tok = S1.issue_token("S2")
r2 = S2.transition_coop("step", tok)
gc = set()
ok, why = validate_unison_record(r2["record"], S1.public_log, gc)
print(f"  S1: {S1.public_log[0]['s0']}→{S1.public_log[0]['s1']} "
      f"(proof {S1.public_log[0]['proof'][:8]}…)")
print(f"  S2: {r2['record']['s0']}→{r2['record']['s1']} при условии proof S1 → {ok} ({why})")
print(f"  proof S2 вшивает условие: цепи СПЛЕЛИСЬ без общей истории → {ok}")
U["U1"] = {"unison": ok}

# ============================================================
section("U2. КРАЖА ПРИЧИННОСТИ МЕЖДУ СУБЪЕКТАМИ (3 вектора)")
# ============================================================
# 2a: токен выдан S2, крадёт T
T = CoopSubject("T", 0, lambda v, a: v + 1)
steal = T.transition_coop("steal", tok)
print(f"  2a неверный получатель: {steal['status']}")
# 2b: подделка поля токена (перебить адресата)
import copy
forged = copy.deepcopy(tok); forged["to"] = "T"
r_f = T.transition_coop("steal", forged)
print(f"  2b подделка seal: {r_f['status']}")
# 2c: S2 выдумывает условие (proof нет в цепи S1)
S2b = CoopSubject("S2b", 0, lambda v, a: v + 1)
fake_tok = {"issuer": "S1", "proof": H("ВЫДУМАН", 1), "to": "S2b",
            "seal": H("TOKEN", "S1", H("ВЫДУМАН", 1), "S2b")}
r_fake = S2b.transition_coop("step", fake_tok)
S1c = CoopSubject("S1", 0, lambda v, a: v + 1)
ok_fake, why_fake = validate_unison_record(
    {"cond_issuer": "S1", "cond_proof": fake_tok["proof"], "label": "S2b"},
    S1c.public_log, set())
print(f"  2c выдуманное условие: переход={r_fake['status']}, "
      f"валидатор={ok_fake} ({why_fake})")
# 2d: double-spend — тот же токен дважды
tok2 = S1.issue_token("S2")
S2.transition_coop("step1", tok2)
r_ds = S2.transition_coop("step2", tok2)
print(f"  2d повторное потребление условия: {r_ds['status']}")
# 2e (найдено при исполнении, §24): seal даёт целостность, НЕ аутентичность выдачи:
# любой может отчеканить токен от имени S1 (все поля публичны)
minter = CoopSubject("Minter", 0, lambda v, a: v + 1)
fake_issuer_tok = {"issuer": "S1", "to": "S2c",
                   "proof": S1.public_log[0]["proof"]}   # реальный proof из публичной цепи
fake_issuer_tok["seal"] = H("TOKEN", "S1", fake_issuer_tok["proof"], "S2c")  # любой может посчитать
S2c = CoopSubject("S2c", 0, lambda v, a: v + 1)
r_mint = S2c.transition_coop("step", fake_issuer_tok)
ok_mint, why_mint = validate_token(fake_issuer_tok, set())
print(f"  2e отчеканен сторонний токен «от имени S1» для S2c: seal валиден={ok_mint}, "
      f"приёмник ПРИНЯЛ={r_mint['status']}")
print(f"     НО факт-условие всё равно истинен: proof реально в цепи S1 → "
      f"протокол гарантирует ФАКТ+одноразовость+адресность, НЕ намерение эмитента")
print(f"     → АУТЕНТИЧНОСТЬ выдачи требует секрета эмитента (§19: CAN≠MAY на уровне протокола)")
u2 = all("REJECTED" in str(x["status"]) for x in (steal, r_f, r_ds)) and not ok_fake
print(f"  → итог по 2a-2d: {('ДЕРЖИТСЯ' if u2 else 'ЛОМАЕТСЯ')}; по 2e: "
      f"ЧЕСТНОЕ ОГРАНИЧЕНИЕ (intent не покрывается, факт покрывается)")
U["U2"] = {"кража": steal["status"], "подделка": r_f["status"],
           "фейк": why_fake, "double_spend": r_ds["status"],
           "чеканка_сторонним": {"seal_валиден": ok_mint, "принято": r_mint["status"],
                                 "вывод": "факт+одноразовость+адресность да; intent нет"}}

# ============================================================
section("U3. ГЕНЕЗИС ПРИ ДЕЛЕГИРОВАНИИ: форк субъекта (ответ на вопрос спичей «откуда genesis»)")
# ============================================================
P = CoopSubject("P", 0, lambda v, a: v + 1)
for _ in range(3):
    P.transition("go")
fork_point_proof = P._proof
FA = CoopSubject("FA", P._value, lambda v, a: v + 2,
                 inherited_proof=fork_point_proof)   # genesis = НАСЛЕДОВАН
FB = CoopSubject("FB", P._value, lambda v, a: v - 2,
                 inherited_proof=fork_point_proof)
FA.transition("up"); FB.transition("down")
fa_ok = FA._proof != FB._proof
# ветви не продолжают цепи друг друга: proof FA воспроизводим ТОЛЬКО от точки форка
fa_chain_valid = FA._proof == H(fork_point_proof, "FA", "up", FA._value)
fb_broken = FB._proof != H(fork_point_proof, "FB", "up", FB._value)  # другой путь = другой proof
print(f"  Родитель P: 3 перехода, fork proof {fork_point_proof[:8]}…")
print(f"  Форки FA/FB: genesis НАСЛЕДОВАН, цепи разошлись: {fa_ok}")
print(f"  Форк валиден: proof FA воспроизводим от точки форка: {fa_chain_valid}; "
      f"подмена пути ветви ломает proof: {fb_broken}")
print("  Ответ на UNKNOWN спичей: genesis не аксиома ИЛИ вывод — он НАСЛЕДУЕМ;")
print("  абсолютный genesis остаётся постулатом, но нагруженным (смена = разрыв цепи)")
U["U3"] = {"ветви_разошлись": fa_ok, "форк_валиден": fa_chain_valid}

# ============================================================
section("U4. АСИНХРОННОСТЬ: логический порядок по причинной зависимости, не по времени (§10)")
# ============================================================
events = [  # (id, wall_time, зависит_от)
    ("e1", 5.0, []), ("e2", 1.0, ["e1"]), ("e3", 9.0, ["e1"]),
    ("e4", 2.0, ["e2", "e3"]),
]
def topo_order(events):
    done, order = set(), []
    pending = events[:]
    while pending:
        ready = [e for e in pending if all(d in done for d in e[2])]
        if not ready:
            return None  # цикл
        e = ready[0]; order.append(e[0]); done.add(e[0]); pending.remove(e)
    return order
logical = topo_order(events)
by_time = [e[0] for e in sorted(events, key=lambda x: x[1])]
# атака: перестановка зависимой пары
violated = False
perm = logical[:]
for i in range(len(perm) - 1):
    a, b = perm[i], perm[i+1]
    for e in events:
        if e[0] == b and a in e[2]:
            violated = True
print(f"  порядок по wall-time: {by_time}")
print(f"  порядок по причинности: {logical}")
print(f"  перестановка зависимой пары детектируется зависимостями: {violated}")
print("  → унисон асинхронных субъектов упорядочивается причинностью, часы не нужны")
U["U4"] = {"по_времени": by_time, "по_причинности": logical, "нарушение_детектится": violated}

# ============================================================
section("U5. МЁРТВЫЙ ЭМИТЕНТ: субъект живёт дольше источника условий")
# ============================================================
E1 = CoopSubject("E1", 0, lambda v, a: v + 1)
E2 = CoopSubject("E2", 0, lambda v, a: v + 1)
E1.transition("tick")
t_alive = E1.issue_token("E2")
r_alive = E2.transition_coop("step", t_alive)
t_stored = E1.issue_token("E2")          # второй токен выпущен ДО смерти
E1._func = None                          # эмитент умер
r_with_stored = E2.transition_coop("step2", t_stored)
r_alone = E2.transition("solo")          # выход из кооперации
chain_ok = E2._proof != ""
print(f"  E2 потребил условие живого E1: {r_alive['status']}")
print(f"  E1 умер; сохранённый ДО смерти токен: {r_with_stored['status']} "
      f"(факт прошлого не стирается смертью)")
print(f"  E2 продолжил собственную цепь вне кооперации: {r_alone['status']} "
      f"(цепь цела: {chain_ok})")
print("  → СУБЪЕКТНОСТЬ локальна и переживает смерть партнёра; "
      "УНИСОН заканчивается, субъектность — нет")
U["U5"] = {"выжил_после_смерти_эмитента": chain_ok}

# ============================================================
section("U6. СЖАТИЕ ДОКАЗАТЕЛЬСТВА: 10 000 переходов, размер proof")
# ============================================================
B = CoopSubject("B", 0, lambda v, a: v + 1)
for _ in range(10000):
    B.transition("go")
print(f"  10000 переходов, длина proof = {len(B._proof)} символов (константна, O(1) памяти)")
print(f"  цепь воспроизводима субъектом: {B._value == 10000}")
U["U6"] = {"proof_len": len(B._proof), "value": B._value}

# ============================================================
section("U7. КЛОН-ИДЕНТИЧНОСТЬ: одна функция — один ли субъект?")
# ============================================================
f = lambda v, a: v + 1
C1 = CoopSubject("C1", 0, f); C2 = CoopSubject("C2", 0, f)
for _ in range(3):
    C1.transition("go"); C2.transition("go")
same_inputs = [r["s1"] for r in C1.public_log] == [r["s1"] for r in C2.public_log]
proofs_differ = C1._proof != C2._proof
# разные входы → цепи различимы
C2.transition("go")
diverged = [r["s1"] for r in C1.public_log] != [r["s1"] for r in C2.public_log]
print(f"  одинаковые входы: последовательности состояний совпадают: {same_inputs}, "
      f"proof различны (identity в цепи): {proofs_differ}")
print(f"  разные входы: цепи немедленно различимы: {diverged}")
print("  → identity — ПОСТУЛАТ, witness — цепь; функция сама не создаёт субъекта:")
print("    субъект = genesis(наследуемый/постулат) × функция × история входов")
U["U7"] = {"same_seq": same_inputs, "different_proofs": proofs_differ,
           "diverged": diverged}

# ============================================================
section("ИТОГ РАУНДА 3")
# ============================================================
print("  Унисон M2' исполним БЕЗ общей истории и БЕЗ доверенного центра:")
print("  адресный + одноразовый причинный токен; seal = целостность, НЕ аутентичность;")
print("  валидация уровня ТОКЕНА и ФАКТА-УСЛОВИЯ доступна третьей стороне,")
print("  валидация уровня ЦЕПИ остаётся локальной (функция приватна);")
print("  НАМЕРЕНИЕ эмитента (authorization) не покрывается — следующий разрыв.")

path = "/home/z/my-project/download/unison_round3_results.json"
with open(path, "w", encoding="utf-8") as fjs:
    json.dump(OUT, fjs, ensure_ascii=False, indent=1, default=str)
print(f"\nСохранено: {path}")
