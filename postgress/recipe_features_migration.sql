CREATE TABLE IF NOT EXISTS recipe_features (
    recipe_id BIGINT PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    source_recipe_id TEXT NOT NULL,
    title TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'unknown',
    is_user_facing BOOLEAN NOT NULL DEFAULT TRUE,
    quality_score NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_minutes INT,
    calories NUMERIC(8,2),
    protein NUMERIC(8,2),
    fat NUMERIC(8,2),
    carbs NUMERIC(8,2),
    source_rating NUMERIC(3,2),
    ingredient_count INT NOT NULL DEFAULT 0,
    priced_ingredient_count INT NOT NULL DEFAULT 0,
    price_coverage NUMERIC(5,4) NOT NULL DEFAULT 0,
    estimated_cost_rub NUMERIC(10,2),
    canonical_ingredients_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    product_categories_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    has_meat BOOLEAN NOT NULL DEFAULT FALSE,
    has_fish BOOLEAN NOT NULL DEFAULT FALSE,
    has_dairy BOOLEAN NOT NULL DEFAULT FALSE,
    has_grains BOOLEAN NOT NULL DEFAULT FALSE,
    has_vegetables BOOLEAN NOT NULL DEFAULT FALSE,
    has_fruit BOOLEAN NOT NULL DEFAULT FALSE,
    has_legumes BOOLEAN NOT NULL DEFAULT FALSE,
    has_nuts BOOLEAN NOT NULL DEFAULT FALSE,
    has_pantry BOOLEAN NOT NULL DEFAULT FALSE,
    budget_tier TEXT,
    time_tier TEXT,
    calorie_tier TEXT,
    protein_tier TEXT,
    seasonal_months_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    seasonal_ingredient_count INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recipe_features_budget_tier
    ON recipe_features(budget_tier);

CREATE INDEX IF NOT EXISTS idx_recipe_features_time_tier
    ON recipe_features(time_tier);

CREATE INDEX IF NOT EXISTS idx_recipe_features_calorie_tier
    ON recipe_features(calorie_tier);

CREATE INDEX IF NOT EXISTS idx_recipe_features_categories
    ON recipe_features USING GIN(product_categories_json);

ALTER TABLE recipe_features
    ADD COLUMN IF NOT EXISTS language TEXT NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS is_user_facing BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS quality_score NUMERIC(4,3) NOT NULL DEFAULT 0.500,
    ADD COLUMN IF NOT EXISTS tags_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS seasonal_months_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS seasonal_ingredient_count INT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_recipe_features_seasonal_months
    ON recipe_features USING GIN(seasonal_months_json);
