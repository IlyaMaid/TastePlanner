import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { PageSkeleton } from "../components/Skeleton";
import { fetchMyProfile } from "../lib/profile";
import { fetchMealPlan } from "../lib/recommendations";

const WEEK_DAYS = [
  "Понедельник",
  "Вторник",
  "Среда",
  "Четверг",
  "Пятница",
  "Суббота",
  "Воскресенье",
];

function formatNumber(value, suffix = "") {
  if (value == null) {
    return "Нет данных";
  }
  return `${Math.round(value)}${suffix}`;
}

function rotateMeals(meals, shift) {
  if (!meals.length) {
    return [];
  }

  return meals.map((meal, index) => {
    const rotatedRecipe = meals[(index + shift) % meals.length].recipe;
    return {
      ...meal,
      recipe: rotatedRecipe,
    };
  });
}

function calculateTotals(meals) {
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

function ReportTile({ label, value, hint, tone = "default" }) {
  const className =
    tone === "good"
      ? "rounded-2xl bg-emerald-50 px-4 py-3 text-emerald-800 ring-1 ring-emerald-100"
      : tone === "warn"
        ? "rounded-2xl bg-amber-50 px-4 py-3 text-amber-800 ring-1 ring-amber-100"
        : "rounded-2xl bg-slate-50 px-4 py-3 text-slate-700";

  return (
    <div className={className}>
      <p className="text-xs font-semibold uppercase tracking-[0.08em] opacity-70">
        {label}
      </p>
      <p className="mt-2 text-lg font-semibold">{value}</p>
      {hint ? <p className="mt-1 text-sm leading-5 opacity-80">{hint}</p> : null}
    </div>
  );
}

export default function WeeklyMealPlanPage({ authSession, notify }) {
  const [basePlan, setBasePlan] = useState(null);
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;

  const loadPlan = useCallback(async (showFullLoader = false) => {
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
      setBasePlan(payload);
      if (!showFullLoader) {
        notify?.({ title: "Неделя обновлена", message: "Отчет пересчитан." });
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить недельный план.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accessToken, notify]);

  useEffect(() => {
    loadPlan(true);
  }, [loadPlan]);

  const weeklyPlan = useMemo(() => {
    if (!basePlan?.meals?.length) {
      return [];
    }

    return WEEK_DAYS.map((day, index) => {
      const meals = rotateMeals(basePlan.meals, index % basePlan.meals.length);
      return {
        day,
        meals,
        totals: calculateTotals(meals),
      };
    });
  }, [basePlan]);

  const weeklyTotals = useMemo(() => {
    if (!weeklyPlan.length) {
      return { calories: 0, protein: 0, fat: 0, carbs: 0, estimated_cost_rub: 0 };
    }

    return {
      calories: Number(
        weeklyPlan.reduce((sum, day) => sum + day.totals.calories, 0).toFixed(1),
      ),
      protein: Number(
        weeklyPlan.reduce((sum, day) => sum + day.totals.protein, 0).toFixed(1),
      ),
      fat: Number(
        weeklyPlan.reduce((sum, day) => sum + day.totals.fat, 0).toFixed(1),
      ),
      carbs: Number(
        weeklyPlan.reduce((sum, day) => sum + day.totals.carbs, 0).toFixed(1),
      ),
      estimated_cost_rub: Number(
        weeklyPlan
          .reduce((sum, day) => sum + day.totals.estimated_cost_rub, 0)
          .toFixed(1),
      ),
    };
  }, [weeklyPlan]);
  const regionalFoodZone = basePlan?.regional_food_zone;
  const weeklyBudget = profile?.weekly_budget_rub;
  const avgDailyCost = weeklyPlan.length
    ? weeklyTotals.estimated_cost_rub / weeklyPlan.length
    : 0;
  const avgDailyCalories = weeklyPlan.length
    ? weeklyTotals.calories / weeklyPlan.length
    : 0;
  const uniqueRecipeCount = new Set(
    weeklyPlan.flatMap((day) => day.meals.map((meal) => meal.recipe.id)),
  ).size;
  const totalMealCount = weeklyPlan.reduce((sum, day) => sum + day.meals.length, 0);
  const varietyPercent =
    totalMealCount > 0 ? Math.round((uniqueRecipeCount / totalMealCount) * 100) : 0;
  const targetCalories = basePlan?.daily_target_calories;
  const avgCalorieDelta =
    targetCalories != null ? Math.round(avgDailyCalories - targetCalories) : null;
  const isWeeklyOverBudget =
    weeklyBudget != null && weeklyTotals.estimated_cost_rub > Number(weeklyBudget);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Недельный рацион
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              План питания на неделю
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Здесь собран недельный обзор на базе текущего плана дня, чтобы
              было удобнее смотреть рацион сразу по всем дням.
            </p>
            {!isLoading ? (
              <p className="mt-3 text-sm font-medium text-emerald-700">
                Приемов пищи в день:{" "}
                {basePlan?.meals_per_day ?? profile?.meals_per_day ?? "не указано"}
              </p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/meal-plan"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
            >
              Вернуться к дню
            </Link>

            <button
              type="button"
              onClick={() => loadPlan(false)}
              disabled={isLoading || isRefreshing}
              className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Обновляем..." : "Обновить неделю"}
            </button>
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <PageSkeleton rows={5} />
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="space-y-6">
              {weeklyPlan.map((dayPlan) => (
                <article
                  key={dayPlan.day}
                  className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
                >
                  <div className="mb-5 flex items-center justify-between gap-4">
                    <div>
                      <h2 className="text-2xl font-semibold">{dayPlan.day}</h2>
                      <p className="mt-2 text-sm text-slate-500">
                        {formatNumber(dayPlan.totals.calories, " ккал")} ·{" "}
                        ≈ {formatNumber(dayPlan.totals.estimated_cost_rub, " ₽")} ·{" "}
                        {formatNumber(dayPlan.totals.protein, " г белка")}
                      </p>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {dayPlan.meals.map((meal) => (
                      <div
                        key={`${dayPlan.day}-${meal.slot}-${meal.recipe.id}`}
                        className="rounded-2xl bg-slate-50 px-4 py-4"
                      >
                        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-emerald-700">
                              {meal.slot}
                            </p>
                            <h3 className="mt-1 text-lg font-semibold text-slate-900">
                              {meal.recipe.title}
                            </h3>
                          </div>

                          <div className="text-sm text-slate-500">
                            {formatNumber(meal.recipe.calories, " ккал")} · ≈{" "}
                            {formatNumber(meal.recipe.estimated_cost_rub, " ₽")}
                          </div>
                        </div>
                        {meal.recipe.cooking_steps?.length > 0 ? (
                          <p className="mt-3 text-sm leading-6 text-slate-600">
                            {meal.recipe.cooking_steps[0]}
                          </p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </section>

            <aside className="space-y-6">
              <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold">Недельный отчет</h2>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <ReportTile
                    label="Средний день"
                    value={`${formatNumber(avgDailyCalories, " ккал")}`}
                    hint={
                      avgCalorieDelta == null
                        ? "Цель не указана"
                        : avgCalorieDelta === 0
                          ? "Ровно по цели"
                          : `${avgCalorieDelta > 0 ? "+" : ""}${avgCalorieDelta} ккал к цели`
                    }
                    tone={
                      avgCalorieDelta != null && Math.abs(avgCalorieDelta) <= 150
                        ? "good"
                        : "default"
                    }
                  />
                  <ReportTile
                    label="Средняя стоимость"
                    value={`≈ ${formatNumber(avgDailyCost, " ₽")}`}
                    hint="На один день питания"
                  />
                  <ReportTile
                    label="Разнообразие"
                    value={`${varietyPercent}%`}
                    hint={`${uniqueRecipeCount} уникальных блюд из ${totalMealCount}`}
                    tone={varietyPercent >= 60 ? "good" : "warn"}
                  />
                  <ReportTile
                    label="Бюджет"
                    value={
                      weeklyBudget != null
                        ? isWeeklyOverBudget
                          ? "Выше бюджета"
                          : "Вписывается"
                        : "Не указан"
                    }
                    hint={
                      weeklyBudget != null
                        ? `Лимит ${formatNumber(weeklyBudget, " ₽")}`
                        : "Можно заполнить в анкете"
                    }
                    tone={
                      weeklyBudget == null
                        ? "default"
                        : isWeeklyOverBudget
                          ? "warn"
                          : "good"
                    }
                  />
                </div>

                <h3 className="mt-6 text-sm font-semibold uppercase tracking-[0.08em] text-slate-500">
                  Сводка за неделю
                </h3>
                <div className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Калории</span>
                    <strong>{formatNumber(weeklyTotals.calories, " ккал")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Стоимость</span>
                    <strong>≈ {formatNumber(weeklyTotals.estimated_cost_rub, " ₽")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Бюджет</span>
                    <strong>
                      {weeklyBudget != null
                        ? `${Math.round(weeklyBudget)} ₽`
                        : "Не указан"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Белки</span>
                    <strong>{formatNumber(weeklyTotals.protein, " г")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Жиры</span>
                    <strong>{formatNumber(weeklyTotals.fat, " г")}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Углеводы</span>
                    <strong>{formatNumber(weeklyTotals.carbs, " г")}</strong>
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

              <div className="rounded-3xl bg-emerald-950 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Параметры недели</h2>
                <div className="mt-4 space-y-3 text-sm text-slate-200">
                  <div className="rounded-2xl bg-white/10 p-4">
                    Приемов пищи в день:{" "}
                    {basePlan?.meals_per_day ?? profile?.meals_per_day ?? "не указано"}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Дней в плане: {WEEK_DAYS.length}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Общая стоимость: ≈ {formatNumber(weeklyTotals.estimated_cost_rub, " ₽")}
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Бюджет:{" "}
                    {weeklyBudget != null
                      ? `${Math.round(weeklyBudget)} ₽ в неделю`
                      : "не указан"}
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
