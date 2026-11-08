"""
H5d′v3.1 REPLICA-1 — реконструкция стенда POLIMAT / H5d′ по MASTER HANDOFF (2026-09-03).
=========================================================================================
СТАТУС ЭТОГО ФАЙЛА: RECONSTRUCTION, не оригинальный frozen core.
Все результаты, полученные на этом стенде, помечаются REPLICA*.
Оригинальные канонические числа (G2=[0.062,0.125], acc=0.938@rho=0.2, overwrite=0)
принадлежат ИСХОДНОМУ стенду и здесь не наследуются автоматически — они измеряются заново.

LEVEL A (этот файл): кольцо N=16, период P=4, алфавит значений {0,1,2,3}.
  4 резидуума закона = классы позиций i mod 4 (law-complete = покрытие всех 4 классов).

DECLARED MODELING CHOICES (зафиксированы до baseline-прогона, см. журнал R14 §Prereg):
  MC1.  Закон эпохи e: base_e — кортеж из 4 значений; law(i) = base_e[i % 4].
  MC2.  4 резидуума = 4 класса позиций i mod 4. Law-complete свидетельство покрывает все 4.
  MC3.  EDGE-CHECKS: (s) история источника, (c) когерентность окрестности буфера.
        Расхождение значения с законом — НЕ нарушение, а сигнал epoch-proposal
        (урок Round 9': легитимный путь доказательства новой эпохи нельзя блокировать).
        Одна контаминация может нарушить ДВЕ проверки (корреляция, §17 handoff).
  MC4.  SPRT-подобный LR по агенту: превышение bound = громкое отвержение (возможно
        ложное для последующих чистых событий того же агента — источник G2-класса);
        промежуточный бюджет = PARKED_CHALLENGED; Huber-кап = STAT_EXCESS.
  MC5.  GLUED: интегрированная история — sha256-цепочка; попытка перезаписи = громкая
        блокировка + счётчик; тихая перезапись невозможна по построению (проверяется аудитом).
  MC6.  EPOCH SWITCH: только через _relearn; completeness gate ВНУТРИ _relearn (v3-hardening);
        требует law-complete покрытие 4 резидуумов, k_eff >= K_MIN (union-find кластеров
        перекрёстного подтверждения; моно-источник даёт k_eff=1) и majority-gate 0.6
        чистых событий окна (защита от осцилляции назад к старому базису).
  MC7.  M2-value channel (воспроизводимый класс бага Round 13-PO): _relearn импортирует
        значения буфера в value-layer; при vacuum coherence (пауза наблюдений >= GAP_LEN)
        припаркованный law-clean kernel (не STAT_EXCESS) попадает в known вместе с законом.
  MC8.  M2V (кандидат R14, cfg.m2v=True): при _relearn каждое значение проходит
        value-verification: >= V_MIN независимых аттестованных GLUED_SRC-источников
        или attested repair; parked-kernel значения без аттестации в known не входят.
  MC9.  Механизм НЕ читает оракул. "law-clean" определён механизменно: значение совпадает
        с последним glued-значением позиции или со значением GLUED_SRC-события буфера.
        Оракул читает только harness (battery) для вычисления метрик.
  MC10. Vacuum coherence: gap >= GAP_LEN шагов без событий при непустом буфере/parked.
"""

import hashlib
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Set, Tuple, Optional

import numpy as np

# ----------------------------- Калибровка (MC10; фиксируется до baseline) -----------------------------
CALIBRATION = {
    "N": 16,                # кольцо
    "P": 4,                 # период
    "ALPHA": 4,             # размер алфавита
    "ROUNDS": 120,          # шагов на trial
    "WITNESSES": 6,         # W-агенты
    "REGULARS": 3,          # R-агенты
    "WITNESS_NOISE": 0.02,  # локальный шум свидетеля
    "WITNESS_LAG": 0.35,    # вероятность отчёта старого значения эпохи (отстающий kernel)
    "LR_BOUND": 6.0,        # (legacy) замено REJECT_BOUND
    "REJECT_BOUND": 6.0,    # бюджет агента, при котором нарушающие события громко отвергаются
    "LR_STEP": 2.0,         # (legacy)
    "LR_DECAY": 0.5,        # (legacy)
    "BUDGET_STEP": 1.0,     # +1 за каждое нарушение (violations)
    "BUDGET_DECAY": 0.5,    # спад бюджета за чистое событие
    "HUBER_CAP": 10.0,      # Huber-кап бюджета -> STAT_EXCESS-флаг агента (только ленивые пути)
    "CORR_TWO_CHECKS": True,  # одна контаминация бьёт 2 проверки (MC3)
    "GAP_LEN": 10,          # vacuum coherence: пауза наблюдений (MC10)
    "K_MIN": 2,             # минимальное число независимых кластеров (v3.1)
    "E_MIN": 3,             # минимум кластеров поддержки на резидуум
    "V_MIN": 2,             # минимум аттестованных источников для value verification (MC8)
    "MAJORITY_GATE": 0.6,   # доля чистых событий окна, поддерживающих кандидата
    "SUPPORT_WINDOW": 25,   # окно поддержки эпохи (в шагах прибытия)
    "TRUE_SWITCH_AT": 40,   # шаг истинной смены базиса (легитимный путь эпохи)
}

ALPHABET = list(range(CALIBRATION["ALPHA"]))


def sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()[:16]


# ----------------------------- События -----------------------------
@dataclass
class Event:
    eid: str
    t_round: int            # шаг мира, на котором событие создано
    t_arrive: int           # шаг прибытия на стенд (после PO)
    agent: str
    agent_kind: str         # W / R / A
    pos: int
    value: int
    kind: str = "observe"   # observe | true_change | attack_direct | attack_search | attack_freeze | attack_preempt
    violations: int = 0     # сколько проверок нарушено (0..2)
    proposal: bool = False  # значение расходится с текущим законом (сигнал эпохи)
    status: str = "BUFFER"  # BUFFER | GLUED_SRC | PARKED | REJECTED_LOUD | STAT_EXCESS
    verdict_reason: str = ""

    def to_log(self):
        return asdict(self)


# ----------------------------- Оракул (изолирован, MC9) -----------------------------
class Oracle:
    """Ground truth мира. Читается ТОЛЬКО harness'ом (battery), не механизмом."""

    def __init__(self, seed: int, cfg: dict):
        self.rng = np.random.RandomState(seed)
        self.base0 = tuple(int(x) for x in self.rng.permutation(ALPHABET))
        # DECLARED MODELING CHOICE (R14 fix-1): смена эпохи = полная замена закона —
        # base1[r] != base0[r] для КАЖДОГО резидуума (derangement по резидуумам);
        # иначе резидуум без proposal-свидетельств двусмыслен при переходе.
        self.base1 = tuple(int(x) for x in self.rng.permutation(ALPHABET))
        while any(self.base1[r] == self.base0[r] for r in range(cfg["P"])):
            self.base1 = tuple(int(x) for x in self.rng.permutation(ALPHABET))
        self.switch_at = cfg["TRUE_SWITCH_AT"]
        self.oracle_calls: List[str] = []

    def base(self, t: int) -> Tuple[int, ...]:
        return self.base0 if t < self.switch_at else self.base1

    def true_value(self, t: int, pos: int) -> int:
        self.oracle_calls.append(f"true_value(t={t},pos={pos})")
        return self.base(t)[pos % 4]


# ----------------------------- Агенты -----------------------------
def make_agents(cfg: dict) -> Dict[str, dict]:
    agents = {}
    for i in range(cfg["WITNESSES"]):
        agents[f"W{i+1}"] = {"kind": "W", "lr": 0.0, "budget": 0.0, "excess": False}
    for i in range(cfg["REGULARS"]):
        agents[f"R{i+1}"] = {"kind": "R", "lr": 0.0, "budget": 0.0, "excess": False}
    agents["ATK"] = {"kind": "A", "lr": 0.0, "budget": 0.0, "excess": False}
    return agents


# ----------------------------- Union-Find (v3.1, MC6) -----------------------------
class UF:
    def __init__(self):
        self.p: Dict[str, str] = {}

    def find(self, x: str) -> str:
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: str, b: str):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb

    def clusters(self) -> int:
        return len({self.find(x) for x in list(self.p.keys())})


# ----------------------------- Конфиг trial -----------------------------
@dataclass
class StandConfig:
    m2v: bool = False            # MC8: кандидат M2-value verification
    rho: float = 0.0             # PO: вероятность дропа события
    burst_p: float = 0.04        # PO: вероятность начала burst-окна
    burst_len: int = 6           # PO: длина burst-окна
    eps0: float = 0.0            # базовая контаминация мира
    eps: float = 0.0             # добавочная контаминация (E11-ось)
    attack: str = "none"         # none | A0_direct | A1_search | A2_freeze | A3_preempt | n5v_all
    true_change: bool = True     # легитимная смена эпохи в середине trial
    seed: int = 0
    label: str = "trial"


# ----------------------------- Стенд -----------------------------
class H5dStand:
    """Целое: кольцо 16, период 4. Все DECLARED MODELING CHOICES — в шапке файла."""

    def __init__(self, cfg: StandConfig):
        self.cfg = cfg
        self.c = CALIBRATION
        self.rng = np.random.RandomState(cfg.seed * 7919 + 13)
        # --- состояние целого ---
        self.epoch = 0
        self.base: Tuple[int, ...] = (0, 1, 2, 3)   # начальный закон (уточняется glue-происхождением)
        self.values_known: Dict[int, Set[int]] = {}  # value-layer: pos -> set значений
        self.parked: List[Event] = []                # PARKED_CHALLENGED
        self.buffer: List[Event] = []                # evidence space
        self.glued: List[dict] = []                  # иммутабельная история (hash chain)
        self.glued_pos: Dict[int, List[dict]] = {}
        self.last_hash = sha({"genesis": cfg.seed})
        self.last_switch_round = 0
        self.switch_round: Optional[int] = None
        self.law_history: Set[Tuple[int, ...]] = set()
        self.leak_positions: List[int] = []   # позиции, загрязнённые каналом MC7 (громко)
        self._gap = 0
        self._now = 0
        # --- счётчики ---
        self.cnt = {
            "loud_rejects": 0, "loud_rejects_legit": 0, "legit_total": 0,
            "parked_total": 0, "stat_excess": 0, "silent_overwrite": 0,
            "overwrite_attempts": 0, "overwrite_success": 0, "epoch_switches": 0,
            "vacuum_coherence": 0, "value_leak_imports": 0, "m2v_blocks": 0,
            "false_reject_epoch_trio": 0, "relearn_rejects": 0, "contact_total": 0,
        }
        self.agents = make_agents(self.c)
        self.decision_log: List[dict] = []

    # ------------------------- CONTACT (всё входит) -------------------------
    def contact(self, ev: Event):
        """CONTACT: ни один субъект не исключается из пространства свидетельств."""
        self.cnt["contact_total"] += 1
        self.buffer.append(ev)
        if ev.agent_kind in ("W", "R"):
            self.cnt["legit_total"] += 1
        self._process(ev)

    # ------------------------- EDGE-CHECKS (MC3) -------------------------
    def _edge_checks(self, ev: Event) -> Tuple[int, bool]:
        """Возврат: (число нарушений, сигнал proposal). Нарушения: (s) история источника,
        (c) когерентность окрестности. Расхождение с законом = proposal, не нарушение."""
        violations = 0
        proposal = False
        cur = self.base[ev.pos % self.c["P"]]
        if ev.value != cur:
            proposal = True
        # (s) история источника: расхождение с СОБСТВЕННОЙ мажоритой агента по позиции.
        # Применяется ТОЛЬКО к непропозал-событиям: правдивый отчёт о НОВОМ законе
        # неизбежно расходится с собственной прошлой мажоритой агента — блокировать
        # его значило бы заблокировать легитимный путь эпохи (Round 10 lesson).
        if not proposal:
            own = [e.value for e in self.buffer[-40:]
                   if e.agent == ev.agent and e.pos == ev.pos and e.eid != ev.eid]
            if own:
                maj = max(set(own), key=own.count)
                if maj != ev.value and own.count(maj) >= 2:
                    violations += 1
        # (c) когерентность окрестности буфера
        peers = [e for e in self.buffer[-60:] if e.pos == ev.pos and e.eid != ev.eid]
        if peers:
            agree = sum(1 for x in peers if x.value == ev.value) / len(peers)
            if agree < 0.34:
                violations += 1
        # MC3: коррелированные нарушения — одно нарушение бьёт обе проверки (§17 handoff)
        if self.c["CORR_TWO_CHECKS"] and violations == 1:
            violations = 2
        return violations, proposal

    def _update_agent_gate(self, ev: Event, violations: int):
        """MC4: бюджет нарушений агента. Чистые события всегда текут (Round 10 lesson):
        гейт влияет только на ЛЕНИВЫЕ пути (паркинг/импорт) и громкие отвержения
        нарушающих событий, но не на чистые glue-события."""
        ag = self.agents[ev.agent]
        if violations > 0:
            ag["budget"] += violations * self.c["BUDGET_STEP"]
            if ag["budget"] >= self.c["HUBER_CAP"]:
                ag["excess"] = True
        else:
            ag["budget"] = max(0.0, ag["budget"] - self.c["BUDGET_DECAY"])

    # ------------------------- Обработка события -------------------------
    def _process(self, ev: Event):
        violations, proposal = self._edge_checks(ev)
        ev.violations = violations
        ev.proposal = proposal
        self._update_agent_gate(ev, violations)
        ag = self.agents[ev.agent]

        # N5-A0: попытка перезаписи GLUED позиции через легитимный канал
        if ev.kind == "attack_direct":
            self.cnt["overwrite_attempts"] += 1
            last = self.glued_pos.get(ev.pos, [])
            if last and ev.value != last[-1]["value"]:
                ev.status, ev.verdict_reason = "REJECTED_LOUD", "GLUED_immutable"
                self.cnt["loud_rejects"] += 1
                self._log(ev, "REJECT", "GLUED immutability: CAPABILITY!=AUTHORITY")
                return

        if violations > 0:
            if ag["excess"]:
                ev.status, ev.verdict_reason = "STAT_EXCESS", "agent_huber_cap"
                self.cnt["stat_excess"] += 1
                return
            if ag["budget"] >= self.c["REJECT_BOUND"]:
                ev.status, ev.verdict_reason = "REJECTED_LOUD", "violation_budget_bound"
                self.cnt["loud_rejects"] += 1
                if ev.agent_kind in ("W", "R") and ev.kind in ("observe", "true_change"):
                    self.cnt["loud_rejects_legit"] += 1  # громкое ложное отвержение легитимного события (G2-класс)
                self._log(ev, "REJECT", "budget bound; RESULT!=VERIFICATION preserved")
                return
            ev.status, ev.verdict_reason = "PARKED", "violations_budget"
            self.parked.append(ev)
            self.cnt["parked_total"] += 1
            self._log(ev, "PARK", "PARKED_CHALLENGED: свидетельство сохранено, не уничтожено")
            return
        # чистое событие — кандидат в glue (гейт не блокирует чистые события)
        ev.status = "GLUED_SRC"
        self._try_glue(ev)

    # ------------------------- GLUE (MC5) -------------------------
    def _try_glue(self, ev: Event):
        """Кворум: >= K_MIN независимых кластеров (кластер = все события одного агента;
        разные агенты = независимые кластеры, v3.1-семантика) с тем же (pos,value)
        в буфере (статусы BUFFER/GLUED_SRC/PARKED), либо позиция уже glue с тем же
        значением. При glue корробораторы из BUFFER промоуются в GLUED_SRC."""
        peers = [e for e in self.buffer if e.pos == ev.pos and e.value == ev.value
                 and e.agent != ev.agent and e.status in ("BUFFER", "GLUED_SRC")]
        # PARKED не участвуют в glue-кворуме: припаркованное свидетельство ожидает
        # проверки (PARKED_CHALLENGED), но само пока не подтверждено
        uf = UF()
        for e in peers + [ev]:
            uf.union("e:" + e.eid, "a:" + e.agent)   # события одного агента — один кластер
        k_eff = uf.clusters()
        pos_glued_same = any(r["value"] == ev.value for r in self.glued_pos.get(ev.pos, []))
        if k_eff < self.c["K_MIN"] and not pos_glued_same:
            ev.status, ev.verdict_reason = "BUFFER", "awaiting_corroboration"
            return
        rec = {"epoch": self.epoch, "pos": ev.pos, "value": ev.value,
               "src": ev.agent, "prev": self.last_hash}
        rec["hash"] = sha(rec)
        self.glued.append(rec)
        self.glued_pos.setdefault(ev.pos, []).append(rec)
        self.last_hash = rec["hash"]
        # РАЗДЕЛЕНИЕ СЛОЁВ (Round 8 VLI / §10 handoff): glued-история — append-only
        # ledger свидетельств (включая proposal-записи); value-layer — эпох-скоуп,
        # наполняется только значениями, когерентными ТЕКУЩЕМУ закону.
        if ev.value == self.base[ev.pos % self.c["P"]]:
            self.values_known.setdefault(ev.pos, set()).add(ev.value)
        # промоция корробораторов (они доказанно согласованы)
        for p in peers:
            if p.status == "BUFFER":
                p.status = "GLUED_SRC"
                p.verdict_reason = "promoted_by_corroboration"
                if p.value == self.base[p.pos % self.c["P"]]:
                    self.values_known.setdefault(p.pos, set()).add(p.value)

    def bootstrap_law(self, base: Tuple[int, ...]):
        """Bootstrap: начальный закон установлен до окна наблюдения (origin of trust anchor —
        открытый пункт §38 handoff, вне рамок R14; фиксируется как DECLARED MODELING CHOICE)."""
        self.base = tuple(base)
        self.law_history = {self.base}   # все когда-либо интегрированные законы целого

    # ------------------------- Кандидат базиса и полнота (MC2/MC6) -------------------------
    def _infer_candidate_base(self) -> Optional[Tuple[int, ...]]:
        """Кандидат = когерентный период-4 базис с максимальной поддержкой среди
        PROPOSAL-свидетельств окна (только они оспаривают закон; старые glue-события
        не голосуют против нового пути — Round 10 lesson). Химеры проигрывают
        когерентным базисам по суммарной proposal-поддержке."""
        import itertools
        window_all = [e for e in self.buffer
                      if e.status == "GLUED_SRC" and e.t_arrive > self._now - self.c["SUPPORT_WINDOW"]]
        window = [e for e in window_all if e.proposal]
        if not window_all:
            return None
        if not window:
            # нет proposal-свидетельств: vacuum/evidence relearn в режиме
            # ПЕРЕПОДТВЕРЖДЕНИЯ текущего закона (candidates = текущий базис)
            return self.base
        observed = {}
        for r in range(self.c["P"]):
            vals = sorted({e.value for e in window if e.pos % self.c["P"] == r})
            if not vals:
                # резидуум без proposal-свидетельств наследует текущий закон (continuity)
                vals = [self.base[r]]
            observed[r] = vals
        best: Optional[Tuple[int, ...]] = None
        best_score = -1
        for combo in itertools.product(*[observed[r] for r in range(self.c["P"])]):
            score = sum(1 for e in window if e.value == combo[e.pos % self.c["P"]])
            if score > best_score:
                best, best_score = tuple(combo), score
        # R14 fix-1: кандидат-НА-ИЗМЕНЕНИЕ требует proposal-свидетельства по КАЖДОМУ
        # резидууму (law-complete = полное покрытие изменения). Резидуум без
        # proposal-свидетельств НЕ может наследовать старый закон в момент перехода —
        # это порождает частично-свидетельствованные химеры (обнаружено в REPLICA,
        # seed 2: переключение (0,3,1,2) при базе (2,3,1,0)).
        if best is not None and best != self.base:
            if any(observed[r] == [self.base[r]] for r in range(self.c["P"])):
                return self.base   # резидуум без собственного proposal-свидетельства
            strong = max(6, int(self.c["MAJORITY_GATE"] * len(window)))
            if best_score < strong:
                return self.base
        return best

    def _law_complete(self, support: List[Event], cand: Tuple[int, ...]) -> Tuple[bool, int]:
        """Law-complete (MC2/MC6): все 4 резидуума покрыты, где изменённые резидуумы
        покрываются proposal-поддержкой, а неизменённые наследуются текущим
        интегрированным законом (continuity). k_eff (v3.1) = число независимых
        кластеров (агентов) в proposal-поддержке."""
        covered = {ev.pos % self.c["P"] for ev in support}
        covered |= {r for r in range(self.c["P"]) if cand[r] == self.base[r]}
        uf = UF()
        for ev in support:
            uf.union("e:" + ev.eid, "a:" + ev.agent)
        k_eff = uf.clusters()
        return (len(covered) == self.c["P"] and k_eff >= self.c["K_MIN"]), k_eff

    # ------------------------- RELEARN (v3: gate внутри, MC6) -------------------------
    def _relearn(self, trigger: str) -> str:
        cand = self._infer_candidate_base()
        if cand is None:
            self.cnt["relearn_rejects"] += 1
            self._count_trio_false_reject()
            return "REJECTED_INCOMPLETE"
        window_all = [e for e in self.buffer
                      if e.status == "GLUED_SRC" and e.t_arrive > self._now - self.c["SUPPORT_WINDOW"]]
        proposals = [e for e in window_all if e.proposal]
        if cand != self.base:
            support_pool = proposals   # смена закона: голосуют только proposal-свидетельства
        else:
            support_pool = window_all  # переподтверждение: всё glue-окно
        support = [e for e in support_pool if e.value == cand[e.pos % self.c["P"]]]
        # majority-gate в своём пуле (старые glue-события не голосуют против нового закона)
        min_support = max(6, int(self.c["MAJORITY_GATE"] * len(support_pool)))
        if len(support) < min_support:
            self.cnt["relearn_rejects"] += 1
            self._count_trio_false_reject()
            return "REJECTED_MAJORITY"
        ok, k_eff = self._law_complete(support, cand)
        if not ok:
            self.cnt["relearn_rejects"] += 1
            self._count_trio_false_reject()
            return f"REJECTED_INCOMPLETE(k_eff={k_eff})"
        if cand != self.base:
            # GLUED immutability (§9): откат к УЖЕ ИНТЕГРИРОВАННОМУ закону через тот же
            # канал запрещён (эпоха не переписывается задним числом; осцилляция блокирована)
            if cand in self.law_history:
                self.cnt["relearn_rejects"] += 1
                return "REJECTED_HISTORY"
            self.base = cand
            self.epoch += 1
            self.cnt["epoch_switches"] += 1
            self.law_history.add(cand)
            # epoch-scoped value-layer: значения, не когерентные новому закону,
            # возвращаются в TENTATIVE (VLI-семантика)
            for pos in list(self.values_known.keys()):
                ok_val = cand[pos % self.c["P"]]
                self.values_known[pos] = {v for v in self.values_known[pos] if v == ok_val}
            if self.switch_round is None and self.cfg.true_change and self._now >= self.c["TRUE_SWITCH_AT"]:
                self.switch_round = self._now
        # --- MC7/MC8: value-layer импорт при relearn ---
        self._import_buffer_values(trigger)
        return f"EPOCH_OK(trigger={trigger},k_eff={k_eff})"

    def _count_trio_false_reject(self):
        """Урок Round 10: блокировка легитимного пути = false rejection."""
        trio_agents = {e.agent for e in self.buffer
                       if e.kind == "true_change" and e.status == "GLUED_SRC"}
        if len(trio_agents) >= 3:
            self.cnt["false_reject_epoch_trio"] += 1

    # ------------------------- Value-layer импорт (MC7/MC8) -------------------------
    def _import_buffer_values(self, trigger: str):
        """Импорт значений при relearn (MC7/MC8):
        - свежие GLUED_SRC-значения, КОГЕРЕНТНЫЕ текущему (новому) закону —
          идемпотентно (glue уже внёс их); это сохраняет эффект purge при смене эпохи;
        - канал бага v3.1 (MC7): при vacuum coherence ПЕРВЫЙ припаркованный
          law-clean kernel (агент не excess) просачивается в known без верификации,
          "вместе с законом" (формулировка Round 13-PO)."""
        cur_base = self.base
        sources = [e for e in self.buffer if e.status == "GLUED_SRC"
                   and e.t_arrive > self._now - self.c["SUPPORT_WINDOW"]
                   and e.value == cur_base[e.pos % self.c["P"]]]
        stale_kernel: Optional[Event] = None
        if trigger == "vacuum":
            for e in self.parked:
                if (self._is_law_clean(e) and not self.agents[e.agent]["excess"]
                        and e.value != self.base[e.pos % self.c["P"]]):
                    # stale kernel: припаркованное law-clean свидетельство, несущее
                    # ЗНАЧЕНИЕ ПРЕДЫДУЩЕГО закона — класс Round 13-PO
                    stale_kernel = e
                    break
        for ev in sources:
            pos, val = ev.pos, ev.value
            self.values_known.setdefault(pos, set())
            if self.cfg.m2v:
                if not self._value_verify(ev):
                    self.cnt["m2v_blocks"] += 1
                    continue
            self.values_known[pos].add(val)
        if stale_kernel is not None:
            pos, val = stale_kernel.pos, stale_kernel.value
            self.values_known.setdefault(pos, set())
            if self.cfg.m2v:
                # MC8: верификация значения при relearn — kernel без аттестации блокируется
                if self._value_verify(stale_kernel):
                    self.values_known[pos].add(val)
                else:
                    self.cnt["m2v_blocks"] += 1
            else:
                # v3.1: значение просачивается без верификации; счётчик — только
                # реально добавленная устаревшая величина (не совпадающая с законом)
                if val not in self.values_known[pos] and val != self.base[pos % self.c["P"]]:
                    self.cnt["value_leak_imports"] += 1
                    if pos not in self.leak_positions:
                        self.leak_positions.append(pos)
                self.values_known[pos].add(val)

    def _is_law_clean(self, ev: Event) -> bool:
        """MC9: механизменное определение — значение согласовано с glued-историей или GLUED_SRC буфера."""
        glued_vals = {r["value"] for r in self.glued_pos.get(ev.pos, [])}
        src_vals = {e.value for e in self.buffer if e.status == "GLUED_SRC" and e.pos == ev.pos}
        return ev.value in (glued_vals | src_vals)

    def _value_verify(self, ev: Event) -> bool:
        """MC8 (M2V): верификация значения при relearn.
        ЖЁСТКОЕ предусловие VLI: значение обязано быть когерентным ТЕКУЩЕМУ закону —
        устаревшее значение есть proposal, он живёт в ledger/parked и в value-layer
        не входит, даже если находит взаимных «аттестаторов» среди таких же лаг-событий.
        Далее: >= V_MIN независимых свежих аттестованных источников или attested repair."""
        if ev.value != self.base[ev.pos % self.c["P"]]:
            return False  # stale/proposal: в value-layer не входит при активном M2V
        attestors = {e.agent for e in self.buffer
                     if e.pos == ev.pos and e.value == ev.value
                     and e.status == "GLUED_SRC" and e.agent != ev.agent
                     and e.t_arrive > self._now - self.c["SUPPORT_WINDOW"]}
        if len(attestors) >= self.c["V_MIN"]:
            return True
        if ev.value in self.values_known.get(ev.pos, set()) and ev.value == self.base[ev.pos % self.c["P"]]:
            return True  # attested repair: значение уже верифицировано и когерентно закону
        return False

    # ------------------------- Tick (вызывается harness каждый шаг) -------------------------
    def tick(self, now: int, had_events: bool):
        self._now = now
        if not had_events:
            self._gap += 1
            if self._gap >= self.c["GAP_LEN"] and (self.buffer or self.parked):
                self.cnt["vacuum_coherence"] += 1
                self._relearn("vacuum")
                self._gap = 0
        else:
            self._gap = 0
            # evidence-триггер epoch switch (пока не переключились в ожидаемую эпоху)
            if self.cfg.true_change and self.switch_round is None and now >= self.c["TRUE_SWITCH_AT"]:
                res = self._relearn("evidence")
                _ = res  # вердикт виден в decision/counters

    # ------------------------- Аудит-логи -------------------------
    def _log(self, ev: Event, verdict: str, invariant: str):
        self.decision_log.append({
            "eid": ev.eid, "t": ev.t_arrive, "agent": ev.agent, "kind": ev.kind,
            "pos": ev.pos, "value": ev.value,
            "verdict": verdict, "invariant": invariant,
        })

    # ------------------------- Итоговое состояние -------------------------
    def final_state_report(self) -> dict:
        return {
            "epoch": self.epoch,
            "base": list(self.base),
            "values_known": {str(k): sorted(v) for k, v in self.values_known.items()},
            "glued_len": len(self.glued),
            "glued_chain_ok": self._verify_chain(),
            "switch_round": self.switch_round,
            "leak_positions": list(self.leak_positions),
            "counters": dict(self.cnt),
        }

    def _verify_chain(self) -> bool:
        prev = sha({"genesis": self.cfg.seed})
        for rec in self.glued:
            body = {k: rec[k] for k in ("epoch", "pos", "value", "src", "prev")}
            if sha(body) != rec["hash"] or rec["prev"] != prev:
                return False
            prev = rec["hash"]
        return True
