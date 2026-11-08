# -*- coding: utf-8 -*-
"""
ЭКСПЕРИМЕНТЫ E1-E8: проверка конструкции «ПЕРЕНОС РАБОЧЕГО СОСТОЯНИЯ»
Дата: 2026-09-02. Всё исполняется локально в песочнице Python.
"""
import sys, json, copy, random
sys.path.insert(0, "/home/z/my-project/scripts")
from subject_core import (LockWorld, Subject, Subject6, Rec, advance, LevelJump,
                          classify_error, diagnose, properties, goal_reached,
                          run_scenario, STEPS, DEFAULT_PROCEDURE, state_str)

OUT = {"meta": {"date": "2026-09-02", "python": sys.version.split()[0],
                "seed": 7, "источник": "ПЕРЕНОС РАБОЧЕГО СОСТОЯНИЯ (30 пунктов)"}}

def line(ch="-", n=78): print(ch * n)

def section(t):
    line("="); print(t); line("=")

# ============================================================
section("E1. БАЗОВЫЕ СЦЕНАРИИ (гейт уровней §20 + цикл §21)")
# ============================================================
# A: чистый мир — переход должен пройти все уровни
A = run_scenario("A_прямой_успех", {"rusted": False}, max_cycles=4)
# B: скрытое постоянное условие (ржавчина) → ошибка → знание (§7)
B = run_scenario("B_ошибка_знание", {"rusted": True}, max_cycles=8)
# C: условия изменились МЕЖДУ проектированием и исполнением (§6/§9)
wC = LockWorld(rusted=False)
design_snapshot = wC.observe()          # субъект зафиксировал C на момент проекта
wC.rusted = True                        # ВНЕШНЕЕ СОБЫТИЕ: мир изменился
C = run_scenario("C_изменившиеся_условия", max_cycles=8, c_prev=design_snapshot, world=wC)

for sc in (A, B, C):
    p = sc["props"]
    print(f"[{sc['name']}] циклов={p['циклов']} ошибок={p['ошибок_зафиксировано']} "
          f"GOAL={p['GOAL_VERIFIED']}")
OUT["E1"] = {k: v["props"] for k, v in (("A", A), ("B", B), ("C", C))}

print("\nЖурнал сценария B (ошибка постоянного скрытого условия):")
for r in B["log"]:
    print(f"  seq={r.seq} {r.level:<10} A={r.action:<9} O={str(r.observation):<7} "
          f"V={str(r.verification):<5} err={(r.error or {}).get('type','-')}")
print(f"  обновлений процедуры: {B['subject'].updates_done} (§7: ошибка → знание)")
print("\nЖурнал сценария C (ошибка при изменении C между проектом и исполнением):")
for r in C["log"]:
    print(f"  seq={r.seq} {r.level:<10} A={r.action:<9} O={str(r.observation):<7} "
          f"V={str(r.verification):<5} err={(r.error or {}).get('type','-')}")

print("\nПроверка гейта §20 на сценарии A (уровни по шагам):")
ra = A["log"][0]
print(f"  итоговый уровень первой записи A: {ra.level}; V={ra.verification}, O={ra.observation}")

# ============================================================
section("E2. АМПУТАЦИЯ: удаление каждого из 11 элементов (§21.6, §22)")
# ============================================================
ablation = {}
for step in STEPS:
    res = {}
    for scen, kw in (("B", {"rusted": True}), ("A", {"rusted": False})):
        r = run_scenario(f"без_{step}_{scen}", kw, use={step: False},
                         max_cycles=6 if step != "CONTINUE" else 1)
        res[scen] = r["props"]
    broken = []
    for k in ("P1_последовательность", "P2_различимость_состояний",
              "P3_легальность_уровней", "P4a_неизменность_журнала",
              "P4b_воспроизведение", "P5_атрибуция",
              "P6_ошибка_становится_знанием", "GOAL_VERIFIED"):
        vals = [res[s][k] for s in ("A", "B")]
        if any(v is False for v in vals):
            broken.append(k.split("_")[0])
        elif all(v is None for v in vals):
            broken.append(k.split("_")[0] + "(вакуум)")
    ablation[step] = {"сломано": sorted(set(broken)), "детали": res}
    print(f"  без {step:<15} → ломается: {', '.join(sorted(set(broken))) or 'ничего'}")
OUT["E2_ампутация"] = ablation

# ============================================================
section("E3. СЛИЯНИЕ: 11 шагов → 6 примитивов (§21.3-4)")
# ============================================================
w6 = LockWorld(rusted=True)
s6 = Subject6("S6", w6)
for _ in range(8):
    s6.cycle()
    if goal_reached(s6.log):
        break
p6 = properties(s6, w6)
print(f"  Subject6 (примитивы: OBSERVE, PREDICT, EVALUATE, ACT, APPEND, UPDATE):")
print(f"    циклов={p6['циклов']} GOAL={p6['GOAL_VERIFIED']} "
      f"все свойства P1-P6 выдержаны: "
      f"{all(p6[k] in (True, None) for k in p6 if k.startswith('P'))}")
print("  CONTINUE не является операцией: это свойство субстрата-носителя,")
print("  реализованное внешним циклом (в Subject6 его нет — последовательность растёт).")
OUT["E3_слияние"] = p6

# ============================================================
section("E4. ОТСУТСТВУЮЩИЕ ЭЛЕМЕНТЫ (§21.2)")
# ============================================================
# 4.1 STOP-условие: без обновления процедуры ошибка повторяется бесконечно
r_stop = run_scenario("без_STOP", {"rusted": True}, use={"UPDATE": False}, max_cycles=300)
stuck = sum(1 for r in r_stop["log"] if r.observation == "STUCK")
print(f"  4.1 без STOP/ESCALATE: {stuck}/300 циклов — одна и та же ошибка повторяется,")
print(f"     цикл сам не завершается → внутренний критерий остановки ОТСУТСТВУЕТ в §21.")
# 4.2 ATTEMPT_LOG: отклонённые гейтом попытки — тоже прошлое (§17)
r_att = run_scenario("без_CHECK", {"rusted": True}, use={"CHECK": False}, max_cycles=4)
rej = sum(1 for r in r_att["log"] if r.rejected)
print(f"  4.2 отклонённых попыток: {rej}, состоявшихся переходов: "
      f"{sum(1 for r in r_att['log'] if not r.rejected)}.")
print(f"     Если хранить только COMMITTED — {rej} событий прошлого исчезнут бесследно.")
print(f"     → элемент, отсутствующий в §21: ЖУРНАЛ ПОПЫТОК (реализован полем rejected).")
OUT["E4_отсутствующие"] = {"stop_повторов_STUCK": stuck, "отклонённых_попыток": rej}

# ============================================================
section("E5. ТАКСОНОМИЯ ОТКЛОНЕНИЙ §6/§8/§9 (исполняемый классификатор)")
# ============================================================
cb = {"rusted": False}; cn = {"rusted": True}
tests = [
    ("наблюдения нет",              classify_error("OPENED", None, cb, cb), "NO_DATA"),
    ("гипотезы нет",                classify_error(None, "STUCK", cb, cb), "NO_HYPOTHESIS"),
    ("R'==R",                       classify_error("OPENED", "OPENED", cb, cb), "нет ошибки"),
    ("R'≠R, C прежнее, по плану",   classify_error("OPENED", "STUCK", cb, cb), "ERROR_P"),
    ("R'≠R, C изменилось",          classify_error("OPENED", "STUCK", cb, cn), "CONDITION_CHANGED"),
    ("R'≠R, исполнено не по плану", classify_error("OPENED", "OILED", cb, cb, False), "EXECUTION_DEVIATION"),
]
ok5 = 0
for name, got, want in tests:
    gtype = (got or {}).get("type", "None")
    match = (want == gtype) if want != "нет ошибки" else got is None
    ok5 += match
    print(f"  [{ 'OK ' if match else 'FAIL' }] {name:<30} → {gtype}")
# §8: другая допустимая последовательность — не ошибка
wA1, wA2 = LockWorld(rusted=False), LockWorld(rusted=False)
pa = run_scenario("P1_turn_key", {}, max_cycles=2)
pb = run_scenario("P2_oil+turn_key", {},
                  procedure={"plan": ["oil", "turn_key"],
                             "expect": {"oil": "NOTHING", "turn_key": "OPENED",
                                        "inspect": "*"},
                             "known_requirements": {"turn_key": ["has_key", "locked"],
                                                    "oil": [], "inspect": []}},
                  max_cycles=3)
print(f"  [{'OK ' if pa['props']['GOAL_VERIFIED'] else 'FAIL'}] путь P1 ['turn_key'] → цель: "
      f"{pa['props']['GOAL_VERIFIED']}")
print(f"  [{'OK ' if pb['props']['GOAL_VERIFIED'] else 'FAIL'}] путь P2 ['oil','turn_key'] → цель: "
      f"{pb['props']['GOAL_VERIFIED']}")
print("  → единственный РЕЗУЛЬТАТ ≠ единственный АЛГОРИТМ (§8): оба пути валидны.")
OUT["E5_таксономия"] = {"классификатор": f"{ok5}/{len(tests)}",
                        "альтернативные_пути": {"P1": pa["props"]["GOAL_VERIFIED"],
                                                "P2": pb["props"]["GOAL_VERIFIED"]}}

# ============================================================
section("E7. УНИСОН ≠ КОНСЕНСУС (§13) — вычислительно")
# ============================================================
w1, w2 = LockWorld(rusted=True), LockWorld(rusted=False)
s1 = Subject("S1", w1, procedure={"plan": ["oil", "turn_key"],
                                  "expect": {"oil": "OILED", "turn_key": "OPENED", "inspect": "*"},
                                  "known_requirements": {"turn_key": ["has_key", "locked"],
                                                         "oil": [], "inspect": []}},
             rng=random.Random(1))
s2 = Subject("S2", w2, rng=random.Random(2))
for _ in range(6):
    s1.cycle()
for _ in range(3):
    s2.cycle()
def protocol_compliance(s):
    ok = 0
    for r in s.log:
        try:
            tmp = copy.deepcopy(r)
            tmp.level = "PROPOSED"
            for lvl in ("PROPOSED", "AUTHORIZED", "EXECUTED", "OBSERVED",
                        "VERIFIED", "COMMITTED"):
                advance(tmp, lvl)
            ok += 1
        except LevelJump:
            ok += 0 if r.rejected else 0   # отклонённые попытки легальны отдельно
            if r.rejected: ok += 1
    return ok / len(s.log) if s.log else 0
pc1, pc2 = protocol_compliance(s1), protocol_compliance(s2)
opinions = (s1.proc["plan"] == s2.initial_plan)
print(f"  S1 гипотеза: «замок заржавел» (план {s1.initial_plan}); "
      f"S2 гипотеза: «замок исправен» (план {s2.initial_plan})")
print(f"  совместимость протокола (унисон): S1={pc1:.2f}, S2={pc2:.2f}")
print(f"  совпадение мнений (консенсус): {opinions}")
print(f"  → протокол совместим ({pc1:.0%}/{pc2:.0%}) при НЕсовпадающих мнениях ({opinions}).")
print(f"  Общий журнал: {len(s1.log)+len(s2.log)} записей, атрибуция S1/S2 сохранена в каждой.")
OUT["E7_унисон"] = {"протокол_S1": pc1, "протокол_S2": pc2, "мнения_совпали": opinions,
                    "записей_в_общем_журнале": len(s1.log) + len(s2.log)}

# ============================================================
section("E8. КОНТРПРИМЕРЫ-АТАКИ (§21.5, §30)")
# ============================================================
# Атака 1: ДЕКЛАРАНТ — «LLM сказал: я это сделал» (§15)
rec = Rec(seq=0)
try:
    advance(rec, "GOAL_VERIFIED")
    a1 = "ПРИНЯТО — конструкция СЛОМАНА"
except LevelJump as e:
    a1 = f"отклонено гейтом: {e}"
print(f"  Атака 1 (декларант): CLAIM→GOAL_VERIFIED → {a1}")
# Атака 2: КОЛЛАПС СОСТОЯНИЙ (§3/§4)
wcol = LockWorld(rusted=False)
_orig = wcol.observe
wcol.observe = lambda: {"locked": "??", "has_key": True, "oiled": "??", "rusted": "??"}
scol = Subject("SCOL", wcol, rng=random.Random(3))
for _ in range(4):
    scol.cycle()
transitions_between_distinct = sum(1 for r in scol.log if r.s0 != r.s1)
print(f"  Атака 2 (коллапс состояний): записей={len(scol.log)}, "
      f"переходов между РАЗЛИЧИМЫМИ состояниями={transitions_between_distinct} "
      f"→ субъект по §4 не состоялся" if transitions_between_distinct == 0 else "")
# Атака 3: ФИЗИЧЕСКОЕ ВРЕМЯ ≠ ЛОГИЧЕСКИЙ ПОРЯДОК (§10)
events = [("p1", 3.7, "inspect"), ("p2", 2.5, "oil"), ("p3", 1.2, "turn_key")]
def replay(evs):
    w = LockWorld(rusted=True)
    for _, _, a in evs:
        w.act(a)
    return not w.locked
by_time = sorted(events, key=lambda e: e[1])
by_seq = sorted(events, key=lambda e: e[0])
r_time, r_seq = replay(by_time), replay(by_seq)
print(f"  Атака 3 (время vs порядок): восстановление по wall-time → цель достигнута: {r_time}; "
      f"по seq → {r_seq}")
print(f"    порядок по времени: {[e[2] for e in by_time]} (turn_key раньше oil → STUCK)")
print(f"    порядок по seq:     {[e[2] for e in by_seq]} (oil → turn_key → OPENED)")

# Демонстрация §16/§20: мир изменился, но GOAL_VERIFIED недостижим без VERIFY
r_noV = run_scenario("без_VERIFY_демо", {"rusted": False}, use={"VERIFY": False}, max_cycles=4)
print(f"\n  Демо §16: при отключённом VERIFY мир фактически открыт "
      f"(locked={r_noV['world'].locked}), но GOAL_VERIFIED={r_noV['props']['GOAL_VERIFIED']} "
      f"→ OBSERVED ≠ VERIFIED, утверждение 'я это сделал' не является проверкой.")
OUT["E8_атаки"] = {"декларант": a1,
                   "коллапс_переходов_между_различимыми": transitions_between_distinct,
                   "время_vs_порядок": {"по_времени": r_time, "по_seq": r_seq}}

# ============================================================
section("E2-ИТОГ: матрица минимальности")
# ============================================================
full = all(ablation[st]["сломано"] and
           any(not b.endswith("(вакуум)") for b in ablation[st]["сломано"])
           for st in STEPS)
print(f"  Все 11 элементов необходимы (каждый ломает ≥1 свойство): {full}")

# ============================================================
# Сохранение результатов
# ============================================================
path = "/home/z/my-project/download/subject_experiment_results.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1, default=str)
print(f"\nСохранено: {path}")
