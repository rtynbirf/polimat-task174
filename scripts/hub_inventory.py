#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hub-инвентарь TASK174: сверка пломб MANIFEST_SHA256.txt через пакет kanon_verify.

Волна ×4 · П45 (issue #2): hub-инвентарь импортирует ОДИН канон проверок —
тот же пакет, что ставится через pip и потребляется клетками роя.
Скрипт только сверяет (канон «чужое не тронуто»): никаких записей и правок.

Запуск:  python3 scripts/hub_inventory.py [--manifest MANIFEST_SHA256.txt]
rc=0 — все пломбы [В]; rc=1 — есть провалы (печатает отчёт).
"""
import argparse
import os
import sys

# Пакет живёт в verifier/ (pip install -e ./verifier кладёт его в site-packages;
# subtree-путь — для потребления без установки, как клетками роя)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "verifier"))

from kanon_verify import CANON_VERSION, verify_manifest  # noqa: E402
from kanon_verify.canon import report_bytes  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Hub-инвентарь: сверка манифеста пломб")
    ap.add_argument("--manifest", default="MANIFEST_SHA256.txt")
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    if not os.path.exists(args.manifest):
        print(f"ФАКТ: манифест не найден: {args.manifest}", file=sys.stderr)
        return 1

    import kanon_verify  # канон импортирован пакетом — не копипастой
    print(f"ФАКТ: канон проверок CANON_VERSION={CANON_VERSION} "
          f"из пакета kanon_verify {kanon_verify.__version__} "
          f"({os.path.dirname(kanon_verify.__file__)})")

    with open(args.manifest, encoding="utf-8") as f:
        text = f.read()
    report = verify_manifest(args.root, text)
    sys.stdout.buffer.write(report_bytes(report) + b"\n")
    print(f"ФАКТ: пломб проверено {report['checked']}, провалов {len(report['failures'])} "
          f"— вердикт {'[В]' if report['ok'] else '[О] с дырами'}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
