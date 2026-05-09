CREATE TABLE user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    sex TEXT CHECK (sex IN ('male', 'female')),
    age INT CHECK (age BETWEEN 0 AND 120),
    height_cm NUMERIC(5,2),
    weight_kg NUMERIC(5,2),
    activity_level TEXT CHECK (
        activity_level IN ('low', 'moderate', 'high')
    ),
    goal TEXT CHECK (
        goal IN ('lose_weight', 'maintain', 'gain_weight')
    ),
    region_code TEXT,
    daily_calorie_target NUMERIC(7,2),
    daily_budget_rub NUMERIC(10,2),
    weekly_budget_rub NUMERIC(10,2),
    meals_per_day INT DEFAULT 3,
    favorite_products_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    disliked_products_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    allergies_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
