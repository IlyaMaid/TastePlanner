import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchMyProfile } from "../lib/profile";
import { fetchShoppingList, saveUserEvent } from "../lib/recommendations";

const BOUGHT_STORAGE_KEY = "tasteplanner.shopping.bought";

function formatCurrency(value) {
  return Number(value || 0).toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
  });
}

function loadBoughtMap() {
  try {
    return JSON.parse(localStorage.getItem(BOUGHT_STORAGE_KEY) || "{}");
  } catch {
    return {};
  }
}

export default function ShoppingListPage({ authSession }) {
  const [payload, setPayload] = useState(null);
  const [boughtMap, setBoughtMap] = useState(loadBoughtMap);
  const [days, setDays] = useState(7);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const accessToken = authSession?.accessToken;

  const loadShoppingList = useCallback(async (nextDays, showFullLoader = false) => {
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
      const profile = await fetchMyProfile(accessToken);
      const nextPayload = await fetchShoppingList(accessToken, {
        days: nextDays,
        mealsPerDay: profile.meals_per_day,
      });
      setPayload(nextPayload);
    } catch (error) {
      setErrorMessage(error.message || "Не удалось сформировать список покупок.");
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadShoppingList(days, true);
  }, [days, loadShoppingList]);

  useEffect(() => {
    localStorage.setItem(BOUGHT_STORAGE_KEY, JSON.stringify(boughtMap));
  }, [boughtMap]);

  const items = useMemo(() => payload?.items ?? [], [payload?.items]);
  const groupedItems = useMemo(
    () =>
      items.reduce((acc, item) => {
        if (!acc[item.category]) {
          acc[item.category] = [];
        }
        acc[item.category].push(item);
        return acc;
      }, {}),
    [items],
  );

  const boughtItems = items.filter((item) => boughtMap[item.id]).length;
  const remainingItems = items.length - boughtItems;
  const progress = items.length > 0 ? Math.round((boughtItems / items.length) * 100) : 0;
  const remainingCost = items
    .filter((item) => !boughtMap[item.id])
    .reduce((sum, item) => sum + (item.estimated_cost_rub || 0), 0);
  const dailyBudget = payload?.preference_profile?.daily_budget_rub;
  const weeklyBudget = payload?.preference_profile?.weekly_budget_rub;

  const toggleBought = (item) => {
    const nextBought = !boughtMap[item.id];
    setBoughtMap((current) => ({
      ...current,
      [item.id]: !current[item.id],
    }));

    if (accessToken) {
      saveUserEvent(accessToken, {
        event_type: "shopping_item_toggle",
        payload_json: {
          item_id: item.id,
          item_name: item.name,
          bought: nextBought,
        },
      }).catch(() => {});
    }
  };

  const handleDaysChange = (nextDays) => {
    setDays(nextDays);
  };

  const resetBought = () => {
    setBoughtMap({});
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Список покупок
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Продукты для рациона
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Список собирается из выбранного рациона, группируется по отделам
              магазина и показывает примерную стоимость.
            </p>
          </div>

          <div className="flex flex-wrap gap-3">
            <div className="flex rounded-2xl bg-slate-100 p-1">
              {[1, 7].map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => handleDaysChange(value)}
                  className={`rounded-xl px-4 py-2 text-sm font-medium transition ${
                    days === value
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {value === 1 ? "На день" : "На неделю"}
                </button>
              ))}
            </div>

            <button
              type="button"
              onClick={() => loadShoppingList(days, false)}
              disabled={isLoading || isRefreshing}
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isRefreshing ? "Обновляем..." : "Сформировать заново"}
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
            <h2 className="text-2xl font-semibold">Собираем список...</h2>
            <p className="mt-3 text-slate-600">
              Подбираем продукты из текущего плана питания.
            </p>
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Список пока пуст</h2>
            <p className="mt-3 text-slate-600">
              Сначала сформируйте рацион, затем обновите список покупок.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <section className="space-y-6">
              {Object.entries(groupedItems).map(([category, categoryItems]) => (
                <div
                  key={category}
                  className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
                >
                  <div className="flex items-center justify-between gap-4">
                    <h2 className="text-xl font-semibold">{category}</h2>
                    <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                      {categoryItems.length}
                    </span>
                  </div>

                  <div className="mt-5 space-y-3">
                    {categoryItems.map((item) => {
                      const isBought = Boolean(boughtMap[item.id]);
                      return (
                        <label
                          key={item.id}
                          className={`flex cursor-pointer flex-col gap-3 rounded-2xl border px-4 py-4 transition sm:flex-row sm:items-center sm:justify-between ${
                            isBought
                              ? "border-emerald-200 bg-emerald-50"
                              : "border-slate-200 bg-white hover:bg-slate-50"
                          }`}
                        >
                          <div className="flex items-start gap-3">
                            <input
                              type="checkbox"
                              checked={isBought}
                              onChange={() => toggleBought(item)}
                              className="mt-1 h-4 w-4 rounded border-slate-300"
                            />
                            <div>
                              <p
                                className={`font-medium ${
                                  isBought
                                    ? "text-slate-400 line-through"
                                    : "text-slate-900"
                                }`}
                              >
                                {item.name}
                              </p>
                              <p className="mt-1 text-sm text-slate-500">
                                {item.quantity} · используется {item.uses} раз
                              </p>
                              {item.recipes?.length > 0 ? (
                                <p className="mt-1 text-xs text-slate-400">
                                  Для: {item.recipes.join(", ")}
                                </p>
                              ) : null}
                            </div>
                          </div>

                          <div className="text-left sm:text-right">
                            <p className="text-sm font-semibold text-slate-900">
                              ≈ {formatCurrency(item.estimated_cost_rub)} ₽
                            </p>
                            <p className="mt-1 text-xs text-slate-500">
                              {item.calories_per_100g
                                ? `${Math.round(item.calories_per_100g)} ккал/100 г`
                                : "ккал нет"}
                            </p>
                          </div>
                        </label>
                      );
                    })}
                  </div>
                </div>
              ))}
            </section>

            <aside className="space-y-6">
              <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold">Сводка</h2>
                <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-emerald-500 transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>

                <div className="mt-5 space-y-3 text-sm">
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Период</span>
                    <strong>{payload?.days === 1 ? "1 день" : "7 дней"}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Всего позиций</span>
                    <strong>{items.length}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Куплено</span>
                    <strong>{boughtItems}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Осталось</span>
                    <strong>{remainingItems}</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Стоимость</span>
                    <strong>≈ {formatCurrency(payload?.estimated_total_cost_rub)} ₽</strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Бюджет</span>
                    <strong>
                      {payload?.days === 1 && dailyBudget != null
                        ? `${formatCurrency(dailyBudget)} ₽`
                        : weeklyBudget != null
                          ? `${formatCurrency(weeklyBudget)} ₽`
                          : "Не указан"}
                    </strong>
                  </div>
                  <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                    <span>Осталось купить</span>
                    <strong>≈ {formatCurrency(remainingCost)} ₽</strong>
                  </div>
                </div>
              </div>

              {payload?.regional_food_zone ? (
                <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                  <h2 className="text-xl font-semibold">Регион</h2>
                  <p className="mt-3 text-sm font-semibold text-emerald-700">
                    {payload.regional_food_zone.name_ru}
                  </p>
                  <p className="mt-3 text-sm leading-6 text-slate-600">
                    {payload.regional_food_zone.summary_ru}
                  </p>
                </div>
              ) : null}

              <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Действия</h2>
                <div className="mt-4 flex flex-col gap-3">
                  <button
                    type="button"
                    onClick={resetBought}
                    className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/20"
                  >
                    Сбросить отметки
                  </button>
                  <button
                    type="button"
                    onClick={() => window.print()}
                    className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/20"
                  >
                    Распечатать список
                  </button>
                </div>
              </div>
            </aside>
          </div>
        )}
      </div>
    </div>
  );
}
