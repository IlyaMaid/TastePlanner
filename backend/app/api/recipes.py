from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.services.recipe_queries import RECIPE_SELECT_SQL, map_recipe_row

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
            {RECIPE_SELECT_SQL}
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

    items = [map_recipe_row(row) for row in rows]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }
