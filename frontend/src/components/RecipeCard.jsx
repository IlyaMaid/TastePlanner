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

function InfoTile({
  label,
  value,
  valueClassName = "",
  className = "",
  compact = false,
}) {
  return (
    <div
      className={`min-w-0 rounded-2xl bg-slate-50 p-4 ${compact ? "w-fit min-w-[12rem]" : ""} ${className}`}
    >
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-slate-500">
        {label}
      </p>
      <p
        className={`mt-2 text-base font-semibold leading-snug text-slate-900 sm:text-lg [overflow-wrap:normal] [word-break:normal] ${valueClassName}`}
      >
        {value}
      </p>
    </div>
  );
}

export default function RecipeCard({
  recipe,
  variant = "default",
  isFavorite = false,
  onFavoriteToggle,
  secondaryAction,
}) {
  return (
    <article className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 transition-shadow hover:shadow-md">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <h2 className="max-w-xl text-2xl font-semibold leading-tight text-slate-950">
            {recipe.title}
          </h2>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600">
            {recipe.description}
          </p>
        </div>

        {variant === "favorite-toggle" ? (
          <button
            type="button"
            onClick={onFavoriteToggle}
            aria-pressed={isFavorite}
            aria-label={
              isFavorite ? "Убрать из избранного" : "Добавить в избранное"
            }
            className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border transition ${
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
            onClick={secondaryAction.onClick}
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-2xl border border-red-200 bg-red-50 px-4 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-100"
          >
            {secondaryAction.label}
          </button>
        ) : null}
      </div>

      <div className="mt-6 flex flex-wrap gap-3">
        <InfoTile
          label="Калории"
          value={`${recipe.calories} ккал`}
          className="min-w-[12rem] flex-1"
        />
        <InfoTile
          label="Кухня"
          value={recipe.cuisine}
          compact
          valueClassName="text-[1.02rem] sm:text-[1.15rem]"
        />
        <InfoTile
          label="Сложность"
          value={recipe.difficulty}
          className="min-w-[12rem] flex-1"
        />
      </div>
    </article>
  );
}
