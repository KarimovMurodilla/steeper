from src.core.errors.enums import ErrorCode

ERROR_TEXTS_RU: dict[ErrorCode, str] = {
    # --- General / Server ---
    ErrorCode.INTERNAL_SERVER_ERROR: "Внутренняя ошибка сервера.",
    # --- Authentication & Authorization ---
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Не удалось проверить учетные данные.",
    ErrorCode.AUTH_COULD_NOT_VALIDATE: "Не удалось подтвердить учетные данные.",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Срок действия токена истёк.",
    ErrorCode.AUTH_TOKEN_INVALID: "Недействительный токен.",
    ErrorCode.AUTH_TOKEN_INVALID_STRUCTURE: "Неверная структура токена.",
    ErrorCode.AUTH_TOKEN_NOT_FOUND: "Токен аутентификации не найден.",
    ErrorCode.AUTH_INVALID_OR_EXPIRED_TOKEN: "Недействительный или просроченный токен.",
    # --- User ---
    ErrorCode.USER_NOT_FOUND: "Пользователь не найден.",
    ErrorCode.USER_BLOCKED: "Пользователь заблокирован.",
    # --- General ---
    ErrorCode.GENERAL_NOT_FOUND: "Ресурс не найден.",
    ErrorCode.GENERAL_DATE_FUTURE: "Невозможно получить информацию для будущих дат.",
    # --- Infrastructure ---
    ErrorCode.SYSTEM_HEALTH_CHECK_FAILED: "Ошибка проверки работоспособности системы.",
    # --- Workspace ---
    ErrorCode.WORKSPACE_NOT_FOUND: "Рабочее пространство не найдено.",
    ErrorCode.WORKSPACE_ACCESS_DENIED: "Рабочее пространство не найдено или доступ запрещен.",
    ErrorCode.WORKSPACE_NOT_OWNER: "Пользователь не является владельцем рабочего пространства.",
    ErrorCode.WORKSPACE_ALREADY_MEMBER: "Пользователь уже является участником этого рабочего пространства.",
    ErrorCode.WORKSPACE_MEMBER_NOT_FOUND: "Пользователь не является участником рабочего пространства.",
    # --- Bot ---
    ErrorCode.BOT_NOT_FOUND: "Бот не найден.",
    ErrorCode.BOT_UPDATE_FAILED: "Не удалось обновить информацию о боте в Telegram.",
    ErrorCode.BOT_REGISTRATION_FAILED: "Не удалось зарегистрировать бота в Telegram.",
    ErrorCode.BOT_ADMIN_ALREADY_EXISTS: "Пользователь уже является администратором этого бота.",
    # --- Marketing ---
    ErrorCode.BROADCAST_NOT_FOUND: "Рассылка не найдена.",
    ErrorCode.BROADCAST_ALREADY_LAUNCHED: "Рассылка уже запущена.",
    ErrorCode.CAMPAIGN_NOT_FOUND: "Кампания не найдена.",
    # --- Communication ---
    ErrorCode.CHAT_NOT_FOUND: "Чат не найден.",
    ErrorCode.MESSAGE_SEND_FAILED: "Не удалось отправить сообщение.",
    # --- Auth Additional ---
    ErrorCode.AUTH_NOT_AUTHENTICATED: "Не аутентифицирован.",
    ErrorCode.AUTH_ACCESS_FORBIDDEN: "Доступ запрещен.",
    ErrorCode.AUTH_PERMISSION_DENIED: "У пользователя нет необходимых разрешений.",
    ErrorCode.AUTH_REFRESH_TOKEN_NOT_OWNED: "Refresh токен не принадлежит пользователю.",
    ErrorCode.AUTH_TOKEN_POTENTIAL_REUSE: "Токен был аннулирован из-за потенциального повторного использования.",
    ErrorCode.AUTH_TOKEN_REUSE_DETECTED: "Обнаружено повторное использование токена. Все сессии аннулированы.",
    ErrorCode.AUTH_TELEGRAM_HASH_MISMATCH: "Несоответствие хэша аутентификации Telegram.",
    ErrorCode.AUTH_TELEGRAM_DATA_OUTDATED: "Данные аутентификации Telegram устарели.",
    ErrorCode.AUTH_TELEGRAM_USER_NOT_FOUND: "Пользователь Telegram не найден в данных.",
    ErrorCode.AUTH_TELEGRAM_DATA_REQUIRED: "Требуются данные аутентификации Telegram.",
}
