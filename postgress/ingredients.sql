CREATE TABLE ingredients (
    id BIGSERIAL PRIMARY KEY,
    canonical_name TEXT UNIQUE NOT NULL,
    category TEXT,
    usda_fdc_id BIGINT,
    calories_per_100g NUMERIC(8,2),
    protein_per_100g NUMERIC(8,2),
    fat_per_100g NUMERIC(8,2),
    carbs_per_100g NUMERIC(8,2),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);