import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { PageSkeleton } from "../components/Skeleton";
import { fetchMyProfile } from "../lib/profile";
import {
  fetchMealPlan,
  fetchRecommendations,
  fetchShoppingList,
} from "../lib/recommendations";

function formatNumber(value, suffix = "") {
  if (value == null || Number.isNaN(Number(value))) {
    return "Нет данных";
  }

  return `${Math.round(Number(value)).toLocaleString("ru-RU")}${suffix}`;
}

function formatCurrency(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "Нет данных";
  }

  return `≈ ${Math.round(Number(value)).toLocaleString("ru-RU")} ₽`;
}

const GOAL_LABELS = {
  lose_weight: "Снижение веса",
  maintain_weight: "Поддержание веса",
  gain_weight: "Набор веса",
};

function formatGoal(value) {
  return GOAL_LABELS[value] ?? value;
}

function DashboardMetric({ label, value, hint }) {
  return (
    <div className="min-w-0 rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 break-words text-2xl font-bold leading-tight text-slate-950">
        {value}
      </p>
      {hint ? <p className="mt-2 text-sm leading-5 text-slate-500">{hint}</p> : null}
    </div>
  );
}

function QuickLink({ to, title, text }) {
  return (
    <Link
      to={to}
      className="block rounded-2xl border border-slate-200 bg-white px-4 py-4 transition hover:border-slate-300 hover:bg-slate-50"
    >
      <span className="text-sm font-semibold text-slate-950">{title}</span>
      <span className="mt-1 block text-sm leading-5 text-slate-500">{text}</span>
    </Link>
  );
}

function PublicHome() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto flex max-w-6xl flex-col px-6 py-16">
        <div className="max-w-3xl">
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            TastePlanner
          </span>

          <h1 className="mt-6 text-5xl font-bold tracking-tight">
            Цифровой помощник для планирования рациона
          </h1>

          <p className="mt-5 text-lg text-slate-600">
            Собирайте рацион с учетом любимых продуктов, аллергий, бюджета,
            региона, калорийности и времени приготовления.
          </p>

          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              to="/onboarding"
              className="rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Начать подбор рациона
            </Link>

            <Link
              to="/auth"
              className="rounded-2xl border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Войти
            </Link>
          </div>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold tracking-tight">Персонализация</h2>
            <p className="mt-3 text-sm text-slate-600">
              Учет целей, бюджета, любимых и нелюбимых продуктов, аллергий и
              региональных особенностей.
            </p>
          </div>

          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold tracking-tight">План питания</h2>
            <p className="mt-3 text-sm text-slate-600">
              Формирование дневного или недельного меню с учетом КБЖУ и
              предпочтений пользователя.
            </p>
          </div>

          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold tracking-tight">Список покупок</h2>
            <p className="mt-3 text-sm text-slate-600">
              Автоматическое создание списка продуктов на основе выбранного
              рациона.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function HomePage({
  authSession,
  isAuthenticated,
  isAuthReady,
  favorites = [],
  notify,
}) {
  const [dashboard, setDashboard] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;
  const userName = authSession?.user?.name || "Добро пожаловать";

  const loadDashboard = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setIsLoading(true);
    setErrorMessage("");

    try {
      const profile = await fetchMyProfile(accessToken);
      const mealsPerDay = profile.meals_per_day || undefined;
      const [mealPlanResult, recommendationsResult, shoppingResult] =
        await Promise.allSettled([
          fetchMealPlan(accessToken, { mealsPerDay }),
          fetchRecommendations(accessToken, { limit: 4 }),
          fetchShoppingList(accessToken, { days: 1, mealsPerDay }),
        ]);

      setDashboard({
        profile,
        mealPlan:
          mealPlanResult.status === "fulfilled" ? mealPlanResult.value : null,
        recommendations:
          recommendationsResult.status === "fulfilled"
            ? recommendationsResult.value
            : null,
        shopping:
          shoppingResult.status === "fulfilled" ? shoppingResult.value : null,
      });
      notify?.({ title: "Главная обновлена", message: "План и покупки актуальны." });

      if (
        mealPlanResult.status === "rejected" &&
        recommendationsResult.status === "rejected" &&
        shoppingResult.status === "rejected"
      ) {
        setErrorMessage("Не удалось загрузить данные главного экрана.");
      }
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить профиль.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken, notify]);

  useEffect(() => {
    if (isAuthenticated) {
      loadDashboard();
    }
  }, [isAuthenticated, loadDashboard]);

  const meals = dashboard?.mealPlan?.meals ?? [];
  const totals = dashboard?.mealPlan?.totals ?? {};
  const recommendations = dashboard?.recommendations?.items ?? [];
  const shoppingItems = dashboard?.shopping?.items ?? [];
  const dailyBudget = dashboard?.profile?.daily_budget_rub;
  const profileHints = useMemo(() => {
    const profile = dashboard?.profile;

    if (!profile) {
      return [];
    }

    return [
      profile.goal ? `Цель: ${formatGoal(profile.goal)}` : null,
      profile.meals_per_day
        ? `Приемов пищи: ${profile.meals_per_day}`
        : null,
      dailyBudget ? `Бюджет: ${formatCurrency(dailyBudget)}` : null,
    ].filter(Boolean);
  }, [dashboard?.profile, dailyBudget]);

  if (!isAuthReady) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-6xl items-center justify-center px-6">
        <div className="rounded-2xl bg-white px-6 py-4 text-sm text-slate-500 ring-1 ring-slate-200">
          Проверяем сессию...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <PublicHome />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Сегодня
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              {userName}, ваш рацион на сегодня
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Короткая сводка по меню, покупкам и свежим рецептам в одном месте.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={loadDashboard}
              disabled={isLoading}
              className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Обновляем..." : "Обновить"}
            </button>

            <Link
              to="/meal-plan/week"
              className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              План на неделю
            </Link>
          </div>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading && !dashboard ? (
          <PageSkeleton rows={3} />
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <DashboardMetric
                label="Калории"
                value={formatNumber(totals.calories, " ккал")}
                hint={
                  dashboard?.mealPlan?.daily_target_calories != null
                    ? `Цель: ${formatNumber(
                        dashboard.mealPlan.daily_target_calories,
                        " ккал",
                      )}`
                    : "Цель можно уточнить в анкете"
                }
              />
              <DashboardMetric
                label="Стоимость"
                value={formatCurrency(totals.estimated_cost_rub)}
                hint={
                  dailyBudget != null
                    ? `Дневной бюджет: ${formatCurrency(dailyBudget)}`
                    : "Бюджет можно добавить в профиле"
                }
              />
              <DashboardMetric
                label="План"
                value={`${meals.length || 0} блюд`}
                hint={
                  dashboard?.profile?.meals_per_day
                    ? `Выбрано: ${dashboard.profile.meals_per_day} приемов`
                    : "Количество приемов настраивается в анкете"
                }
              />
              <DashboardMetric
                label="Покупки"
                value={`${shoppingItems.length || 0} позиций`}
                hint={
                  dashboard?.shopping?.estimated_total_cost_rub != null
                    ? formatCurrency(dashboard.shopping.estimated_total_cost_rub)
                    : "Список обновится после плана"
                }
              />
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-[1.35fr_0.65fr]">
              <section className="space-y-6">
                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="text-2xl font-semibold">План на день</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        Блюда, которые уже распределены по приемам пищи.
                      </p>
                    </div>
                    <Link
                      to="/meal-plan"
                      className="inline-flex min-h-10 items-center justify-center rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                    >
                      Открыть план
                    </Link>
                  </div>

                  {meals.length > 0 ? (
                    <div className="mt-5 divide-y divide-slate-100">
                      {meals.slice(0, 4).map((meal) => (
                        <div
                          key={`${meal.slot}-${meal.recipe.id}`}
                          className="grid gap-3 py-4 sm:grid-cols-[1fr_auto]"
                        >
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-emerald-700">
                              {meal.slot}
                            </p>
                            <p className="mt-1 truncate text-base font-semibold text-slate-950">
                              {meal.recipe.title}
                            </p>
                          </div>
                          <div className="flex flex-wrap gap-2 text-sm text-slate-600 sm:justify-end">
                            <span className="inline-flex min-h-11 min-w-24 items-center justify-center rounded-full bg-slate-100 px-4 py-2 text-center">
                              {formatNumber(meal.recipe.calories, " ккал")}
                            </span>
                            <span className="inline-flex min-h-11 min-w-24 items-center justify-center rounded-full bg-slate-100 px-4 py-2 text-center">
                              {formatCurrency(meal.recipe.estimated_cost_rub)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-5 rounded-2xl bg-slate-50 p-5 text-sm text-slate-600">
                      План еще не собран. Откройте анкету или страницу питания,
                      чтобы получить блюда на день.
                    </div>
                  )}
                </div>

                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h2 className="text-2xl font-semibold">Рекомендации</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        Несколько блюд, которые можно открыть или добавить в избранное.
                      </p>
                    </div>
                    <Link
                      to="/recipes"
                      className="inline-flex min-h-10 items-center justify-center rounded-2xl border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
                    >
                      Все рецепты
                    </Link>
                  </div>

                  <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {recommendations.slice(0, 4).map((recipe) => (
                      <Link
                        key={recipe.id}
                        to="/recipes"
                        className="rounded-2xl border border-slate-200 p-4 transition hover:border-slate-300 hover:bg-slate-50"
                      >
                        <p className="line-clamp-2 min-h-10 text-sm font-semibold leading-5 text-slate-950">
                          {recipe.title}
                        </p>
                        <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium text-slate-600">
                          <span className="rounded-full bg-slate-100 px-2.5 py-1">
                            {formatNumber(recipe.calories, " ккал")}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1">
                            {formatCurrency(recipe.estimated_cost_rub)}
                          </span>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1">
                            {recipe.total_minutes
                              ? `${recipe.total_minutes} мин`
                              : "Время нет"}
                          </span>
                        </div>
                      </Link>
                    ))}
                  </div>
                </div>
              </section>

              <aside className="space-y-6">
                <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
                  <h2 className="text-xl font-semibold">Быстрые действия</h2>
                  <div className="mt-5 grid gap-3">
                    <QuickLink
                      to="/onboarding"
                      title="Анкета"
                      text="Обновить цель, бюджет, аллергии и продукты."
                    />
                    <QuickLink
                      to="/shopping-list"
                      title="Покупки"
                      text="Открыть список продуктов на день или неделю."
                    />
                    <QuickLink
                      to="/favorites"
                      title="Избранное"
                      text={`Сохранено рецептов: ${favorites.length}.`}
                    />
                  </div>
                </div>

                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <h2 className="text-xl font-semibold">Профиль вкусов</h2>
                  {profileHints.length > 0 ? (
                    <div className="mt-5 space-y-3 text-sm text-slate-600">
                      {profileHints.map((hint) => (
                        <div
                          key={hint}
                          className="rounded-2xl bg-slate-50 px-4 py-3"
                        >
                          {hint}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-slate-600">
                      Заполните анкету, чтобы рекомендации точнее учитывали ваш
                      режим и ограничения.
                    </p>
                  )}
                </div>

                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <h2 className="text-xl font-semibold">Покупки на сегодня</h2>
                  {shoppingItems.length > 0 ? (
                    <div className="mt-5 space-y-3">
                      {shoppingItems.slice(0, 5).map((item) => (
                        <div
                          key={item.id}
                          className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-sm"
                        >
                          <span className="min-w-0 truncate font-medium text-slate-800">
                            {item.name}
                          </span>
                          <span className="shrink-0 text-slate-500">
                            {item.quantity}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-slate-600">
                      Список появится после формирования плана питания.
                    </p>
                  )}
                </div>
              </aside>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
