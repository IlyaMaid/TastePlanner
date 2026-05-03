ALTER TABLE ingredients
    ADD COLUMN IF NOT EXISTS display_name_ru TEXT,
    ADD COLUMN IF NOT EXISTS price_per_100g_rub NUMERIC(8,2),
    ADD COLUMN IF NOT EXISTS price_source TEXT,
    ADD COLUMN IF NOT EXISTS price_updated_at DATE;
