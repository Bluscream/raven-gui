"""Icons read from program resources."""

from __future__ import annotations

import struct
from pathlib import Path

from raven_gui.core.icons import extract_icon, icon_from_group

FIXTURES = Path(__file__).parent / "fixtures" / "icon-program"


def _ico_entries(ico: bytes) -> list[tuple[int, bytes]]:
    """Return each image's width and data, read the way an .ico reader does."""
    _reserved, kind, count = struct.unpack_from("<HHH", ico)
    assert kind == 1
    entries = []
    for index in range(count):
        width, _h, _c, _r, _p, _b, size, offset = struct.unpack_from("<BBBBHHII", ico, 6 + index * 16)
        entries.append((width, ico[offset : offset + size]))
    return entries


def test_extract_icon_rebuilds_the_original_file() -> None:
    # The fixture was linked from icon.ico; reassembled from the resources, the images must come back unchanged.
    extracted = extract_icon(FIXTURES / "icon-program.exe")
    assert extracted is not None
    original = (FIXTURES / "icon.ico").read_bytes()
    assert _ico_entries(extracted) == _ico_entries(original)
    assert [width for width, _ in _ico_entries(extracted)] == [16, 48]


def test_extract_icon_from_a_non_program(tmp_path: Path) -> None:
    text = tmp_path / "readme.exe"
    text.write_text("not a program", encoding="utf-8")
    assert extract_icon(text) is None
    assert extract_icon(tmp_path / "missing.exe") is None


def test_icon_from_group_skips_images_it_does_not_have() -> None:
    group = struct.pack("<HHH", 0, 1, 2)
    group += struct.pack("<BBBBHHIH", 16, 16, 0, 0, 1, 32, 3, 1)
    group += struct.pack("<BBBBHHIH", 32, 32, 0, 0, 1, 32, 3, 2)
    ico = icon_from_group(group, {2: b"abc"})
    assert ico is not None
    assert _ico_entries(ico) == [(32, b"abc")]


def test_icon_from_group_with_nothing_usable() -> None:
    assert icon_from_group(b"\x00", {}) is None
    assert (
        icon_from_group(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHIH", 16, 16, 0, 0, 1, 32, 3, 9), {}) is None
    )
