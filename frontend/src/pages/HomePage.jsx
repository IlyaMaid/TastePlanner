import { Link } from "react-router-dom";

export default function HomePage() {
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
            Веб-приложение для формирования персонального плана питания на
            основе вкусовых предпочтений, ограничений, целей пользователя и
            образа жизни.
          </p>

          <div className="mt-8 flex gap-4">
            <Link
              to="/onboarding"
              className="rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Начать подбор рациона
            </Link>

            <button
              className="rounded-2xl border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700"
              type="button"
            >
              О проекте
            </button>
          </div>
        </div>

        <div className="mt-16 grid gap-6 md:grid-cols-3">
          <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
            <h2 className="text-xl font-semibold tracking-tight">Персонализация</h2>
            <p className="mt-3 text-sm text-slate-600">
              Учет целей, бюджета, любимых кухонь, аллергий и нелюбимых
              продуктов.
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