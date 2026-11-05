#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""МЕХАНИЧЕСКОЕ ДОКАЗАТЕЛЬСТВО: три дефекта ветки ProofObject (v2.1.0 пользователя)
против исправлений v2.2.0 (слияние + Proof Gate + Claim Compiler).

Запуск:  python3 proof_v210_defects.py <путь_к_версии.py>
  * polymath_agent_v2.1.0.py (ветка пользователя): дефекты 1–3 ВОСПРОИЗВОДЯТСЯ
      D1 «Мёртвый proof-гейт»: _finalize штампует VERIFIED, хотя собственный
         _proof_allows_verified говорит False (имитация успеха через квитанцию).
      D2 «Restore running → deadlock»: после краша во время действия capability
         невыполнима навсегда (start() требует pending).
      D3 «http_get мимо pinning»: rebinding-атака доносит секрет с 127.0.0.1.
  * polymath_agent_v2.2.0.py: все три закрыты (гейт отклоняет, демоция pending,
    dial только по валидированному IP).
"""
import socket, sys, threading, http.server, importlib.util, json, tempfile
from pathlib import Path

TARGET = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/upload/polymath_agent_v2.1.0.py"
IS_V22 = "v2.2.0" in TARGET or "v220" in TARGET


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = load(TARGET, "poly_target")
name = Path(TARGET).name
print("=" * 74)
print(f"ЦЕЛЬ: {name}  →  ожидание: {'дефекты ЗАКРЫТЫ' if IS_V22 else 'дефекты ВОСПРОИЗВОДЯТСЯ'}")

# ══ D1: proof-гейт мёртв — имитация успеха проходит ══════════════════════════
print("=" * 74)
print("D1: вердикт принимается ДО proof-объекта? (критерий свидетелен по квитанции,")
print("    содержимое артефакта критерий НЕ подтверждает)")
script = [
    {"thought": "План.", "status": "plan",
     "success_criteria": ["itog.txt содержит 'секрет-42'"], "plan": ["записать", "финал"]},
    {"thought": "Пишу заглушку.", "status": "act",
     "actions": [{"name": "write_file", "args": {"path": "itog.txt", "content": "заглушка"}}]},
    {"thought": "Имя файла в фактах — объявляю успех.", "status": "final",
     "outcome": "verified", "final_answer": "имитация успеха"},
    {"thought": "Честный финал.", "status": "final", "outcome": "failed",
     "final_answer": "отклонено", "lesson": "retry"},
]
td = tempfile.mkdtemp(prefix="proof_d1_")
audit = V.AuditChain(Path(td) / "a.jsonl")
cfg, _ = V._fresh_cfg(td)
cap = {}
agent = V.Agent(cfg, V.MockBrain(script), V.Governor(cfg, audit), audit)
real_fin = agent._finalize
def cap_fin(task_id, state, outcome, answer, started, lesson=""):
    r = real_fin(task_id, state, outcome, answer, started, lesson=lesson)
    cap.update(state)          # захват ПОСЛЕ _finalize: proof штампуется внутри
    return r
agent._finalize = cap_fin
res = agent.solve("запиши отчёт в файл d1")
gate_rows = [r for r in cap.get("ledger", []) if r.get("action") == "(verify-fail)" and "Proof-гейтом" in r.get("obs_brief", "")]
proof = cap.get("proof") or {}
gate_says = None
if proof:
    pf = V.ProofObject(**{k: v for k, v in proof.items() if k in V.ProofObject.__dataclass_fields__})
    gate_says = V.Agent._proof_allows_verified(pf, cap)
print(f"  итог решения:            outcome={res['outcome']}")
print(f"  proof в state:           proof_level={proof.get('proof_level')}")
print(f"  _proof_allows_verified:  {gate_says}  ← механическое мнение собственной proof-машины")
print(f"  proof-гейт сработал?     {bool(gate_rows)}")
if not IS_V22:
    assert res["outcome"] == "verified", f"ожидался дефект D1 (verified принят), получено {res['outcome']}"
    assert not gate_rows, "дефект D1: гейта в runtime нет"
    assert proof.get("proof_level") == "VERIFIED", "дефект D1: ожидан штамп VERIFIED пост-фактум"
    body = (Path(cfg.workspace) / "itog.txt").read_text(encoding="utf-8")
    assert "секрет-42" not in body, "сценарий сломан: заглушка обязана не содержать секрет"
    print("  ВЕРДИКТ D1: ДЕФЕКТ ВОСПРОИЗВЕДЁН:")
    print("    (а) _proof_allows_verified НЕ вызывается в runtime — вердикт принят без неё;")
    print("    (б) proof-объект построен ПОСТ-ФАКТУМ как квитанция (proof_level=VERIFIED);")
    print("    (в) правило proof-машины без per-claim контрактов соглашается с имитацией:")
    print("        артефакт не содержит 'секрет-42', а машина говорит True.")
else:
    assert res["outcome"] == "failed", f"v2.2.0: имитация обязана быть отклонена, получено {res['outcome']}"
    assert gate_rows, "v2.2.0: proof-гейт обязан отклонить"
    print("  ВЕРДИКТ D1: ЗАКРЫТ — гейт отклонил имитацию, честный retry, outcome=failed")

# ══ D2: restore running → вечный deadlock ════════════════════════════════════
print("=" * 74)
print("D2: краш во время действия (статус running) → resume → capability жива?")
td2 = tempfile.mkdtemp(prefix="proof_d2_")
cfg2, _ = V._fresh_cfg(td2)
gov2 = V.Governor(cfg2, V.AuditChain(Path(td2) / "a.jsonl"), V.CatalogBridge(""))
g2 = V.CapabilityGraph(gov2.registry)
g2.add_dependency("research_web", "web_search")   # в ветке без DependencyKnowledge
                                                  # web_search вообще не попадает в план —
                                                  # зерно как в их же T41 делает DAG сопоставимым
spec2 = V.FormalGoalCompiler().compile_spec("исследуй тему через интернет", gov2.registry, V.CapabilityPlanner(g2))
dag = V.ActionDAG(spec2, g2)
dag.start("web_search")                       # ← краш процесса ровно здесь
snap = dag.snapshot()
dag2 = V.ActionDAG(spec2, g2)
if hasattr(V.ActionDAG, "restore_snapshot"):  # путь v2.2.0
    dag2.restore_snapshot(snap)
else:                                         # путь v2.1.0: слепое копирование как в Agent.solve
    for c, s in snap.items():
        if c in dag2.nodes:
            dag2.nodes[c].status = s.get("status", "pending")
st = dag2.nodes["web_search"].status
try:
    dag2.start("web_search"); alive = True
except V.PolicyViolation:
    alive = False
print(f"  статус после restore:    {st}")
print(f"  capability исполнима:    {alive}")
if not IS_V22:
    assert st == "running" and not alive, "ожидался дефект D2 (deadlock)"
    print("  ВЕРДИКТ D2: ДЕФЕКТ ВОСПРОИЗВЕДЁН — running заморожен навсегда, перевыполнение невозможно")
else:
    assert st == "pending" and alive, "v2.2.0: демоция running→pending обязана вернуть исполнимость"
    print("  ВЕРДИКТ D2: ЗАКРЫТ — running демотирован в pending, capability перевыполнима")

# ══ D3: http_get мимо DNS-pinning (TOCTOU/rebinding) ═════════════════════════
print("=" * 74)
print("D3: rebinding-атака против http_get (guard видит публичный IP, dial — приватный)")
class Quiet(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Type", "text/plain")
        self.end_headers(); self.wfile.write(b"SECRET_FROM_LOCALHOST")
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("127.0.0.1", 0), Quiet)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
HOST = "rebind.proof.invalid"
real_gai = socket.getaddrinfo
calls = {"n": 0}
def rebind(host, port_=None, *a, **kw):
    if host == HOST:
        calls["n"] += 1
        ip = "93.184.216.34" if calls["n"] == 1 else "127.0.0.1"
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port_ if port_ else 80))]
    return real_gai(host, *a, **kw)
dials = []
real_create = socket.create_connection
def spy(address, *a, **kw):
    dials.append(address); return real_create(address, *a, **kw)
td3 = tempfile.mkdtemp(prefix="proof_d3_")
cfg3, _ = V._fresh_cfg(td3)
gov3 = V.Governor(cfg3, V.AuditChain(Path(td3) / "a.jsonl"), V.CatalogBridge(""))
socket.getaddrinfo = rebind; socket.create_connection = spy
try:
    obs, _fp = gov3.run("d3", 1, "http_get", {"url": f"http://{HOST}:{port}/x"})
finally:
    socket.getaddrinfo = real_gai; socket.create_connection = real_create
    srv.shutdown()
body = obs.content
hit_local = any(d[0] == "127.0.0.1" for d in dials)
print(f"  obs.ok={obs.ok}  kind={obs.kind}")
print(f"  dials: {dials}")
print(f"  секрет с 127.0.0.1 получен: {'SECRET_FROM_LOCALHOST' in body}")
if not IS_V22:
    assert obs.ok and "SECRET_FROM_LOCALHOST" in body, "ожидался дефект D3 (секрет добыт)"
    print("  ВЕРДИКТ D3: ДЕФЕКТ ВОСПРОИЗВЕДЁН:")
    print("    guard отрезолвил 93.184.216.34 (пропустил), dial пошёл ПО ИМЕНИ ХОСТА —")
    print("    повторный резолв внутри socket.create_connection получил 127.0.0.1,")
    print("    соединение ушло во внутреннюю зону, секрет добыт (TOCTOU/rebinding).")
else:
    assert not obs.ok and obs.kind == "policy_denied", f"v2.2.0: атака обязана быть отклонена: {obs.brief(120)}"
    assert not hit_local, "v2.2.0: dial на 127.0.0.1 запрещён"
    print("  ВЕРДИКТ D3: ЗАКРЫТ — dial только по валидированному IP, атака policy_denied")

print("=" * 74)
print(f"ИТОГ: {'все три дефекта ЗАКРЫТЫ в v2.2.0' if IS_V22 else 'все три дефекта ВОСПРОИЗВЕДЕНЫ на ' + name}")
