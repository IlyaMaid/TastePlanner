import { Link } from "react-router-dom";
import RecipeCard from "../components/RecipeCard";

export default function RecipesPage({ favorites, toggleFavorite }) {
  const recipes = [
    {
      id: 1,
      title: "Овсяная каша с бананом",
      description:
        "Полезный завтрак с хорошим балансом углеводов и клетчатки.",
      calories: 420,
      cuisine: "Европейская",
      difficulty: "Легко",
    },
    {
      id: 2,
      title: "Куриная грудка с гречкой",
      description: "Питательный обед для сбалансированного рациона.",
      calories: 560,
      cuisine: "Домашняя",
      difficulty: "Средне",
    },
    {
      id: 3,
      title: "Запечённый лосось с овощами",
      description: "Лёгкий и полезный ужин с высоким содержанием белка.",
      calories: 480,
      cuisine: "Средиземноморская",
      difficulty: "Средне",
    },
    {
      id: 4,
      title: "Йогурт с яблоком и орехами",
      description: "Быстрый перекус для поддержания энергии в течение дня.",
      calories: 220,
      cuisine: "Универсальная",
      difficulty: "Легко",
    },
  ];

  const isFavorite = (id) => favorites.some((item) => item.id === id);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Рецепты
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Подборка рецептов
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Здесь собраны блюда, которые могут быть рекомендованы
              пользователю на основе его предпочтений и целей питания.
            </p>
          </div>

          <Link
            to="/favorites"
            className="inline-flex min-h-11 items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-slate-400 hover:bg-slate-100"
          >
            Избранное{favorites.length > 0 ? ` · ${favorites.length}` : ""}
          </Link>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {recipes.map((recipe) => (
            <RecipeCard
              key={recipe.id}
              recipe={recipe}
              variant="favorite-toggle"
              isFavorite={isFavorite(recipe.id)}
              onFavoriteToggle={() => toggleFavorite(recipe)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
