from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

try:
    from pyaterochka_api import PyaterochkaAPI
except ImportError as exc:  # pragma: no cover - import guard for optional dependency
    raise SystemExit(
        "Missing dependency 'pyaterochka-api'. Install parser dependencies with "
        "`pip install -r scripts/requirements.txt` and run `python -m camoufox fetch` once."
    ) from exc


DEFAULT_OUTPUT = Path("datasets/pyaterochka_prices.csv")


@dataclass(frozen=True)
class CatalogCategory:
    id: str
    name: str
    path: str
    depth: int
    is_leaf: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export product prices from Pyaterochka catalog into CSV."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Path to the destination CSV file.",
    )
    parser.add_argument(
        "--store-sap-code",
        default=None,
        help="Explicit SAP code of a store. If omitted, the script uses the selected store from 5ka.ru session.",
    )
    parser.add_argument(
        "--category-id",
        action="append",
        default=[],
        help="Restrict export to specific category IDs. Repeat the option to pass multiple values.",
    )
    parser.add_argument(
        "--category-name-contains",
        default=None,
        help="Filter categories by case-insensitive substring match in the category path.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Per-category product limit. 499 is the current API maximum.",
    )
    parser.add_argument(
        "--max-categories",
        type=int,
        default=None,
        help="Optional cap on the number of categories to fetch, useful for test runs.",
    )
    parser.add_argument(
        "--include-non-leaf",
        action="store_true",
        help="Fetch products for parent categories too. By default only leaf categories are exported.",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Request product detail endpoint for each product and append flattened detail fields.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser warmup in headless mode.",
    )
    parser.add_argument(
        "--timeout-ms",
        type=float,
        default=10000.0,
        help="Browser and API timeout in milliseconds.",
    )
    return parser.parse_args()


def flatten_categories(
    categories: Iterable[dict[str, Any]],
    parent_path: str = "",
    depth: int = 0,
) -> list[CatalogCategory]:
    flattened: list[CatalogCategory] = []
    for category in categories:
        name = str(category.get("name", "")).strip()
        category_id = str(category.get("id", "")).strip()
        if not category_id or not name:
            continue

        path = f"{parent_path} / {name}" if parent_path else name
        children = category.get("categories") or []
        is_leaf = len(children) == 0
        flattened.append(
            CatalogCategory(
                id=category_id,
                name=name,
                path=path,
                depth=depth,
                is_leaf=is_leaf,
            )
        )
        flattened.extend(flatten_categories(children, parent_path=path, depth=depth + 1))
    return flattened


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def flatten_json(value: Any, prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    if isinstance(value, dict):
        for key, nested_value in value.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.update(flatten_json(nested_value, prefix=next_prefix))
        return flattened

    if isinstance(value, list):
        if all(is_scalar(item) for item in value):
            flattened[prefix] = json.dumps(value, ensure_ascii=False)
        else:
            flattened[prefix] = json.dumps(value, ensure_ascii=False)
        return flattened

    flattened[prefix] = value
    return flattened


def first_present(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, ""):
            return value
    return None


def build_product_row(
    *,
    collected_at: str,
    store_sap_code: str,
    category: CatalogCategory,
    product: dict[str, Any],
    detail: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    flattened_product = flatten_json(product, prefix="product")
    flattened_detail = flatten_json(detail, prefix="detail") if detail else {}
    merged = {**flattened_product, **flattened_detail}

    relative_url = first_present(
        merged,
        "product.link",
        "product.url",
        "detail.link",
        "detail.url",
    )
    if isinstance(relative_url, str) and relative_url.startswith("/"):
        relative_url = f"https://5ka.ru{relative_url}"

    row = {
        "collected_at_utc": collected_at,
        "store_sap_code": store_sap_code,
        "category_id": category.id,
        "category_name": category.name,
        "category_path": category.path,
        "category_depth": category.depth,
        "product_id": first_present(merged, "product.id", "detail.id"),
        "plu": first_present(merged, "product.plu", "detail.plu"),
        "name": first_present(merged, "product.name", "detail.name"),
        "brand": first_present(
            merged,
            "product.brand",
            "product.brand_name",
            "detail.brand",
            "detail.brand_name",
        ),
        "current_price": first_present(
            merged,
            "product.price",
            "product.current_price",
            "product.current_prices.price_promo__min",
            "product.current_prices.price_reg__min",
            "detail.price",
            "detail.current_price",
            "detail.current_prices.price_promo__min",
            "detail.current_prices.price_reg__min",
        ),
        "regular_price": first_present(
            merged,
            "product.current_prices.price_reg__min",
            "detail.current_prices.price_reg__min",
            "product.old_price",
            "detail.old_price",
        ),
        "promo_price": first_present(
            merged,
            "product.current_prices.price_promo__min",
            "detail.current_prices.price_promo__min",
        ),
        "discount_percent": first_present(
            merged,
            "product.discount_percent",
            "detail.discount_percent",
        ),
        "unit": first_present(
            merged,
            "product.measurement_unit",
            "detail.measurement_unit",
            "product.unit",
            "detail.unit",
        ),
        "weight_or_volume": first_present(
            merged,
            "product.weight",
            "product.volume",
            "detail.weight",
            "detail.volume",
        ),
        "url": relative_url,
    }
    row.update(merged)
    return row


def select_categories(
    categories: list[CatalogCategory],
    *,
    category_ids: list[str],
    category_name_contains: Optional[str],
    include_non_leaf: bool,
    max_categories: Optional[int],
) -> list[CatalogCategory]:
    selected = categories
    if not include_non_leaf:
        selected = [category for category in selected if category.is_leaf]
    if category_ids:
        allowed_ids = {value.strip() for value in category_ids if value.strip()}
        selected = [category for category in selected if category.id in allowed_ids]
    if category_name_contains:
        needle = category_name_contains.casefold()
        selected = [
            category for category in selected if needle in category.path.casefold()
        ]
    if max_categories is not None:
        selected = selected[:max_categories]
    return selected


async def resolve_store_sap_code(
    api: PyaterochkaAPI, explicit_sap_code: Optional[str]
) -> str:
    if explicit_sap_code:
        return explicit_sap_code

    store_info = await api.delivery_panel_store()
    selected_store = (store_info or {}).get("selectedStore") or {}
    sap_code = str(selected_store.get("sapCode", "")).strip()
    if not sap_code:
        raise RuntimeError(
            "Could not determine the selected store SAP code. Pass --store-sap-code explicitly."
        )
    return sap_code


async def fetch_catalog_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.limit < 1 or args.limit > 499:
        raise SystemExit("--limit must be between 1 and 499.")

    collected_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    api = PyaterochkaAPI(
        headless=args.headless,
        timeout_ms=args.timeout_ms,
    )
    try:
        await api.__aenter__()
        store_sap_code = await resolve_store_sap_code(api, args.store_sap_code)

        category_response = await api.Catalog.tree(
            sap_code_store_id=store_sap_code,
            subcategories=True,
        )
        category_payload = category_response.json()
        categories = flatten_categories(category_payload)
        selected_categories = select_categories(
            categories,
            category_ids=args.category_id,
            category_name_contains=args.category_name_contains,
            include_non_leaf=args.include_non_leaf,
            max_categories=args.max_categories,
        )

        if not selected_categories:
            raise RuntimeError("No categories matched the provided filters.")

        rows: list[dict[str, Any]] = []
        for index, category in enumerate(selected_categories, start=1):
            print(
                f"[{index}/{len(selected_categories)}] Fetching category "
                f"{category.path} ({category.id})"
            )
            products_response = await api.Catalog.products_list(
                category_id=category.id,
                sap_code_store_id=store_sap_code,
                limit=args.limit,
            )
            products_payload = products_response.json() or {}
            products = products_payload.get("products") or []

            for product in products:
                detail_payload: Optional[dict[str, Any]] = None
                if args.details:
                    plu = product.get("plu")
                    if plu is not None:
                        detail_response = await api.Catalog.Product.info(
                            sap_code_store_id=store_sap_code,
                            plu_id=plu,
                        )
                        detail_payload = detail_response.json()

                rows.append(
                    build_product_row(
                        collected_at=collected_at,
                        store_sap_code=store_sap_code,
                        category=category,
                        product=product,
                        detail=detail_payload,
                    )
                )

        return rows
    finally:
        if hasattr(api, "session"):
            await api.close()


def export_rows_to_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    ensure_parent_dir(output_path)
    dataframe = pd.DataFrame(rows)
    dataframe.to_csv(output_path, index=False, encoding="utf-8-sig")


def main() -> None:
    args = parse_args()
    output_path = Path(args.output)
    try:
        rows = asyncio.run(fetch_catalog_rows(args))
    except Exception as exc:
        message = str(exc)
        if "xpvnsulc" in message or "next-route-announcer" in message:
            raise SystemExit(
                "Pyaterochka anti-bot blocked the session during browser warmup. "
                "Try running from a regular residential Russian IP, disable headless mode, "
                "increase --timeout-ms, or provide a working HTTPS proxy in HTTPS_PROXY."
            ) from exc
        raise
    export_rows_to_csv(rows, output_path)
    print(f"Saved {len(rows)} rows to {output_path}")


if __name__ == "__main__":
    main()
