ALTER TABLE recipes
    ADD COLUMN IF NOT EXISTS translated_steps_json JSONB;
