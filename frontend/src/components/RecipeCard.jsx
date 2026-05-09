import { useEffect, useState } from "react";

function StarIcon({ filled }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className="h-5 w-5"
      fill={filled ? "currentColor" : "none"}
      stroke="currentColor"
      strokeWidth="1.8"
    >
      <path d="M12 3.75l2.55 5.16 5.7.83-4.13 4.02.98 5.67L12 16.76l-5.1 2.67.98-5.67-4.11-4.02 5.68-.83L12 3.75z" />
    </svg>
  );
}

function formatNumber(value) {
  if (value == null) {
    return null;
  }
  return Number(value).toLocaleString("ru-RU", {
    maximumFractionDigits: 1,
  });
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) {
    return null;
  }

  return `${Math.round(Number(value) * 100)}%`;
}

function DetailBlock({ title, children }) {
  return (
    <section className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-100">
      <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="flex min-h-20 flex-col justify-center rounded-2xl bg-slate-50 px-4 py-3 ring-1 ring-slate-100">
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
        {label}
      </p>
      <p className="mt-2 break-words text-base font-semibold text-slate-950">
        {value}
      </p>
    </div>
  );
}

function sourceLabel(source) {
  if (source === "curated_ru") {
    return "Русский датасет";
  }
  if (source === "povarenok") {
    return "Поварёнок";
  }
  return "Food.com";
}

function reasonDescription(reason) {
  if (reason.includes("аллерген")) {
    return "Блюдо не содержит выбранные аллергены и ограничения.";
  }
  if (reason.includes("бюджет")) {
    return "Стоимость блюда подходит под указанный бюджет.";
  }
  if (reason.includes("сезон")) {
    return "В рецепте есть продукты, актуальные для текущего сезона.";
  }
  if (reason.includes("Быстро")) {
    return "Рецепт не требует много времени на приготовление.";
  }
  if (reason.includes("калор")) {
    return "Калорийность близка к дневной цели пользователя.";
  }
  if (reason.includes("нелюбимых")) {
    return "В составе не найдено продуктов из списка нелюбимых.";
  }
  return "Фактор учтен при итоговом ранжировании рекомендации.";
}

export default function RecipeCard({
  recipe,
  variant = "default",
  isFavorite = false,
  onFavoriteToggle,
  onDislike,
  onFeedbackReason,
  onOpen,
  secondaryAction,
  isBusy = false,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const estimatedCost =
    recipe.estimatedCostRub != null
      ? `≈ ${formatNumber(recipe.estimatedCostRub)} ₽`
      : "Нет данных";
  const cookingSteps = recipe.cookingSteps ?? recipe.cooking_steps ?? [];
  const ingredients = recipe.ingredientsList ?? recipe.ingredientsPreview ?? [];
  const productDetails = recipe.productDetails ?? recipe.productDetailsPreview ?? [];
  const recommendationReasons = recipe.recommendationReasons ?? [];
  const isSeasonalNow = Boolean(recipe.is_seasonal_now ?? recipe.isSeasonalNow);
  const scoreMetrics = [
    ["Сходство", formatPercent(recipe.contentSimilarity ?? recipe.content_similarity)],
    ["Прогноз", formatPercent(recipe.predictedScore ?? recipe.predicted_score)],
    ["Совпадение", formatPercent(recipe.finalScore ?? recipe.final_score)],
  ].filter(([, value]) => value);

  const openRecipe = () => {
    if (!isOpen) {
      onOpen?.();
    }
    setIsOpen(true);
  };

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setIsOpen(false);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.body.style.overflow = "hidden";

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  const handleActionClick = (event, action) => {
    event.stopPropagation();
    action?.();
  };

  return (
    <>
      <article
        role="button"
        tabIndex={0}
        onClick={openRecipe}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            openRecipe();
          }
        }}
        className="cursor-pointer rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-emerald-400"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h2 className="line-clamp-2 text-xl font-semibold leading-tight text-slate-950">
              {recipe.title}
            </h2>
            {isSeasonalNow ? (
              <span className="mt-3 inline-flex rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-100">
                По сезону
              </span>
            ) : null}
          </div>

          {variant === "favorite-toggle" ? (
            <button
              type="button"
              onClick={(event) => handleActionClick(event, onFavoriteToggle)}
              disabled={isBusy}
              aria-pressed={isFavorite}
              aria-label={
                isFavorite ? "Убрать из избранного" : "Добавить в избранное"
              }
              className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border transition disabled:cursor-not-allowed disabled:opacity-60 ${
                isFavorite
                  ? "border-amber-200 bg-amber-100 text-amber-700 hover:bg-amber-200"
                  : "border-slate-200 bg-white text-slate-400 hover:border-slate-300 hover:text-amber-500"
              }`}
            >
              <StarIcon filled={isFavorite} />
            </button>
          ) : secondaryAction ? (
            <button
              type="button"
              onClick={(event) => handleActionClick(event, secondaryAction.onClick)}
              className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100"
            >
              {secondaryAction.label}
            </button>
          ) : null}
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <Metric label="Стоимость" value={estimatedCost} />
          <Metric label="Время" value={recipe.metaLabel || "Нет данных"} />
        </div>

        {recommendationReasons.length > 0 ? (
          <div className="mt-4 flex flex-wrap gap-2">
            {recommendationReasons.slice(0, 3).map((reason) => (
              <span
                key={reason}
                className="rounded-full bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 ring-1 ring-slate-200"
              >
                {reason}
              </span>
            ))}
          </div>
        ) : null}
      </article>

      {isOpen ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/60 px-4 py-6 sm:py-10"
          onClick={() => setIsOpen(false)}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label={recipe.title}
            className="w-full max-w-5xl rounded-3xl bg-white p-5 shadow-2xl ring-1 ring-slate-200 sm:p-8"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-medium text-emerald-700">
                  Расширенный рецепт
                </p>
                <h2 className="mt-2 text-2xl font-semibold leading-tight text-slate-950 sm:text-3xl">
                  {recipe.title}
                </h2>
                <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
                  {recipe.description || "Описание пока не добавлено."}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setIsOpen(false)}
                aria-label="Закрыть"
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-slate-200 text-2xl leading-none text-slate-500 transition hover:bg-slate-50 hover:text-slate-900"
              >
                ×
              </button>
            </div>

            <div className="mt-6 grid gap-3 sm:grid-cols-4">
              <Metric
                label="Калории"
                value={recipe.calories != null ? `${recipe.calories} ккал` : "Нет данных"}
              />
              <Metric label="Стоимость" value={estimatedCost} />
              <Metric label="Время" value={recipe.metaLabel || "Нет данных"} />
              <Metric
                label="Источник"
                value={sourceLabel(recipe.source)}
              />
            </div>

            {recommendationReasons.length > 0 ? (
              <div className="mt-5 flex flex-wrap gap-2">
                {recommendationReasons.map((reason) => (
                  <span
                    key={reason}
                    className="rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-100"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            ) : null}

            {scoreMetrics.length > 0 ? (
              <div className="mt-5 grid gap-3 sm:grid-cols-3">
                {scoreMetrics.map(([label, value]) => (
                  <Metric key={label} label={label} value={value} />
                ))}
              </div>
            ) : null}

            {recommendationReasons.length > 0 ? (
              <div className="mt-5 rounded-2xl bg-emerald-50 p-4 ring-1 ring-emerald-100">
                <h3 className="text-sm font-semibold text-emerald-950">
                  Почему рекомендовано
                </h3>
                <div className="mt-3 grid gap-3 sm:grid-cols-2">
                  {recommendationReasons.map((reason) => (
                    <div
                      key={reason}
                      className="rounded-2xl bg-white/80 px-4 py-3 text-sm"
                    >
                      <p className="font-semibold text-emerald-800">{reason}</p>
                      <p className="mt-1 leading-5 text-emerald-900/70">
                        {reasonDescription(reason)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="mt-6 grid gap-4 lg:grid-cols-[0.95fr_1.05fr]">
              <div className="space-y-4">
                <DetailBlock title="Ингредиенты">
                  {ingredients.length > 0 ? (
                    <ul className="space-y-2 text-sm leading-6 text-slate-700">
                      {ingredients.map((ingredient, index) => (
                        <li key={`${index}-${ingredient}`}>{ingredient}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">Нет данных.</p>
                  )}
                </DetailBlock>

                <DetailBlock title="Стоимость и продукты">
                  {productDetails.length > 0 ? (
                    <ul className="space-y-2 text-sm leading-6 text-slate-700">
                      {productDetails.map((product, index) => (
                        <li key={`${index}-${product}`}>{product}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-slate-500">Нет данных по продуктам.</p>
                  )}
                </DetailBlock>
              </div>

              <DetailBlock title="Способ приготовления">
                {cookingSteps.length > 0 ? (
                  <ol className="space-y-3 text-sm leading-6 text-slate-700">
                    {cookingSteps.map((step, index) => (
                      <li key={`${index}-${step}`} className="flex gap-3">
                        <span className="font-semibold text-slate-950">
                          {index + 1}.
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="text-sm text-slate-500">
                    Способ приготовления пока не добавлен для этого рецепта.
                  </p>
                )}
              </DetailBlock>
            </div>

            {onDislike || onFavoriteToggle || onFeedbackReason ? (
              <div className="mt-6 border-t border-slate-200 pt-5">
                {onFeedbackReason ? (
                  <div className="mb-4 flex flex-wrap gap-2">
                    {[
                      {
                        label: "Слишком дорого",
                        payload: { reason: "too_expensive", too_expensive: true },
                      },
                      {
                        label: "Долго готовить",
                        payload: { reason: "too_long", too_long: true },
                      },
                      {
                        label: "Не люблю ингредиенты",
                        payload: {
                          reason: "contains_disliked",
                          contains_disliked: true,
                        },
                      },
                      {
                        label: "Много калорий",
                        payload: { reason: "too_many_calories", too_many_calories: true },
                      },
                    ].map((option) => (
                      <button
                        key={option.payload.reason}
                        type="button"
                        onClick={() => {
                          onFeedbackReason(option.payload);
                          setIsOpen(false);
                        }}
                        className="rounded-full border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 transition hover:border-slate-300 hover:bg-slate-50"
                      >
                        {option.label}
                      </button>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap justify-end gap-3">
                  {onDislike ? (
                    <button
                      type="button"
                      onClick={() => {
                        onDislike();
                        setIsOpen(false);
                      }}
                      className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                    >
                      Не подходит
                    </button>
                  ) : null}
                  {onFavoriteToggle ? (
                    <button
                      type="button"
                      onClick={() => {
                        onFavoriteToggle();
                        setIsOpen(false);
                      }}
                      className="inline-flex min-h-11 items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                    >
                      {isFavorite ? "Убрать из избранного" : "Добавить в избранное"}
                    </button>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </>
  );
}
