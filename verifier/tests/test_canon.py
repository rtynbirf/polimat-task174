# -*- coding: utf-8 -*-
"""Юнит-приёмки канона kanon_verify (Волна ×4 · П45).

Запуск:  python3 -m unittest discover -s verifier/tests -v
Канон:   python3 -m unittest verifier.tests.test_canon -v
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from kanon_verify import (  # noqa: E402
    CANON_VERSION,
    GENESIS,
    parse_manifest,
    sha256_file,
    selftest,
    verify_files,
    verify_manifest,
)


class TestSha256File(unittest.TestCase):
    def test_known_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.txt")
            with open(p, "wb") as f:
                f.write(b"polymath")
            self.assertEqual(sha256_file(p),
                             "9a4a4b2e2b0d0fd0eb2b1e0e2e0f0a6e"[:0] +
                             __import__("hashlib").sha256(b"polymath").hexdigest())

    def test_streaming_equals_bulk(self):
        """Поточное чтение == разовое: пломба не зависит от размера куска."""
        import hashlib
        data = b"0123456789" * 100000  # ~1 МБ, гарантированно несколько кусков
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "big.bin")
            with open(p, "wb") as f:
                f.write(data)
            self.assertEqual(sha256_file(p), hashlib.sha256(data).hexdigest())


class TestParseManifest(unittest.TestCase):
    def test_basic_and_comments(self):
        h = "a" * 64
        rows = parse_manifest(f"# комментарий\n\n{h}  path/one.md\n{h.upper()}  two\n")
        self.assertEqual(rows, [("path/one.md", h), ("two", h)])

    def test_duplicate_path_raises(self):
        h = "b" * 64
        with self.assertRaises(ValueError):
            parse_manifest(f"{h}  a\n{h}  a\n")

    def test_bad_hash_raises(self):
        with self.assertRaises(ValueError):
            parse_manifest("xyz  a\n")

    def test_order_insensitive(self):
        """Порядок строк не влияет: сверяется множество путей, не стиль."""
        h = "c" * 64
        self.assertEqual(parse_manifest(f"{h}  a\n{h}  b\n"),
                         parse_manifest(f"{h}  b\n{h}  a\n"))


class TestVerifyManifest(unittest.TestCase):
    def test_ok_then_mutation_caught(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "doc.md")
            with open(p, "w", encoding="utf-8") as f:
                f.write("канон")
            h = sha256_file(p)
            ok = verify_manifest(td, f"{h}  doc.md\n")
            self.assertTrue(ok["ok"])
            self.assertEqual(ok["checked"], 1)
            with open(p, "a", encoding="utf-8") as f:
                f.write("!")  # silent mutation
            bad = verify_manifest(td, f"{h}  doc.md\n")
            self.assertFalse(bad["ok"])
            self.assertEqual(bad["failures"][0]["reason"], "MUTATED")

    def test_missing_file_is_failure(self):
        h = "d" * 64
        with tempfile.TemporaryDirectory() as td:
            r = verify_manifest(td, f"{h}  ghost.md\n")
            self.assertFalse(r["ok"])
            self.assertEqual(r["failures"][0]["reason"], "MISSING")

    def test_bad_manifest_is_structure_failure(self):
        with tempfile.TemporaryDirectory() as td:
            r = verify_manifest(td, "мусор без формы\n")
            self.assertFalse(r["ok"])
            self.assertTrue(r["failures"][0]["reason"].startswith("STRUCTURE"))

    def test_report_is_deterministic_bytes(self):
        """Двойная генерация отчёта идентична: одна правда, одни байты."""
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x")
            open(p, "wb").close()
            h = sha256_file(p)
            m = f"{h}  x\n"
            from kanon_verify.canon import report_bytes
            self.assertEqual(report_bytes(verify_manifest(td, m)),
                             report_bytes(verify_manifest(td, m)))


class TestVerifyFiles(unittest.TestCase):
    def test_b25_canon(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "KANON.md")
            with open(p, "wb") as f:
                f.write(b"v5.1.2")
            expect = {"KANON.md": sha256_file(p), "НЕТ.md": "e" * 64}
            r = verify_files(td, expect)
            self.assertFalse(r["ok"])
            reasons = {f["path"]: f["reason"] for f in r["failures"]}
            self.assertEqual(reasons, {"НЕТ.md": "MISSING"})


class TestSelftest(unittest.TestCase):
    def test_selftest_green(self):
        r = selftest()
        self.assertTrue(r["ok"], r["failures"])
        self.assertEqual(r["checked"], 5)

    def test_genesis_shape(self):
        self.assertEqual(GENESIS, "0" * 64)
        self.assertEqual(CANON_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
