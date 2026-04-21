CREATE TABLE seasons (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,     -- spring, summer, autumn, winter
    name_ru TEXT NOT NULL
);

CREATE TABLE regions (
    code TEXT PRIMARY KEY,         -- LV, RU, EU_NORTH ...
    name_ru TEXT NOT NULL,
    climate_zone TEXT
);