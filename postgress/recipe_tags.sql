CREATE TABLE recipe_tags (
    id BIGSERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,             -- soup, dinner, vegan, gluten_free, winter
    name_ru TEXT NOT NULL,
    tag_type TEXT NOT NULL                 -- meal_type / diet / cuisine / season / region
);

CREATE TABLE recipe_tag_links (
    recipe_id BIGINT REFERENCES recipes(id) ON DELETE CASCADE,
    tag_id BIGINT REFERENCES recipe_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (recipe_id, tag_id)
);