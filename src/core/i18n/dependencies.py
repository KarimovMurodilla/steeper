from fastapi import Header

from src.core.i18n.enums import LanguageType
from src.core.i18n.utils import parse_language


async def get_language(
    accept_language: str | None = Header(default=None, alias="Accept-Language"),
) -> LanguageType:
    return parse_language(accept_language)
