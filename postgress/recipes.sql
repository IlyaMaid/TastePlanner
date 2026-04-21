CREATE TABLE recipes (
    id BIGSERIAL PRIMARY KEY,
    source TEXT NOT NULL,                  -- foodcom / epicurious
    source_recipe_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    steps_json JSONB,
    total_minutes INT,
    servings NUMERIC(6,2),
    calories NUMERIC(8,2),
    protein NUMERIC(8,2),
    fat NUMERIC(8,2),
    carbs NUMERIC(8,2),
    rating NUMERIC(3,2),
    region_code TEXT REFERENCES regions(code),
    season_code TEXT REFERENCES seasons(code),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (source, source_recipe_id)
);

CREATE TABLE recipe_ingredients (
    id BIGSERIAL PRIMARY KEY,
    recipe_id BIGINT REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id BIGINT REFERENCES ingredients(id),
    raw_text TEXT NOT NULL,                -- как было в датасете
    quantity NUMERIC(10,3),
    unit TEXT
);