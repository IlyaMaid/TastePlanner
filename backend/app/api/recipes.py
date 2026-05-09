from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
def list_recipes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: Optional[str] = Query(default=None, min_length=1),
    source: Optional[str] = Query(default=None, min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user

    filters: list[str] = []
    params: dict[str, object] = {"limit": limit, "offset": offset}

    if source:
        filters.append("r.source = :source")
        params["source"] = source.strip().lower()
    else:
        filters.append("COALESCE(r.is_user_facing, TRUE) = TRUE")

    if search:
        normalized_search = f"%{search.strip().lower()}%"
        filters.append(
            """
            (
                LOWER(COALESCE(r.translated_title, r.title)) LIKE :search
                OR EXISTS (
                    SELECT 1
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                      AND (
                          LOWER(ri.raw_text) LIKE :search
                          OR LOWER(i.canonical_name) LIKE :search
                          OR LOWER(COALESCE(i.display_name_ru, '')) LIKE :search
                      )
                )
            )
            """
        )
        params["search"] = normalized_search

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    total = db.execute(
        text(
            f"""
            SELECT COUNT(*)
            FROM recipes r
            {where_clause}
            """
        ),
        params,
    ).scalar_one()

    current_month = datetime.now().month

    rows = db.execute(
        text(
            f"""
            SELECT
                r.id,
                r.source,
                r.source_recipe_id,
                COALESCE(r.translated_title, r.title) AS title,
                COALESCE(r.translated_description, r.description) AS description,
                COALESCE(r.translated_steps_json, r.steps_json, '[]'::jsonb) AS cooking_steps,
                r.total_minutes,
                r.calories,
                COALESCE(rf.seasonal_months_json, '[]'::jsonb) AS seasonal_months_json,
                COALESCE(rf.seasonal_ingredient_count, 0) AS seasonal_ingredient_count,
                CASE
                    WHEN COALESCE(rf.seasonal_months_json, '[]'::jsonb)
                        @> to_jsonb(CAST(:current_month AS integer))
                    THEN TRUE
                    ELSE FALSE
                END AS is_seasonal_now,
                (
                    SELECT ROUND(
                        SUM(
                            CASE
                                WHEN ri.quantity IS NOT NULL
                                  AND ri.unit = 'g'
                                  AND i.price_per_100g_rub IS NOT NULL
                                THEN ri.quantity * i.price_per_100g_rub / 100
                                ELSE i.price_per_100g_rub
                            END
                        ),
                        2
                    )
                    FROM recipe_ingredients ri
                    JOIN ingredients i ON i.id = ri.ingredient_id
                    WHERE ri.recipe_id = r.id
                      AND i.price_per_100g_rub IS NOT NULL
                ) AS estimated_cost_rub,
                COALESCE(
                    r.translated_ingredients_json,
                    CAST((
                        SELECT json_agg(ingredient_row.raw_text ORDER BY ingredient_row.id)
                        FROM (
                            SELECT ri.id, ri.raw_text
                            FROM recipe_ingredients ri
                            WHERE ri.recipe_id = r.id
                            ORDER BY ri.id
                            LIMIT 8
                        ) AS ingredient_row
                    ) AS jsonb),
                    '[]'::jsonb
                ) AS ingredients,
                COALESCE(
                    CAST((
                        SELECT json_agg(
                            json_build_object(
                                'raw_text', ingredient_row.raw_text,
                                'name_ru', ingredient_row.name_ru,
                                'quantity', ingredient_row.quantity,
                                'unit', ingredient_row.unit,
                                'calories_per_100g', ingredient_row.calories_per_100g,
                                'price_per_100g_rub', ingredient_row.price_per_100g_rub,
                                'calories_total', ingredient_row.calories_total,
                                'estimated_cost_rub', ingredient_row.estimated_cost_rub
                            )
                            ORDER BY ingredient_row.id
                        )
                        FROM (
                            SELECT
                                ri.id,
                                ri.raw_text,
                                ri.quantity,
                                ri.unit,
                                COALESCE(i.display_name_ru, i.canonical_name) AS name_ru,
                                i.calories_per_100g,
                                i.price_per_100g_rub,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.calories_per_100g IS NOT NULL
                                    THEN ROUND(ri.quantity * i.calories_per_100g / 100, 1)
                                    ELSE NULL
                                END AS calories_total,
                                CASE
                                    WHEN ri.quantity IS NOT NULL
                                      AND ri.unit = 'g'
                                      AND i.price_per_100g_rub IS NOT NULL
                                    THEN ROUND(ri.quantity * i.price_per_100g_rub / 100, 2)
                                    ELSE NULL
                                END AS estimated_cost_rub
                            FROM recipe_ingredients ri
                            JOIN ingredients i ON i.id = ri.ingredient_id
                            WHERE ri.recipe_id = r.id
                            ORDER BY ri.id
                            LIMIT 8
                        ) AS ingredient_row
                    ) AS jsonb),
                    '[]'::jsonb
                ) AS ingredient_details
            FROM recipes r
            LEFT JOIN recipe_features rf ON rf.recipe_id = r.id
            {where_clause}
            ORDER BY
                CASE
                    WHEN COALESCE(rf.seasonal_months_json, '[]'::jsonb)
                        @> to_jsonb(CAST(:current_month AS integer))
                    THEN 0
                    ELSE 1
                END,
                CASE WHEN r.source = 'curated_ru' THEN 0 ELSE 1 END,
                r.quality_score DESC NULLS LAST,
                r.id DESC
            LIMIT :limit
            OFFSET :offset
            """
        ),
        {**params, "current_month": current_month},
    ).mappings()

    items = [
        {
            "id": row["id"],
            "source": row["source"],
            "source_recipe_id": row["source_recipe_id"],
            "title": row["title"],
            "description": row["description"],
            "cooking_steps": list(row["cooking_steps"] or []),
            "total_minutes": row["total_minutes"],
            "calories": float(row["calories"]) if row["calories"] is not None else None,
            "seasonal_months": list(row["seasonal_months_json"] or []),
            "seasonal_ingredient_count": int(row["seasonal_ingredient_count"] or 0),
            "is_seasonal_now": bool(row["is_seasonal_now"]),
            "estimated_cost_rub": (
                float(row["estimated_cost_rub"])
                if row["estimated_cost_rub"] is not None
                else None
            ),
            "ingredients": list(row["ingredients"] or []),
            "ingredient_details": list(row["ingredient_details"] or []),
        }
        for row in rows
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
