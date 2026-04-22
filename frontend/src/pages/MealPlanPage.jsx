import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchMealPlan, swapMeal } from "../lib/recommendations";

function NutritionTile({ label, value }) {
  return (
    <div className="min-w-0 rounded-2xl bg-slate-50 p-4">
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 break-words text-lg font-semibold leading-snug text-slate-900">
        {value}
      </p>
    </div>
  );
}

function formatNumber(value, suffix = "") {
  if (value == null) {
    return "Нет данных";
  }
  return `${Math.round(value)}${suffix}`;
}

function recalculateTotals(meals) {
  return {
    calories: Number(
      meals.reduce((sum, meal) => sum + (meal.recipe.calories || 0), 0).toFixed(1),
    ),
    protein: Number(
      meals.reduce((sum, meal) => sum + (meal.recipe.protein || 0), 0).toFixed(1),
    ),
    fat: Number(
      meals.reduce((sum, meal) => sum + (meal.recipe.fat || 0), 0).toFixed(1),
    ),
    carbs: Number(
      meals.reduce((sum, meal) => sum + (meal.recipe.carbs || 0), 0).toFixed(1),
    ),
  };
}

export default function MealPlanPage({ authSession }) {
  const [mealPlan, setMealPlan] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [swappingSlot, setSwappingSlot] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;

  const loadMealPlan = async (showFullLoader = false) => {
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
      const payload = await fetchMealPlan(accessToken);
      setMealPlan(payload);
    } catch (error) {
      setErrorMessage(error.message || "Не удалось построить план питания.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadMealPlan(true);
  }, [accessToken]);

  const meals = mealPlan?.meals ?? [];
  const totals = mealPlan?.totals ?? {
    calories: 0,
    protein: 0,
    fat: 0,
    carbs: 0,
  };

  const handleSwapMeal = async (meal) => {
    if (!accessToken || !mealPlan) {
      return;
    }

    setSwappingSlot(meal.slot);
    setErrorMessage("");

    try {
      const payload = await swapMeal(accessToken, {
        slot: meal.slot,
        current_recipe_id: meal.recipe.id,
        target_calories: meal.target_calories,
        excluded_recipe_ids: mealPlan.meals.map((item) => item.recipe.id),
      });

      setMealPlan((prev) => {
        if (!prev) {
          return prev;
        }

        const nextMeals = prev.meals.map((item) =>
          item.slot === meal.slot ? payload.meal : item,
        );

        return {
          ...prev,
          strategy: payload.strategy ?? prev.strategy,
          meals: nextMeals,
          totals: recalculateTotals(nextMeals),
        };
      });
    } catch (error) {
      setErrorMessage(error.message || "Не удалось заменить блюдо.");
    } finally {
      setSwappingSlot(null);
    }
  };

  const strategyLabel =
    mealPlan?.strategy === "personalized_feedback"
      ? "ML-персонализация по вашим лайкам"
      : mealPlan?.strategy === "cold_start_popularity"
        ? "Стартовый ML-план по популярным рецептам"
        : "ML-план питания";

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Персональный рацион
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              План питания на день
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Этот экран собирается из ML-рекомендаций и параметров вашего
              профиля: числа приемов пищи, целей и расчетной калорийности.
            </p>
            {!isLoading ? (
              <p className="mt-3 text-sm font-medium text-emerald-700">
                Режим: {strategyLabel}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/meal-plan/week"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              План на неделю
            </Link>

            <button
              type="button"
              onClick={() => loadMealPlan(false)}
              disabled={isLoading || isRefreshing}
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Обновляем..." : "Собрать заново"}
            </button>
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Собираем рацион...</h2>
            <p className="mt-3 text-slate-600">
              Система подбирает блюда из ML-рекомендаций и раскладывает их по
              приемам пищи.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <section className="space-y-4">
              {meals.map((meal) => (
                <article
                  key={`${meal.slot}-${meal.recipe.id}`}
                  className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
                >
                  <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-emerald-700">
                        {meal.slot}
                      </p>
                      <h2 className="mt-2 max-w-xl text-xl font-semibold leading-tight text-slate-950">
                        {meal.recipe.title}
                      </h2>
                      <p className="mt-3 text-sm leading-6 text-slate-600">
                        {meal.recipe.description || "Описание пока не добавлено."}
                      </p>
                    </div>

                    <div className="flex w-full shrink-0 flex-col gap-3 sm:w-auto sm:min-w-[12rem]">
                      <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        <div className="font-semibold text-slate-900">
                          Цель:{" "}
                          {meal.target_calories != null
                            ? `${Math.round(meal.target_calories)} ккал`
                            : "без цели"}
                        </div>
                      </div>

                      <button
                        type="button"
                        onClick={() => handleSwapMeal(meal)}
                        disabled={swappingSlot === meal.slot}
                        className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-200 px-4 py-2 text-sm font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {swappingSlot === meal.slot ? "Меняем..." : "Заменить"}
                      </button>
                    </div>
                  </div>

                  <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
                    <NutritionTile
                      label="Калории"
                      value={formatNumber(meal.recipe.calories, " ккал")}
                    />
                    <NutritionTile
                      label="Белки"
                      value={formatNumber(meal.recipe.protein, " г")}
                    />
                    <NutritionTile
                      label="Жиры"
                      value={formatNumber(meal.recipe.fat, " г")}
                    />
                    <NutritionTile
                      label="Углеводы"
                      value={formatNumber(meal.recipe.carbs, " г")}
                    />
                  </div>
                </article>
              ))}
            </section>

            <aside className="space-y-6">
              <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold">Итог за день</h2>
                <div className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Цель</span>
                    <strong>
                      {mealPlan?.daily_target_calories != null
                        ? `${Math.round(mealPlan.daily_target_calories)} ккал`
                        : "Нет данных"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Калории</span>
                    <strong>{formatNumber(totals.calories, " ккал")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Белки</span>
                    <strong>{formatNumber(totals.protein, " г")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Жиры</span>
                    <strong>{formatNumber(totals.fat, " г")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Углеводы</span>
                    <strong>{formatNumber(totals.carbs, " г")}</strong>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Как это работает</h2>
                <div className="mt-4 space-y-3 text-sm text-slate-200">
                  <div className="rounded-2xl bg-white/10 p-4">
                    ML-модель сначала выбирает наиболее подходящие рецепты
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Затем система раскладывает их по приемам пищи, учитывая
                    число приемов и ориентир по калориям
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Кнопка «Заменить» подбирает другой рецепт для того же слота
                    и пересчитывает итог по дню
                  </div>
                </div>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
