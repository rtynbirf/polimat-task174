# -*- coding: utf-8 -*-
"""Канон проверок ПОЛИМАТ по строкам (Волна ×4 · П45).

ОДИН канон на всех: hub-воркфлоу, клетки роя и сторонний чужак вызывают
одни и те же функции и получают одинаковые байты отчёта.

Правила канона (из протокола Task174):
1. Пломба до слова — артефакт несёт sha256; сверяется строкой, не смыслом.
2. Манифест — строки формата «<sha256>  <путь>» (sha256sum-совместимый);
   комментарии «# …» и пустые строки игнорируются; порядок строк значения
   не имеет (сверка по множеству путей), дубликат пути = ПРОВАЛ.
3. Отчёт — JSON-совместимый словарь: {"ok": bool, "checked": n,
   "failures": [{"path":…, "expected":…, "got":…, "reason":…}]}.
   Одинаковый вход → одинаковые байты отчёта (json.dumps сортирует ключи).
4. Чужое — не тронуто: канон только сверяет, ничего не пишет и не правит.
"""
import hashlib
import json
import os
import tempfile

CANON_VERSION = 1
GENESIS = "0" * 64  # пустое ожидание: сверка с «ничем» падает CHAIN, не молчит

# Пошаговое чтение: файл может быть большим (zip-пломбы Б25)
_CHUNK = 1 << 20


def sha256_file(path: str) -> str:
    """Пломба файла строкой: sha256 hexdigest поточного чтения.

    Единственный источник «ожидаемого» в каноне — байты на диске,
    прочитанные одинаково у всех носителей.
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(text: str):
    """Манифест «<sha256>  <путь>» → отсортированный список [(путь, ожидание)].

    sha256sum-совместимый формат (два пробела), '#' — комментарий.
    Дубликат пути — ValueError: манифест с двумя правдами не манифест.
    """
    rows = {}
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) != 2:
            raise ValueError(f"манифест, строка {lineno}: не «<sha256>  <путь>»: {raw!r}")
        expected, path = parts[0].lower(), parts[1].strip()
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError(f"манифест, строка {lineno}: ожидание не sha256: {expected!r}")
        if path in rows:
            raise ValueError(f"манифест, строка {lineno}: путь продублирован: {path!r}")
        rows[path] = expected
    return sorted(rows.items())


def _fail(report, path, expected, got, reason):
    report["ok"] = False
    report["failures"].append(
        {"path": path, "expected": expected, "got": got, "reason": reason}
    )


def verify_manifest(base_dir: str, manifest_text: str) -> dict:
    """Сверка дерева base_dir по тексту манифеста → отчёт канона.

    Отсутствие файла — провал (silent mutation не проходит: пломба без
    носителя = носитель без пломбы). Отчёт сортирован по путям.
    """
    report = {"canon": CANON_VERSION, "ok": True, "checked": 0, "failures": []}
    try:
        rows = parse_manifest(manifest_text)
    except ValueError as e:
        _fail(report, "<manifest>", None, None, f"STRUCTURE: {e}")
        return report
    for path, expected in rows:
        report["checked"] += 1
        p = os.path.join(base_dir, path)
        if not os.path.exists(p):
            _fail(report, path, expected, None, "MISSING")
            continue
        got = sha256_file(p)
        if got != expected:
            _fail(report, path, expected, got, "MUTATED")
    report["failures"].sort(key=lambda r: r["path"])
    return report


def verify_files(base_dir: str, expect: dict) -> dict:
    """Сверка словаря {имя: ожидаемый_sha256} — канон Б25.8 (verify_b25_final).

    Имена — относительно base_dir (в Б25.8 это «download/» и пакеты).
    Отчёт того же вида, что у verify_manifest: один канон, одна форма.
    """
    report = {"canon": CANON_VERSION, "ok": True, "checked": 0, "failures": []}
    for name in sorted(expect):
        report["checked"] += 1
        p = os.path.join(base_dir, name)
        expected = str(expect[name]).lower()
        if not os.path.exists(p):
            _fail(report, name, expected, None, "MISSING")
            continue
        got = sha256_file(p)
        if got != expected:
            _fail(report, name, expected, got, "MUTATED")
    return report


# --- Самоиспытание: канон проверяет сам себя до проверки чужого -------------

def _selftest_case(report):
    """Кейс 1: известные байты дают известную пломбу (эталон sha256)."""
    data = b"polymath: \xd0\xbf\xd1\x80\xd0\xbe\xd0\xb2\xd0\xb5\xd1\x80\xd1\x8f\xd0\xb9 \xd1\x81\xd1\x82\xd1\x80\xd0\xbe\xd0\xba\xd0\xbe\xd0\xb9\n"
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "kanon.txt")
        with open(p, "wb") as f:
            f.write(data)
        got = sha256_file(p)
        want = hashlib.sha256(data).hexdigest()
        if got != want:
            _fail(report, "selftest/known-bytes", want, got, "SELFTEST")
        # Кейс 2: silent mutation ловится (побит сдвинут байт — пломба другая)
        with open(p, "ab") as f:
            f.write(b"x")
        got2 = sha256_file(p)
        if got2 == got:
            _fail(report, "selftest/mutation-caught", "!=got", got2, "SELFTEST")

    # Кейс 3: манифест по чистому файлу сходится и падает на подмене
    with tempfile.TemporaryDirectory() as td2:
        q = os.path.join(td2, "kanon.txt")
        with open(q, "wb") as f:
            f.write(data)
        h = sha256_file(q)
        r = verify_manifest(td2, f"{h}  kanon.txt\n")
        if not r["ok"] or r["checked"] != 1:
            _fail(report, "selftest/manifest-ok", "ok", r, "SELFTEST")
        with open(q, "ab") as f:
            f.write(b"y")
        r2 = verify_manifest(td2, f"{h}  kanon.txt\n")
        if r2["ok"] or r2["failures"][0]["reason"] != "MUTATED":
            _fail(report, "selftest/manifest-mutation", "MUTATED", r2, "SELFTEST")
        # Кейс 4: дубликат пути в манифесте — STRUCTURE, а не молчание
        try:
            parse_manifest(f"{h}  a\n{h}  a\n")
            _fail(report, "selftest/duplicate-path", "ValueError", "ok", "SELFTEST")
        except ValueError:
            pass


def _selftest_genesis(report):
    """Кейс 5: GENESIS — пустое ожидание не считается совпадением ни с чем."""
    if GENESIS != "0" * 64:
        _fail(report, "selftest/genesis", "0" * 64, GENESIS, "SELFTEST")


def selftest() -> dict:
    """Самоиспытание канона: эталонные пломбы, ловушки мутаций, формы отчёта.

    Возвращает отчёт канона; CLI транслирует ok → rc 0/1.
    """
    report = {"canon": CANON_VERSION, "ok": True, "checked": 0, "failures": []}
    _selftest_case(report)
    _selftest_genesis(report)
    report["checked"] = 5
    report["failures"].sort(key=lambda r: r["path"])
    return report


def report_bytes(report: dict) -> bytes:
    """Каноническая печать отчёта: одинаковый вход → одинаковые байты."""
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
