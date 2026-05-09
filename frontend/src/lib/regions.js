export const FOOD_ZONES = {
  "RU-CENTRAL": {
    name: "Центральная смешанная зона",
    products: ["гречка", "овощи", "молоко", "курица", "яйца", "яблоки"],
  },
  "RU-NORTHWEST": {
    name: "Северо-Западная рыбно-молочная зона",
    products: ["рыба", "молоко", "картофель", "капуста", "ягоды", "грибы"],
  },
  "RU-SOUTH": {
    name: "Южная овощно-зерновая зона",
    products: ["помидоры", "перец", "фрукты", "рис", "пшеница", "подсолнечное масло"],
  },
  "RU-NORTH-CAUCASUS": {
    name: "Северо-Кавказская садово-молочная зона",
    products: ["сыр", "кефир", "зелень", "овощи", "фасоль", "орехи"],
  },
  "RU-VOLGA": {
    name: "Поволжская зерно-молочная зона",
    products: ["молоко", "говядина", "гречка", "фасоль", "картофель", "овощи"],
  },
  "RU-URAL": {
    name: "Уральская мясо-крупяная зона",
    products: ["говядина", "курица", "крупы", "картофель", "морковь", "грибы"],
  },
  "RU-SIBERIA": {
    name: "Сибирская мясо-молочная зона",
    products: ["говядина", "молоко", "овсянка", "картофель", "рыба", "ягоды"],
  },
  "RU-FAR-EAST": {
    name: "Дальневосточная рыбно-таежная зона",
    products: ["рыба", "морепродукты", "рис", "соя", "грибы", "ягоды"],
  },
};

export const REGION_GROUPS = [
  {
    label: "Центральная зона",
    options: [
      { label: "Москва", value: "RU-MOW", zone: "RU-CENTRAL" },
      { label: "Московская область", value: "RU-MOS", zone: "RU-CENTRAL" },
      { label: "Центральный федеральный округ", value: "RU-CFO", zone: "RU-CENTRAL" },
    ],
  },
  {
    label: "Северо-Запад",
    options: [
      { label: "Санкт-Петербург", value: "RU-SPE", zone: "RU-NORTHWEST" },
      { label: "Северо-Западный федеральный округ", value: "RU-NWFO", zone: "RU-NORTHWEST" },
    ],
  },
  {
    label: "Юг России",
    options: [
      { label: "Краснодарский край", value: "RU-KDA", zone: "RU-SOUTH" },
      { label: "Южный федеральный округ", value: "RU-SFO-SOUTH", zone: "RU-SOUTH" },
    ],
  },
  {
    label: "Северный Кавказ",
    options: [
      { label: "Северо-Кавказский федеральный округ", value: "RU-NCFO", zone: "RU-NORTH-CAUCASUS" },
    ],
  },
  {
    label: "Поволжье",
    options: [
      { label: "Республика Татарстан", value: "RU-TA", zone: "RU-VOLGA" },
      { label: "Приволжский федеральный округ", value: "RU-PFO", zone: "RU-VOLGA" },
    ],
  },
  {
    label: "Урал",
    options: [
      { label: "Свердловская область", value: "RU-SVE", zone: "RU-URAL" },
      { label: "Уральский федеральный округ", value: "RU-UFO", zone: "RU-URAL" },
    ],
  },
  {
    label: "Сибирь",
    options: [
      { label: "Новосибирская область", value: "RU-NVS", zone: "RU-SIBERIA" },
      { label: "Сибирский федеральный округ", value: "RU-SFO", zone: "RU-SIBERIA" },
    ],
  },
  {
    label: "Дальний Восток",
    options: [
      { label: "Дальневосточный федеральный округ", value: "RU-DFO", zone: "RU-FAR-EAST" },
    ],
  },
];

export const REGION_OPTIONS = REGION_GROUPS.flatMap((group) => group.options);

export function formatRegion(value) {
  if (!value) {
    return "Не выбран";
  }

  return REGION_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

export function getFoodZoneByRegion(value) {
  const zoneCode = REGION_OPTIONS.find((option) => option.value === value)?.zone;
  return zoneCode ? { code: zoneCode, ...FOOD_ZONES[zoneCode] } : null;
}
