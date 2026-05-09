import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchReadiness } from "../lib/recommendations";

const CHECK_LABELS = {
  basic: "Базовые данные",
  goal: "Цель и активность",
  region: "Регион",
  budget: "Бюджет",
  food_preferences: "Любимые продукты, ограничения и аллергии",
  meal_mode: "Количество приемов пищи",
};

function formatNumber(value, options = {}) {
  if (value == null || Number.isNaN(Number(value))) {
    return "Нет данных";
  }

  return Number(value).toLocaleString("ru-RU", options);
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return "Нет данных";
  }

  return `${Math.round(Number(value) * 100)}%`;
}

function MetricCard({ label, value, hint, tone = "default" }) {
  const className =
    tone === "subtle"
      ? "rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-100"
      : "rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200";

  return (
    <div className={className}>
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-3 break-words text-2xl font-semibold text-slate-950">
        {value}
      </p>
      {hint ? <p className="mt-2 text-sm leading-6 text-slate-500">{hint}</p> : null}
    </div>
  );
}

function ChecklistItem({ label, done }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-slate-100 py-3 last:border-b-0">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      <span
        className={`rounded-full px-3 py-1 text-xs font-semibold ${
          done
            ? "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100"
            : "bg-amber-50 text-amber-700 ring-1 ring-amber-100"
        }`}
      >
        {done ? "Готово" : "Нужно заполнить"}
      </span>
    </div>
  );
}

export default function ReadinessPage({ authSession }) {
  const [readiness, setReadiness] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const accessToken = authSession?.accessToken;

  const loadReadiness = useCallback(async () => {
    if (!accessToken) {
      return;
    }

    setIsLoading(true);
    setErrorMessage("");

    try {
      setReadiness(await fetchReadiness(accessToken));
    } catch (error) {
      setErrorMessage(error.message || "Не удалось загрузить готовность системы.");
    } finally {
      setIsLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    loadReadiness();
  }, [loadReadiness]);

  const profileChecks = readiness?.profile_checks ?? {};
  const dataset = readiness?.dataset ?? {};
  const feedback = readiness?.feedback ?? {};
  const model = readiness?.model ?? {};
  const eventCount = useMemo(
    () =>
      Object.values(readiness?.events ?? {}).reduce(
        (sum, value) => sum + Number(value || 0),
        0,
      ),
    [readiness],
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Отчет
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Готовность системы
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Короткая сводка по анкете, данным, обратной связи и обученной
              модели для демонстрации проекта.
            </p>
          </div>

          <button
            type="button"
            onClick={loadReadiness}
            disabled={isLoading}
            className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Обновляем..." : "Обновить"}
          </button>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Загружаем показатели...</h2>
            <p className="mt-3 text-slate-600">
              Сверяем профиль, датасет и артефакты рекомендательной модели.
            </p>
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              <MetricCard
                label="Профиль пользователя"
                value={`${readiness?.profile_completion_percent ?? 0}%`}
                hint="Заполненность анкеты для персонализации."
              />
              <MetricCard
                label="Рецепты"
                value={formatNumber(dataset.recipes_count)}
                hint={`${formatNumber(dataset.recipe_features_count)} с признаками`}
              />
              <MetricCard
                label="Обратная связь"
                value={formatNumber(dataset.total_feedback_count)}
                hint={`${formatNumber(dataset.bootstrap_feedback_count)} bootstrap-оценок`}
              />
              <MetricCard
                label="Модель рекомендаций"
                value={model.exists ? "Подключена" : "Не обучена"}
                hint={model.model_type || "Нужен запуск retrain-скрипта"}
              />
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
              <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold text-slate-950">
                  Анкета и действия
                </h2>
                <div className="mt-4">
                  {Object.entries(CHECK_LABELS).map(([key, label]) => (
                    <ChecklistItem
                      key={key}
                      label={label}
                      done={Boolean(profileChecks[key])}
                    />
                  ))}
                </div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  <MetricCard
                    label="Оценки"
                    value={formatNumber(feedback.total)}
                    hint={`${formatNumber(feedback.liked_count)} понравилось`}
                    tone="subtle"
                  />
                  <MetricCard
                    label="События"
                    value={formatNumber(eventCount)}
                    hint="Открытия, лайки и действия"
                    tone="subtle"
                  />
                  <MetricCard
                    label="Причины"
                    value={formatNumber(feedback.reasoned_count)}
                    hint="Почему блюдо не подошло"
                    tone="subtle"
                  />
                </div>
              </section>

              <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
                <h2 className="text-xl font-semibold text-slate-950">
                  Датасет и качество модели
                </h2>
                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  <MetricCard
                    label="Покрытие цен"
                    value={formatPercent(dataset.avg_price_coverage)}
                    hint={`${formatNumber(dataset.priced_products_count)} продуктов с ценой`}
                    tone="subtle"
                  />
                  <MetricCard
                    label="Локализация"
                    value={formatNumber(dataset.localized_recipes_count)}
                    hint="Рецепты с русским названием"
                    tone="subtle"
                  />
                  <MetricCard
                    label="Validation AUC"
                    value={formatNumber(model.validation_roc_auc, {
                      maximumFractionDigits: 3,
                    })}
                    hint={`AP ${formatNumber(model.validation_average_precision, {
                      maximumFractionDigits: 3,
                    })}`}
                    tone="subtle"
                  />
                  <MetricCard
                    label="Test AUC"
                    value={formatNumber(model.test_roc_auc, {
                      maximumFractionDigits: 3,
                    })}
                    hint={`AP ${formatNumber(model.test_average_precision, {
                      maximumFractionDigits: 3,
                    })}`}
                    tone="subtle"
                  />
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
