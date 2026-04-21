import { Link } from "react-router-dom";

export default function ProfilePage() {
  const user = {
    name: "Алина",
    age: 21,
    goal: "Поддержание веса",
    activity: "Умеренный",
    budget: "Средний",
    mealsPerDay: 4,
    cookingLevel: "Средний",
    allergies: ["Лактоза"],
    dislikedFoods: ["Грибы", "Острое", "Лук"],
    favoriteCuisines: ["Итальянская", "Японская", "Средиземноморская"],
  };

  const stats = [
    { label: "Составлено рационов", value: 12 },
    { label: "Любимых блюд", value: 18 },
    { label: "Дней отслеживания", value: 24 },
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Личный кабинет
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Профиль пользователя
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Здесь собрана основная информация о пользователе, его целях,
              предпочтениях и параметрах, которые используются для персонального
              подбора рациона.
            </p>
          </div>

          <div className="flex gap-3">
            <Link
              to="/onboarding"
              className="rounded-2xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Редактировать анкету
            </Link>
            <Link
              to="/meal-plan"
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Открыть план питания
            </Link>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 text-2xl font-bold text-emerald-700">
                  {user.name[0]}
                </div>

                <div>
                  <h2 className="text-2xl font-semibold">{user.name}</h2>
                  <p className="mt-1 text-sm text-slate-500">
                    Возраст: {user.age} · Цель: {user.goal}
                  </p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Основные параметры</h2>

              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Цель питания</p>
                  <p className="mt-1 font-semibold">{user.goal}</p>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Уровень активности</p>
                  <p className="mt-1 font-semibold">{user.activity}</p>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Бюджет</p>
                  <p className="mt-1 font-semibold">{user.budget}</p>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Приёмов пищи в день</p>
                  <p className="mt-1 font-semibold">{user.mealsPerDay}</p>
                </div>

                <div className="rounded-2xl bg-slate-50 p-4 sm:col-span-2">
                  <p className="text-sm text-slate-500">Кулинарные навыки</p>
                  <p className="mt-1 font-semibold">{user.cookingLevel}</p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Предпочтения и ограничения</h2>

              <div className="mt-6 space-y-5">
                <div>
                  <p className="mb-3 text-sm font-medium text-slate-500">
                    Любимые кухни
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {user.favoriteCuisines.map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="mb-3 text-sm font-medium text-slate-500">
                    Аллергии / непереносимости
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {user.allergies.map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-red-50 px-4 py-2 text-sm font-medium text-red-700"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="mb-3 text-sm font-medium text-slate-500">
                    Нелюбимые продукты
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {user.dislikedFoods.map((item) => (
                      <span
                        key={item}
                        className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Краткая статистика</h2>

              <div className="mt-5 space-y-3">
                {stats.map((stat) => (
                  <div
                    key={stat.label}
                    className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                  >
                    <span className="text-sm text-slate-600">{stat.label}</span>
                    <strong>{stat.value}</strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
              <h2 className="text-xl font-semibold">Быстрые действия</h2>

              <div className="mt-4 flex flex-col gap-3">
                <Link
                  to="/onboarding"
                  className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/20"
                >
                  Изменить предпочтения
                </Link>

                <Link
                  to="/meal-plan"
                  className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/20"
                >
                  Посмотреть рацион
                </Link>

                <button
                  type="button"
                  className="rounded-2xl bg-white/10 px-4 py-3 text-left text-sm font-medium text-white transition hover:bg-white/20"
                >
                  История прогресса
                </button>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}