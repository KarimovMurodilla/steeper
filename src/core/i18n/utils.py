from src.core.i18n.enums import LanguageType


def parse_language(value: str | None) -> LanguageType:
    if not value:
        return LanguageType.RU

    language = value.split(",")[0].split("-")[0].lower()

    try:
        return LanguageType(language)
    except ValueError:
        return LanguageType.RU
