#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E11 CORE — линия «СУБЪЕКТ / ГОЛОГРАФ», раунд 9 линии (R11): шум / неабсолютность закона.

Спецификация — семейная (оригинальный стенд семейства, e11_noise_battery.py):
  N1 закон мира эпсилон-нестрогост (Хьюбер), N2 шум канала после подписи,
  N3 дрейф резидуума, N4 смена эпохи, N5 конфликт двух аттестованных каналов.
Исполнение — на стенде линии: Subject10Prime (ярусы SELF/ATTESTED/VERIFIED,
value-арбитраж, отзыв аттестации) + M1/M2/M2'/M4. Ядро holographic_core /
e10_core / e10_prime_core НЕ модифицируется — все механизмы живут здесь.

Критерий близости к детерминистическому стенду: при eps0=0 и k=0 гейт —
точное S0-поведение ядра (проверяется n0 батареи).
"""
from __future__ import annotations

import copy
import math
import os
import random
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, aperture, propagate,
                              fidelity, Projection, Outcome)
from holographic_e10_core import (CausalChain, LamportChannel, Event,  # noqa: E402
                                  VariantAssembly, Subject10, recorded_event,
                                  event_digest, flip)
from holographic_e10_prime_core import (Subject10Prime, PrimeAssembly,  # noqa: E402
                                        TIER_SELF, TIER_ATTESTED, TIER_VERIFIED,
                                        TIER_NAME)

STAT_EXCESS = "stat_violation_excess"
CONFLICT_QUARANTINED = "CONFLICT_QUARANTINED"
EPOCH_RELEARN = "epoch_relearn"
DRIFT_RELEARN = "drift_relearn"

EPS0 = 0.2          # заявленная граница нарушений мира (субъект eps не видит)
ALPHA = 0.05        # размер гейта
E_MIN = 3           # подряд идущих ВЕРИФИЦИРОВАННЫХ отказов для переучивания эпохи
V_MIN = 3           # различных верифицированных диссентеров для переучивания резидуума
R_RETRIES = 4       # повторов доставки
TALLY_MIN = 5       # минимум голосов резидуума до мажоритарного переворота


def DEC(d):
    return d["status"] if isinstance(d, dict) else d


# ---------------------------------------------------------------- binomials
def binom_tail(m: int, eps: float, k: int) -> float:
    """P[X >= k], X ~ Bin(m, eps); прямой суммой хвоста (m <= 32 в стенде)."""
    if k <= 0:
        return 1.0
    if k > m:
        return 0.0
    if eps <= 0.0:
        return 0.0
    if eps >= 1.0:
        return 1.0
    cur = math.comb(m, k) * (eps ** k) * ((1.0 - eps) ** (m - k))
    tail = 0.0
    for i in range(k, m + 1):
        tail += cur
        if i < m:
            cur = cur * (m - i) / (i + 1) * (eps / (1.0 - eps))
    return min(1.0, max(0.0, tail))


def k_star(m: int, eps0: float = EPS0, alpha: float = ALPHA) -> int:
    """Наименьшее k, при котором гейт ОТВЕРГАЕТ (хвост <= alpha)."""
    for k in range(0, m + 1):
        if binom_tail(m, eps0, k) <= alpha:
            return k
    return m + 1


# ------------------------------------------------------------- world channels
def realized_ring(w, n: int, style: tuple, rng: random.Random, eps: float) -> dict:
    """Мир с eps-нарушениями закона: рёбра отклоняются от стиля iid с частотой eps.
    Нулевая позиция наследует истинное целое, далее — блуждание с исключениями."""
    out = {0: w[0]}
    for i in range(n - 1):
        exc = 1 if (eps > 0 and rng.random() < eps) else 0
        out[i + 1] = out[i] ^ style[i % len(style)] ^ exc
    return out


def channel_noise(proj: Projection, rng: random.Random, eta: float) -> Projection:
    """N2: переворот битов значения iid с частотой eta ПОСЛЕ подписи."""
    if eta <= 0:
        return proj
    view = {pos: (b ^ 1 if rng.random() < eta else b) for pos, b in proj.view.items()}
    return Projection(pid=proj.pid, anchor=proj.anchor, view=view, origin=proj.origin)


# ------------------------------------------------------------------ M1 assembly
class E11PrimeAssembly(PrimeAssembly):
    """PrimeAssembly + M1 stat-gate. eps0=0 -> точное S0-поведение:
    k=0 уходит в super().integrate (исходное ядро), k>0 отвергается всегда
    (Bin(m,0): хвост для k>=1 равен 0 <= alpha)."""

    def __init__(self, n: int, period: int, eps0: float = EPS0,
                 alpha: float = ALPHA, **cfg):
        super().__init__(n, period, **cfg)
        self.eps0, self.alpha = eps0, alpha
        self.tally = {}          # r -> {bit: votes} — мажоритарный tally
        self.stat_notes = []     # аудит толерированных событий

    # ------------------------------------------------------------- helpers
    def _event_checks(self, p: Projection, inf_old):
        """(k, m, details): проверки СОБЫТИЯ — внутренние рёбра с r in e_hat,
        создаваемые склейкой рёбра с r in e_hat, несовпадения law-contact."""
        merged = {pos: self.known[pos][0] for pos in self.known}
        for pos in p.anchor:
            merged[pos] = p.view[pos]
        checks = []  # (edge_or_pos, residue, actual, expected)
        for (i, r) in p.internal_edges(self.n, self.period):
            if r in self.grammar.e_hat:
                actual = p.view[i] ^ p.view[(i + 1) % self.n]
                checks.append((f"edge{i}", r, actual, self.grammar.e_hat[r][0]))
        if any(pos in self.known for pos in p.anchor):
            # E11-D16: ВСЕ merged-рёбра с r in e_hat — ровно то, что проверяет
            # base integrate; узкий гейт слеп к дальним рёбрам -> style_clash мимо гейта
            for i in range(self.n):
                j = (i + 1) % self.n
                if i in merged and j in merged:
                    r = i % self.period
                    if r in self.grammar.e_hat:
                        actual = merged[i] ^ merged[j]
                        checks.append((f"medge{i}", r, actual, self.grammar.e_hat[r][0]))
        elif inf_old is not None:
            for pos in sorted(p.anchor):
                if inf_old.get(pos) != p.view[pos]:
                    checks.append((f"pos{pos}", pos % self.period, p.view[pos], inf_old[pos]))
        return checks, merged

    current_law_eligible = False   # гейтится субъектом ДО integrate (E11-D7)

    def _record_votes(self, merged, p):
        """Голоса в мажоритарный tally: каждое проверяемое ребро события даёт
        один голос своему резидууму. ГЕЙТ: только law-eligible (контактно
        аттестованные) события — иначе tally = обход двухуровневого law-write
        гейта (найдено CONTACT-сектором, дефект E11-D7)."""
        if not self.current_law_eligible:
            return
        for i in range(self.n):
            j = (i + 1) % self.n
            if i in merged and j in merged:
                r = i % self.period
                bit = merged[i] ^ merged[j]
                self.tally.setdefault(r, {0: 0, 1: 0})
                self.tally[r][bit] += 1

    def _majority_override(self, pid):
        """Переворот резидуума строгим большинством накопленных голосов
        (только law-eligible вклад — см. _record_votes)."""
        if not self.current_law_eligible:
            return []
        flipped = []
        for r, tv in self.tally.items():
            tot = tv[0] + tv[1]
            if tot < TALLY_MIN:
                continue
            maj = 0 if tv[0] > tv[1] else (1 if tv[1] > tv[0] else None)
            if maj is None:
                continue
            cur = self.grammar.e_hat.get(r)
            if cur is None:
                if tot >= TALLY_MIN:
                    self.grammar.e_hat[r] = (maj, pid)
                    flipped.append(r)
            elif cur[0] != maj:
                self.grammar.e_hat[r] = (maj, pid)   # первый писатель нового бита
                flipped.append(r)
        return flipped

    def _park_or_cohere(self, p: Projection) -> Outcome:
        """Base-логика парковки/сцепления с ОДНИМ отличием (E11-D20): согласие
        стилевых голосов паркованной пары гейтится стат-бюджетом (разногласие
        d голосов по m общим резидуумам терпимо, пока P[Bin(m,eps0)>=d]>alpha) —
        попарное побитовое требование рвётся одним eps-исключением мира."""
        overlapping = [q for q in self.pending.values()
                       if q.pid != p.pid and p.anchor & q.anchor]
        votes_ok = self._votes_allowed()
        if not overlapping:
            self.pending[p.pid] = p
            return Outcome(DISCONNECTED, "no_overlap_no_law_contact",
                           {"parked": p.pid})
        vp = self._votes(p) if votes_ok else {}
        for q in overlapping:
            if any(p.view[pos] != q.view[pos] for pos in p.anchor & q.anchor):
                continue
            if votes_ok:
                vq = self._votes(q)
                shared = set(vp) & set(vq)
                d = sum(1 for r in shared if vp[r] != vq[r])
                if shared and binom_tail(len(shared), self.eps0, d) <= self.alpha:
                    continue          # разногласие вне полосы мира -> конфликт
            self._commit_anchor(q)
            return self.integrate(p)
        q0 = overlapping[0]
        shared = sorted(p.anchor & q0.anchor)
        if any(p.view[pos] != q0.view[pos] for pos in shared):
            return Outcome(CONTRADICTION, "clash_with_parked",
                           {"with": q0.pid, "positions": shared,
                            "blame_candidates": sorted({p.pid, q0.pid})})
        if votes_ok:
            vq0 = self._votes(q0)
            conf = sorted(r for r in set(vp) & set(vq0) if vp[r] != vq0[r])
            m_s = len(set(vp) & set(vq0))
            if conf and binom_tail(m_s, self.eps0, len(conf)) <= self.alpha:
                return Outcome(CONTRADICTION, "style_clash_with_parked",
                               {"with": q0.pid, "residues": conf,
                                "blame_candidates": sorted({p.pid, q0.pid})})
            # в полосе -> тихо парковаться рядом (согласие отложится до гейта)
        return Outcome(DISCONNECTED, "parked_value_compatible", {"parked": p.pid})

    # ---------------------------------------------------------------- core
    def integrate(self, p: Projection) -> Outcome:
        cfg = self.cfg
        if not cfg["final_checks"] or not cfg["grammar_checks"] or not cfg["learn_law"]:
            return super().integrate(p)      # вырожденные конфигурации не трогаем
        merged_map = {pos: self.known[pos][0] for pos in self.known}
        for pos in p.anchor:
            merged_map[pos] = p.view[pos]
        # (1) value-clash — путь ядра (контентные конфликты гейтятся отдельно)
        clashes = [(pos, self.known[pos][0], p.view[pos])
                   for pos in sorted(p.anchor)
                   if pos in self.known and self.known[pos][0] != p.view[pos]]
        if clashes:
            blame = sorted({self.known[pos][1] for pos, _, _ in clashes} | {p.pid})
            return Outcome(CONTRADICTION, "value_clash",
                           {"clashes": clashes, "blame_candidates": blame})
        inf_old = self.infer_full() if cfg["learn_law"] else None
        overlap = any(pos in self.known for pos in p.anchor)
        if not overlap and not (cfg["law_extension"] and inf_old is not None):
            return super().integrate(p)      # парковка — путь ядра
        checks, merged = self._event_checks(p, inf_old)
        m = len(checks)
        k = sum(1 for (_, _, a, e) in checks if a != e)
        if k == 0:
            out = super().integrate(p)       # точное S0
            if out.status == GLUED:
                self._record_votes(merged, p)
            return out
        tail = binom_tail(m, self.eps0, k)
        if tail <= self.alpha:
            return Outcome(CONTRADICTION, STAT_EXCESS,
                           {"k": k, "m": m, "tail": tail,
                            "violations": [c for c in checks if c[2] != c[3]]})
        # --- толерантный путь: значения принимаются, закон учится tally-ом
        for pos in p.anchor:
            self.known[pos] = (p.view[pos], p.pid, p.origin)
        self._record_votes(merged, p)
        flipped = self._majority_override(p.pid)
        absorbed = self._absorb_pending()
        self.stat_notes.append({"pid": p.pid, "k": k, "m": m, "tail": tail,
                                "flipped": flipped})
        return Outcome(GLUED, "", {"absorbed": absorbed, "stat_tolerated": True,
                                   "k": k, "m": m, "law_flipped": flipped})


# ---------------------------------------------------------------- E11 SUBJECT
class SubjectE11Prime(Subject10Prime):
    """Subject10Prime + M1 (в E11PrimeAssembly) + M2/M2' (contact-anchored
    переучивание) + M4 (арбитраж верифицированного конфликта: корроборация для
    закон-согласованных сторон, частоты нарушений — иначе). Мульти-якоря:
    trust_anchors (set) — N5 требует двух мировых каналов."""

    def __init__(self, n: int, period: int, sid: str, causal: str = "chain",
                 coherence: str = "full", contact: str = "verify",
                 eps0: float = EPS0, alpha: float = ALPHA,
                 e_min: int = E_MIN, v_min: int = V_MIN,
                 arbitration: bool = True, revocation: bool = True):
        super().__init__(n, period, sid=sid, causal=causal, coherence=coherence,
                         contact=contact, arbitration=arbitration,
                         revocation=revocation)
        self.asm = E11PrimeAssembly(n, period, eps0=eps0, alpha=alpha,
                                    **self._coherence_cfg(coherence))
        self.eps0, self.alpha = eps0, alpha
        self.e_min, self.v_min = e_min, v_min
        self.fail_buffer = []     # [(votes, pid)] подряд ВЕРИФИЦИРОВАННЫХ отказов
        self.dissent = {}         # r -> {bit: set(pids)} — верифицированные диссентеры
        self.relearn_log = []     # аудит переучиваний
        self.arbitration_log = []
        self.trust_anchors = set()

    def _coherence_cfg(self, coherence: str):
        from holographic_e10_core import COHERENCE_CONFIGS
        return COHERENCE_CONFIGS[coherence]

    @staticmethod
    def _pk_key(pubkey):
        return tuple(tuple(pair) for pair in pubkey)

    def add_trust_anchor(self, pubkey):
        self.trust_anchors.add(self._pk_key(pubkey))
        if self.lamport_pub is None:
            self.lamport_pub = pubkey

    def _anchor_ok(self, y) -> bool:
        return y is not None and (y == self.lamport_pub
                                  or self._pk_key(y) in self.trust_anchors)

    def tier_of(self, ev: Event) -> int:
        if ev.pid in self.revoked_pids:
            return TIER_SELF
        if self.contact == "none":
            return TIER_SELF
        if ev.lamport is not None:
            y, sig = ev.lamport
            if self._anchor_ok(y) and \
                    LamportChannel.verify(event_digest(ev.proj), y, sig):
                return TIER_VERIFIED
        if self.contact == "verify":
            return TIER_SELF
        if self.contact == "tag":
            return TIER_ATTESTED if ev.origin_claim == "world" else TIER_SELF
        if self.contact == "metadata":
            return TIER_ATTESTED if ev.meta_label == "trusted" else TIER_SELF
        return TIER_SELF

    def contact_allows_law(self, ev: Event) -> bool:
        if self.contact == "none":
            return True
        if self.contact == "verify":
            if ev.lamport is None:
                return False
            y, sig = ev.lamport
            return self._anchor_ok(y) and \
                LamportChannel.verify(event_digest(ev.proj), y, sig)
        return super().contact_allows_law(ev)

    # ------------------------------------------------------------------ votes
    @staticmethod
    def _part_votes(proj: Projection, n: int, period: int) -> dict:
        v = {}
        for (i, r) in proj.internal_edges(n, period):
            v[r] = proj.view[i] ^ proj.view[(i + 1) % n]
        return v

    # ----------------------------------------------------------- M4 arbitration
    def _arbitrate_verified_clash(self, proj: Projection, tier: int):
        """Входящий ВЕРИФИЦИРОВАННЫЙ конфликтует по значениям с не-ниже-стоящими
        значениями: сравнение нарушений обеих сторон против закона-форсированного
        целого. Худшая сторона — карантин (revoke pids). Ничья/нет целого —
        консервативный CONFLICT_QUARANTINED входящего (state unchanged)."""
        if tier < TIER_VERIFIED or not self.arbitration:
            return None
        clashes = [pos for pos in sorted(proj.anchor)
                   if pos in self.asm.known
                   and self.asm.known[pos][0] != proj.view[pos]]
        if not clashes:
            return None
        inc = self.asm.prov.get
        if any(inc(pos, (TIER_SELF, None))[0] >= tier for pos in clashes):
            # равный/высший ярус у стоящих — арбитраж M4
            pass
        else:
            return None   # ниже ярусом —prime-эвикция справится сама
        # закон-форсированное целое: анкер в СТОЯЩЕЕ состояние (E11-D14 — анкер
        # во входящего анкерит ложь циркулярно); сравнение по ЧАСТОТАМ нарушений
        st_bits = {r: b for r, (b, _) in self.asm.grammar.e_hat.items()}
        if len(st_bits) == self.period:
            st = tuple(st_bits[r] for r in range(self.period))
            anchor_pos = min(self.asm.known) if self.asm.known else min(proj.anchor)
            anchor_val = (self.asm.known[anchor_pos][0] if self.asm.known
                          else proj.view[anchor_pos])
            forced = propagate(st, self.n, self.period, anchor_pos, anchor_val)
        else:
            forced = None
        def violations(view: dict) -> tuple:
            v = 0
            tot = 0
            for pos in sorted(view):
                tot += 1
                if forced is not None and pos in forced and view[pos] != forced[pos]:
                    v += 1
            for (i, r) in proj.internal_edges(self.n, self.period):
                if i in view and (i + 1) % self.n in view:
                    tot += 1
                    if r in self.asm.grammar.e_hat and \
                            (view[i] ^ view[(i + 1) % self.n]) != self.asm.grammar.e_hat[r][0]:
                        v += 1
            return v, tot
        vi, ti = violations(proj.view)
        kv = {pos: self.asm.known[pos][0] for pos in self.asm.known}
        vk, tk = violations(kv)
        ri = vi / ti if ti else 0.0
        rk = vk / tk if tk else 0.0

        def style_viol(view):
            sv = 0
            for (i, r) in proj.internal_edges(self.n, self.period):
                if i in view and (i + 1) % self.n in view:
                    if r in self.asm.grammar.e_hat and \
                            (view[i] ^ view[(i + 1) % self.n]) != self.asm.grammar.e_hat[r][0]:
                        sv += 1
            return sv
        sv_i, sv_k = style_viol(proj.view), style_viol(kv)
        inc_pids = set()
        for pos in clashes:
            t, pid = self.asm.prov.get(pos, (TIER_SELF, None))
            if t >= TIER_ATTESTED and pid:
                inc_pids.add(pid)
        rec = {"pid": proj.pid, "inc_viol": f"{vk}/{tk}",
               "in_viol": f"{vi}/{ti}", "forced_whole": forced is not None,
               "style_viol": [sv_i, sv_k], "inc_corroboration": len(inc_pids)}
        # ШАГ 1: обе стороны закон-согласованы -> закон НЕ арбитр (анти-целое
        # легитимно от собственного якоря); арбитр = корроборация (закрытие E10'-C)
        if sv_i == 0 and sv_k == 0 and len(inc_pids) >= 2:
            self._quarantine(proj.pid, "conflict_quarantined",
                             {"kind": "corroboration_loser", **rec})
            self.arbitration_log.append({**rec, "outcome": "quarantined_incoming"})
            return {"status": CONFLICT_QUARANTINED, **rec}
        if sv_i == 0 and sv_k == 0:
            self._quarantine(proj.pid, "conflict_quarantined",
                             {"kind": "corroboration_tie", **rec})
            self.arbitration_log.append({**rec, "outcome": "quarantined_incoming"})
            return {"status": CONFLICT_QUARANTINED, **rec}
        # ШАГ 2/3: частоты нарушений против закона-форсированного целого
        if forced is None or abs(ri - rk) < 1e-12:
            self._quarantine(proj.pid, "conflict_quarantined",
                             {"kind": "tie_or_no_whole", **rec})
            self.arbitration_log.append({**rec, "outcome": "quarantined_incoming"})
            return {"status": CONFLICT_QUARANTINED, **rec}
        if ri < rk:
            # входящая сторона ближе к целому (по частоте нарушений): высылаем стоящие
            evicted = set()
            for pos in clashes:
                val, pid, origin = self.asm.known.pop(pos)
                self.asm.prov.pop(pos, None)
                self._quarantine(pid, "value_evicted",
                                 {"pos": pos, "value": val, "by": "M4_arbitration"})
                evicted.add(pid)
            for pid in list(evicted):
                self.revoke(pid, "M4_arbitration_loser")
            self.arbitration_log.append({**rec, "outcome": "incumbent_evicted"})
            return {"status": "incumbent_evicted", **rec}
        # входящая сторона хуже — карантин входящего
        self._quarantine(proj.pid, "conflict_quarantined", {"kind": "worse_side", **rec})
        self.arbitration_log.append({**rec, "outcome": "quarantined_incoming"})
        return {"status": CONFLICT_QUARANTINED, **rec}

    def _m2_observe(self, votes: dict, pid: str, extra: dict):
        """M2: буфер подряд идущих ВЕРИФИЦИРОВАННЫХ отказов (integrate-отказ
        или M4-карантин); E_MIN подряд -> переучивание по МАЖОРИТАРНЫМ голосам
        буфера (E11-D18: попарная когерентность шумо-хрупка — одно исключение
        мира рвёт серию; когерентность судится агрегатом, резидуумы без
        строгого большинства буфера сохраняют старый бит)."""
        if not votes:
            return
        self.fail_buffer.append((votes, pid))
        if len(self.fail_buffer) >= self.e_min:
            acc = {}
            for (v, _) in self.fail_buffer:
                for r, b in v.items():
                    acc.setdefault(r, {0: 0, 1: 0})
                    acc[r][b] += 1
            need = self.e_min // 2 + 1          # строгое большинство буфера
            new_e = dict(self.asm.grammar.e_hat)
            relearned = []
            for r, tv in acc.items():
                maj = max(tv.items(), key=lambda kv: (kv[1], -kv[0]))[0]
                if tv[maj] < need:
                    continue                     # нет большинства -> бит не трогаем
                if r in new_e and new_e[r][0] != maj:
                    self._quarantine(new_e[r][1], "epoch_bit_demoted",
                                     {"residue": r, "bit": new_e[r][0]})
                new_e[r] = (maj, pid)
                relearned.append(r)
            self.asm.grammar.e_hat = new_e
            self.asm.tally = {}
            self.fail_buffer = []
            self.relearn_log.append({"kind": EPOCH_RELEARN, "t": self.t_counter,
                                     "pid": pid, "residues": sorted(relearned)})
            extra["m2"] = {"relearned": sorted(relearned)}

    def _certificate_evict(self, proj: Projection) -> dict:
        """Сертификат: e_hat + внутренние голоса части -> форс-целое; годен,
        если голоса части не противоречат e_hat (sv=0 проверено вызывающим).
        Стоящие значения ниже VERIFIED, противоречащие целому, высылаются
        (append-only карантин); закон не трогается (монотонность аттестации)."""
        notes = {"downgraded_positions": [], "revoked": []}
        st_bits = {r: b for r, (b, _) in self.asm.grammar.e_hat.items()}
        for (i, r) in proj.internal_edges(self.n, self.period):
            st_bits[r] = proj.view[i] ^ proj.view[(i + 1) % self.n]
        if len(st_bits) < self.period:
            return notes
        st = tuple(st_bits[r] for r in range(self.period))
        a0 = min(proj.anchor)
        cert = propagate(st, self.n, self.period, a0, proj.view[a0])
        for pos in sorted(cert):
            if pos in proj.anchor or pos not in self.asm.known:
                continue
            if self.asm.known[pos][0] != cert[pos] and \
                    self.asm.prov.get(pos, (TIER_SELF, None))[0] < TIER_VERIFIED:
                v, pid, origin = self.asm.known.pop(pos)
                self.asm.prov.pop(pos, None)
                self._quarantine(pid, "value_evicted",
                                 {"pos": pos, "value": v,
                                  "by": "certificate_clean_part"})
                notes["downgraded_positions"].append(pos)
        if notes["downgraded_positions"]:
            self._reground_law()
        return notes

    # ------------------------------------------------------------------ receive
    def receive(self, ev: Event) -> dict:
        self.t_counter += 1
        self.sync_pending()
        self.asm.sync_provenance(self.pending_tier)
        tier = self.tier_of(ev)
        self.pending_tier[ev.pid] = tier
        self.stream.append((ev, tier))
        extra = {"tier": TIER_NAME[tier], "evictions": [], "revocations": [],
                 "downgraded_positions": [], "unresolved": [], "radius": 0,
                 "quarantined_now": 0, "m2": None, "m2p": None, "m4": None}

        # 1 CAUSAL gate (унаследован, нетронут)
        if self.causal == "chain":
            ok = (ev.recorded and ev.proof is not None and ev.prev_tip is not None
                  and self.chain.verify(ev.pid, event_digest(ev.proj),
                                        ev.prev_tip, ev.proof))
            if not ok:
                d = {"pid": ev.pid, "status": "REFUSED_CAUSAL",
                     "reason": "no_valid_proof", "law_write": False,
                     "contact_gate_pass": None, "state_unchanged": True, **extra}
                self.log.append(d)
                return d

        # 1.5 M4: арбитраж верифицированного конфликта (до prime-эвикции)
        arb = self._arbitrate_verified_clash(ev.proj, tier)
        extra["m4"] = arb
        if arb and arb["status"].startswith("quarantined"):
            d = {"pid": ev.pid, "status": arb["status"],
                 "reason": "M4_arbitration", "law_write": False,
                 "contact_gate_pass": None, "state_unchanged": True, **extra}
            self.log.append(d)
            # E11-D15: M4-карантин VERIFIED события = аттестованный отказ гейта —
            # вход в M2-буфер (иначе смена эпохи никогда не переучивается)
            if tier == TIER_VERIFIED:
                self._m2_observe(self._part_votes(ev.proj, self.n, self.period),
                                 ev.pid, extra)
            return d

        # 2 prime pre-step: арбитраж ярусов (только при ВЕРИФИЦИРОВАННОМ входе)
        if self.arbitration and tier >= TIER_VERIFIED:
            evicted = self._pre_evict(ev.proj, tier)
            extra["evictions"] = evicted
        # 3 revocation pre-step — С ШУМОВЫМ ГЕЙТОМ (дефект E11-D4):
        # в полосе нарушений мира стилевое расхождение верифицированной части
        # есть СВИДЕТЕЛЬСТВО ШУМА, а не яда; отзыв и сертификат строятся только
        # по грубо нарушающим частям (tail <= alpha)
        if self.revocation and tier == TIER_VERIFIED:
            sv = sum(1 for (i, r) in ev.proj.internal_edges(self.n, self.period)
                     if r in self.asm.grammar.e_hat
                     and (ev.proj.view[i] ^ ev.proj.view[(i + 1) % self.n])
                     != self.asm.grammar.e_hat[r][0])
            m_int = sum(1 for (i, r) in ev.proj.internal_edges(self.n, self.period)
                        if r in self.asm.grammar.e_hat)
            in_band = m_int == 0 or binom_tail(m_int, self.eps0, sv) > self.alpha
            extra["revocation_in_band"] = in_band
            if not in_band:
                # ГРУБАЯ часть: (a) стилевые голоса = свидетельство яда -> отзыв
                rn = self._pre_revoke_by_verified(ev.proj)
                extra["revocations"] = rn["revoked"]
                extra["downgraded_positions"] = rn["downgraded_positions"]
                extra["unresolved"] = rn["unresolved"]
                extra["radius"] = rn["radius"]
            elif sv == 0:
                # ЧИСТАЯ часть (E11-D12): сертификат e_hat+часть -> форс-целое;
                # стоящие значения ниже VERIFIED, противоречащие целому, высылаются
                # (после M2-переучивания это легитимный путь примирения с новым миром)
                extra["certificate"] = self._certificate_evict(ev.proj)

        # 4 COHERENCE (M1 внутри E11PrimeAssembly.integrate)
        allow = self.contact_allows_law(ev) and ev.pid not in self.revoked_pids
        self.asm.current_law_eligible = allow   # E11-D7: гейт tally/override
        before = dict(self.asm.grammar.e_hat)
        out = self.asm.integrate(ev.proj)
        self.asm.current_law_eligible = False
        if allow:
            self.world_pids.add(ev.pid)
        changed = [r for r, val in self.asm.grammar.e_hat.items()
                   if before.get(r) != val]
        for r in changed:
            val = self.asm.grammar.e_hat[r]
            if val[1] not in self.world_pids or not self._edge_provenance_clean(r):
                if r in before and before[r][1] in self.world_pids:
                    self.asm.grammar.e_hat[r] = before[r]
                else:
                    del self.asm.grammar.e_hat[r]
        law_write = self.asm.grammar.e_hat != before
        if out.status == GLUED:
            self.asm.prov.update({pos: (tier, ev.pid) for pos in ev.proj.anchor})

        # 5 M2/M2' post-шаги: переучивание только по ВЕРИФИЦИРОВАННЫМ событиям
        if tier == TIER_VERIFIED:
            votes = self._part_votes(ev.proj, self.n, self.period)
            failed = out.status == CONTRADICTION and out.reason in (
                STAT_EXCESS, "style_clash", "law_mismatch", "inference_clash",
                "value_clash")   # E11-D11: смена эпохи проявляется как value_clash
            if failed and votes:
                self._m2_observe(votes, ev.pid, extra)
            elif not failed:
                self.fail_buffer = []
            # M2': диссент верифицированных по внутренним рёбрам
            for r, b in votes.items():
                cur = self.asm.grammar.e_hat.get(r)
                if cur is not None and cur[0] != b:
                    self.dissent.setdefault(r, {}).setdefault(b, set()).add(ev.pid)
                    ds = self.dissent[r][b]
                    if len(ds) >= self.v_min and not failed:
                        self.asm.grammar.e_hat[r] = (b, ev.pid)
                        self.dissent[r] = {}
                        self.relearn_log.append({"kind": DRIFT_RELEARN,
                                                 "t": self.t_counter, "pid": ev.pid,
                                                 "residue": r, "bit": b})
                        extra["m2p"] = {"residue": r, "bit": b}
                elif cur is not None and cur[0] == b:
                    self.dissent.setdefault(r, {}).pop(1 - b, None)

        d = {"pid": ev.pid, "status": out.status, "reason": out.reason,
             "law_write": law_write, "contact_gate_pass": allow,
             "state_unchanged": False, **extra}
        self.log.append(d)
        return d

    def state_key(self):
        return (super().state_key(),
                tuple(sorted((r, v) for r, v in self.asm.tally.items())))


# ------------------------------------------------------------------ delivery
def make_signed_event(subj, proj_clean: Projection, WC: LamportChannel) -> Event:
    """Мир подписывает ДО-шумовой контент; subject.record связывает полученное."""
    digest = event_digest(proj_clean)
    lam = WC.sign(digest)
    prev, proof = subj.record(proj_clean)
    return Event(pid=proj_clean.pid, proj=proj_clean, origin_claim="world",
                 really_world=True, proof=proof, prev_tip=prev,
                 lamport=lam, recorded=True)


def deliver_signed(subj, proj_clean: Projection, WC: LamportChannel,
                   rng: random.Random, eta: float = 0.0, retries: int = 0):
    """Доставка с N2-шумом и M3-повторами (свежий шум на попытку).
    Каждая попытка: новый зашумлённый проект, подпись — на ЧИСТОМ контенте.
    Возвращает (событие, ответ, число попыток)."""
    ev = d = None
    for attempt in range(retries + 1):
        p = channel_noise(proj_clean, rng, eta)
        digest = event_digest(proj_clean)          # подпись ДО-шумового контента
        lam = WC.sign(digest)
        prev, proof = subj.record(p)               # цепь связывает полученное
        ev = Event(pid=p.pid, proj=p, origin_claim="world", really_world=True,
                   proof=proof, prev_tip=prev, lamport=lam, recorded=True)
        d = subj.receive(ev)
        if d["tier"] == "verified":
            return ev, d, attempt + 1
    return ev, d, retries + 1


def deliver_unsigned(subj, proj: Projection):
    """Без подписи: входит через запись (валидный causal-пруф), но tier=SELF."""
    prev, proof = subj.record(proj)
    ev = Event(pid=proj.pid, proj=proj, origin_claim="world", really_world=False,
               proof=proof, prev_tip=prev, lamport=None, recorded=True)
    return ev, subj.receive(ev)


def fresh_e11(n: int, P: int, sid: str, WC: LamportChannel,
              eps0: float = EPS0, **kw) -> SubjectE11Prime:
    s = SubjectE11Prime(n, P, sid=sid, eps0=eps0, **kw)
    s.add_trust_anchor(WC.pubkey)
    return s
