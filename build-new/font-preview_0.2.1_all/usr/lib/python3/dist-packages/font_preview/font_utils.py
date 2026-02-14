#!/usr/bin/env python3
# Font Preview - A better font viewer for Linux
# Copyright (C) 2025 Daniel Nylander <daniel@danielnylander.se>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Font utilities using fontconfig."""

import subprocess
import re
from dataclasses import dataclass, field
from typing import Optional

from fontTools.ttLib import TTFont


@dataclass
class FontInfo:
    """Information about a font."""

    family: str
    style: str
    path: str
    weight: str = ""
    slant: str = ""
    width: str = ""
    favorite: bool = False

    @property
    def display_name(self) -> str:
        if self.style and self.style.lower() != "regular":
            return f"{self.family} {self.style}"
        return self.family


# Unicode blocks for coverage analysis
UNICODE_BLOCKS = {
    "Basic Latin": (0x0020, 0x007F),
    "Latin-1 Supplement": (0x0080, 0x00FF),
    "Latin Extended-A": (0x0100, 0x017F),
    "Latin Extended-B": (0x0180, 0x024F),
    "Cyrillic": (0x0400, 0x04FF),
    "Greek and Coptic": (0x0370, 0x03FF),
    "Arabic": (0x0600, 0x06FF),
    "Devanagari": (0x0900, 0x097F),
    "CJK Unified Ideographs": (0x4E00, 0x9FFF),
    "Hiragana": (0x3040, 0x309F),
    "Katakana": (0x30A0, 0x30FF),
    "Hangul Syllables": (0xAC00, 0xD7AF),
    "Thai": (0x0E00, 0x0E7F),
    "Georgian": (0x10A0, 0x10FF),
    "Armenian": (0x0530, 0x058F),
    "Hebrew": (0x0590, 0x05FF),
    "Ethiopic": (0x1200, 0x137F),
    "Mathematical Operators": (0x2200, 0x22FF),
    "Box Drawing": (0x2500, 0x257F),
    "Currency Symbols": (0x20A0, 0x20CF),
    "General Punctuation": (0x2000, 0x206F),
    "Arrows": (0x2190, 0x21FF),
    "Dingbats": (0x2700, 0x27BF),
    "Emoticons": (0x1F600, 0x1F64F),
}

# Language-specific character sets for coverage testing
LANGUAGE_CHARS = {
    "Swedish": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÅåÄäÖö",
    "Norwegian": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÆæØøÅå",
    "Danish": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÆæØøÅå",
    "Finnish": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÅåÄäÖö",
    "German": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÄäÖöÜüß",
    "French": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZzÀàÂâÆæÇçÈèÉéÊêËëÎîÏïÔôŒœÙùÛûÜüŸÿ",
    "Spanish": "AaBbCcDdEeFfGgHhIiJjKkLlMmNnÑñOoPpQqRrSsTtUuVvWwXxYyZzÁáÉéÍíÓóÚúÜü¡¿",
    "Polish": "AaĄąBbCcĆćDdEeĘęFfGgHhIiJjKkLlŁłMmNnŃńOoÓóPpQqRrSsŚśTtUuVvWwXxYyZzŹźŻż",
    "Czech": "AaÁáBbCcČčDdĎďEeÉéĚěFfGgHhIiÍíJjKkLlMmNnŇňOoÓóPpQqRrŘřSsŠšTtŤťUuÚúŮůVvWwXxYyÝýZzŽž",
    "Russian": "АаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя",
    "Greek": "ΑαΒβΓγΔδΕεΖζΗηΘθΙιΚκΛλΜμΝνΞξΟοΠπΡρΣσςΤτΥυΦφΧχΨψΩω",
    "Japanese (Hiragana)": "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん",
    "Korean (Basic)": "가나다라마바사아자차카타파하",
    "Arabic": "ابتثجحخدذرزسشصضطظعغفقكلمنهوي",
    "Hebrew": "אבגדהוזחטיכלמנסעפצקרשת",
    "Thai": "กขฃคฅฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ",
    "Vietnamese": "AaĂăÂâBbCcDdĐđEeÊêGgHhIiKkLlMmNnOoÔôƠơPpQqRrSsTtUuƯưVvXxYy",
}


def get_installed_fonts() -> list[FontInfo]:
    """Get all installed fonts via fc-list."""
    try:
        result = subprocess.run(
            ["fc-list", "--format", "%{family}|%{style}|%{file}|%{weight}|%{slant}|%{width}\n"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    fonts = []
    seen = set()
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split("|")
        if len(parts) < 3:
            continue
        family = parts[0].split(",")[0].strip()
        style = parts[1].split(",")[0].strip() if len(parts) > 1 else ""
        path = parts[2].strip()
        weight = parts[3].strip() if len(parts) > 3 else ""
        slant = parts[4].strip() if len(parts) > 4 else ""
        width = parts[5].strip() if len(parts) > 5 else ""

        key = (family, style, path)
        if key in seen:
            continue
        seen.add(key)

        fonts.append(FontInfo(
            family=family,
            style=style,
            path=path,
            weight=weight,
            slant=slant,
            width=width,
        ))

    fonts.sort(key=lambda f: f.family.lower())
    return fonts


def get_font_coverage(font_path: str) -> set[int]:
    """Get the set of Unicode codepoints supported by a font."""
    try:
        tt = TTFont(font_path)
        cmap = tt.getBestCmap()
        if cmap:
            return set(cmap.keys())
    except Exception:
        pass
    return set()


def get_block_coverage(supported: set[int], block_start: int, block_end: int) -> float:
    """Get coverage percentage for a Unicode block."""
    total = block_end - block_start + 1
    if total == 0:
        return 0.0
    covered = sum(1 for cp in range(block_start, block_end + 1) if cp in supported)
    return covered / total * 100


def get_language_coverage(supported: set[int], language: str) -> tuple[float, list[str]]:
    """Check if a font covers all characters for a language.

    Returns (coverage_percent, list_of_missing_chars).
    """
    chars = LANGUAGE_CHARS.get(language, "")
    if not chars:
        return 0.0, []

    unique_chars = set(chars)
    missing = [ch for ch in unique_chars if ord(ch) not in supported]
    total = len(unique_chars)
    if total == 0:
        return 100.0, []
    coverage = (total - len(missing)) / total * 100
    return coverage, sorted(missing)
