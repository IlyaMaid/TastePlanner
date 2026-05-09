import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { PageSkeleton } from "../components/Skeleton";
import RecipeCard from "../components/RecipeCard";
import {
  fetchRecommendations,
  saveRecommendationFeedback,
  saveUserEvent,
} from "../lib/recommendations";

const FILTERS = [
  { id: "all", label: "Все" },
  { id: "seasonal", label: "По сезону" },
  { id: "quick", label: "До 30 минут" },
  { id: "budget", label: "Дешевле" },
  { id: "light", label: "Меньше калорий" },
  { id: "protein", label: "Больше белка" },
];

function formatProductDetail(ingredient) {
  const name = ingredient.name_ru || ingredient.raw_text;
  const quantity = formatIngredientQuantity(ingredient);
  const calories =
    ingredient.calories_total != null
      ? `${Math.round(Number(ingredient.calories_total))} ккал`
      : ingredient.calories_per_100g != null
        ? `${Math.round(Number(ingredient.calories_per_100g))} ккал/100 г`
        : "ккал нет";
  const price =
    ingredient.estimated_cost_rub != null
      ? `≈ ${Number(ingredient.estimated_cost_rub).toLocaleString("ru-RU", {
          maximumFractionDigits: 1,
        })} ₽`
      : ingredient.price_per_100g_rub != null
        ? `${Number(ingredient.price_per_100g_rub).toLocaleString("ru-RU", {
            maximumFractionDigits: 1,
          })} ₽/100 г`
        : "цены нет";

  return `${name}${quantity ? `, ${quantity}` : ""}: ${calories}, ${price}`;
}

function formatIngredientQuantity(ingredient) {
  const quantity =
    ingredient.quantity != null && ingredient.unit === "g"
      ? `${Number(ingredient.quantity).toLocaleString("ru-RU", {
          maximumFractionDigits: 0,
        })} г`
      : null;

  return quantity;
}

function formatIngredientListItem(ingredient) {
  const name = ingredient.name_ru || ingredient.raw_text;
  const quantity = formatIngredientQuantity(ingredient);

  return `${name}${quantity ? ` - ${quantity}` : ""}`;
}

function formatRecipe(recipe) {
  const cleanedDescription =
    recipe.source === "povarenok" && typeof recipe.description === "string"
      ? recipe.description.replace(/^Источник:\s*https?:\/\/\S+\s*$/i, "").trim()
      : recipe.description;
  const ingredientDetails = Array.isArray(recipe.ingredient_details)
    ? recipe.ingredient_details
    : [];

  return {
    ...recipe,
    description:
      cleanedDescription || "Описание для этого рецепта пока не добавлено.",
    calories:
      typeof recipe.calories === "number" ? Math.round(recipe.calories) : null,
    metaLabel:
      recipe.total_minutes != null
        ? `${recipe.total_minutes} мин`
        : "Время не указано",
    predictedRating:
      typeof recipe.predicted_rating === "number"
        ? recipe.predicted_rating.toFixed(2)
        : null,
    contentSimilarity:
      typeof recipe.content_similarity === "number"
        ? recipe.content_similarity
        : null,
    predictedScore:
      typeof recipe.predicted_score === "number"
        ? recipe.predicted_score
        : null,
    finalScore:
      typeof recipe.final_score === "number" ? recipe.final_score : null,
    estimatedCostRub:
      typeof recipe.estimated_cost_rub === "number"
        ? recipe.estimated_cost_rub
        : null,
    ingredientsPreview:
      ingredientDetails.length > 0
        ? ingredientDetails.slice(0, 4).map(formatIngredientListItem)
        : Array.isArray(recipe.ingredients)
          ? recipe.ingredients.slice(0, 4)
          : [],
    ingredientsList:
      ingredientDetails.length > 0
        ? ingredientDetails.map(formatIngredientListItem)
        : Array.isArray(recipe.ingredients)
          ? recipe.ingredients
          : [],
    cookingSteps: Array.isArray(recipe.cooking_steps) ? recipe.cooking_steps : [],
    cookingStepsPreview: Array.isArray(recipe.cooking_steps)
      ? recipe.cooking_steps.slice(0, 4)
      : [],
    productDetails: ingredientDetails.map(formatProductDetail),
    productDetailsPreview: ingredientDetails.slice(0, 4).map(formatProductDetail),
    recommendationReasons: Array.isArray(recipe.recommendation_reasons)
      ? recipe.recommendation_reasons
      : [],
  };
}

function matchesFilter(recipe, filterId) {
  if (filterId === "seasonal") {
    return Boolean(recipe.is_seasonal_now);
  }

  if (filterId === "quick") {
    return recipe.total_minutes != null && Number(recipe.total_minutes) <= 30;
  }

  if (filterId === "budget") {
    return recipe.estimatedCostRub != null && Number(recipe.estimatedCostRub) <= 250;
  }

  if (filterId === "light") {
    return recipe.calories != null && Number(recipe.calories) <= 500;
  }

  if (filterId === "protein") {
    return recipe.protein != null && Number(recipe.protein) >= 20;
  }

  return true;
}

export default function RecipesPage({
  authSession,
  favorites,
  toggleFavorite,
  notify,
}) {
  const [recipes, setRecipes] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [activeRecipeId, setActiveRecipeId] = useState(null);
  const [activeFilter, setActiveFilter] = useState("all");

  const accessToken = authSession?.accessToken;

  const loadRecipes = useCallback(async (showFullLoader = false) => {
    if (!accessToken) {
      return;
    }

    if (showFullLoader) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }

    setErrorMessage("");

    try {
      const payload = await fetchRecommendations(accessToken, { limit: 12 });
      setRecipes((payload.items ?? []).map((item) => formatRecipe(item)));
      if (!showFullLoader) {
        notify?.({ title: "Рецепты обновлены", message: "Подборка стала свежее." });
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить рецепты.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accessToken, notify]);

  useEffect(() => {
    loadRecipes(true);
  }, [loadRecipes]);

  const isFavorite = (id) => favorites.some((item) => item.id === id);
  const visibleRecipes = useMemo(
    () => recipes.filter((recipe) => matchesFilter(recipe, activeFilter)),
    [recipes, activeFilter],
  );

  const logRecipeEvent = useCallback(async (event_type, recipe, payload_json = {}) => {
    if (!accessToken) {
      return;
    }

    try {
      await saveUserEvent(accessToken, {
        event_type,
        recipe_id: recipe?.id,
        payload_json,
      });
    } catch {
      // Event tracking should never interrupt the main recipe flow.
    }
  }, [accessToken]);

  const handleRefresh = async () => {
    await loadRecipes(false);
  };

  const handleLike = async (recipe) => {
    const wasFavorite = isFavorite(recipe.id);
    toggleFavorite(recipe);

    if (!accessToken) {
      return;
    }

    setActiveRecipeId(recipe.id);
    setErrorMessage("");

    try {
      await saveRecommendationFeedback(accessToken, {
        recipe_id: recipe.id,
        liked: !wasFavorite,
        rating: !wasFavorite ? 5 : null,
      });
      await logRecipeEvent("favorite_toggle", recipe, {
        is_favorite: !wasFavorite,
      });
      await loadRecipes(false);
      notify?.({
        title: !wasFavorite ? "Реакция сохранена" : "Рецепт обновлен",
        message: !wasFavorite
          ? "Учтем это в следующих рекомендациях."
          : "Избранное обновлено.",
      });
    } catch (error) {
      setErrorMessage(error.message || "Не удалось сохранить реакцию на рецепт.");
    } finally {
      setActiveRecipeId(null);
    }
  };

  const handleDislike = async (recipe, reasonPayload = {}) => {
    if (!accessToken) {
      setRecipes((items) => items.filter((item) => item.id !== recipe.id));
      return;
    }

    setActiveRecipeId(recipe.id);
    setErrorMessage("");

    try {
      await saveRecommendationFeedback(accessToken, {
        recipe_id: recipe.id,
        liked: false,
        rating: 1,
        reason: reasonPayload.reason ?? "not_suitable",
        too_expensive: Boolean(reasonPayload.too_expensive),
        too_long: Boolean(reasonPayload.too_long),
        contains_disliked: Boolean(reasonPayload.contains_disliked),
        too_many_calories: Boolean(reasonPayload.too_many_calories),
        not_enough_calories: Boolean(reasonPayload.not_enough_calories),
      });
      await logRecipeEvent("recipe_feedback", recipe, {
        liked: false,
        reason: reasonPayload.reason ?? "not_suitable",
      });
      setRecipes((items) => items.filter((item) => item.id !== recipe.id));
      await loadRecipes(false);
      notify?.({
        title: "Спасибо за обратную связь",
        message: "Мы покажем более подходящие блюда.",
      });
    } catch (error) {
      setErrorMessage(error.message || "Не удалось сохранить реакцию на рецепт.");
    } finally {
      setActiveRecipeId(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Рецепты
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Подборка блюд
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Единая подборка учитывает профиль, предпочтения, ограничения,
              примерную стоимость и время приготовления.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing || isLoading}
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Обновляем..." : "Обновить"}
            </button>

            <Link
              to="/favorites"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
            >
              Избранное{favorites.length > 0 ? ` · ${favorites.length}` : ""}
            </Link>
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        <div className="mb-6 flex flex-wrap gap-2">
          {FILTERS.map((filter) => (
            <button
              key={filter.id}
              type="button"
              onClick={() => setActiveFilter(filter.id)}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition ${
                activeFilter === filter.id
                  ? "border-slate-900 bg-slate-900 text-white"
                  : "border-slate-200 bg-white text-slate-600 hover:border-slate-300"
              }`}
            >
              {filter.label}
            </button>
          ))}
        </div>

        {isLoading ? (
          <PageSkeleton rows={4} />
        ) : visibleRecipes.length === 0 ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Ничего не найдено</h2>
            <p className="mt-3 text-slate-600">
              Обновите подборку, сбросьте фильтр или измените предпочтения в анкете.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {visibleRecipes.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                variant="favorite-toggle"
                isFavorite={isFavorite(recipe.id)}
                onFavoriteToggle={() => handleLike(recipe)}
                onDislike={() => handleDislike(recipe)}
                onFeedbackReason={(payload) => handleDislike(recipe, payload)}
                onOpen={() => logRecipeEvent("recipe_open", recipe)}
                isBusy={activeRecipeId === recipe.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
