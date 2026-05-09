ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS translated_title TEXT,
    ADD COLUMN IF NOT EXISTS translated_description TEXT,
    ADD COLUMN IF NOT EXISTS translated_ingredients_json JSONB,
    ADD COLUMN IF NOT EXISTS translated_steps_json JSONB,
    ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS is_user_facing BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS quality_score NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    ADD COLUMN IF NOT EXISTS tags_json JSONB NOT NULL DEFAULT '[]'::jsonb;

UPDATE recipes
SET
    language = 'en',
    is_user_facing = FALSE,
    quality_score = 0.250
WHERE source = 'foodcom';

UPDATE recipes
SET
    language = 'ru',
    is_user_facing = TRUE,
    quality_score = GREATEST(quality_score, 0.750)
WHERE source IN ('curated_ru', 'povarenok');
