import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import RecipeCard from "../components/RecipeCard";
import {
  fetchRecipeCatalog,
  fetchRecommendations,
  saveRecommendationFeedback,
} from "../lib/recommendations";

function formatRecipe(recipe, mode) {
  const isMlMode = mode === "ml";
  const cleanedDescription =
    recipe.source === "povarenok" && typeof recipe.description === "string"
      ? recipe.description.replace(/^Источник:\s*https?:\/\/\S+\s*$/i, "").trim()
      : recipe.description;

  return {
    ...recipe,
    description:
      cleanedDescription ||
      (isMlMode
        ? "Описание пока не заполнено, но рецепт участвует в ML-подборке."
        : "Описание для этого рецепта пока не добавлено."),
    calories:
      typeof recipe.calories === "number" ? Math.round(recipe.calories) : null,
    metaLabel:
      recipe.total_minutes != null
        ? `${recipe.total_minutes} мин`
        : "Время не указано",
    predictedRating:
      isMlMode && typeof recipe.predicted_rating === "number"
        ? recipe.predicted_rating.toFixed(2)
        : null,
    ingredientsPreview: Array.isArray(recipe.ingredients)
      ? recipe.ingredients.slice(0, 4)
      : [],
  };
}

export default function RecipesPage({
  authSession,
  favorites,
  toggleFavorite,
}) {
  const [recipes, setRecipes] = useState([]);
  const [mode, setMode] = useState("ml");
  const [search, setSearch] = useState("");
  const [strategy, setStrategy] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [activeRecipeId, setActiveRecipeId] = useState(null);

  const accessToken = authSession?.accessToken;

  const loadRecipes = async (nextMode = mode, showFullLoader = false) => {
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
      if (nextMode === "ml") {
        const payload = await fetchRecommendations(accessToken, { limit: 12 });
        setRecipes((payload.items ?? []).map((item) => formatRecipe(item, "ml")));
        setStrategy(payload.strategy ?? null);
      } else {
        const payload = await fetchRecipeCatalog(accessToken, {
          limit: 12,
          source: "povarenok",
          search,
        });
        setRecipes((payload.items ?? []).map((item) => formatRecipe(item, "ru")));
        setStrategy("russian_catalog");
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить рецепты.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadRecipes(mode, true);
  }, [accessToken, mode]);

  const isFavorite = (id) => favorites.some((item) => item.id === id);

  const handleRefresh = async () => {
    await loadRecipes(mode, false);
  };

  const handleSearchSubmit = async (event) => {
    event.preventDefault();
    await loadRecipes("ru", false);
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

      if (mode === "ml") {
        await loadRecipes("ml", false);
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось сохранить реакцию на рецепт.");
    } finally {
      setActiveRecipeId(null);
    }
  };

  const strategyLabel =
    strategy === "personalized_feedback"
      ? "Персонализация по вашим лайкам"
      : strategy === "cold_start_popularity"
        ? "Стартовая ML-подборка"
        : strategy === "russian_catalog"
          ? "Русский каталог рецептов"
          : "Подборка рецептов";

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
              По умолчанию здесь показываются русские рецепты. ML-подборку на
              Food.com можно включить отдельно для демонстрации модели в
              курсовой.
            </p>
            <p className="mt-3 text-sm font-medium text-emerald-700">
              Режим выдачи: {strategyLabel}
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex rounded-2xl bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => setMode("ru")}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  mode === "ru"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Русские рецепты
              </button>
              <button
                type="button"
                onClick={() => setMode("ml")}
                className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                  mode === "ml"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-600 hover:text-slate-900"
                }`}
              >
                ML-демо
              </button>
            </div>

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

        {mode === "ru" ? (
          <form
            onSubmit={handleSearchSubmit}
            className="mb-6 flex flex-col gap-3 rounded-3xl bg-white p-4 shadow-sm ring-1 ring-slate-200 md:flex-row"
          >
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по названию или ингредиенту"
              className="min-h-12 flex-1 rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-slate-400"
            />
            <button
              type="submit"
              className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Найти
            </button>
          </form>
        ) : null}

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Загружаем рецепты...</h2>
            <p className="mt-3 text-slate-600">
              Подождите немного, сейчас появится свежая подборка.
            </p>
          </div>
        ) : recipes.length === 0 ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Ничего не найдено</h2>
            <p className="mt-3 text-slate-600">
              Попробуйте другой запрос или переключитесь на другой режим выдачи.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {recipes.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                variant="favorite-toggle"
                isFavorite={isFavorite(recipe.id)}
                onFavoriteToggle={() => handleLike(recipe)}
                isBusy={activeRecipeId === recipe.id}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
