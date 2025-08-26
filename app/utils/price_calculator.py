from app.config import REGION_CURRENCIES, RANKS
from app.utils.settings import SettingsManager

async def get_mythic_price(stars, region):
    """Возвращает цену за звезду в зависимости от количества звезд"""
    rank_prices = await SettingsManager.get_setting("RANK_PRICES")
    
    if stars <= 25:
        return rank_prices[region]["Мифик0-25"]
    elif stars <= 50:
        return rank_prices[region]["Мифик25-50"]
    elif stars <= 100:
        return rank_prices[region]["Мифик50-100"]
    else:
        return rank_prices[region]["Мифик100+"]

def get_rank_type(rank):
    """Определяет тип ранга для расчета цены"""
    if "Воин" in rank:
        return "Воин"
    elif "Элита" in rank:
        return "Элита"
    elif "Мастер" in rank:
        return "Мастер"
    elif "Грандмастер" in rank:
        return "Грандмастер"
    elif "Эпик" in rank:
        return "Эпик"
    elif "Легенда" in rank:
        return "Легенда"
    elif "Мифик" in rank:
        return "Мифик"
    else:
        return "Воин"

async def calculate_regular_rank_cost(current_rank, target_rank, region):
    """Рассчитывает стоимость буста обычных рангов"""
    rank_prices = await SettingsManager.get_setting("RANK_PRICES")
    current_index = RANKS.index(current_rank)
    target_index = RANKS.index(target_rank)
    
    total_cost = 0
    
    # ✅ ИСПРАВЛЕНО: считаем переходы между рангами, а не умножаем на звезды
    for i in range(current_index, target_index):
        rank = RANKS[i + 1]  # Следующий ранг
        rank_type = get_rank_type(rank)
        price_per_rank = rank_prices[region][rank_type]
        total_cost += price_per_rank
    
    return total_cost

async def calculate_mythic_cost(current_stars, target_stars, region):
    """Рассчитывает стоимость буста Мифик звезд с учетом ценовых диапазонов"""
    rank_prices = await SettingsManager.get_setting("RANK_PRICES")
    total_cost = 0
    
    for star in range(current_stars + 1, target_stars + 1):
        if star <= 25:
            price = rank_prices[region]["Мифик0-25"]
        elif star <= 50:
            price = rank_prices[region]["Мифик25-50"]
        elif star <= 100:
            price = rank_prices[region]["Мифик50-100"]
        else:
            price = rank_prices[region]["Мифик100+"]
        
        total_cost += price
    
    return total_cost

async def calculate_total_order_cost(base_cost, boost_type, region):
    """Рассчитывает финальную стоимость заказа с множителями"""
    boost_multipliers = await SettingsManager.get_setting("BOOST_MULTIPLIERS")
    multiplier = boost_multipliers.get(boost_type, 1.0)
    total_cost = base_cost * multiplier
    currency = REGION_CURRENCIES[region]
    
    return total_cost, currency