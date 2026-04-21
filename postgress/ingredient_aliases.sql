CREATE TABLE ingredient_aliases (
    id BIGSERIAL PRIMARY KEY,
    ingredient_id BIGINT REFERENCES ingredients(id) ON DELETE CASCADE,
    alias TEXT UNIQUE NOT NULL
);