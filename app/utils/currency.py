REGION_TO_CODE = {
    "🇰🇬 КР": "KGS",
    "🇷🇺 РУ": "RUB",
    "🇰🇿 КЗ": "KZT",
}


def get_currency(region: str) -> str:
    if region == "🇰🇬 КР":
        return "сом"
    elif region == "🇷🇺 РУ":
        return "₽"
    elif region == "🇰🇿 КЗ":
        return "₸"
    return ""


def get_active_balance(user):
    if user.region == "🇰🇬 КР":
        return user.balance_kg, user.bonus_kg, "сом"
    elif user.region == "🇷🇺 РУ":
        return user.balance_ru, user.bonus_ru, "₽"
    elif user.region == "🇰🇿 КЗ":
        return user.balance_kz, user.bonus_kz, "₸"
    return 0, 0, ""

def get_currency_info(currency_code: str) -> dict:
    """Получает информацию о валюте по коду"""
    currency_map = {
        "kg": {"name": "сом (КР)", "symbol": "сом", "flag": "🇰🇬"},
        "kz": {"name": "тенге (КЗ)", "symbol": "₸", "flag": "🇰🇿"},
        "ru": {"name": "рубли (РУ)", "symbol": "₽", "flag": "🇷🇺"}
    }
    return currency_map.get(currency_code, {"name": "неизвестная валюта", "symbol": "", "flag": "❓"})