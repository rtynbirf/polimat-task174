# -*- coding: utf-8 -*-
"""kanon_verify — верификатор канона ПОЛИМАТ как библиотека (Волна ×4 · П45).

Извлечён из scripts/verify_b25_final.py (прогон Б25.8) в импортируемый
пакет: hub-воркфлоу и клетки роя потребляют ОДИН канон проверок —
одна правда на всех. Инструмент = договор.

Инвариант протокола (README канона): «проверяй строкой, не смыслом».
Вердикты однословные: [В] проверено / [О] частично / [Н] непроверяемо.

Публичный канон (экспорт):
    sha256_file        — пломба файла строкой (sha256 hexdigest)
    parse_manifest     — манифест «<sha256>  <путь>» → список (путь, ожидание)
    verify_manifest    — сверка дерева по манифесту → отчёт (машиночитаемый)
    verify_files       — сверка словаря {имя: ожидаемый_sha256} (канон Б25)
    selftest           — самоиспытание канона (rc 0/1), вызывается CLI
CANON_VERSION — версия канона проверок (растёт только дельтой).
"""
from .canon import (
    CANON_VERSION,
    GENESIS,
    parse_manifest,
    sha256_file,
    selftest,
    verify_files,
    verify_manifest,
)

__all__ = [
    "CANON_VERSION",
    "GENESIS",
    "parse_manifest",
    "sha256_file",
    "selftest",
    "verify_files",
    "verify_manifest",
]
__version__ = "1.0.0"
