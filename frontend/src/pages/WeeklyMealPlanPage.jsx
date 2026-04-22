import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

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
  };
}

export default function WeeklyMealPlanPage({ authSession }) {
  const [basePlan, setBasePlan] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;

  const loadPlan = async (showFullLoader = false) => {
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
      setBasePlan(payload);
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить недельный план.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadPlan(true);
  }, [accessToken]);

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
      return { calories: 0, protein: 0, fat: 0, carbs: 0 };
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
    };
  }, [weeklyPlan]);

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
              Здесь собран недельный обзор на базе текущего ML-плана дня, чтобы
              было удобнее смотреть рацион сразу по всем дням.
            </p>
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
              className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
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
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Собираем неделю...</h2>
            <p className="mt-3 text-slate-600">
              Сейчас подготовим рацион по дням недели.
            </p>
          </div>
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
                            {formatNumber(meal.recipe.calories, " ккал")}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </section>

            <aside className="space-y-6">
              <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold">Сводка за неделю</h2>
                <div className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Калории</span>
                    <strong>{formatNumber(weeklyTotals.calories, " ккал")}</strong>
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

              <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Как использовать</h2>
                <div className="mt-4 space-y-3 text-sm text-slate-200">
                  <div className="rounded-2xl bg-white/10 p-4">
                    Смотрите распределение блюд по всей неделе одним экраном
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    Возвращайтесь в дневной план, если нужно заменить отдельное блюдо
                  </div>
                  <div className="rounded-2xl bg-white/10 p-4">
                    После новых лайков и обновления неделя тоже станет точнее
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
