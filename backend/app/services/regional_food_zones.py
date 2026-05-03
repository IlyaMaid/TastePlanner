from __future__ import annotations


REGIONAL_FOOD_ZONES = {
    "RU-NORTHWEST": {
        "name_ru": "Северо-Западная рыбно-молочная зона",
        "summary_ru": "Рыба, молочные продукты, картофель, капуста, ягоды и грибы.",
        "products_ru": ["рыба", "молоко", "картофель", "капуста", "ягоды", "грибы"],
    },
    "RU-CENTRAL": {
        "name_ru": "Центральная смешанная зона",
        "summary_ru": "Крупы, овощи, молочные продукты, птица, яйца и сезонные фрукты.",
        "products_ru": ["гречка", "овощи", "молоко", "курица", "яйца", "яблоки"],
    },
    "RU-SOUTH": {
        "name_ru": "Южная овощно-зерновая зона",
        "summary_ru": "Овощи, фрукты, бахчевые, зерновые, подсолнечное масло и рыба.",
        "products_ru": ["помидоры", "перец", "фрукты", "рис", "пшеница", "подсолнечное масло"],
    },
    "RU-NORTH-CAUCASUS": {
        "name_ru": "Северо-Кавказская садово-молочная зона",
        "summary_ru": "Молочные продукты, баранина, зелень, овощи, фрукты, орехи и фасоль.",
        "products_ru": ["сыр", "кефир", "зелень", "овощи", "фасоль", "орехи"],
    },
    "RU-VOLGA": {
        "name_ru": "Поволжская зерно-молочная зона",
        "summary_ru": "Молоко, говядина, крупы, бобовые, картофель и овощи.",
        "products_ru": ["молоко", "говядина", "гречка", "фасоль", "картофель", "овощи"],
    },
    "RU-URAL": {
        "name_ru": "Уральская мясо-крупяная зона",
        "summary_ru": "Мясо, птица, крупы, картофель, корнеплоды, грибы и ягоды.",
        "products_ru": ["говядина", "курица", "крупы", "картофель", "морковь", "грибы"],
    },
    "RU-SIBERIA": {
        "name_ru": "Сибирская мясо-молочная зона",
        "summary_ru": "Мясо, молочные продукты, крупы, картофель, рыба, ягоды и грибы.",
        "products_ru": ["говядина", "молоко", "овсянка", "картофель", "рыба", "ягоды"],
    },
    "RU-FAR-EAST": {
        "name_ru": "Дальневосточная рыбно-таежная зона",
        "summary_ru": "Рыба, морепродукты, рис, соя, грибы, ягоды и овощи.",
        "products_ru": ["рыба", "морепродукты", "рис", "соя", "грибы", "ягоды"],
    },
}


REGION_TO_FOOD_ZONE = {
    "RU-MOW": "RU-CENTRAL",
    "RU-MOS": "RU-CENTRAL",
    "RU-CFO": "RU-CENTRAL",
    "RU-SPE": "RU-NORTHWEST",
    "RU-NWFO": "RU-NORTHWEST",
    "RU-KDA": "RU-SOUTH",
    "RU-SFO-SOUTH": "RU-SOUTH",
    "RU-NCFO": "RU-NORTH-CAUCASUS",
    "RU-TA": "RU-VOLGA",
    "RU-PFO": "RU-VOLGA",
    "RU-SVE": "RU-URAL",
    "RU-UFO": "RU-URAL",
    "RU-NVS": "RU-SIBERIA",
    "RU-SFO": "RU-SIBERIA",
    "RU-DFO": "RU-FAR-EAST",
}


def get_region_food_zone(region_code: str | None) -> dict | None:
    if not region_code:
        return None

    zone_code = REGION_TO_FOOD_ZONE.get(region_code)
    if not zone_code:
        return None

    zone = REGIONAL_FOOD_ZONES.get(zone_code)
    if not zone:
        return None

    return {
        "code": zone_code,
        **zone,
    }
