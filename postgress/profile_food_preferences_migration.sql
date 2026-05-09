ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS favorite_products_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS disliked_products_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS allergies_json JSONB NOT NULL DEFAULT '[]'::jsonb;
