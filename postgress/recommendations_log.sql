CREATE TABLE recommendations_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recipe_id BIGINT REFERENCES recipes(id) ON DELETE CASCADE,
    score NUMERIC(8,4),
    context_json JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE user_recipe_feedback (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    recipe_id BIGINT REFERENCES recipes(id) ON DELETE CASCADE,
    liked BOOLEAN,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    cooked_at TIMESTAMP,
    PRIMARY KEY (user_id, recipe_id)
);