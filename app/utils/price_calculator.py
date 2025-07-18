from app.config import RANK_PRICES, BOOST_MULTIPLIERS, COACHING_PRICES, REGION_CURRENCIES, RANKS

def get_mythic_price(stars, region):
    """Возвращает цену за звезду в зависимости от количества звезд"""
    if stars <= 25:
        return RANK_PRICES[region]["Mythic0-25"]
    elif stars <= 50:
        return RANK_PRICES[region]["Mythic25-50"]
    elif stars <= 100:
        return RANK_PRICES[region]["Mythic50-100"]
    else:
        return RANK_PRICES[region]["Mythic100+"]

def get_rank_type(rank):
    """Определяет тип ранга для расчета цены"""
    # Извлекаем основной ранг из полного названия
    if "Воин" in rank:
        return "Воин"
    elif "Элита" in rank:
        return "Элита"
    elif "Мастер" in rank:
        return "Мастер"
    elif "Грандмастер" in rank:  # Исправляем
        return "Грандмастер"
    elif "Эпик" in rank:
        return "Эпик"
    elif "Легенда" in rank:
        return "Легенда"
    elif "Мифик" in rank:
        return "Мифик"
    else:
        return "Воин"  # По умолчанию

def calculate_regular_rank_cost(current_rank, target_rank, region):
    """Рассчитывает стоимость буста обычных рангов"""
    current_index = RANKS.index(current_rank)
    target_index = RANKS.index(target_rank)
    
    total_cost = 0
    
    # Проходим по всем рангам от текущего до желаемого
    for i in range(current_index, target_index):
        rank = RANKS[i]
        rank_type = get_rank_type(rank)
        
        # Получаем цену за звезду для данного ранга
        price_per_star = RANK_PRICES[region][rank_type]
        
        # Для каждого ранга считаем количество звезд
        if "I" in rank:
            stars = 1
        elif "II" in rank:
            stars = 2
        elif "III" in rank:
            stars = 3
        elif "IV" in rank:
            stars = 4
        elif "V" in rank:
            stars = 5
        else:
            stars = 1  # Для рангов без градации
        
        total_cost += price_per_star * stars
    
    return total_cost

def calculate_mythic_cost(current_stars, target_stars, region):
    """Рассчитывает стоимость буста Мифик звезд"""
    stars_diff = target_stars - current_stars
    
    # Определяем цену за звезду в зависимости от диапазона
    if target_stars <= 25:
        price_per_star = RANK_PRICES[region]["Мифик0-25"]
    elif target_stars <= 50:
        price_per_star = RANK_PRICES[region]["Мифик25-50"]
    elif target_stars <= 100:
        price_per_star = RANK_PRICES[region]["Мифик50-100"]
    else:
        price_per_star = RANK_PRICES[region]["Мифик100+"]
    
    return stars_diff * price_per_star

def calculate_total_order_cost(base_cost, boost_type, region):
    """Рассчитывает финальную стоимость заказа с множителями"""
    multiplier = BOOST_MULTIPLIERS.get(boost_type, 1.0)
    total_cost = base_cost * multiplier
    currency = REGION_CURRENCIES[region]
    
    return total_cost, currency