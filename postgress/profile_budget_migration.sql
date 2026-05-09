ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS daily_budget_rub NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS weekly_budget_rub NUMERIC(10,2);
