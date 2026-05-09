from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import pandas as pd
from passlib.context import CryptContext
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.build_recipe_features import ensure_schema as ensure_recipe_features_schema
from scripts.build_recipe_features import refresh_recipe_features

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class BootstrapProfile:
    key: str
    email: str
    sex: str
    age: int
    height_cm: float
    weight_kg: float
    activity_level: str
    goal: str
    region_code: str
    daily_budget_rub: int
    weekly_budget_rub: int
    meals_per_day: int
    favorite_products: list[str]
    disliked_products: list[str]
    allergies: list[str]
    positive_selector: Callable[[pd.DataFrame], pd.Series]
    negative_selector: Callable[[pd.DataFrame], pd.Series]
    negative_reason: str
    negative_flags: dict[str, bool]


def resolve_db_url(db_url: Optional[str]) -> str:
    if db_url:
        return db_url

    env_db_url = os.getenv("DATABASE_URL")
    if env_db_url:
        return env_db_url

    backend_env_path = PROJECT_ROOT / "backend/.env"
    if backend_env_path.exists():
        for line in backend_env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip()

    raise SystemExit(
        "--db-url is required unless DATABASE_URL is available in the environment "
        "or backend/.env"
    )


def ensure_schema(conn) -> None:
    for migration_name in (
        "profile_budget_migration.sql",
        "feedback_training_signals_migration.sql",
    ):
        migration_path = PROJECT_ROOT / "postgress" / migration_name
        if migration_path.exists():
            conn.execute(text(migration_path.read_text(encoding="utf-8")))
    ensure_recipe_features_schema(conn)


def stable_user_id(email: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, email)


def bool_series(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column].fillna(False).astype(bool)


def has_any_category(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    result = pd.Series(False, index=df.index)
    for column in columns:
        result = result | bool_series(df, column)
    return result


def not_null_number(df: pd.DataFrame, column: str) -> pd.Series:
    return df[column].notna()


def bootstrap_profiles() -> list[BootstrapProfile]:
    return [
        BootstrapProfile(
            key="budget_student",
            email="bootstrap.student@tasteplanner.local",
            sex="female",
            age=21,
            height_cm=165,
            weight_kg=58,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-MOW",
            daily_budget_rub=450,
            weekly_budget_rub=3000,
            meals_per_day=3,
            favorite_products=["Рис", "Гречка", "Куриная грудка", "Овощи"],
            disliked_products=["Морепродукты", "Свинина"],
            allergies=[],
            positive_selector=lambda df: (
                (df["estimated_cost_rub"].fillna(9999) <= 180)
                & (df["total_minutes"].fillna(9999) <= 45)
                & has_any_category(df, ["has_grains", "has_vegetables", "has_meat"])
            ),
            negative_selector=lambda df: (
                (df["estimated_cost_rub"].fillna(0) >= 360)
                | (df["total_minutes"].fillna(0) >= 100)
            ),
            negative_reason="too_expensive",
            negative_flags={"too_expensive": True},
        ),
        BootstrapProfile(
            key="athlete_high_protein",
            email="bootstrap.athlete@tasteplanner.local",
            sex="male",
            age=28,
            height_cm=184,
            weight_kg=84,
            activity_level="high",
            goal="gain_weight",
            region_code="RU-UFO",
            daily_budget_rub=900,
            weekly_budget_rub=6200,
            meals_per_day=5,
            favorite_products=["Куриная грудка", "Говядина", "Творог", "Рыба"],
            disliked_products=["Сахар", "Майонез"],
            allergies=[],
            positive_selector=lambda df: (
                (df["protein"].fillna(0) >= 20)
                & (df["calories"].fillna(0).between(250, 850))
                & has_any_category(df, ["has_meat", "has_fish", "has_dairy"])
            ),
            negative_selector=lambda df: (
                (df["protein"].fillna(999) <= 6)
                | (df["calories"].fillna(0) >= 1000)
            ),
            negative_reason="not_enough_calories",
            negative_flags={"not_enough_calories": True},
        ),
        BootstrapProfile(
            key="weight_loss_light",
            email="bootstrap.light@tasteplanner.local",
            sex="female",
            age=35,
            height_cm=170,
            weight_kg=76,
            activity_level="low",
            goal="lose_weight",
            region_code="RU-CFO",
            daily_budget_rub=650,
            weekly_budget_rub=4500,
            meals_per_day=4,
            favorite_products=["Овощи", "Рыба", "Куриная грудка", "Йогурт"],
            disliked_products=["Сахар", "Темный шоколад", "Майонез"],
            allergies=[],
            positive_selector=lambda df: (
                (df["calories"].fillna(9999) <= 450)
                & (df["total_minutes"].fillna(9999) <= 60)
                & has_any_category(df, ["has_vegetables", "has_fish", "has_meat"])
            ),
            negative_selector=lambda df: (
                (df["calories"].fillna(0) >= 850)
                | (df["fat"].fillna(0) >= 45)
            ),
            negative_reason="too_many_calories",
            negative_flags={"too_many_calories": True},
        ),
        BootstrapProfile(
            key="family_fast",
            email="bootstrap.family@tasteplanner.local",
            sex="male",
            age=41,
            height_cm=178,
            weight_kg=82,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-PFO",
            daily_budget_rub=950,
            weekly_budget_rub=6500,
            meals_per_day=4,
            favorite_products=["Куриная грудка", "Картофель", "Макароны", "Овощи"],
            disliked_products=["Острые соусы", "Морепродукты"],
            allergies=[],
            positive_selector=lambda df: (
                (df["total_minutes"].fillna(9999) <= 45)
                & (df["estimated_cost_rub"].fillna(9999) <= 320)
                & has_any_category(df, ["has_meat", "has_grains", "has_vegetables"])
            ),
            negative_selector=lambda df: df["total_minutes"].fillna(0) >= 120,
            negative_reason="too_long",
            negative_flags={"too_long": True},
        ),
        BootstrapProfile(
            key="far_east_fish",
            email="bootstrap.fareast@tasteplanner.local",
            sex="female",
            age=30,
            height_cm=164,
            weight_kg=61,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-DFO",
            daily_budget_rub=850,
            weekly_budget_rub=5800,
            meals_per_day=3,
            favorite_products=["Рыба", "Морепродукты", "Рис", "Овощи"],
            disliked_products=["Свинина", "Говядина"],
            allergies=[],
            positive_selector=lambda df: (
                bool_series(df, "has_fish")
                | (bool_series(df, "has_grains") & bool_series(df, "has_vegetables"))
            ),
            negative_selector=lambda df: bool_series(df, "has_meat")
            & ~bool_series(df, "has_fish"),
            negative_reason="contains_disliked",
            negative_flags={"contains_disliked": True},
        ),
        BootstrapProfile(
            key="dairy_allergy",
            email="bootstrap.nodairy@tasteplanner.local",
            sex="male",
            age=33,
            height_cm=176,
            weight_kg=74,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-SFO",
            daily_budget_rub=700,
            weekly_budget_rub=4900,
            meals_per_day=3,
            favorite_products=["Куриная грудка", "Рис", "Овощи", "Фасоль"],
            disliked_products=["Сметана", "Сыр", "Йогурт"],
            allergies=["Молоко", "Сыр", "Творог", "Сметана", "Йогурт"],
            positive_selector=lambda df: (
                ~bool_series(df, "has_dairy")
                & (df["calories"].fillna(9999) <= 700)
                & has_any_category(df, ["has_meat", "has_grains", "has_vegetables", "has_legumes"])
            ),
            negative_selector=lambda df: bool_series(df, "has_dairy"),
            negative_reason="contains_disliked",
            negative_flags={"contains_disliked": True},
        ),
        BootstrapProfile(
            key="vegetarian_budget",
            email="bootstrap.vegetarian@tasteplanner.local",
            sex="female",
            age=26,
            height_cm=168,
            weight_kg=63,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-SPE",
            daily_budget_rub=600,
            weekly_budget_rub=4100,
            meals_per_day=3,
            favorite_products=["Овощи", "Фасоль", "Чечевица", "Рис", "Гречка"],
            disliked_products=["Куриная грудка", "Говядина", "Свинина", "Рыба"],
            allergies=[],
            positive_selector=lambda df: (
                ~has_any_category(df, ["has_meat", "has_fish"])
                & has_any_category(df, ["has_vegetables", "has_legumes", "has_grains"])
                & (df["estimated_cost_rub"].fillna(9999) <= 260)
            ),
            negative_selector=lambda df: has_any_category(df, ["has_meat", "has_fish"]),
            negative_reason="contains_disliked",
            negative_flags={"contains_disliked": True},
        ),
        BootstrapProfile(
            key="busy_office",
            email="bootstrap.office@tasteplanner.local",
            sex="male",
            age=31,
            height_cm=181,
            weight_kg=78,
            activity_level="low",
            goal="maintain",
            region_code="RU-MOW",
            daily_budget_rub=800,
            weekly_budget_rub=5600,
            meals_per_day=3,
            favorite_products=["Куриная грудка", "Рис", "Йогурт", "Овощи"],
            disliked_products=["Долгое приготовление", "Жирные блюда"],
            allergies=[],
            positive_selector=lambda df: (
                (df["total_minutes"].fillna(9999) <= 25)
                & (df["calories"].fillna(9999) <= 650)
                & (df["estimated_cost_rub"].fillna(9999) <= 320)
            ),
            negative_selector=lambda df: df["total_minutes"].fillna(0) >= 90,
            negative_reason="too_long",
            negative_flags={"too_long": True},
        ),
        BootstrapProfile(
            key="south_seasonal",
            email="bootstrap.south@tasteplanner.local",
            sex="female",
            age=44,
            height_cm=166,
            weight_kg=68,
            activity_level="moderate",
            goal="lose_weight",
            region_code="RU-KDA",
            daily_budget_rub=700,
            weekly_budget_rub=4800,
            meals_per_day=4,
            favorite_products=["Помидор", "Болгарский перец", "Фасоль", "Рыба", "Фрукты"],
            disliked_products=["Свинина", "Майонез"],
            allergies=[],
            positive_selector=lambda df: (
                bool_series(df, "has_vegetables")
                & (df["calories"].fillna(9999) <= 550)
                & (df["estimated_cost_rub"].fillna(9999) <= 300)
            ),
            negative_selector=lambda df: (
                bool_series(df, "has_meat")
                & (df["fat"].fillna(0) >= 35)
            ),
            negative_reason="too_many_calories",
            negative_flags={"too_many_calories": True},
        ),
        BootstrapProfile(
            key="nuts_allergy",
            email="bootstrap.nutsallergy@tasteplanner.local",
            sex="male",
            age=24,
            height_cm=174,
            weight_kg=70,
            activity_level="high",
            goal="maintain",
            region_code="RU-NVS",
            daily_budget_rub=750,
            weekly_budget_rub=5200,
            meals_per_day=4,
            favorite_products=["Куриная грудка", "Картофель", "Рис", "Овощи"],
            disliked_products=["Орехи", "Миндаль"],
            allergies=["Орехи", "Миндаль"],
            positive_selector=lambda df: (
                ~bool_series(df, "has_nuts")
                & has_any_category(df, ["has_meat", "has_grains", "has_vegetables"])
                & (df["protein"].fillna(0) >= 10)
            ),
            negative_selector=lambda df: bool_series(df, "has_nuts"),
            negative_reason="contains_disliked",
            negative_flags={"contains_disliked": True},
        ),
        BootstrapProfile(
            key="high_budget_balanced",
            email="bootstrap.highbudget@tasteplanner.local",
            sex="female",
            age=38,
            height_cm=172,
            weight_kg=65,
            activity_level="moderate",
            goal="maintain",
            region_code="RU-CFO",
            daily_budget_rub=1400,
            weekly_budget_rub=9500,
            meals_per_day=3,
            favorite_products=["Лосось", "Говядина", "Овощи", "Сыр", "Фрукты"],
            disliked_products=["Сахар"],
            allergies=[],
            positive_selector=lambda df: (
                (df["calories"].fillna(0).between(250, 800))
                & (df["protein"].fillna(0) >= 12)
                & has_any_category(df, ["has_fish", "has_meat", "has_vegetables", "has_dairy"])
            ),
            negative_selector=lambda df: (
                (df["calories"].fillna(0) >= 1100)
                | (df["protein"].fillna(999) <= 4)
            ),
            negative_reason="too_many_calories",
            negative_flags={"too_many_calories": True},
        ),
        BootstrapProfile(
            key="siberia_hearty",
            email="bootstrap.siberia@tasteplanner.local",
            sex="male",
            age=46,
            height_cm=179,
            weight_kg=88,
            activity_level="high",
            goal="maintain",
            region_code="RU-SFO",
            daily_budget_rub=850,
            weekly_budget_rub=5900,
            meals_per_day=4,
            favorite_products=["Говядина", "Картофель", "Гречка", "Грибы", "Молоко"],
            disliked_products=["Морепродукты"],
            allergies=[],
            positive_selector=lambda df: (
                has_any_category(df, ["has_meat", "has_grains", "has_vegetables"])
                & (df["calories"].fillna(0).between(350, 900))
                & (df["estimated_cost_rub"].fillna(9999) <= 360)
            ),
            negative_selector=lambda df: bool_series(df, "has_fish")
            & ~bool_series(df, "has_meat"),
            negative_reason="contains_disliked",
            negative_flags={"contains_disliked": True},
        ),
    ]


def select_recipe_ids(
    df: pd.DataFrame,
    selector: Callable[[pd.DataFrame], pd.Series],
    limit: int,
    exclude_ids: set[int] | None = None,
) -> list[int]:
    exclude_ids = exclude_ids or set()
    selected = df[selector(df)].copy()
    if selected.empty:
        selected = df[not_null_number(df, "calories")].copy()

    selected = selected[~selected["recipe_id"].isin(exclude_ids)]
    selected = selected.sort_values(
        by=["source_rating", "price_coverage", "recipe_id"],
        ascending=[False, False, True],
        na_position="last",
    )
    return [int(recipe_id) for recipe_id in selected["recipe_id"].head(limit).tolist()]


def upsert_user(conn, profile: BootstrapProfile, password_hash: str) -> uuid.UUID:
    user_id = stable_user_id(profile.email)
    conn.execute(
        text(
            """
            INSERT INTO users (id, email, password_hash)
            VALUES (:id, :email, :password_hash)
            ON CONFLICT (id)
            DO UPDATE SET
                email = EXCLUDED.email,
                password_hash = EXCLUDED.password_hash
            """
        ),
        {
            "id": user_id,
            "email": profile.email,
            "password_hash": password_hash,
        },
    )
    conn.execute(
        text(
            """
            INSERT INTO user_profiles (
                user_id,
                sex,
                age,
                height_cm,
                weight_kg,
                activity_level,
                goal,
                region_code,
                daily_budget_rub,
                weekly_budget_rub,
                meals_per_day,
                favorite_products_json,
                disliked_products_json,
                allergies_json,
                updated_at
            )
            VALUES (
                :user_id,
                :sex,
                :age,
                :height_cm,
                :weight_kg,
                :activity_level,
                :goal,
                :region_code,
                :daily_budget_rub,
                :weekly_budget_rub,
                :meals_per_day,
                CAST(:favorite_products AS jsonb),
                CAST(:disliked_products AS jsonb),
                CAST(:allergies AS jsonb),
                NOW()
            )
            ON CONFLICT (user_id)
            DO UPDATE SET
                sex = EXCLUDED.sex,
                age = EXCLUDED.age,
                height_cm = EXCLUDED.height_cm,
                weight_kg = EXCLUDED.weight_kg,
                activity_level = EXCLUDED.activity_level,
                goal = EXCLUDED.goal,
                region_code = EXCLUDED.region_code,
                daily_budget_rub = EXCLUDED.daily_budget_rub,
                weekly_budget_rub = EXCLUDED.weekly_budget_rub,
                meals_per_day = EXCLUDED.meals_per_day,
                favorite_products_json = EXCLUDED.favorite_products_json,
                disliked_products_json = EXCLUDED.disliked_products_json,
                allergies_json = EXCLUDED.allergies_json,
                updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "sex": profile.sex,
            "age": profile.age,
            "height_cm": profile.height_cm,
            "weight_kg": profile.weight_kg,
            "activity_level": profile.activity_level,
            "goal": profile.goal,
            "region_code": profile.region_code,
            "daily_budget_rub": profile.daily_budget_rub,
            "weekly_budget_rub": profile.weekly_budget_rub,
            "meals_per_day": profile.meals_per_day,
            "favorite_products": json.dumps(profile.favorite_products, ensure_ascii=False),
            "disliked_products": json.dumps(profile.disliked_products, ensure_ascii=False),
            "allergies": json.dumps(profile.allergies, ensure_ascii=False),
        },
    )
    return user_id


def upsert_feedback(
    conn,
    user_id: uuid.UUID,
    recipe_id: int,
    liked: bool,
    rating: int,
    reason: str,
    flags: dict[str, bool],
) -> None:
    conn.execute(
        text(
            """
            INSERT INTO user_recipe_feedback (
                user_id,
                recipe_id,
                liked,
                rating,
                reason,
                too_expensive,
                too_long,
                contains_disliked,
                too_many_calories,
                not_enough_calories,
                updated_at
            )
            VALUES (
                :user_id,
                :recipe_id,
                :liked,
                :rating,
                :reason,
                :too_expensive,
                :too_long,
                :contains_disliked,
                :too_many_calories,
                :not_enough_calories,
                NOW()
            )
            ON CONFLICT (user_id, recipe_id)
            DO UPDATE SET
                liked = EXCLUDED.liked,
                rating = EXCLUDED.rating,
                reason = EXCLUDED.reason,
                too_expensive = EXCLUDED.too_expensive,
                too_long = EXCLUDED.too_long,
                contains_disliked = EXCLUDED.contains_disliked,
                too_many_calories = EXCLUDED.too_many_calories,
                not_enough_calories = EXCLUDED.not_enough_calories,
                updated_at = NOW()
            """
        ),
        {
            "user_id": user_id,
            "recipe_id": recipe_id,
            "liked": liked,
            "rating": rating,
            "reason": reason,
            "too_expensive": flags.get("too_expensive", False),
            "too_long": flags.get("too_long", False),
            "contains_disliked": flags.get("contains_disliked", False),
            "too_many_calories": flags.get("too_many_calories", False),
            "not_enough_calories": flags.get("not_enough_calories", False),
        },
    )


def insert_event(conn, user_id: uuid.UUID, recipe_id: int, event_type: str, payload: dict) -> None:
    conn.execute(
        text(
            """
            INSERT INTO user_events (user_id, recipe_id, event_type, payload_json)
            VALUES (:user_id, :recipe_id, :event_type, CAST(:payload_json AS jsonb))
            """
        ),
        {
            "user_id": user_id,
            "recipe_id": recipe_id,
            "event_type": event_type,
            "payload_json": json.dumps(payload, ensure_ascii=False),
        },
    )


def seed_bootstrap_data(
    db_url: str,
    positive_per_profile: int,
    negative_per_profile: int,
) -> dict[str, int]:
    engine = create_engine(db_url)
    password_hash = pwd_context.hash("tasteplanner-bootstrap")

    with engine.begin() as conn:
        ensure_schema(conn)
        refresh_recipe_features(conn)
        features = pd.read_sql_query(
            text("SELECT * FROM recipe_features WHERE source = 'curated_ru'"),
            conn,
        )

        if features.empty:
            raise SystemExit("curated_ru recipe_features is empty; import curated recipes before seeding.")

        profiles = bootstrap_profiles()
        users_count = 0
        feedback_count = 0
        events_count = 0

        for profile in profiles:
            user_id = upsert_user(conn, profile, password_hash)
            users_count += 1
            conn.execute(
                text("DELETE FROM user_recipe_feedback WHERE user_id = :user_id"),
                {"user_id": user_id},
            )
            conn.execute(
                text(
                    """
                    DELETE FROM user_events
                    WHERE user_id = :user_id
                      AND payload_json ->> 'bootstrap_profile' = :profile_key
                    """
                ),
                {"user_id": user_id, "profile_key": profile.key},
            )

            positive_ids = select_recipe_ids(
                features,
                profile.positive_selector,
                positive_per_profile,
            )
            negative_ids = select_recipe_ids(
                features,
                profile.negative_selector,
                negative_per_profile,
                exclude_ids=set(positive_ids),
            )

            for recipe_id in positive_ids:
                upsert_feedback(
                    conn,
                    user_id=user_id,
                    recipe_id=recipe_id,
                    liked=True,
                    rating=5,
                    reason="bootstrap_positive_match",
                    flags={},
                )
                insert_event(
                    conn,
                    user_id,
                    recipe_id,
                    "recipe_open",
                    {"bootstrap_profile": profile.key, "label": "positive"},
                )
                insert_event(
                    conn,
                    user_id,
                    recipe_id,
                    "favorite_toggle",
                    {"bootstrap_profile": profile.key, "is_favorite": True},
                )
                feedback_count += 1
                events_count += 2

            for recipe_id in negative_ids:
                upsert_feedback(
                    conn,
                    user_id=user_id,
                    recipe_id=recipe_id,
                    liked=False,
                    rating=1,
                    reason=profile.negative_reason,
                    flags=profile.negative_flags,
                )
                insert_event(
                    conn,
                    user_id,
                    recipe_id,
                    "recipe_open",
                    {"bootstrap_profile": profile.key, "label": "negative"},
                )
                insert_event(
                    conn,
                    user_id,
                    recipe_id,
                    "recipe_feedback",
                    {
                        "bootstrap_profile": profile.key,
                        "liked": False,
                        "reason": profile.negative_reason,
                    },
                )
                feedback_count += 1
                events_count += 2

    return {
        "profiles": users_count,
        "feedback_rows": feedback_count,
        "event_rows": events_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed deterministic bootstrap profiles and interactions for model training."
    )
    parser.add_argument("--db-url", default=None)
    parser.add_argument("--positive-per-profile", type=int, default=14)
    parser.add_argument("--negative-per-profile", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = seed_bootstrap_data(
        db_url=resolve_db_url(args.db_url),
        positive_per_profile=args.positive_per_profile,
        negative_per_profile=args.negative_per_profile,
    )
    print(
        "Seeded "
        f"{summary['profiles']} profiles, "
        f"{summary['feedback_rows']} feedback rows, "
        f"{summary['event_rows']} events"
    )


if __name__ == "__main__":
    main()
