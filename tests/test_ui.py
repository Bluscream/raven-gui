"""The Qt helpers that need no window: icon conversion and the KI18n stand-ins."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage

from raven_gui.core.icons import extract_icon
from raven_gui.ui.backend import _png_from_ico
from raven_gui.ui.i18n import I18nContext, substitute

FIXTURE = Path(__file__).parent / "fixtures" / "icon-program" / "icon-program.exe"


def test_largest_icon_image_is_saved_as_png(tmp_path: Path) -> None:
    # Regression: QImage.save with a bytes format passed mypy but raised at runtime, so no icon was ever saved.
    ico = extract_icon(FIXTURE)
    assert ico is not None
    image = _png_from_ico(ico)
    assert image is not None
    assert image.width() == 48
    target = tmp_path / "icon.png"
    assert image.save(str(target))
    assert target.read_bytes().startswith(b"\x89PNG")
    assert QImage(str(target)).width() == 48


def test_substitute_fills_numbered_placeholders() -> None:
    assert substitute("%1 of %2", 3, 7) == "3 of 7"
    assert substitute("100%", 1) == "100%"
    assert substitute("%3 missing", 1) == "%3 missing"


def test_i18n_context_answers_what_kirigami_addons_calls() -> None:
    # Regression: Kirigami Addons' form fields call i18nc and i18ndc, which only KLocalizedContext provided.
    context = I18nContext()
    assert context.i18n("Hello %1", "you") == "Hello you"
    assert context.i18nc("@info", "Clear %1", "text") == "Clear text"
    assert context.i18ndc("kirigami-addons6", "@action", "Show password") == "Show password"
    assert context.i18np("%n file", "%n files", 1) == "1 file"
    assert context.i18ncp("@info", "%n file", "%n files", 4) == "4 files"
