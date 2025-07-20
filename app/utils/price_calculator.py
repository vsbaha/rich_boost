from app.config import RANK_PRICES, BOOST_MULTIPLIERS, COACHING_PRICES, REGION_CURRENCIES, RANKS

def get_mythic_price(stars, region):
    """Возвращает цену за звезду в зависимости от количества звезд"""
    if stars <= 25:
        return RANK_PRICES[region]["Мифик0-25"]  # ✅ ИСПРАВЛЕНО
    elif stars <= 50:
        return RANK_PRICES[region]["Мифик25-50"]  # ✅ ИСПРАВЛЕНО
    elif stars <= 100:
        return RANK_PRICES[region]["Мифик50-100"]  # ✅ ИСПРАВЛЕНО
    else:
        return RANK_PRICES[region]["Мифик100+"]  # ✅ ИСПРАВЛЕНО

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

def calculate_regular_rank_cost(current_rank, target_rank, region):
    """Рассчитывает стоимость буста обычных рангов"""
    current_index = RANKS.index(current_rank)
    target_index = RANKS.index(target_rank)
    
    total_cost = 0
    
    # ✅ ИСПРАВЛЕНО: считаем переходы между рангами, а не умножаем на звезды
    for i in range(current_index, target_index):
        rank = RANKS[i + 1]  # Следующий ранг
        rank_type = get_rank_type(rank)
        price_per_rank = RANK_PRICES[region][rank_type]
        total_cost += price_per_rank
    
    return total_cost

def calculate_mythic_cost(current_stars, target_stars, region):
    """Рассчитывает стоимость буста Мифик звезд с учетом ценовых диапазонов"""
    total_cost = 0
    
    for star in range(current_stars + 1, target_stars + 1):
        if star <= 25:
            price = RANK_PRICES[region]["Мифик0-25"]
        elif star <= 50:
            price = RANK_PRICES[region]["Мифик25-50"]
        elif star <= 100:
            price = RANK_PRICES[region]["Мифик50-100"]
        else:
            price = RANK_PRICES[region]["Мифик100+"]
        
        total_cost += price
    
    return total_cost

def calculate_total_order_cost(base_cost, boost_type, region):
    """Рассчитывает финальную стоимость заказа с множителями"""
    multiplier = BOOST_MULTIPLIERS.get(boost_type, 1.0)
    total_cost = base_cost * multiplier
    currency = REGION_CURRENCIES[region]
    
    return total_cost, currency