def get_currency(region: str) -> str:
    if region == "🇰🇬 КР":
        return "сом"
    elif region == "🇷🇺 РУ":
        return "₽"
    elif region == "🇰🇿 КЗ":
        return "₸"
    return ""