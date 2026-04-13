export default function TastePlannerOnboardingPage() {
  const goals = ["Похудение", "Поддержание веса", "Набор массы", "Здоровое питание"];
  const cuisines = ["Русская", "Итальянская", "Японская", "Средиземноморская", "Индийская", "Мексиканская"];
  const dislikes = ["Острое", "Молочные продукты", "Рыба", "Грибы", "Лук", "Брокколи"];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-3xl bg-white p-8 shadow-sm ring-1 ring-slate-200">
            <div className="mb-8">
              <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
                TastePlanner · Персональный помощник питания
              </span>
              <h1 className="mt-4 text-4xl font-bold tracking-tight">
                Создайте рацион, который подходит именно вам
              </h1>
              <p className="mt-3 max-w-2xl text-base text-slate-600">
                Заполните короткий профиль, и система подберёт персональный план питания с учётом ваших вкусов,
                ограничений, бюджета и целей.
              </p>
            </div>

            <form className="space-y-8">
              <div className="grid gap-5 md:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Ваше имя</span>
                  <input
                    type="text"
                    placeholder="Например, Алина"
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                  />
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Возраст</span>
                  <input
                    type="number"
                    placeholder="22"
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                  />
                </label>
              </div>

              <div>
                <h2 className="text-lg font-semibold">1. Цель питания</h2>
                <p className="mt-1 text-sm text-slate-500">Выберите основную цель, чтобы мы могли подобрать подходящую калорийность и БЖУ.</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                  {goals.map((goal) => (
                    <button
                      key={goal}
                      type="button"
                      className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium transition hover:border-emerald-300 hover:bg-emerald-50"
                    >
                      {goal}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Бюджет на неделю</span>
                  <select className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-slate-400">
                    <option>Минимальный</option>
                    <option>Средний</option>
                    <option>Свободный</option>
                  </select>
                </label>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">Приёмов пищи в день</span>
                  <select className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-slate-400">
                    <option>3</option>
                    <option>4</option>
                    <option>5</option>
                    <option>6</option>
                  </select>
                </label>
              </div>

              <div>
                <h2 className="text-lg font-semibold">2. Любимые кухни</h2>
                <div className="mt-4 flex flex-wrap gap-3">
                  {cuisines.map((cuisine) => (
                    <button
                      key={cuisine}
                      type="button"
                      className="rounded-full border border-slate-200 px-4 py-2 text-sm transition hover:border-emerald-300 hover:bg-emerald-50"
                    >
                      {cuisine}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <h2 className="text-lg font-semibold">3. Исключения и ограничения</h2>
                <div className="mt-4 grid gap-5 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Аллергии / непереносимости</span>
                    <textarea
                      rows={4}
                      placeholder="Например: лактоза, арахис, морепродукты"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-slate-400"
                    />
                  </label>
                  <div>
                    <span className="mb-2 block text-sm font-medium">Нелюбимые продукты</span>
                    <div className="flex flex-wrap gap-3 rounded-2xl border border-slate-200 p-4">
                      {dislikes.map((item) => (
                        <button
                          key={item}
                          type="button"
                          className="rounded-full bg-slate-100 px-3 py-2 text-sm text-slate-700 transition hover:bg-slate-200"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h2 className="text-lg font-semibold">4. Образ жизни</h2>
                <div className="mt-4 grid gap-5 md:grid-cols-2">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Уровень активности</span>
                    <select className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-slate-400">
                      <option>Низкий</option>
                      <option>Умеренный</option>
                      <option>Высокий</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Кулинарные навыки</span>
                    <select className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none focus:border-slate-400">
                      <option>Начинающий</option>
                      <option>Средний</option>
                      <option>Продвинутый</option>
                    </select>
                  </label>
                </div>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-slate-500">После сохранения профиля можно будет сгенерировать персональный рацион на день или неделю.</p>
                <button
                  type="submit"
                  className="rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                >
                  Сохранить и продолжить
                </button>
              </div>
            </form>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
              <h2 className="text-xl font-semibold">Что даст эта анкета</h2>
              <div className="mt-5 space-y-4 text-sm text-slate-200">
                <div className="rounded-2xl bg-white/10 p-4">
                  Персональный подбор блюд по вкусам и ограничениям
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  Автоматический расчёт калорийности и БЖУ
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  Удобный список покупок на основе меню
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">MVP страницы</h2>
              <ul className="mt-4 space-y-3 text-sm text-slate-600">
                <li>• Сбор предпочтений пользователя</li>
                <li>• Сохранение профиля в БД</li>
                <li>• Подготовка данных для генерации плана питания</li>
                <li>• Основа для дальнейшей персонализации</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
