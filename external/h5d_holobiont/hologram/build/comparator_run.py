#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# COMPARATOR LIVE RUNNER (Task 16-c)
# =====================================================================
# 1. Static self-check of every candidate against the EXACT challenge
#    code extracted from the comparator bundle (forbidden tokens,
#    main-theorem signature identity, aux-defs-before-main ordering).
# 2. Live submission to https://comparator.live.lean-lang.org:
#       GET  /comparator/api/projects        (reachability)
#       POST /comparator/api/start           {project, challenge, solution}
#       GET  /comparator/api/track/{reqId}   (SSE -> verdict)
#    Submissions: triv, primes, ramsey (<=4 total; ramsey is explicitly
#    EXPERIMENTAL: the live compiler is the only available verifier of
#    the `ramsey` Mathlib citation - a verification-failed there is a
#    measured honest result, not a claimed proof).
# Honesty Clause: until the service reports verification-ok, every
# artifact is a CANDIDATE; the report contains only actual verdicts.
# =====================================================================
import json
import time
import re
import requests

BASE = "https://comparator.live.lean-lang.org"
API = BASE + "/comparator/api"
CDIR = "/home/z/my-project/download/comparator_candidates"
OUT_JSON = "/home/z/my-project/download/comparator_submission_results.json"
OUT_LOG = "/home/z/my-project/download/comparator_candidates_stdout.log"

PROJECT = "mathlib-stable"   # Stable Release v4.33.0 (least API drift)

# challenge code VERBATIM from the bundle (id -> contents)
CHALLENGES = {
    "triv": 'theorem triv : True := by\n  sorry',
    "primes": ('def IsPrime (n : Nat) := 1 < n ∧ ∀ k, 1 < k → k < n → ¬ k ∣ n\n'
               '\n'
               'theorem InfinitudeOfPrimes : ∀ n, ∃ p > n, IsPrime p := by\n'
               '  sorry'),
    "ramsey": ('import Mathlib\n'
               '\n'
               'open SimpleGraph\n'
               '\n'
               'theorem finite_graph_ramsey_theorem :\n'
               '    ∀ r s : ℕ, 2 ≤ r → 2 ≤ s → ∃ n : ℕ, ∀ G : SimpleGraph (Fin n), ¬ G.CliqueFree r ∨ ¬ Gᶜ.CliqueFree s := by\n'
               '  sorry'),
}
SUBMIT = [("primes", "primes.lean", "CANDIDATE")]
# NOTE (16-c, final attempt): v4.33.0 sources verified from the release
# tag: exists_infinite_primes lives in Mathlib.Data.Nat.Prime.Infinite;
# the graph Ramsey theorem is ABSENT from Mathlib v4.33.0 entirely ->
# ramsey is NOT submitted (CANDIDATE-INCOMPLETE per Honesty Clause).
# triv already verification-ok (log 1); primes gets its final targeted
# submission here.

FORBIDDEN = ["sorry", "admit", "axiom", "native_decide", "unsafe",
             "partial", "implemented_by", "extern"]

_lines = []


def p(s=""):
    print(s, flush=True)
    _lines.append(str(s))


def selfcheck(name, fname):
    code = open(f"{CDIR}/{fname}").read()
    chal = CHALLENGES[name]
    res = {"candidate": fname, "challenge": name, "checks": {}}
    # (i) forbidden tokens (word-ish scan, skip comments)
    body = re.sub(r"--[^\n]*", "", code)
    hits = [t for t in FORBIDDEN
            if re.search(r"(?<![A-Za-z_.])" + re.escape(t) + r"(?![A-Za-z_])",
                         body)]
    res["checks"]["forbidden_tokens"] = {"hits": hits,
                                         "ok": not hits}
    # (ii) main theorem present, signature identity (normalized)
    def norm(s):
        return re.sub(r"\s+", " ", s).strip()
    # robust: capture 'theorem <name> ... :=' (multi-colon signatures)
    thm_re = re.compile(r"theorem\s+([A-Za-z0-9_.']+)(.*?):=",
                        re.DOTALL)
    chal_thm = thm_re.findall(norm(chal))
    cand_thm = thm_re.findall(norm(code))
    ok_sig = False
    if chal_thm and cand_thm:
        ch = chal_thm[-1]
        for cd in cand_thm:
            if cd[0] == ch[0] and norm(cd[1]) == norm(ch[1]):
                ok_sig = True
                break
    res["checks"]["signature_identity"] = {"ok": ok_sig,
                                           "challenge_theorem":
                                               chal_thm[-1][0] if chal_thm
                                               else None}
    # (iii) aux declarations before the main theorem
    lines = [ln for ln in code.splitlines() if ln.strip()
             and not ln.strip().startswith("--")]
    decl_idx = [(i, ln) for i, ln in enumerate(lines)
                if re.match(r"\s*(theorem|def|lemma|abbrev)\s", ln)]
    main_idx = next((i for i, ln in decl_idx
                     if f"theorem {chal_thm[-1][0]}" in ln
                     or ln.startswith(f"theorem {chal_thm[-1][0]} ")), None)
    order_ok = True
    if main_idx is not None:
        after_main = [ln for i, ln in decl_idx if i > main_idx]
        order_ok = not after_main
    res["checks"]["aux_before_main"] = {"ok": order_ok}
    res["ok"] = all(v.get("ok") for v in res["checks"].values())
    return res


def live_submit(name, fname, label):
    solution = open(f"{CDIR}/{fname}").read()
    challenge = CHALLENGES[name]
    rec = {"challenge": name, "candidate": fname, "label": label,
           "project": PROJECT, "events": []}
    try:
        r0 = requests.get(f"{API}/projects", timeout=30)
        rec["projects_http"] = r0.status_code
        r = requests.post(f"{API}/start", timeout=60,
                          json={"project": PROJECT,
                                "challenge": challenge,
                                "solution": solution})
        rec["start_http"] = r.status_code
        j = r.json()
        rec["start_response"] = j
        if j.get("type") != "ready":
            rec["verdict"] = "START-REJECTED"
            return rec
        rid = j["requestId"]
        rec["requestId"] = rid
        t0 = time.time()
        with requests.get(f"{API}/track/{rid}", stream=True, timeout=(
                30, 300)) as st:
            for raw in st.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    ev = json.loads(raw[5:].strip())
                except Exception:
                    continue
                rec["events"].append({"t": round(time.time() - t0, 1),
                                      "event": ev})
                p(f"    [{name} t+{rec['events'][-1]['t']}s] "
                  f"{ev.get('type')} "
                  f"{ev.get('theoremNames', '') or ev.get('description', '') or ev.get('position', '')}")
                if ev.get("type") in ("verification-ok",
                                      "verification-failed"):
                    rec["verdict"] = ev["type"]
                    rec["theoremNames"] = ev.get("theoremNames", [])
                    rec["description"] = ev.get("description")
                    break
                if time.time() - t0 > 420:
                    rec["verdict"] = "TIMEOUT"
                    break
        if "verdict" not in rec:
            rec["verdict"] = "CONNECTION-LOST"
    except Exception as ex:  # noqa
        rec["verdict"] = f"ERROR: {ex!r}"
    return rec


def main():
    p("=" * 68)
    p("COMPARATOR LIVE RUNNER (Task 16-c)")
    p("=" * 68)
    results = {"service": BASE, "project": PROJECT,
               "honesty_clause": "verdicts below are the service's; "
                                 "before verification-ok everything is "
                                 "a CANDIDATE"}

    # ---- self-check -------------------------------------------------
    p("1) static self-check")
    sc = {}
    for name, fname, label in SUBMIT:
        r = selfcheck(name, fname)
        sc[name] = r
        p(f"  {fname}: ok={r['ok']} "
          f"forbidden={r['checks']['forbidden_tokens']['hits']} "
          f"sig={r['checks']['signature_identity']['ok']} "
          f"order={r['checks']['aux_before_main']['ok']}")
    results["selfcheck"] = sc

    # ---- reachability ------------------------------------------------
    p("2) reachability: GET /comparator/api/projects")
    try:
        pr = requests.get(f"{API}/projects", timeout=30)
        projects = pr.json()
        results["projects"] = projects
        p(f"  HTTP {pr.status_code}: "
          f"{[x['project'] for x in projects if not x.get('hidden')]}")
    except Exception as ex:  # noqa
        results["projects"] = f"UNREACHABLE: {ex!r}"
        p(f"  UNREACHABLE: {ex!r}")
        with open(OUT_JSON, "w") as f:
            json.dump(results, f, indent=2, default=str)
        return

    # ---- live submissions (sequential, <=4) --------------------------
    p("3) live submissions (sequential)")
    subs = []
    for name, fname, label in SUBMIT:
        if not sc[name]["ok"]:
            p(f"  SKIP {fname}: failed self-check")
            subs.append({"challenge": name, "verdict": "SKIPPED_SELFCHECK"})
            continue
        p(f"  submitting {fname} ({label}) to {PROJECT} ...")
        rec = live_submit(name, fname, label)
        subs.append(rec)
        p(f"  -> {name}: {rec.get('verdict')} "
          f"{rec.get('theoremNames', '')}")
        time.sleep(5)
    results["submissions"] = subs

    # ---- meta.json + verdict ----------------------------------------
    meta = []
    for f_, lab, note in [
            ("triv.lean", "CANDIDATE", "submitted"),
            ("primes.lean", "CANDIDATE", "submitted"),
            ("ramsey.lean", "CANDIDATE-EXPERIMENTAL",
             "submitted; live compiler is the verifier of the citation"),
            ("FLT_INCOMPLETE.md", "CANDIDATE-INCOMPLETE",
             "open problem; not submitted"),
            ("Collatz_INCOMPLETE.md", "CANDIDATE-INCOMPLETE",
             "open problem; not submitted"),
            ("REFUSAL_false.md", "REFUSAL",
             "special case; not submitted")]:
        meta.append({"file": f_, "status": lab, "note": note})
    json.dump(meta, open(f"{CDIR}/meta.json", "w"), indent=2,
              ensure_ascii=False)

    verdicts = {s["challenge"]: s.get("verdict") for s in subs}
    ok = [k for k, v in verdicts.items() if v == "verification-ok"]
    results["summary_verdicts"] = verdicts
    p("")
    p("SUMMARY VERDICTS (service-reported): " + json.dumps(verdicts))
    p(f"verified-ok: {ok or 'none'}")
    p("HONESTY CLAUSE: only verification-ok entries may be called "
      "proven; everything else stays CANDIDATE/REFUSED/INCOMPLETE.")

    with open(OUT_JSON, "w") as f:
        json.dump(results, f, indent=2, default=str, ensure_ascii=False)
    with open(OUT_LOG, "w") as f:
        f.write("\n".join(_lines) + "\n")
    p(f"saved: {OUT_JSON}")
    p(f"saved: {OUT_LOG}")


if __name__ == "__main__":
    main()
