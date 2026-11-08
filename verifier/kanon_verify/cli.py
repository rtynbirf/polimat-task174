# -*- coding: utf-8 -*-
"""CLI верификатора канона (Волна ×4 · П45): kanon-verify.

Команды:
  kanon-verify --selftest                     — самоиспытание канона (rc 0/1)
  kanon-verify manifest [PATH] [--root DIR]   — сверка дерева по манифесту
                                                (по умолчанию MANIFEST_SHA256.txt)
  kanon-verify files --expect JSON [--root D] — сверка по словарю ожиданий
                                                (канон Б25.8)
Выход: машиночитаемый отчёт (JSON) на stdout; rc 0 = ok, 1 = провал.
"""
import argparse
import json
import os
import sys

from . import CANON_VERSION, selftest, verify_files, verify_manifest
from .canon import report_bytes


def _print(report):
    sys.stdout.buffer.write(report_bytes(report) + b"\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="kanon-verify",
        description="Верификатор канона ПОЛИМАТ по строкам (инструмент = договор)",
    )
    ap.add_argument("--version", action="version",
                    version=f"kanon-verify {CANON_VERSION}")
    ap.add_argument("--selftest", action="store_true",
                    help="самоиспытание канона (rc 0/1)")
    sub = ap.add_subparsers(dest="cmd")

    p_m = sub.add_parser("manifest", help="сверка дерева по манифесту sha256")
    p_m.add_argument("path", nargs="?", default="MANIFEST_SHA256.txt",
                     help="путь манифеста (по умолчанию MANIFEST_SHA256.txt)")
    p_m.add_argument("--root", default=".", help="корень дерева (по умолчанию .)")

    p_f = sub.add_parser("files", help="сверка по словарю ожиданий (канон Б25.8)")
    p_f.add_argument("--expect", required=True,
                     help="JSON-файл {имя: sha256} или '-' для stdin")
    p_f.add_argument("--root", default=".", help="корень дерева (по умолчанию .)")

    args = ap.parse_args(argv)

    if args.selftest or args.cmd is None:
        report = selftest()
        _print(report)
        return 0 if report["ok"] else 1

    if args.cmd == "manifest":
        if not os.path.exists(args.path):
            print(f"манифест не найден: {args.path}", file=sys.stderr)
            return 1
        with open(args.path, encoding="utf-8") as f:
            text = f.read()
        report = verify_manifest(args.root, text)
        _print(report)
        return 0 if report["ok"] else 1

    if args.cmd == "files":
        raw = sys.stdin.read() if args.expect == "-" else open(
            args.expect, encoding="utf-8").read()
        expect = json.loads(raw)
        if not isinstance(expect, dict):
            print("--expect: ожидается JSON-объект {имя: sha256}", file=sys.stderr)
            return 1
        report = verify_files(args.root, expect)
        _print(report)
        return 0 if report["ok"] else 1

    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
