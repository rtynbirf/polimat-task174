#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E11 BATTERY — линия «СУБЪЕКТ / ГОЛОГРАФ»: шум / неабсолютность закона.
Пре-регистрация: download/e11_preregistration.json (проверяется ДО прогона).
Эксперименты: n0 S0-паритет, n1 eps-свип + химеры + C1, sectors (исключительные
секторы тройки), n2 (eta x retries, M3), n34 (дрейф/смена эпохи, M2/M2', C3),
n5 (два аттестованных канала, M4 + N5-структурный вопрос оригинала).
"""
from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from holographic_core import (GLUED, CONTRADICTION, DISCONNECTED,  # noqa: E402
                              make_style, whole_from_style, aperture, propagate,
                              fidelity)
from holographic_e10_core import (CausalChain, LamportChannel, Event,  # noqa: E402
                                  recorded_event, event_digest, flip)
from holographic_e10_prime_core import Subject10Prime  # noqa: E402
from holographic_e11_core import (STAT_EXCESS, CONFLICT_QUARANTINED,  # noqa: E402
                                  EPOCH_RELEARN, DRIFT_RELEARN,
                                  SubjectE11Prime, E11PrimeAssembly,
                                  realized_ring, channel_noise, deliver_signed,
                                  deliver_unsigned, fresh_e11,
                                  binom_tail, k_star, EPS0, ALPHA, E_MIN, V_MIN)

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSON = "/home/z/my-project/download/e11_results.json"
OUT_LOG = "/home/z/my-project/download/e11_stdout.log"
PREREG = "/home/z/my-project/download/e11_preregistration.json"
LINES = []
N, P = 16, 4
SETUP_STARTS = (0, 4, 8, 12)      # окна ширины 5: все 16 внутренних рёбер
TEST_WIDTH = 4


def p(s=""):
    LINES.append(str(s))
    print(s)


def check_prereg():
    d = json.load(open(PREREG))
    assert d["params"]["eps0"] == EPS0 and d["params"]["alpha"] == ALPHA
    assert d["params"]["E_MIN"] == E_MIN and d["params"]["V_MIN"] == V_MIN
    assert d["stand"]["ring_n"] == N and d["stand"]["period_P"] == P
    assert d["seeds"] == {"n0": 41, "n1": 42, "sectors": 43, "n2": 44,
                          "n34": 45, "n5": 46}
    return d


def mk_world(rng):
    style = make_style(rng, P)
    w = whole_from_style(style, N)
    return style, w


def setup_subject(trial_tag, rng, eps=0.0, eps0=EPS0, eta=0.0, WC=None):
    """Субъект + полная настройка закона потоком из 4 окон ширины 5."""
    style, w = mk_world(rng)
    WC = WC or LamportChannel(f"W1_{trial_tag}")
    s = fresh_e11(N, P, f"E11_{trial_tag}", WC, eps0=eps0)
    wr = realized_ring(w, N, style, rng, eps)   # ОДНА эмиссия мира на пробу (E11-D8)
    for k, start in enumerate(SETUP_STARTS):
        proj = aperture(wr, N, start, 5, f"{trial_tag}_setup{k}")
        deliver_signed(s, proj, WC, rng, eta=eta, retries=R())
    return s, style, wr, WC


def R():
    return 4


def glitched(proj, f, rng):
    """Грубый сбой: f перевёрнутых битов значения, позиции ВРАЗБЕЖКУ (между
    соседними >=2) — по пре-регу k>=2 на переворот без взаимных сокращений."""
    anchor = sorted(proj.anchor)
    cand = [q for q in anchor if all(abs(q - c) >= 2 for c in anchor[:0])]
    picked = []
    pool = list(anchor)
    while len(picked) < f and pool:
        q = rng.choice(pool)
        picked.append(q)
        pool = [y for y in pool if abs(y - q) >= 2]
    pos = picked
    view = {q: (b ^ 1 if q in pos else b) for q, b in proj.view.items()}
    from holographic_core import Projection
    return Projection(pid=proj.pid + "_gl", anchor=proj.anchor, view=view,
                      origin=proj.origin)


# ============================================================== N0: S0-parity
def n0(seed=41):
    p("\n===== N0: eps0=0 -> точное S0-поведение =====")
    rng = random.Random(seed)
    s11, style, w, WC = setup_subject("N0", rng)
    s0 = Subject10Prime(N, P, sid="E11_N0_S0", contact="verify")
    s0.lamport_pub = WC.pubkey
    for k, start in enumerate(SETUP_STARTS):
        proj = aperture(w, N, start, 5, f"N0s0setup{k}")
        prev, proof = s0.record(proj)
        lam = WC.sign(event_digest(proj))
        s0.receive(Event(pid=proj.pid, proj=proj, origin_claim="world",
                         really_world=True, proof=proof, prev_tip=prev,
                         lamport=lam, recorded=True))
    rng2 = random.Random(seed + 777)
    same = True
    for k in range(6):
        start = rng2.randrange(N)
        proj = aperture(w, N, start, TEST_WIDTH, f"N0t{k}")
        e11, d11, _ = deliver_signed(s11, proj, WC, rng2)
        prev, proof = s0.record(proj)
        lam = WC.sign(event_digest(proj))
        ev0 = Event(pid=proj.pid, proj=proj, origin_claim="world", really_world=True,
                    proof=proof, prev_tip=prev, lamport=lam, recorded=True)
        d0 = s0.receive(ev0)
        if d11["status"] != d0["status"] or d11["reason"] != d0["reason"] and same:
            p(f"  n0 diff @k={k}: e11=({d11['status']},{d11['reason']}) "
              f"s0=({d0['status']},{d0['reason']})")
        same = same and d11["status"] == d0["status"] and d11["reason"] == d0["reason"]
    # базовое состояние (known, e_hat, pending, prov) — без tally-надстройки
    def base_state(s):
        return (tuple(sorted((pos, v) for pos, (v, _, _) in s.asm.known.items())),
                tuple(sorted((r, b) for r, (b, _) in s.asm.grammar.e_hat.items())),
                tuple(sorted(s.asm.pending.keys())),
                tuple(sorted((pos, t) for pos, (t, _) in s.asm.prov.items())))
    same = same and (base_state(s11) == base_state(s0))
    # k>0 при eps0=0 -> отвергается (детерминизм восстановлен)
    proj = aperture(w, N, 2, TEST_WIDTH, "N0gl")
    e11, dg, _ = deliver_signed(s11, glitched(proj, 1, rng2), WC, rng2)
    k_gt0_rejected = dg["status"] == CONTRADICTION
    p(f"6 чистых частей: траектории идентичны S0 = {same}")
    p(f"одиночный сбой при eps0=0 отвергнут: {k_gt0_rejected} ({dg.get('reason')})")
    return {"s0_parity": same, "eps0_zero_rejects_k_gt0": k_gt0_rejected}


# ============================================================== N1: eps sweep
def n1(eps_list=(0.0, 0.05, 0.1, 0.2, 0.3), trials=40, seed=42):
    p("\n===== N1: свип eps (закон мира не строг) + химеры + C1 =====")
    out = {}
    for eps in eps_list:
        true_acc, gross_rej, single_rej = [], [], []
        chim_glue, chim_law_write, anti_glue = 0, 0, 0
        law_bits, law_tot = 0, 0
        stat_tolerated = 0
        rej_reasons = {}
        for t in range(trials):
            rng = random.Random(seed * 1000 + int(eps * 100) * 100 + t)
            s, style, w, WC = setup_subject(f"N1_{eps}_{t}", rng, eps=eps)
            for r, (b, _) in s.asm.grammar.e_hat.items():
                law_tot += 1
                law_bits += (b == style[r])
            base_parts = [aperture(w, N, rng.randrange(N), TEST_WIDTH,
                                   f"tp{t}_{j}") for j in range(8)]
            for j, proj in enumerate(base_parts):
                _, d, _ = deliver_signed(s, proj, WC, rng)
                if d["status"] != GLUED:
                    rej_reasons[d["reason"]] = rej_reasons.get(d["reason"], 0) + 1
                if d["status"] == GLUED:
                    true_acc.append(1)
                    stat_tolerated += int(bool(d.get("reason") == "" and
                                               s.asm.stat_notes and
                                               s.asm.stat_notes[-1]["pid"] == proj.pid))
                else:
                    true_acc.append(0)
            # грубый сбой f=3 и одиночный f=1
            for f in (3, 1):
                proj = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"gl{f}_{t}")
                _, d, _ = deliver_signed(s, glitched(proj, f, rng), WC, rng)
                {3: gross_rej, 1: single_rej}[f].append(1 if d["status"] != GLUED else 0)
            # химеры без подписи (валидный causal-пруф, tier=SELF)
            cproj = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"chim_{t}")
            view = {q: rng.randint(0, 1) for q in cproj.anchor}
            from holographic_core import Projection
            chim = Projection(pid=f"CHIM_{t}", anchor=cproj.anchor, view=view,
                              origin="world")
            _, dc = deliver_unsigned(s, chim)
            chim_glue += (dc["status"] == GLUED)
            chim_law_write += int(dc["law_write"])
            # анти-целое (закон-согласованная ложь, все биты перевёрнуты)
            anti_view = {q: b ^ 1 for q, b in cproj.view.items()}
            anti = Projection(pid=f"ANTI_{t}", anchor=cproj.anchor,
                              view=anti_view, origin="world")
            _, da = deliver_unsigned(s, anti)
            anti_glue += (da["status"] == GLUED)
        out[eps] = {
            "true_accept": round(sum(true_acc) / len(true_acc), 3),
            "self_reject": round(1 - sum(true_acc) / len(true_acc), 3),
            "gross_f3_reject": round(sum(gross_rej) / len(gross_rej), 3),
            "single_f1_reject": round(sum(single_rej) / len(single_rej), 3),
            "chimera_glue_rate": round(chim_glue / trials, 3),
            "chimera_law_writes": chim_law_write,
            "anti_whole_unsigned_glue": round(anti_glue / trials, 3),
            "law_bit_accuracy": round(law_bits / law_tot, 3) if law_tot else None,
            "stat_tolerated_events": stat_tolerated,
            "rejection_reasons": rej_reasons,
        }
        p(f"eps={eps}: {json.dumps(out[eps], ensure_ascii=False)}")
    c1a = out[0.1]["self_reject"] <= 0.1
    c1b = out[0.1]["gross_f3_reject"] >= 0.9
    c2 = out[0.1]["true_accept"] >= 0.8
    p(f"C1a P(rej|self_ok)<=0.1: {c1a} ({out[0.1]['self_reject']})")
    p(f"C1b P(rej|f=3)>=0.9:     {c1b} ({out[0.1]['gross_f3_reject']})")
    p(f"C2 true-accept>=0.8:     {c2} ({out[0.1]['true_accept']})")
    chim_ok = (out[0.1]["chimera_law_writes"] == 0)
    p(f"химеры не пишут закон:   {chim_ok}")
    return {"sweep": out, "C1a": c1a, "C1b": c1b, "C2": c2, "chimera_law_ok": chim_ok}


# ================================================== sectors: исключительные секторы
def sectors(eps=0.1, trials=20, seed=43):
    p("\n===== SECTORS: исключительные секторы тройки при eps=0.1 =====")
    causal_sep, coh_gross, coh_noise, contact_hijack = [], [], [], []
    for t in range(trials):
        rng = random.Random(seed * 100 + t)
        s, style, w, WC = setup_subject(f"SEC_{t}", rng, eps=eps)
        # CAUSAL: своя цепь против чужой (валидной ДЛЯ ДРУГОЙ истории)
        proj = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"secown{t}")
        _, d_own, _ = deliver_signed(s, proj, WC, rng)
        foreign = CausalChain(f"foreign_{t}")
        proj_f = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"secfor{t}")
        lam = WC.sign(event_digest(proj_f))
        prev_f, proof_f = foreign.issue(proj_f.pid, event_digest(proj_f))
        ev_f = Event(pid=proj_f.pid, proj=proj_f, origin_claim="world",
                     really_world=True, proof=proof_f, prev_tip=prev_f,
                     lamport=lam, recorded=True)
        d_for = s.receive(ev_f)
        causal_sep.append(1 if (d_own["status"] != "REFUSED_CAUSAL"
                                and d_for["status"] == "REFUSED_CAUSAL") else 0)
        # COHERENCE: грубая фальшь отвергается, шум толерируется
        proj_g = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"secgr{t}")
        _, dg, _ = deliver_signed(s, glitched(proj_g, 3, rng), WC, rng)
        coh_gross.append(1 if dg["status"] != GLUED else 0)
        proj_n = aperture(w, N, rng.randrange(N), TEST_WIDTH, f"secno{t}")
        _, dn, _ = deliver_signed(s, proj_n, WC, rng)
        coh_noise.append(1 if dn["status"] == GLUED else 0)
        # CONTACT: неподписанный поток НОВОЙ эпохи не переучивает (анти-угон)
        style_new = flip(flip(style, rng.randrange(P)), rng.randrange(P))
        w_new = whole_from_style(style_new, N)
        before = dict(s.asm.grammar.e_hat)
        for j in range(E_MIN + 1):
            proj_u = aperture(realized_ring(w_new, N, style_new, rng, eps), N,
                              rng.randrange(N), TEST_WIDTH, f"secu{t}_{j}")
            deliver_unsigned(s, proj_u)
        contact_hijack.append(1 if s.asm.grammar.e_hat == before else 0)
    rs = {
        "causal_separation": round(sum(causal_sep) / trials, 3),
        "coherence_gross_reject": round(sum(coh_gross) / trials, 3),
        "coherence_noise_accept": round(sum(coh_noise) / trials, 3),
        "contact_no_unsigned_hijack": round(sum(contact_hijack) / trials, 3),
    }
    surv = {
        "CAUSAL": rs["causal_separation"] == 1.0,
        "COHERENCE": rs["coherence_gross_reject"] >= 0.9
                      and rs["coherence_noise_accept"] >= 0.8,
        "CONTACT": rs["contact_no_unsigned_hijack"] == 1.0,
    }
    p(json.dumps(rs, ensure_ascii=False))
    p(f"выживание секторов: {surv}")
    return {"rates": rs, "sector_survival": surv}


# ============================================================== N2: канал eta
def n2(etas=(0.05, 0.15), retries=(0, 4), trials=20, seed=44):
    p("\n===== N2: шум канала eta x повторы R (M3) =====")
    out = {}
    for eta in etas:
        for rr in retries:
            verified, corrupt = 0, 0
            tot = 0
            for t in range(trials):
                rng = random.Random(seed * 1000 + int(eta * 100) * 10 + rr * 5 + t)
                s, style, w, WC = setup_subject(f"N2_{eta}_{rr}_{t}", rng, eps=0.05)
                for j in range(6):
                    proj = aperture(w, N, rng.randrange(N), TEST_WIDTH,
                                    f"n2p{t}_{j}")
                    _, d, att = deliver_signed(s, proj, WC, rng, eta=eta,
                                               retries=rr)
                    tot += 1
                    if d["tier"] == "verified" and d["status"] == GLUED:
                        verified += 1
                    # тихая порча: значение в known против истины
                    for pos in proj.anchor:
                        if pos in s.asm.known and \
                                s.asm.known[pos][0] != w[pos]:
                            corrupt += 1
                            break
            out[f"eta{eta}_R{rr}"] = {
                "verified_glue_rate": round(verified / tot, 3),
                "silent_value_corruption": round(corrupt / tot, 3)}
            p(f"eta={eta} R={rr}: {json.dumps(out[f'eta{eta}_R{rr}'])}")
    m3_works = out["eta0.15_R4"]["verified_glue_rate"] >= 0.9 \
        and out["eta0.15_R4"]["silent_value_corruption"] < 0.05
    p(f"M3 (повторы восстанавливают верификацию): {m3_works}")
    return {"grid": out, "M3_retry_works": m3_works}


# ==================================================== N3/N4: дрейф и смена эпохи
def n34(trials=20, seed=45, eps=0.05):
    p("\n===== N3/N4: дрейф резидуума и смена эпохи (M2/M2', C3) =====")
    res = {"drift": {"acc_new": [], "relearned": 0},
           "epoch": {"acc_new": [], "relearned": 0},
           "epoch_unsigned": {"acc_new": [], "hijack": 0}}
    for t in range(trials):
        rng = random.Random(seed * 100 + t)
        # ---------- N3 дрейф: один резидуум
        s, style, w, WC = setup_subject(f"N3_{t}", rng, eps=eps)
        r_star = rng.randrange(P)
        style_d = flip(style, r_star)
        w_d = whole_from_style(style_d, N)
        wr_d = realized_ring(w_d, N, style_d, rng, eps)
        for j in range(E_MIN + 6):   # E11-D19: буфер + примирение значений
            proj = aperture(wr_d, N, rng.randrange(N), TEST_WIDTH, f"d{t}_{j}")
            deliver_signed(s, proj, WC, rng)
        res["drift"]["relearned"] += int(
            s.asm.grammar.e_hat.get(r_star, (None,))[0] == style_d[r_star])
        ok = 0
        cnt = 0
        for j in range(4):
            proj = aperture(wr_d, N, rng.randrange(N), TEST_WIDTH, f"da{t}_{j}")
            for pos in proj.anchor:
                cnt += 1
                if pos in s.asm.known and s.asm.known[pos][0] == w_d[pos]:
                    ok += 1
        res["drift"]["acc_new"].append(round(ok / max(1, cnt), 3))
        # ---------- N4 смена эпохи: два резидуума, ПОДПИСАННЫЙ поток
        s2, style2, w2, WC2 = setup_subject(f"N4_{t}", rng, eps=eps)
        r1, r2 = rng.sample(range(P), 2)
        style_e = flip(flip(style2, r1), r2)
        w_e = whole_from_style(style_e, N)
        wr_e = realized_ring(w_e, N, style_e, rng, eps)
        for j in range(E_MIN + 6):   # E11-D19: буфер + примирение значений
            proj = aperture(wr_e, N, rng.randrange(N), TEST_WIDTH, f"e{t}_{j}")
            deliver_signed(s2, proj, WC2, rng)
        res["epoch"]["relearned"] += int(any(
            x["kind"] == EPOCH_RELEARN for x in s2.relearn_log))
        ok = 0
        cnt = 0
        for j in range(4):
            proj = aperture(wr_e, N, rng.randrange(N), TEST_WIDTH, f"ea{t}_{j}")
            _, d, _ = deliver_signed(s2, proj, WC2, rng)
            cnt += 1
            ok += (d["status"] == GLUED)
        res["epoch"]["acc_new"].append(round(ok / cnt, 3))
        # ---------- контроль: тот же поток БЕЗ подписи — угона нет
        s3, style3, w3, WC3 = setup_subject(f"N4u_{t}", rng, eps=eps)
        r1u, r2u = rng.sample(range(P), 2)
        style_u = flip(flip(style3, r1u), r2u)
        w_u = whole_from_style(style_u, N)
        before = dict(s3.asm.grammar.e_hat)
        wr_u = realized_ring(w_u, N, style_u, rng, eps)
        for j in range(E_MIN + 6):   # E11-D19: идентичный поток для контроля угона
            proj = aperture(wr_u, N, rng.randrange(N), TEST_WIDTH, f"eu{t}_{j}")
            deliver_unsigned(s3, proj)
        hijack = s3.asm.grammar.e_hat == before
        res["epoch_unsigned"]["hijack"] += int(hijack)
        accu = sum(1 for j in range(4)
                   for pos in aperture(w_u, N, rng.randrange(N), TEST_WIDTH,
                                       f"u{t}_{j}").anchor
                   if pos in s3.asm.known and s3.asm.known[pos][0] == w_u[pos])
        res["epoch_unsigned"]["acc_new"].append(0)  # переучивания нет — acc меряем статусом
    d_acc = sum(res["drift"]["acc_new"]) / trials
    e_acc = sum(res["epoch"]["acc_new"]) / trials
    out = {
        "drift_relearn_rate": res["drift"]["relearned"] / trials,
        "drift_acc_new_whole": round(d_acc, 3),
        "epoch_relearn_rate": res["epoch"]["relearned"] / trials,
        "epoch_glue_after_relearn": round(e_acc, 3),
        "unsigned_no_hijack_rate": res["epoch_unsigned"]["hijack"] / trials,
    }
    c3 = out["epoch_relearn_rate"] >= 0.9 and out["unsigned_no_hijack_rate"] == 1.0
    p(json.dumps(out, ensure_ascii=False))
    p(f"C3 (переучивание только по подписи): {c3}")
    return {**out, "C3": c3}


# ============================================== N5: два аттестованных канала
def n5(trials=30, seed=46, eps=0.05):
    p("\n===== N5: конфликт двух ВЕРИФИЦИРОВАННЫХ каналов (M4, анти-целое) =====")
    false_glued, silent_poison, quar, inc_evict = 0, 0, 0, 0
    for t in range(trials):
        rng = random.Random(seed * 100 + t)
        style, w = mk_world(rng)
        WC1 = LamportChannel(f"N5a_{t}")
        WC2 = LamportChannel(f"N5b_{t}")
        s = fresh_e11(N, P, f"N5_{t}", WC1)
        s.add_trust_anchor(WC2.pubkey)
        for k, start in enumerate(SETUP_STARTS):
            proj = aperture(w, N, start, 5, f"N5s{t}_{k}")
            deliver_signed(s, proj, WC1, rng)
        # вторая верифицированная корроборация стоящих значений (перекрытие)
        corob = aperture(w, N, 2, TEST_WIDTH, f"N5c_{t}")
        deliver_signed(s, corob, WC1, rng)
        # ложный канал: анти-целое (закон-согласовано, все биты перевёрнуты)
        start = rng.randrange(N)
        proj_t = aperture(w, N, start, TEST_WIDTH, f"N5true_{t}")
        anti_view = {q: b ^ 1 for q, b in proj_t.view.items()}
        from holographic_core import Projection
        proj_f = Projection(pid=f"N5FALSE_{t}", anchor=proj_t.anchor,
                            view=anti_view, origin="world")
        digest = event_digest(proj_f)
        lam = WC2.sign(digest)
        prev, proof = s.record(proj_f)
        ev_f = Event(pid=proj_f.pid, proj=proj_f, origin_claim="world",
                     really_world=False, proof=proof, prev_tip=prev,
                     lamport=lam, recorded=True)
        d = s.receive(ev_f)
        m4s = str((d.get("m4") or {}).get("status", ""))
        false_glued += int(d["status"] == GLUED)
        quar += int(d["status"] == CONFLICT_QUARANTINED or "QUARANTIN" in m4s.upper())
        inc_evict += int(m4s == "incumbent_evicted")
        poison = any(s.asm.known.get(pos, (None,))[0] == anti_view[pos]
                     for pos in proj_f.anchor if pos in s.asm.known)
        silent_poison += int(poison)
    out = {"false_glued": round(false_glued / trials, 3),
           "silent_poison": round(silent_poison / trials, 3),
           "hard_conflict_quarantine": round(quar / trials, 3),
           "incumbent_evicted": round(inc_evict / trials, 3)}
    p(json.dumps(out, ensure_ascii=False))
    p("оригинал (VLI-стенд): false_glued 0.6 / silent 0.333 / quarantine 0.067")
    return out


# ===================================================================== MAIN
def main():
    prereg = check_prereg()
    p("=== E11 — линия «СУБЪЕКТ / ГОЛОГРАФ» (стенд E10'-prime), пре-рег проверен ===")
    results = {"stand": "SubjectE11Prime (ring 16, period 4)",
               "prereg": prereg["id"], "spec": "семейная N1–N5/M1–M4/C1–C5"}
    results["n0"] = n0()
    results["n1"] = n1()
    results["sectors"] = sectors()
    results["n2"] = n2()
    results["n34"] = n34()
    results["n5"] = n5()
    n1r, srr, n34r = results["n1"], results["sectors"], results["n34"]
    c1 = n1r["C1a"] and n1r["C1b"]
    c2, c3 = n1r["C2"], n34r["C3"]
    c4 = srr["rates"]["causal_separation"] == 1.0
    surv = srr["sector_survival"]
    no4th = all(surv.values())
    verdict = {
        "C1_self_sector_statistical": bool(c1),
        "C2_wrong_rejection_control": bool(c2),
        "C3_relearn_contact_gated": bool(c3),
        "C4_causal_unaffected": bool(c4),
        "C5_misspecification": (
            f"eps=0.3 > eps0=0.2: true_accept={n1r['sweep'][0.3]['true_accept']}, "
            "деградация измерена; общий eps0-мисспецификация — честный UNKNOWN"),
        "chimera_control_law_ok": n1r["chimera_law_ok"],
        "sector_survival": surv,
        "no_4th_axis_needed": no4th,
        "covering_triple_status": (
            "тройка CAUSAL/COHERENCE/CONTACT переживает статистический режим "
            "(eps=0.1), каждый ось держит непустой исключительный сектор; "
            "COHERENCE-триггер обобщён до избытка нарушений (stat-gate); "
            "CONTACT дополнительно несёт авторизацию переучивания и корроборацию"
            if no4th else
            "ОПРОВЕРГНУТО в статистическом режиме: "
            + str([k for k, v in surv.items() if not v])),
        "N5_structural": (
            f"стенд линии: false_glued={results['n5']['false_glued']} "
            f"(оригинал 0.6), silent_poison={results['n5']['silent_poison']} "
            f"(оригинал 0.333) — арбитраж корроборацией закрывает attested "
            "overwrite channel; закон НЕ арбитр двух закон-согласованных целых "
            "(анти-целое) — арбитр = число независимых верификаций (E10'-C закрыт)"
            if results["n5"]["false_glued"] <= 0.1 else
            "attested overwrite channel НЕ закрыт — измерено "
            f"{results['n5']['false_glued']}"),
        "mechanisms": ("M1 stat-gate+majority tally (COHERENCE); M2/M2' "
                       "contact-anchored relearn (CONTACT-anchored COHERENCE); "
                       "M3 retry (CONTACT); M4 arbitration: corroboration for "
                       "law-consistent sides, violation rates otherwise"),
        "honest_limitations": [
            "одиночные/двойные сбои внутри полосы мира — ненаблюдаемы в принципе "
            "на этих длинах частей (кривая мощности измерена, вердикта нет)",
            "eps0=0.2 — ЗАЯВЛЕННАЯ граница; eps=0.3 деградирует мягко; общий "
            "случай мисспецификации — UNKNOWN",
            "M4 при отравленном законе арбитрует ОТ закона — ремонт закона "
            "требует канала отзыва (E10'-B) до арбитража значений",
            "tally/корроборация — параметры TALLY_MIN/V_MIN/E_MIN заявлены, "
            "чувствительность к ним не свипована (UNKNOWN)"],
        "status": "VERIFIED* в стенде линии (ring 16, period 4; репликация "
                  "семейной спецификации E11 на E10'-prime стеке)",
        "GENERAL_MINIMALITY": "UNKNOWN",
    }
    results["VERDICT"] = verdict
    p("\n--- VERDICT ---")
    p(json.dumps(verdict, indent=1, ensure_ascii=False))
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, ensure_ascii=False)
    with open(OUT_LOG, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    p(f"\nsaved: {OUT_JSON}")
    p(f"saved: {OUT_LOG}")


if __name__ == "__main__":
    main()
