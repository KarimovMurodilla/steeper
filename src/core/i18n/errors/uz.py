from src.core.errors.enums import ErrorCode

ERROR_TEXTS_UZ: dict[ErrorCode, str] = {
    # --- General / Server ---
    ErrorCode.INTERNAL_SERVER_ERROR: "Ichki server xatosi.",
    # --- Authentication & Authorization ---
    ErrorCode.AUTH_INVALID_CREDENTIALS: "Hisob ma'lumotlarini tekshirib bo'lmadi.",
    ErrorCode.AUTH_COULD_NOT_VALIDATE: "Hisob ma'lumotlarini tasdiqlab bo'lmadi.",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Token muddati tugagan.",
    ErrorCode.AUTH_TOKEN_INVALID: "Noto'g'ri token.",
    ErrorCode.AUTH_TOKEN_INVALID_STRUCTURE: "Noto'g'ri token tuzilishi.",
    ErrorCode.AUTH_TOKEN_NOT_FOUND: "Autentifikatsiya tokeni topilmadi.",
    ErrorCode.AUTH_INVALID_OR_EXPIRED_TOKEN: "Noto'g'ri yoki muddati tugagan token.",
    # --- User ---
    ErrorCode.USER_NOT_FOUND: "Foydalanuvchi topilmadi.",
    ErrorCode.USER_BLOCKED: "Foydalanuvchi bloklangan.",
    # --- General ---
    ErrorCode.GENERAL_NOT_FOUND: "Resurs topilmadi.",
    ErrorCode.GENERAL_DATE_FUTURE: "Kelajakdagi sanalar uchun ma'lumot olib bo'lmaydi.",
    # --- Infrastructure ---
    ErrorCode.SYSTEM_HEALTH_CHECK_FAILED: "Tizim holatini tekshirish muvaffaqiyatsiz tugadi.",
    # --- Workspace ---
    ErrorCode.WORKSPACE_NOT_FOUND: "Ishchi maydoni topilmadi.",
    ErrorCode.WORKSPACE_ACCESS_DENIED: "Ishchi maydoni topilmadi yoki kirish taqiqlangan.",
    ErrorCode.WORKSPACE_NOT_OWNER: "Foydalanuvchi ishchi maydonining egasi emas.",
    ErrorCode.WORKSPACE_ALREADY_MEMBER: "Foydalanuvchi allaqachon ushbu ishchi maydonining a'zosi.",
    ErrorCode.WORKSPACE_MEMBER_NOT_FOUND: "Foydalanuvchi ishchi maydoni a'zosi emas.",
    # --- Bot ---
    ErrorCode.BOT_NOT_FOUND: "Bot topilmadi.",
    ErrorCode.BOT_UPDATE_FAILED: "Telegram orqali bot ma'lumotlarini yangilab bo'lmadi.",
    ErrorCode.BOT_REGISTRATION_FAILED: "Telegram'da botni ro'yxatdan o'tkazib bo'lmadi.",
    ErrorCode.BOT_ADMIN_ALREADY_EXISTS: "Foydalanuvchi allaqachon ushbu botning admini.",
    # --- Marketing ---
    ErrorCode.BROADCAST_NOT_FOUND: "Xabar tarqatish topilmadi.",
    ErrorCode.BROADCAST_ALREADY_LAUNCHED: "Xabar tarqatish allaqachon boshlangan.",
    ErrorCode.CAMPAIGN_NOT_FOUND: "Kampaniya topilmadi.",
    # --- Communication ---
    ErrorCode.CHAT_NOT_FOUND: "Chat topilmadi.",
    ErrorCode.MESSAGE_SEND_FAILED: "Xabar yuborish muvaffaqiyatsiz tugadi.",
    # --- Auth Additional ---
    ErrorCode.AUTH_NOT_AUTHENTICATED: "Autentifikatsiyadan o'tilmagan.",
    ErrorCode.AUTH_ACCESS_FORBIDDEN: "Kirish taqiqlangan.",
    ErrorCode.AUTH_PERMISSION_DENIED: "Foydalanuvchida kerakli ruxsatlar yo'q.",
    ErrorCode.AUTH_REFRESH_TOKEN_NOT_OWNED: "Yangilanish (refresh) tokeni foydalanuvchiga tegishli emas.",
    ErrorCode.AUTH_TOKEN_POTENTIAL_REUSE: "Token mumkin bo'lgan qayta foydalanish tufayli bekor qilindi.",
    ErrorCode.AUTH_TOKEN_REUSE_DETECTED: "Tokendan qayta foydalanish aniqlandi. Barcha seanslar bekor qilindi.",
    ErrorCode.AUTH_TELEGRAM_HASH_MISMATCH: "Telegram autentifikatsiya xeshi mos kelmadi.",
    ErrorCode.AUTH_TELEGRAM_DATA_OUTDATED: "Telegram autentifikatsiya ma'lumotlari eskirgan.",
    ErrorCode.AUTH_TELEGRAM_USER_NOT_FOUND: "Ma'lumotlarda Telegram foydalanuvchisi topilmadi.",
    ErrorCode.AUTH_TELEGRAM_DATA_REQUIRED: "Telegram autentifikatsiya ma'lumotlari talab qilinadi.",
}
