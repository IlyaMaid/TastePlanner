CREATE TABLE dietary_restrictions (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,     -- vegan, vegetarian, gluten_free, lactose_free
    name_ru TEXT NOT NULL
);

CREATE TABLE allergens (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,     -- milk, nuts, eggs, fish
    name_ru TEXT NOT NULL
);

CREATE TABLE user_dietary_restrictions (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    restriction_id INT REFERENCES dietary_restrictions(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, restriction_id)
);

CREATE TABLE user_allergens (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    allergen_id INT REFERENCES allergens(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, allergen_id)
);

CREATE TABLE user_disliked_ingredients (
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ingredient_name TEXT NOT NULL,
    PRIMARY KEY (user_id, ingredient_name)
);