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
    reason TEXT,
    too_expensive BOOLEAN NOT NULL DEFAULT FALSE,
    too_long BOOLEAN NOT NULL DEFAULT FALSE,
    contains_disliked BOOLEAN NOT NULL DEFAULT FALSE,
    too_many_calories BOOLEAN NOT NULL DEFAULT FALSE,
    not_enough_calories BOOLEAN NOT NULL DEFAULT FALSE,
    cooked_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, recipe_id)
);

CREATE TABLE user_events (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    recipe_id BIGINT REFERENCES recipes(id) ON DELETE SET NULL,
    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_events_user_created_at
    ON user_events(user_id, created_at DESC);
