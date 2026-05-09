CREATE TABLE ingredients (
    id BIGSERIAL PRIMARY KEY,
    canonical_name TEXT UNIQUE NOT NULL,
    display_name_ru TEXT,
    category TEXT,
    usda_fdc_id BIGINT,
    calories_per_100g NUMERIC(8,2),
    protein_per_100g NUMERIC(8,2),
    fat_per_100g NUMERIC(8,2),
    carbs_per_100g NUMERIC(8,2),
    price_per_100g_rub NUMERIC(8,2),
    price_source TEXT,
    price_updated_at DATE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);
