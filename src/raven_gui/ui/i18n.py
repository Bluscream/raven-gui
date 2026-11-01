"""The KI18n functions Kirigami Addons calls from QML, for an app that cannot load KLocalizedContext from Python."""

from __future__ import annotations

import re

from PySide6.QtCore import QObject, Slot

_PLACEHOLDER = re.compile(r"%(\d+)")


def substitute(text: str, *arguments: object) -> str:
    """Fill in %1, %2 and so on, as KI18n does; untranslated, since this app ships no translations."""

    def value(match: re.Match[str]) -> str:
        index = int(match[1]) - 1
        return str(arguments[index]) if 0 <= index < len(arguments) else match[0]

    return _PLACEHOLDER.sub(value, text)


def _plural(singular: str, plural: str, count: object, *arguments: object) -> str:
    chosen = singular if count == 1 else plural
    return substitute(chosen.replace("%n", str(count)), count, *arguments)


class I18nContext(QObject):
    """Set as the root context object, so i18n(), i18nc() and their kin resolve in every QML file."""

    @Slot(str, result=str)
    @Slot(str, "QVariant", result=str)
    @Slot(str, "QVariant", "QVariant", result=str)
    def i18n(self, text: str, *arguments: object) -> str:
        """Return text with its arguments filled in."""
        return substitute(text, *arguments)

    @Slot(str, str, result=str)
    @Slot(str, str, "QVariant", result=str)
    @Slot(str, str, "QVariant", "QVariant", result=str)
    def i18nc(self, _context: str, text: str, *arguments: object) -> str:
        """Return text with its arguments filled in; the translator's context is not needed untranslated."""
        return substitute(text, *arguments)

    @Slot(str, str, result=str)
    @Slot(str, str, "QVariant", result=str)
    @Slot(str, str, "QVariant", "QVariant", result=str)
    def i18nd(self, _domain: str, text: str, *arguments: object) -> str:
        """Return text from a translation domain with its arguments filled in."""
        return substitute(text, *arguments)

    @Slot(str, str, str, result=str)
    @Slot(str, str, str, "QVariant", result=str)
    @Slot(str, str, str, "QVariant", "QVariant", result=str)
    def i18ndc(self, _domain: str, _context: str, text: str, *arguments: object) -> str:
        """Return text from a translation domain, with a context, with its arguments filled in."""
        return substitute(text, *arguments)

    @Slot(str, str, "QVariant", result=str)
    @Slot(str, str, "QVariant", "QVariant", result=str)
    def i18np(self, singular: str, plural: str, count: object, *arguments: object) -> str:
        """Return the singular or plural text for a count."""
        return _plural(singular, plural, count, *arguments)

    @Slot(str, str, str, "QVariant", result=str)
    @Slot(str, str, str, "QVariant", "QVariant", result=str)
    def i18ncp(self, _context: str, singular: str, plural: str, count: object, *arguments: object) -> str:
        """Return the singular or plural text for a count, with a context."""
        return _plural(singular, plural, count, *arguments)

    @Slot(str, str, str, "QVariant", result=str)
    @Slot(str, str, str, "QVariant", "QVariant", result=str)
    def i18ndp(self, _domain: str, singular: str, plural: str, count: object, *arguments: object) -> str:
        """Return the singular or plural text for a count, from a translation domain."""
        return _plural(singular, plural, count, *arguments)

    @Slot(str, str, str, str, "QVariant", result=str)
    @Slot(str, str, str, str, "QVariant", "QVariant", result=str)
    def i18ndcp(
        self, _domain: str, _context: str, singular: str, plural: str, count: object, *arguments: object
    ) -> str:
        """Return the singular or plural text for a count, from a translation domain, with a context."""
        return _plural(singular, plural, count, *arguments)
