"""
R14-M2V battery — harness/окружение эксперимента. Оракул читает ТОЛЬКО harness (MC9).
Фазы: baseline (E1) -> freeze (манифест ядра) -> [prereg пишется отдельно] -> full (E1r,E2..E6).
PO-модель REPLICA-1 (DECLARED MODELING CHOICE MC10-replica):
  - случайные дропы с вероятностью rho;
  - burst-потери длиной 12 шагов с вероятностью p=0.06/шаг ВНУТРИ полосы rho in (0.15, 0.27]
    и p=0 вне её (окно burst-уязвимости зафиксировано калибровкой до baseline-прогона;
    точные внутренности PO исходного стенда сессии недоступны — воспроизводится класс
    явления Round 13-PO: громкая acc-деградация через M2-value import при vacuum coherence);
  - переупорядочение прибытия в окне 3 шага.
Все результаты = REPLICA*.
"""

import hashlib
import json
import sys
import time
from typing import List, Dict, Optional, Tuple

import numpy as np

sys.path.insert(0, "/home/z/my-project/stand/core")
from h5d_core import H5dStand, StandConfig, Oracle, Event, CALIBRATION, ALPHABET, sha

BASE = "/home/z/my-project/stand"
RHO_GRID = [0.0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3]
SEEDS_GRID = list(range(12))
SEEDS_BATT = list(range(8))
EPS0_GRID = [0.0, 0.05, 0.1]
EPS_GRID = [0.0, 0.05, 0.1, 0.2]
ATTACKS = ["A0_direct", "A1_search", "A2_freeze", "A3_preempt", "n5v_all"]

BURST_LEN = 14
BURST_P = 0.06
REORDER_WIN = 3


def burst_p_for(rho: float) -> float:
    return BURST_P if (0.15 < rho <= 0.27) else 0.0


# ============================ WORLD (harness) ============================
def run_trial(seed: int, m2v: bool, rho: float, eps0: float = 0.0, eps: float = 0.0,
              attack: str = "none", true_change: bool = True) -> dict:
    cfg = StandConfig(m2v=m2v, rho=rho, eps0=eps0, eps=eps, attack=attack,
                      true_change=true_change, seed=seed)
    oracle = Oracle(seed, CALIBRATION)
    if not true_change:
        # R14 fix-2: статистический режим G2 — мир СТАТИЧЕН (оракул не переключает эпоху);
        # иначе стенд остаётся на base0 при смене истинного базиса -> ложный epoch-mismatch
        oracle.switch_at = 10 ** 9
    stand = H5dStand(cfg)
    stand.bootstrap_law(oracle.base0)   # MC-bootstrap: origin of anchor = открытый пункт §38
    wrng = np.random.RandomState(seed * 104729 + 7)
    prng = np.random.RandomState(seed * 15485863 + 3)

    c = CALIBRATION
    pending: List[Tuple[int, int, Event]] = []
    seq = 0
    burst_left = 0
    atk_base = (3, 2, 1, 0)  # фиксированный «выгодный» базис атакера для A3

    for t in range(c["ROUNDS"]):
        base_true = oracle.base(t)
        events: List[Event] = []

        def mk(agent: str, kind: str, pos: int, value: int) -> Event:
            nonlocal seq
            ev = Event(eid=f"s{seed}-{seq}", t_round=t, t_arrive=t, agent=agent,
                       agent_kind=("A" if agent == "ATK" else agent[0]),
                       pos=int(pos), value=int(value), kind=kind)
            seq += 1
            return ev

        # свидетели: post-switch — лаг (старый базис) либо true_change (новый)
        for i in range(c["WITNESSES"]):
            agent = f"W{i+1}"
            pos = int(wrng.randint(0, c["N"]))
            if true_change and t >= oracle.switch_at:
                if wrng.rand() < c["WITNESS_LAG"]:
                    events.append(mk(agent, "observe", pos, oracle.base0[pos % c["P"]]))
                else:
                    events.append(mk(agent, "true_change", pos, base_true[pos % c["P"]]))
            else:
                v = base_true[pos % c["P"]]
                if wrng.rand() < c["WITNESS_NOISE"]:
                    v = int(wrng.choice([x for x in ALPHABET if x != v]))
                events.append(mk(agent, "observe", pos, v))

        # regulars: контаминация eps0+eps
        for i in range(c["REGULARS"]):
            agent = f"R{i+1}"
            pos = int(wrng.randint(0, c["N"]))
            v = base_true[pos % c["P"]]
            if wrng.rand() < (eps0 + eps):
                v = int(wrng.choice([x for x in ALPHABET if x != v]))
            events.append(mk(agent, "observe", pos, v))

        # N5-атаки (атакер аутентифицирован, канал легитимен — в этом суть N5)
        if attack != "none":
            if attack in ("A0_direct", "n5v_all") and t >= 30 and t % 5 == 0:
                pos = int(prng.randint(0, c["N"]))
                wrong = [x for x in ALPHABET if x != base_true[pos % c["P"]]]
                events.append(mk("ATK", "attack_direct", pos, int(prng.choice(wrong))))
            if attack in ("A1_search", "n5v_all") and t >= 30 and t % 4 == 0:
                pos = int(prng.randint(0, c["N"]))
                events.append(mk("ATK", "attack_search", pos, (t // 4) % c["ALPHA"]))
            if attack in ("A2_freeze", "n5v_all") and t >= oracle.switch_at:
                for _ in range(3):
                    events.append(mk("ATK", "attack_freeze", int(prng.randint(0, c["N"])),
                                     int(prng.randint(0, c["ALPHA"]))))
            if attack in ("A3_preempt", "n5v_all") and t >= oracle.switch_at and t % 2 == 0:
                pos = int((t // 2) % c["N"])
                events.append(mk("ATK", "attack_preempt", pos, atk_base[pos % c["P"]]))

        # ---- Partial observability ----
        if burst_left > 0:
            burst_left -= 1
            surv: List[Event] = []
        else:
            if prng.rand() < burst_p_for(rho):
                burst_left = BURST_LEN - 1
                surv: List[Event] = []   # стартовый раунд burst тоже глухой
            else:
                surv = [ev for ev in events if prng.rand() >= rho]
        for ev in surv:
            arrival = t + int(prng.randint(0, REORDER_WIN))
            pending.append((arrival, seq, ev))

        due = [p for p in pending if p[0] <= t]
        pending = [p for p in pending if p[0] > t]
        due.sort(key=lambda x: (x[0], x[1]))
        had = False
        for _, _, ev in due:
            ev.t_arrive = int(ev.t_arrive)
            stand.contact(ev)
            had = True
        stand.tick(t, had_events=had)

    # ---- метрики (harness читает оракул — MC9) ----
    rep = stand.final_state_report()
    final_base_true = oracle.base(c["ROUNDS"] - 1)
    epoch_match = (tuple(rep["base"]) == final_base_true)
    corrupted: List[int] = []
    if not epoch_match:
        corrupted = list(range(c["N"]))
    else:
        for pos in range(c["N"]):
            vals = rep["values_known"].get(str(pos), [])
            if any(v != final_base_true[pos % c["P"]] for v in vals):
                corrupted.append(pos)
    acc = (c["N"] - len(corrupted)) / c["N"]

    # silent corruption: коррупция value-layer, НЕ объяснённая громким каналом утечки
    # (ledger-записи proposal'ов легальны и в silent не считаются — это CONTACT-семантика)
    leak_pos = set(rep["leak_positions"])
    unexplained = [p for p in corrupted if p not in leak_pos] if epoch_match else corrupted
    silent = len(unexplained) if epoch_match else len(corrupted)
    ledger_mismatch = 0
    if epoch_match:
        for pos in range(c["N"]):
            recs = [r for r in stand.glued if r["pos"] == pos]
            if recs and recs[-1]["value"] != final_base_true[pos % c["P"]]:
                ledger_mismatch += 1

    cnt = rep["counters"]
    g2_rate = (cnt["loud_rejects_legit"] / cnt["legit_total"]) if cnt["legit_total"] else 0.0
    delay = (rep["switch_round"] - oracle.switch_at) if rep["switch_round"] is not None else None

    return {
        "seed": seed, "m2v": m2v, "rho": rho, "eps0": eps0, "eps": eps,
        "attack": attack, "true_change": true_change,
        "acc": acc, "corrupted_positions": corrupted, "epoch_match": bool(epoch_match),
        "epoch_switches": cnt["epoch_switches"], "switch_round": rep["switch_round"],
        "epoch_delay": delay, "false_reject_epoch_trio": cnt["false_reject_epoch_trio"],
        "value_leak_imports": cnt["value_leak_imports"], "m2v_blocks": cnt["m2v_blocks"],
        "vacuum_coherence": cnt["vacuum_coherence"],
        "loud_rejects_legit": cnt["loud_rejects_legit"], "legit_total": cnt["legit_total"],
        "g2_rate": g2_rate, "parked_total": cnt["parked_total"],
        "stat_excess": cnt["stat_excess"], "silent_overwrite": cnt["silent_overwrite"],
        "overwrite_attempts": cnt["overwrite_attempts"], "overwrite_success": cnt["overwrite_success"],
        "silent_corruption": silent, "ledger_last_mismatch": ledger_mismatch,
        "glued_chain_ok": rep["glued_chain_ok"],
        "glued_len": rep["glued_len"],
    }


# ============================ Сводки ============================
def cell(recs: List[dict]) -> dict:
    accs = [r["acc"] for r in recs]
    delays = [r["epoch_delay"] for r in recs if r["epoch_delay"] is not None]
    return {
        "n": len(recs),
        "acc_mean": round(sum(accs) / len(accs), 4),
        "acc_min": round(min(accs), 4),
        "leak_trials": sum(1 for r in recs if r["value_leak_imports"] > 0),
        "leak_mean": round(sum(r["value_leak_imports"] for r in recs) / len(recs), 3),
        "m2v_blocks_mean": round(sum(r["m2v_blocks"] for r in recs) / len(recs), 2),
        "g2_rate_mean": round(sum(r["g2_rate"] for r in recs) / len(recs), 4),
        "silent_total": sum(r["silent_corruption"] + r["silent_overwrite"] for r in recs),
        "overwrite_success_total": sum(r["overwrite_success"] for r in recs),
        "overwrite_attempts_total": sum(r["overwrite_attempts"] for r in recs),
        "chain_ok_all": all(r["glued_chain_ok"] for r in recs),
        "epoch_match_trials": sum(1 for r in recs if r["epoch_match"]),
        "delay_mean": round(sum(delays) / len(delays), 2) if delays else None,
        "trio_false_rejects": sum(r["false_reject_epoch_trio"] for r in recs),
        "vacuum_mean": round(sum(r["vacuum_coherence"] for r in recs) / len(recs), 2),
    }


def phase_baseline() -> dict:
    print("=== E1 BASELINE (v3.1 REPLICA, m2v=False) — PO grid ===")
    out = {"phase": "baseline", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "grid": {}}
    for rho in RHO_GRID:
        recs = [run_trial(seed, m2v=False, rho=rho) for seed in SEEDS_GRID]
        cc = cell(recs)
        out["grid"][str(rho)] = cc
        print(f"rho={rho:<5} acc_mean={cc['acc_mean']:.4f} acc_min={cc['acc_min']:.4f} "
              f"leak_trials={cc['leak_trials']}/{cc['n']} vacuum_mean={cc['vacuum_mean']} "
              f"silent={cc['silent_total']} epoch_match={cc['epoch_match_trials']}/{cc['n']} "
              f"delay={cc['delay_mean']} trioFR={cc['trio_false_rejects']}")
    json.dump(out, open(f"{BASE}/results/round14_baseline.json", "w"), indent=1)
    print("saved: results/round14_baseline.json")
    return out


def phase_freeze() -> dict:
    man = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "core_sha256": hashlib.sha256(open(f"{BASE}/core/h5d_core.py", "rb").read()).hexdigest(),
        "battery_sha256": hashlib.sha256(open(f"{BASE}/battery.py", "rb").read()).hexdigest(),
        "calibration": CALIBRATION,
        "po_model": {"burst_p": BURST_P, "burst_len": BURST_LEN, "burst_band": "(0.15, 0.27]",
                     "reorder_win": REORDER_WIN,
                     "note": "DECLARED MODELING CHOICE MC10-replica: окно burst-уязвимости"},
        "note": "Frozen REPLICA-1 core. Изменение после этой точки = новый механизм/новый baseline (§41).",
    }
    json.dump(man, open(f"{BASE}/core/FROZEN_MANIFEST.json", "w"), indent=1)
    print("FROZEN core:", man["core_sha256"][:16], "| battery:", man["battery_sha256"][:16])
    return man


def phase_full() -> dict:
    prereg_path = f"{BASE}/preregistration_R14_M2V.json"
    prereg = json.load(open(prereg_path))
    print(f"=== FULL BATTERY (prereg {prereg['prereg_id']}, hash {sha(prereg)[:12]}) ===")
    out = {"phase": "full", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "prereg_hash": sha(prereg), "prereg_id": prereg["prereg_id"],
           "frozen_core_sha256": json.load(open(f"{BASE}/core/FROZEN_MANIFEST.json"))["core_sha256"],
           "experiments": {}}

    print("--- E1r: baseline (m2v=False), frozen core ---")
    e1r = {}
    for rho in RHO_GRID:
        recs = [run_trial(seed, m2v=False, rho=rho) for seed in SEEDS_GRID]
        e1r[str(rho)] = cell(recs)
        cc = e1r[str(rho)]
        print(f"rho={rho:<5} acc_mean={cc['acc_mean']:.4f} leak_trials={cc['leak_trials']}/{cc['n']} "
              f"silent={cc['silent_total']}")
    out["experiments"]["E1r_baseline_po_grid"] = e1r

    print("--- E2: M2V PO grid (m2v=True) ---")
    e2 = {}
    for rho in RHO_GRID:
        recs = [run_trial(seed, m2v=True, rho=rho) for seed in SEEDS_GRID]
        e2[str(rho)] = cell(recs)
        cc = e2[str(rho)]
        print(f"rho={rho:<5} acc_mean={cc['acc_mean']:.4f} acc_min={cc['acc_min']:.4f} "
              f"leak_trials={cc['leak_trials']}/{cc['n']} m2v_blocks_mean={cc['m2v_blocks_mean']} "
              f"silent={cc['silent_total']}")
    out["experiments"]["E2_m2v_po_grid"] = e2

    print("--- E3: N5 battery (attacks x m2v) ---")
    e3 = {}
    for atk in ATTACKS:
        for m2v in (False, True):
            key = f"{atk}|m2v={int(m2v)}"
            recs = [run_trial(seed, m2v=m2v, rho=0.05, eps=0.05, attack=atk) for seed in SEEDS_BATT]
            e3[key] = cell(recs)
            cc = e3[key]
            print(f"{key:<22} attempts={cc['overwrite_attempts_total']:<4} "
                  f"ow_success={cc['overwrite_success_total']} silent={cc['silent_total']} "
                  f"chain_ok={cc['chain_ok_all']} epoch_match={cc['epoch_match_trials']}/{cc['n']} "
                  f"delay={cc['delay_mean']}")
    out["experiments"]["E3_n5_battery"] = e3

    print("--- E4: G2 replica mini-grid (rho=0) ---")
    e4 = {}
    for eps0 in EPS0_GRID:
        for eps in EPS_GRID:
            for m2v in (False, True):
                key = f"eps0={eps0}|eps={eps}|m2v={int(m2v)}"
                recs = [run_trial(seed, m2v=m2v, rho=0.0, eps0=eps0, eps=eps) for seed in SEEDS_BATT]
                e4[key] = cell(recs)
            k0, k1 = f"eps0={eps0}|eps={eps}|m2v=0", f"eps0={eps0}|eps={eps}|m2v=1"
            print(f"eps0={eps0} eps={eps} g2[0]={e4[k0]['g2_rate_mean']:.4f} "
                  f"g2[1]={e4[k1]['g2_rate_mean']:.4f} "
                  f"silent={e4[k0]['silent_total']}/{e4[k1]['silent_total']} "
                  f"acc={e4[k0]['acc_mean']}/{e4[k1]['acc_mean']}")
    out["experiments"]["E4_g2_minigrid"] = e4

    print("--- E5: legit epoch path (true_change, rho=0.05) ---")
    e5 = {}
    for m2v in (False, True):
        recs = [run_trial(seed, m2v=m2v, rho=0.05) for seed in SEEDS_GRID]
        e5[f"m2v={int(m2v)}"] = cell(recs)
        cc = e5[f"m2v={int(m2v)}"]
        print(f"m2v={int(m2v)} epoch_match={cc['epoch_match_trials']}/{cc['n']} "
              f"delay_mean={cc['delay_mean']} trio_false_rejects={cc['trio_false_rejects']}")
    out["experiments"]["E5_legit_epoch"] = e5

    print("--- E6: determinism 4x (E1 grid, m2v=False) ---")
    runs = []
    for _ in range(4):
        payload = []
        for rho in RHO_GRID:
            for seed in SEEDS_GRID:
                r = run_trial(seed, m2v=False, rho=rho)
                payload.append([r["acc"], r["value_leak_imports"], r["g2_rate"],
                                r["epoch_switches"], r["glued_len"]])
        runs.append(sha(payload))
    det = {"run_hashes": runs, "bit_identical": len(set(runs)) == 1}
    print(f"determinism: {'BIT-IDENTICAL ' + runs[0][:16] if det['bit_identical'] else 'MISMATCH ' + str(runs)}")
    out["experiments"]["E6_determinism"] = det

    json.dump(out, open(f"{BASE}/results/round14_results.json", "w"), indent=1)
    print("saved: results/round14_results.json")
    return out


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    if phase == "baseline":
        phase_baseline()
    elif phase == "freeze":
        phase_freeze()
    elif phase == "full":
        phase_full()
    else:
        raise SystemExit(f"unknown phase {phase}")
