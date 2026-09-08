import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { PageSkeleton } from "../components/Skeleton";
import { fetchMyProfile } from "../lib/profile";
import { fetchMealPlan, saveUserEvent, swapMeal } from "../lib/recommendations";

const SWAP_MODES = [
  { id: "cheaper", label: "Дешевле" },
  { id: "faster", label: "Быстрее" },
  { id: "lighter", label: "Легче" },
];

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
    estimated_cost_rub: Number(
      meals
        .reduce((sum, meal) => sum + (meal.recipe.estimated_cost_rub || 0), 0)
        .toFixed(1),
    ),
  };
}

function ProgressBar({ value, max, tone = "emerald" }) {
  const percent =
    max && max > 0 ? Math.min(100, Math.round((Number(value || 0) / max) * 100)) : 0;
  const color = tone === "amber" ? "bg-amber-500" : "bg-emerald-500";

  return (
    <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
      <div className={`h-full rounded-full ${color}`} style={{ width: `${percent}%` }} />
    </div>
  );
}

export default function MealPlanPage({ authSession, notify }) {
  const [mealPlan, setMealPlan] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [swappingSlot, setSwappingSlot] = useState(null);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;

  const loadMealPlan = useCallback(async (showFullLoader = false) => {
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
      const currentProfile = await fetchMyProfile(accessToken);
      setProfile(currentProfile);
      const payload = await fetchMealPlan(accessToken, {
        mealsPerDay: currentProfile.meals_per_day,
      });
      setMealPlan(payload);
      if (!showFullLoader) {
        notify?.({ title: "Рацион обновлен", message: "Подборка блюд пересобрана." });
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось построить план питания.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accessToken, notify]);

  useEffect(() => {
    loadMealPlan(true);
  }, [loadMealPlan]);

  const meals = mealPlan?.meals ?? [];
  const totals = mealPlan?.totals ?? {
    calories: 0,
    protein: 0,
    fat: 0,
    carbs: 0,
    estimated_cost_rub: 0,
  };

  const handleSwapMeal = async (meal, mode = "balanced") => {
    if (!accessToken || !mealPlan) {
      return;
    }

    setSwappingSlot(`${meal.slot}-${mode}`);
    setErrorMessage("");

    try {
      const payload = await swapMeal(accessToken, {
        slot: meal.slot,
        current_recipe_id: meal.recipe.id,
        target_calories: meal.target_calories,
        excluded_recipe_ids: mealPlan.meals.map((item) => item.recipe.id),
        mode,
      });

      try {
        await saveUserEvent(accessToken, {
          event_type: "meal_swap",
          recipe_id: payload.meal.recipe.id,
          payload_json: {
            slot: meal.slot,
            previous_recipe_id: meal.recipe.id,
            mode,
          },
        });
      } catch {
        // Event tracking is intentionally non-blocking for the meal plan.
      }

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
      notify?.({
        title: "Блюдо заменено",
        message:
          mode === "cheaper"
            ? "Подобрали более бюджетный вариант."
            : mode === "faster"
              ? "Подобрали более быстрый вариант."
              : "Подобрали более легкий вариант.",
      });
    } catch (error) {
      setErrorMessage(error.message || "Не удалось заменить блюдо.");
      notify?.({
        type: "error",
        title: "Не удалось заменить блюдо",
        message: "Попробуйте обновить план или выбрать другой режим.",
      });
    } finally {
      setSwappingSlot(null);
    }
  };

  const strategyLabel =
    mealPlan?.strategy === "personalized_feedback"
      ? "Персонализация по вашим лайкам"
      : mealPlan?.strategy === "cold_start_popularity"
        ? "Стартовый план по популярным рецептам"
        : "План питания";
  const selectedMealsPerDay =
    mealPlan?.meals_per_day ?? profile?.meals_per_day ?? "не указано";
  const regionalFoodZone = mealPlan?.regional_food_zone;
  const preferenceProfile = mealPlan?.preference_profile;
  const dailyBudget = profile?.daily_budget_rub;
  const weeklyBudget = profile?.weekly_budget_rub;
  const calorieTarget = mealPlan?.daily_target_calories;
  const budgetLimit =
    dailyBudget != null
      ? Number(dailyBudget)
      : weeklyBudget != null
        ? Number(weeklyBudget) / 7
        : null;
  const isOverBudget =
    budgetLimit != null && Number(totals.estimated_cost_rub || 0) > budgetLimit;

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
              Рацион учитывает параметры профиля: число приемов пищи, цель,
              ориентир по калориям, регион и пищевые ограничения.
            </p>
            {!isLoading ? (
              <p className="mt-3 text-sm font-medium text-emerald-700">
                Режим: {strategyLabel} · приемов пищи: {selectedMealsPerDay}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/meal-plan/week"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
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
          <PageSkeleton rows={4} />
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

                      <div className="grid grid-cols-3 gap-2">
                        {SWAP_MODES.map((mode) => {
                          const isBusy = swappingSlot === `${meal.slot}-${mode.id}`;
                          return (
                            <button
                              key={mode.id}
                              type="button"
                              onClick={() => handleSwapMeal(meal, mode.id)}
                              disabled={Boolean(swappingSlot)}
                              className="inline-flex min-h-10 items-center justify-center rounded-xl border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {isBusy ? "..." : mode.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  {meal.recipe.recommendation_reasons?.length > 0 ? (
                    <div className="mt-5 flex flex-wrap gap-2">
                      {meal.recipe.recommendation_reasons.slice(0, 4).map((reason) => (
                        <span
                          key={reason}
                          className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-100"
                        >
                          {reason}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
                    <NutritionTile
                      label="Калории"
                      value={formatNumber(meal.recipe.calories, " ккал")}
                    />
                    <NutritionTile
                      label="Стоимость"
                      value={
                        meal.recipe.estimated_cost_rub != null
                          ? `≈ ${formatNumber(meal.recipe.estimated_cost_rub, " ₽")}`
                          : "Нет данных"
                      }
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

                  {meal.recipe.cooking_steps?.length > 0 ? (
                    <div className="mt-6 rounded-2xl bg-slate-50 p-4">
                      <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
                        Способ приготовления
                      </p>
                      <ol className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
                        {meal.recipe.cooking_steps.slice(0, 4).map((step, index) => (
                          <li key={`${meal.recipe.id}-${index}`} className="flex gap-3">
                            <span className="font-semibold text-slate-900">
                              {index + 1}.
                            </span>
                            <span>{step}</span>
                          </li>
                        ))}
                      </ol>
                    </div>
                  ) : null}
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
                      {calorieTarget != null
                        ? `${Math.round(calorieTarget)} ккал`
                        : "Нет данных"}
                    </strong>
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span>Калории</span>
                      <strong>{formatNumber(totals.calories, " ккал")}</strong>
                    </div>
                    <ProgressBar value={totals.calories} max={calorieTarget} />
                  </div>
                  <div className="rounded-2xl bg-slate-50 px-4 py-3">
                    <div className="flex items-center justify-between">
                      <span>Стоимость</span>
                      <strong>≈ {formatNumber(totals.estimated_cost_rub, " ₽")}</strong>
                    </div>
                    <ProgressBar
                      value={totals.estimated_cost_rub}
                      max={budgetLimit}
                      tone={isOverBudget ? "amber" : "emerald"}
                    />
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Бюджет</span>
                    <strong>
                      {budgetLimit != null
                        ? `${Math.round(budgetLimit)} ₽`
                        : "Не указан"}
                    </strong>
                  </div>
                  {budgetLimit != null ? (
                    <div
                      className={`flex items-center justify-between rounded-2xl px-4 py-3 ${
                        isOverBudget
                          ? "bg-amber-50 text-amber-700"
                          : "bg-emerald-50 text-emerald-700"
                      }`}
                    >
                      <span>Статус</span>
                      <strong>{isOverBudget ? "Выше бюджета" : "Вписывается"}</strong>
                    </div>
                  ) : null}
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

              {regionalFoodZone ? (
                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <h2 className="text-xl font-semibold">Региональная зона</h2>
                  <p className="mt-3 text-sm font-semibold text-emerald-700">
                    {regionalFoodZone.name_ru}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {regionalFoodZone.summary_ru}
                  </p>
                </div>
              ) : null}

              {preferenceProfile ? (
                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <h2 className="text-xl font-semibold">Предпочтения</h2>
                  <div className="mt-5 space-y-3 text-sm text-slate-600">
                    <div className="rounded-2xl bg-slate-50 px-4 py-3">
                      Любимые продукты:{" "}
                      {preferenceProfile.favorite_products?.length
                        ? preferenceProfile.favorite_products.join(", ")
                        : "не выбраны"}
                    </div>
                    <div className="rounded-2xl bg-slate-50 px-4 py-3">
                      Исключить:{" "}
                      {preferenceProfile.allergies?.length
                        ? preferenceProfile.allergies.join(", ")
                        : "не выбрано"}
                    </div>
                  </div>
                </div>
              ) : null}

              <div className="rounded-3xl bg-emerald-950 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Настройки рациона</h2>
                <div className="mt-4 space-y-3 text-sm text-slate-200">
                  <div className="rounded-2xl bg-white/10 p-4">
                    Приемов пищи в день: {selectedMealsPerDay}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Дневная цель:{" "}
                    {mealPlan?.daily_target_calories != null
                      ? `${Math.round(mealPlan.daily_target_calories)} ккал`
                      : "не указана"}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Бюджет:{" "}
                    {dailyBudget != null
                      ? `${Math.round(dailyBudget)} ₽ в день`
                      : weeklyBudget != null
                        ? `${Math.round(weeklyBudget)} ₽ в неделю`
                        : "не указан"}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Рацион можно обновить или заменить отдельное блюдо.
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
