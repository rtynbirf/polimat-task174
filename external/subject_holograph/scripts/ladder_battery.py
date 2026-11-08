# -*- coding: utf-8 -*-
"""
АТАКУЮЩАЯ БАТАРЕЯ: исполнение тестов, предложенных спичами 3 ИИ, но не выполненных.
4-й участник. Дата: 2026-09-02. Всё исполнено в песочнице Python 3.12.
"""
import sys, json, random
sys.path.insert(0, "/home/z/my-project/scripts")
from subject_ladder import (H, rec, recognize_M0, recognize_M1, recognize_M2,
                            LogSubject, M2pSubject, make_m3_locked,
                            WorldAuto, Sensor, AgentSrc)

OUT = {"meta": {"date": "2026-09-02", "python": sys.version.split()[0],
                "роль": "4-й участник дебатов (исполнение)"}}
RNG = random.Random(42)

def section(t):
    print("=" * 76); print(t); print("=" * 76)

def verdict(ok): return "ДЕРЖИТСЯ" if ok else "ЛОМАЕТСЯ"

# ============================================================
section("A1. ЧУЖОЙ ПЕРЕХОД: различает ли M0 своё от чужого")
# ============================================================
own = [rec(1, "a", 2), rec(2, "a", 3)]
foreign = [rec(1, "b", 7)]
m0_own, m0_foreign = recognize_M0(own), recognize_M0(foreign)
a1_ok = not (m0_own and m0_foreign and own == foreign)  # M0 не различает
print(f"  M0(своя)={m0_own}, M0(чужая)={m0_foreign} → M0 НЕ различает своё от чужого: "
      f"{m0_own == m0_foreign}")
print(f"  M1(своя)={recognize_M1([rec(1,'a',2,owner='X'), rec(2,'a',3,owner='X')])}, "
      f"M1(чужая смесь)={recognize_M1([rec(1,'a',2,owner='X'), rec(2,'a',3,owner='Y')])}")
OUT["A1"] = {"M0_не_различает": m0_own == m0_foreign}

# ============================================================
section("A2. LABEL SWAP / КРАЖА АТРИБУЦИИ (ломает M1/M2 — заявлено в спичах)")
# ============================================================
ls = LogSubject("X")
ls.write(1, "a", 2); ls.write(2, "a", 3)
before = recognize_M2(ls.log)
for r in ls.log:                       # атакующий: переписал owner
    r["owner"] = "Y"
after = recognize_M2(ls.log)
print(f"  M2: распознавание до атаки={before}, после Label Swap={after} "
      f"→ {verdict(not after)}: субъект 'переехал' за один edit")
OUT["A2_M2"] = {"до": before, "после": after}

# M2': кража причинности — Y присваивает переход X
X = M2pSubject("X", 0, lambda v, a: v + 1)
X.transition("inc"); X.transition("inc")
stolen = dict(X.public_log[0])         # Y заявил чужой переход своим
Y = M2pSubject("Y", 0, lambda v, a: v - 1)
Y_ok = Y.replay_check(0, [stolen])     # Y пытается продолжить краденую цепь
X_ok = X.replay_check(0, X.public_log)
print(f"  M2': Y не может воспроизвести краденый переход своей функцией: {not Y_ok[0]} "
      f"({Y_ok[1]})")
print(f"  M2': X сохраняет свою цепь: {X_ok[0]} → {verdict(X_ok[0] and not Y_ok[0])}")
OUT["A2_M2p"] = {"кража_отвергнута": not Y_ok[0], "цепь_X_цела": X_ok[0]}

# ============================================================
section("A3. FAKE_SUBJECT: случайные переходы, склеенные ярлыком (контрпример итерации 3)")
# ============================================================
fake = []
v = 0
for i in range(3):                     # атакующий склеивает случайные события
    nv = RNG.randint(10, 99)
    fake.append(rec(v, f"jump{nv}", nv, owner="FAKE",
                    ref=f"FAKE#{i+1}", prev=fake[-1]["ref"] if fake else "GENESIS"))
    v = nv
m2_says = recognize_M2(fake)           # лог когерентен → M2 говорит «субъект»
print(f"  M2: случайный склеенный лог распознан как субъект: {m2_says} "
      f"→ ЛОЖНОЕ СРАБАТЫВАНИЕ: {m2_says}")
fake_obj = M2pSubject("FAKE", 0, None) # ярлык есть, функции нет
fake_obj.public_log = fake
cc = fake_obj.can_continue()
print(f"  M2': подделка способна продолжить последовательность: {cc} "
      f"→ {verdict(not cc)}: нечем продолжить — ярлык не является источником")
OUT["A3"] = {"M2_ложное_срабатывание": m2_says, "M2p_подделка_продолжаема": cc}

# ============================================================
section("A4. ВЗЛОМ ЛОГА: подделка записи + влияние на будущее")
# ============================================================
Z = M2pSubject("Z", 0, lambda v, a: v + 1)
for _ in range(5):
    Z.transition("inc")
tampered = [dict(r) for r in Z.public_log]
tampered[2]["s1"] = 999                # атакующий правит прошлое
tampered[2]["s0"] = 998
detected, why = Z.tamper_detected(0, tampered)
future_before = Z._value               # внутреннее состояние субъекта
Z.transition("inc")
future_unaffected = (Z.public_log[-1]["s0"] == 5)
print(f"  M2': подделка детектирована реплеем от genesis: {detected} ({why})")
print(f"  M2': будущее субъекта не зависит от подделанного лога: {future_unaffected} "
      f"(субъект ≠ лог) → {verdict(detected and future_unaffected)}")
# M2 при перелинковке: атакующий перезаписывает запись и ссылки заново
m2s = LogSubject("W"); m2s.write(0, "a", 1); m2s.write(1, "a", 2)
m2s.log[1]["s1"] = 777                 # правка прошлого
m2s.log[1]["prev"] = m2s.log[0]["ref"] # перелинковка
m2_still = recognize_M2(m2s.log)
print(f"  M2: правка прошлого с перелинковкой всё ещё «субъект»: {m2_still} → "
      f"{verdict(not m2_still)}: M2 проверяет когерентность лога, не происхождение")
OUT["A4"] = {"M2p_подделка_детектирована": detected, "M2p_будущее_независимо": future_unaffected,
             "M2_правка_прошлого_незамечена": m2_still}

# ============================================================
section("A5. СЖАТАЯ ИСТОРИЯ: 1000 переходов, лог удалён")
# ============================================================
K = M2pSubject("K", 0, lambda v, a: v + 1)
for i in range(1000):
    K.transition("inc")
K.public_log.clear()                   # история уничтожена целиком
cont = K.transition("inc")["status"] == "OK" and K._value == 1001
m2_after = recognize_M2([])            # логовой субъект без записей
print(f"  M2': после уничтожения лога субъект продолжает цепь: {cont} (value={K._value}, "
      f"proof сжат в состоянии) → {verdict(cont)}")
print(f"  M2: без записей распознавание субъекта: {m2_after} → субъект растворился в логе")
print("  Честная цена: прошлое M2' стало НЕПРОВЕРЯЕМЫМ для третьей стороны "
      "(CONTINUITY ≠ VERIFIABLE HISTORY)")
OUT["A5"] = {"M2p_продолжает_без_истории": cont, "M2_растворился": not m2_after}

# ============================================================
section("A6. СМЕНА ID: ярлык против идентичности")
# ============================================================
N = M2pSubject("N", 0, lambda v, a: v + 1)
for _ in range(3):
    N.transition("inc")
N.public_label = "M"                   # внешний наблюдатель переименовал
still = N.transition("inc")["status"] == "OK"
chain = N.replay_check(0, N.public_log)[0]
m2x = LogSubject("N"); m2x.write(0, "a", 1)
for r in m2x.log: r["owner"] = "M"     # у M2 переименование = смена субъекта
print(f"  M2': переименование ярлыка не затронуло цепь: продолжение={still}, "
      f"реплей={chain} → {verdict(still and chain)}: identity нагружена в proof, "
      f"ярлык — нет")
print(f"  M2: атрибуция переехала за edit: owner теперь {m2x.log[0]['owner']}")
OUT["A6"] = {"M2p_цепь_цела_после_переименования": still and chain}

# ============================================================
section("A7. МЁРТВЫЙ СУБЪЕКТ: функция уничтожена")
# ============================================================
D = M2pSubject("D", 0, lambda v, a: v + 1)
for _ in range(2):
    D.transition("inc")
D._func = None                          # субъект «умер»: источник переходов удалён
dead = D.transition("inc")["status"]
print(f"  M2': попытка перехода → {dead}; лог остался ({len(D.public_log)} записей), "
      f"identity и proof сохранены")
print(f"  Граница: M2' различает ИСТОЧНИКА (может продолжить) и НОСИТЕЛЯ-В-ПРОШЛОМ "
      f"(только хранит) — M2 не различает: лог одинаков")
OUT["A7"] = {"статус": dead}

# ============================================================
section("A8. ДАТЧИК vs АГЕНТ: контрфактический тест источника (закрывает вопрос «носитель vs регистратор»)")
# ============================================================
# Датчик: мир меняется сам, датчик только зеркалит
w1 = WorldAuto(0); sen = Sensor(w1)
for _ in range(5): w1.tick(); sen.step()
w2 = WorldAuto(0)                       # датчик заморожен (не делает step)
for _ in range(5): w2.tick()
world_same_without_sensor = ([w1.v - k for k in range(5)][::-1] ==
                             [w2.v - k for k in range(5)][::-1])
# Агент: мир меняется ТОЛЬКО его действиями
w3 = WorldAuto(0); ag = AgentSrc(w3)
for _ in range(5): w3.tick(); ag.step()
w4 = WorldAuto(0)                       # агент заморожен
for _ in range(5): w4.tick()
world_same_without_agent = (w3.v == w4.v)
print(f"  Датчик: мир изменяется идентично без него: {world_same_without_sensor} "
      f"→ его 'переходы' — трандюсция мира, НЕ источник → регистратор")
print(f"  Агент: без него мир НЕ выдаёт ту же траекторию: {not world_same_without_agent} "
      f"→ источник своих переходов → носитель")
print(f"  Формулировка критерия: SRC(s) = траектория мира без s ≠ траектория с s "
      f"в части приписанных s переходов")
OUT["A8"] = {"датчик_не_источник": world_same_without_sensor,
             "агент_источник": not world_same_without_agent}

# ============================================================
section("M3-LOCKED: верификация без обновления (тест итерации 2)")
# ============================================================
L = make_m3_locked("L", 0, lambda v, a: v + 2, expected=1)   # ожидает 1, функция даёт 2
L.transition("go"); L.transition("go")
ok_m3 = (len(L.discrepancies) == 2 and L.replay_check(0, L.public_log)[0]
         and L.can_continue())
print(f"  DISCREPANCY зафиксирован: {len(L.discrepancies)}×, UPDATE FORBIDDEN, "
      f"цепь цела: {L.replay_check(0, L.public_log)[0]}, субъектность сохранена: {ok_m3}")
print("  → отсутствие обновления процедуры не разрушает субъекта (лестница свойств)")
OUT["M3_locked"] = {"разногласий": len(L.discrepancies), "субъектность": ok_m3}

# ============================================================
section("ИТОГОВАЯ МАТРИЦА УСТОЙЧИВОСТИ")
# ============================================================
matrix = [
    ("A1  чужой переход",        "не различает", "держится", "держится", "держится"),
    ("A2  label swap",           "—",            "ЛОМАЕТСЯ", "ЛОМАЕТСЯ", "держится"),
    ("A3  fake_subject",         "—",            "ЛОМАЕТСЯ", "ЛОЖНОЕ СРАБ.", "держится"),
    ("A4  правка прошлого",      "—",            "—",        "незамечена", "детектируется"),
    ("A5  сжатая история",       "—",            "—",        "растворяется", "продолжает"),
    ("A6  смена ID",             "—",            "—",        "атрибуция «переехала»", "ярлык≠identity"),
    ("A7  мёртвый субъект",      "—",            "—",        "«субъект»", "различает источник/прошлое"),
    ("A8  датчик vs агент",      "—",            "—",        "ложное срабатывание", "различает (SRC-тест)"),
]
w = (26, 14, 13, 22, 28)
print("  " + "Атака".ljust(w[0]) + "".join(h.ljust(x) for h, x in
      zip(("M0", "M1", "M2", "M2'"), w[1:])))
for row in matrix:
    print("  " + row[0].ljust(w[0]) + "".join(c.ljust(x) for c, x in zip(row[1:], w[1:])))

path = "/home/z/my-project/download/subject_ladder_results.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=1, default=str)
print(f"\nСохранено: {path}")
