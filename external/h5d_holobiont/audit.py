"""
R14-M2V INDEPENDENT AUDIT (§39 step 7).
Аудит НЕ импортирует внутренние решения механизма: он
  1) переисполняет все ячейки батареи детерминированно (те же сиды/параметры),
  2) сверяет с results.json бит-в-бит (детерминизм + отсутствие ручных правок),
  3) перевыводит вердикты V1..V8 из preregistration ТОЛЬКО по переисполненным данным,
  4) проверяет oracle-independence механизма по AST (H5dStand не ссылается на Oracle),
  5) проверяет frozen manifest (sha256 ядра и батареи).
Выход: results/round14_audit.json
"""

import ast
import hashlib
import json
import sys

sys.path.insert(0, "/home/z/my-project/stand/core")
sys.path.insert(0, "/home/z/my-project/stand")
from battery import (run_trial, cell, RHO_GRID, SEEDS_GRID, SEEDS_BATT,
                     EPS0_GRID, EPS_GRID, ATTACKS)

BASE = "/home/z/my-project/stand"


def sha_obj(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def check_oracle_independence(path: str) -> dict:
    """AST-проверка: тело класса H5dStand не содержит обращений к Oracle/oracle."""
    tree = ast.parse(open(path).read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "H5dStand":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id in ("Oracle", "oracle"):
                    violations.append(f"line {getattr(sub, 'lineno', '?')}: {sub.id}")
                if isinstance(sub, ast.Attribute) and sub.attr in ("true_value", "oracle_calls"):
                    violations.append(f"line {getattr(sub, 'lineno', '?')}: .{sub.attr}")
    return {"ok": len(violations) == 0, "violations": violations}


def recompute_cells() -> dict:
    out = {}
    e1r = {}
    for rho in RHO_GRID:
        e1r[str(rho)] = cell([run_trial(s, m2v=False, rho=rho) for s in SEEDS_GRID])
    out["E1r_baseline_po_grid"] = e1r
    e2 = {}
    for rho in RHO_GRID:
        e2[str(rho)] = cell([run_trial(s, m2v=True, rho=rho) for s in SEEDS_GRID])
    out["E2_m2v_po_grid"] = e2
    e3 = {}
    for atk in ATTACKS:
        for m2v in (False, True):
            e3[f"{atk}|m2v={int(m2v)}"] = cell(
                [run_trial(s, m2v=m2v, rho=0.05, eps=0.05, attack=atk) for s in SEEDS_BATT])
    out["E3_n5_battery"] = e3
    e4 = {}
    for eps0 in EPS0_GRID:
        for eps in EPS_GRID:
            for m2v in (False, True):
                e4[f"eps0={eps0}|eps={eps}|m2v={int(m2v)}"] = cell(
                    [run_trial(s, m2v=m2v, rho=0.0, eps0=eps0, eps=eps) for s in SEEDS_BATT])
    out["E4_g2_minigrid"] = e4
    e5 = {}
    for m2v in (False, True):
        e5[f"m2v={int(m2v)}"] = cell([run_trial(s, m2v=m2v, rho=0.05) for s in SEEDS_GRID])
    out["E5_legit_epoch"] = e5
    return out


def verdicts(re: dict, raw_samples: dict, results_cache: dict) -> dict:
    v = {}
    e1r, e2 = re["E1r_baseline_po_grid"], re["E2_m2v_po_grid"]
    c02 = e1r["0.2"]
    v["V1_bug_reproduced"] = {
        "cell_0.2_acc_mean": c02["acc_mean"], "cell_0.2_leak_trials": c02["leak_trials"],
        "clean_cells_acc": {r: e1r[r]["acc_mean"] for r in ("0.0", "0.05", "0.1", "0.15", "0.3")},
        "silent_total_all": sum(e1r[r]["silent_total"] for r in e1r),
        "pass": (c02["acc_mean"] < 0.99 and c02["leak_trials"] >= 9
                 and all(e1r[r]["acc_mean"] == 1.0 for r in ("0.0", "0.05", "0.1", "0.15", "0.3"))
                 and sum(e1r[r]["silent_total"] for r in e1r) == 0),
    }
    blocks_sum = sum(e2[r]["m2v_blocks_mean"] for r in e2)
    v["V2_m2v_closes"] = {
        "all_acc_mean_1": all(e2[r]["acc_mean"] == 1.0 for r in e2),
        "all_acc_min_1": all(e2[r]["acc_min"] == 1.0 for r in e2),
        "all_leak_zero": all(e2[r]["leak_trials"] == 0 for r in e2),
        "blocks_sum": round(blocks_sum, 2),
        "pass": (all(e2[r]["acc_mean"] == 1.0 and e2[r]["acc_min"] == 1.0
                     and e2[r]["leak_trials"] == 0 for r in e2) and blocks_sum > 0),
    }
    chain_ok = raw_samples["chain_ok_all_cells"]
    v["V3_no_new_silent"] = {
        "silent_total_all": sum(e2[r]["silent_total"] for r in e2),
        "chain_ok_everywhere": chain_ok["E2"],
        "pass": sum(e2[r]["silent_total"] for r in e2) == 0 and chain_ok["E2"],
    }
    e3 = re["E3_n5_battery"]
    e5 = re["E5_legit_epoch"]
    a2_delay = e3["A2_freeze|m2v=1"]["delay_mean"]
    e5_delay = e5["m2v=1"]["delay_mean"]
    v4_items = {}
    for k in e3:
        v4_items[k] = (e3[k]["overwrite_success_total"] == 0 and e3[k]["silent_total"] == 0
                       and e3[k]["chain_ok_all"] and e3[k]["epoch_match_trials"] >= 6)
    v["V4_n5_closure_preserved"] = {
        "per_cell": v4_items,
        "a2_delay": a2_delay, "e5_delay": e5_delay,
        "a2_within_bound": (a2_delay is not None and e5_delay is not None and a2_delay <= 3 * e5_delay),
        "pass": all(v4_items.values()) and a2_delay is not None and a2_delay <= 3 * e5_delay,
    }
    e4 = re["E4_g2_minigrid"]
    g2_ok = []
    for eps0 in EPS0_GRID:
        for eps in EPS_GRID:
            g0 = e4[f"eps0={eps0}|eps={eps}|m2v=0"]["g2_rate_mean"]
            g1 = e4[f"eps0={eps0}|eps={eps}|m2v=1"]["g2_rate_mean"]
            g2_ok.append(g1 <= g0 + 0.02)
    v5_items = {
        "g2_not_worsened_anywhere": all(g2_ok),
        "eps0_cell_acc": e4["eps0=0.0|eps=0.0|m2v=1"]["acc_mean"],
        "eps0_cell_silent": e4["eps0=0.0|eps=0.0|m2v=1"]["silent_total"],
        "silent_all_cells": sum(e4[k]["silent_total"] for k in e4),
    }
    v5_items["pass"] = (all(g2_ok) and v5_items["eps0_cell_acc"] == 1.0
                        and v5_items["silent_all_cells"] == 0)
    v["V5_g2_not_worsened"] = v5_items
    v["V6_legit_epoch_path"] = {
        "match_0": e5["m2v=0"]["epoch_match_trials"], "match_1": e5["m2v=1"]["epoch_match_trials"],
        "delay_0": e5["m2v=0"]["delay_mean"], "delay_1": e5["m2v=1"]["delay_mean"],
        "trio_fr_0": e5["m2v=0"]["trio_false_rejects"], "trio_fr_1": e5["m2v=1"]["trio_false_rejects"],
        "pass": (e5["m2v=0"]["epoch_match_trials"] == 12 and e5["m2v=1"]["epoch_match_trials"] == 12
                 and (e5["m2v=0"]["delay_mean"] or 0) <= 25 and (e5["m2v=1"]["delay_mean"] or 0) <= 25
                 and e5["m2v=0"]["trio_false_rejects"] <= 12 and e5["m2v=1"]["trio_false_rejects"] <= 12),
    }
    det_runs = raw_samples["determinism"]["audit_hashes"]
    det_pass = (det_runs[0] == det_runs[1]
                and det_runs[0] == results_cache["experiments"]["E6_determinism"]["run_hashes"][0])
    v["V7_determinism"] = {
        "audit_hashes": det_runs,
        "bit_identical": det_runs[0] == det_runs[1],
        "matches_battery_E6": det_runs[0] == results_cache["experiments"]["E6_determinism"]["run_hashes"][0],
        "pass": det_pass,
    }
    parked_ok = all(raw_samples["parked_totals"][r] > 0 for r in ("0.1", "0.2", "0.25"))
    a0_attempts = re["E3_n5_battery"]["A0_direct|m2v=0"]["overwrite_attempts_total"]
    v["V8_contact_preserved"] = {
        "parked_totals_sample": raw_samples["parked_totals"],
        "a0_attempts": a0_attempts,
        "pass": parked_ok and a0_attempts > 0,
    }
    v["FINAL"] = all(v[k]["pass"] for k in
                     ("V1_bug_reproduced", "V2_m2v_closes", "V3_no_new_silent",
                      "V4_n5_closure_preserved", "V5_g2_not_worsened",
                      "V6_legit_epoch_path", "V7_determinism", "V8_contact_preserved"))
    return v


def main():
    prereg = json.load(open(f"{BASE}/preregistration_R14_M2V.json"))
    results = json.load(open(f"{BASE}/results/round14_results.json"))
    manifest = json.load(open(f"{BASE}/core/FROZEN_MANIFEST.json"))

    # 5) manifest
    core_sha = hashlib.sha256(open(f"{BASE}/core/h5d_core.py", "rb").read()).hexdigest()
    batt_sha = hashlib.sha256(open(f"{BASE}/battery.py", "rb").read()).hexdigest()
    manifest_ok = (core_sha == manifest["core_sha256"] and batt_sha == manifest["battery_sha256"]
                   and core_sha == results["frozen_core_sha256"])
    print("manifest:", "OK" if manifest_ok else "MISMATCH", core_sha[:16], batt_sha[:16])

    # 4) oracle-independence (AST)
    oi = check_oracle_independence(f"{BASE}/core/h5d_core.py")
    print("oracle-independence:", "OK" if oi["ok"] else oi["violations"])

    # 1+2) переисполнение и сверка
    print("re-executing battery cells (deterministic)...")
    re = recompute_cells()
    mismatches = []
    for exp in ("E1r_baseline_po_grid", "E2_m2v_po_grid", "E3_n5_battery", "E4_g2_minigrid", "E5_legit_epoch"):
        for k, cellv in re[exp].items():
            if json.dumps(cellv, sort_keys=True) != json.dumps(results["experiments"][exp][k], sort_keys=True):
                mismatches.append((exp, k))
    repro_identical = len(mismatches) == 0
    print("re-execution vs results.json:", "BIT-IDENTICAL" if repro_identical else f"MISMATCH {mismatches[:5]}")

    # сырые образцы для аудита (детерминированны)
    parked_totals = {}
    chain_ok_cells = {"E2": True}
    for rho in ("0.1", "0.2", "0.25"):
        rr = run_trial(0, m2v=False, rho=float(rho))
        parked_totals[rho] = rr["parked_total"]
    for rho in RHO_GRID:
        rr = run_trial(0, m2v=True, rho=rho)
        chain_ok_cells["E2"] &= rr["glued_chain_ok"]
    det_runs = []
    for _ in range(2):
        payload = []
        for rho in RHO_GRID:
            for s in SEEDS_GRID:
                r = run_trial(s, m2v=False, rho=rho)
                payload.append([r["acc"], r["value_leak_imports"], r["g2_rate"],
                                r["epoch_switches"], r["glued_len"]])
        det_runs.append(sha_obj(payload))
    raw_samples = {
        "parked_totals": parked_totals,
        "chain_ok_all_cells": chain_ok_cells,
        "determinism": {"audit_hashes": det_runs,
                        "bit_identical": det_runs[0] == det_runs[1],
                        "matches_battery_E6": det_runs[0] == results["experiments"]["E6_determinism"]["run_hashes"][0]},
    }

    # 3) вердикты
    vd = verdicts(re, raw_samples, results)
    report = {
        "audit_id": "R14-M2V-audit-1",
        "ts": results["ts"],
        "prereg_id": prereg["prereg_id"],
        "prereg_hash": results["prereg_hash"],
        "manifest_ok": manifest_ok,
        "oracle_independence": oi,
        "reexecution_bit_identical": repro_identical,
        "mismatches": mismatches,
        "verdicts": vd,
        "note": "Аудит переисполнил все ячейки детерминированно и перевывел вердикты независимо от battery-сводок.",
    }
    json.dump(report, open(f"{BASE}/results/round14_audit.json", "w"), indent=1)
    print("--- VERDICTS ---")
    for k in ("V1_bug_reproduced", "V2_m2v_closes", "V3_no_new_silent", "V4_n5_closure_preserved",
              "V5_g2_not_worsened", "V6_legit_epoch_path", "V7_determinism", "V8_contact_preserved"):
        print(f"{k:<28} {'PASS' if vd[k]['pass'] else 'FAIL'}")
    print("FINAL:", "CONFIRMED 8/8" if vd["FINAL"] else "REJECTED / PARTIAL")


if __name__ == "__main__":
    main()
