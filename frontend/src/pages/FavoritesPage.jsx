import RecipeCard from "../components/RecipeCard";

export default function FavoritesPage({ favorites, toggleFavorite }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <span className="inline-flex rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-700">
            Избранное
          </span>
          <h1 className="mt-4 text-4xl font-bold tracking-tight">
            Избранные рецепты
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Здесь сохраняются рецепты, которые пользователь отметил как
            интересные для дальнейшего использования.
          </p>
        </div>

        {favorites.length === 0 ? (
          <div className="rounded-3xl bg-white p-10 text-center shadow-sm ring-1 ring-slate-200">
            <h2 className="text-2xl font-semibold">Пока ничего нет</h2>
            <p className="mt-3 text-slate-600">
              Отмечайте рецепты звездой, чтобы они появлялись на этой странице.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2">
            {favorites.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                secondaryAction={{
                  label: "Удалить",
                  onClick: () => toggleFavorite(recipe),
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
