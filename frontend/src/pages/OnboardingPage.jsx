function SectionHeader({ step, title, description }) {
  return (
    <div>
      <p className="text-sm font-medium text-emerald-700">{step}</p>
      <h2 className="mt-2 text-xl font-semibold tracking-tight text-slate-950">
        {title}
      </h2>
      {description ? (
        <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
          {description}
        </p>
      ) : null}
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>
      {children}
    </label>
  );
}

function inputClassName() {
  return "w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-400";
}

export default function TastePlannerOnboardingPage() {
  const goals = [
    "Похудение",
    "Поддержание веса",
    "Набор массы",
    "Здоровое питание",
  ];

  const cuisines = [
    "Русская",
    "Итальянская",
    "Японская",
    "Средиземноморская",
    "Индийская",
    "Мексиканская",
  ];

  const dislikes = [
    "Острое",
    "Молочные продукты",
    "Рыба",
    "Грибы",
    "Лук",
    "Брокколи",
  ];

  const benefits = [
    "Персональный подбор блюд по вкусам и ограничениям",
    "Автоматический расчёт калорийности и БЖУ",
    "Подготовка списка покупок на основе меню",
  ];

  const roadmap = [
    "Сбор предпочтений пользователя",
    "Сохранение профиля в БД",
    "Подготовка данных для генерации плана питания",
    "Основа для дальнейшей персонализации",
  ];

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            TastePlanner • Персональный помощник питания
          </span>
          <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight text-slate-950">
            Создайте рацион, который подходит именно вам
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Заполните короткий профиль, и система подготовит основу для
            персонального плана питания с учётом вкусов, ограничений, бюджета и
            целей.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
            <form className="space-y-8">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Ваше имя">
                  <input
                    type="text"
                    placeholder="Например, Алина"
                    className={inputClassName()}
                  />
                </Field>

                <Field label="Возраст">
                  <input
                    type="number"
                    placeholder="22"
                    className={inputClassName()}
                  />
                </Field>
              </div>

              <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                <SectionHeader
                  step="Шаг 1"
                  title="Цель питания"
                  description="Выберите основную цель, чтобы система подобрала подходящую калорийность и базовый баланс БЖУ."
                />

                <div className="mt-5 grid gap-3 sm:grid-cols-2">
                  {goals.map((goal) => (
                    <button
                      key={goal}
                      type="button"
                      className="flex min-h-14 items-center justify-center rounded-2xl border border-slate-200 bg-white px-4 text-center text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"
                    >
                      {goal}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Бюджет на неделю">
                  <select className={inputClassName()}>
                    <option>Минимальный</option>
                    <option>Средний</option>
                    <option>Свободный</option>
                  </select>
                </Field>

                <Field label="Приёмов пищи в день">
                  <select className={inputClassName()}>
                    <option>3</option>
                    <option>4</option>
                    <option>5</option>
                    <option>6</option>
                  </select>
                </Field>
              </div>

              <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                <SectionHeader
                  step="Шаг 2"
                  title="Любимые кухни"
                  description="Отметьте направления, которые вам нравятся, чтобы рекомендации были ближе к привычному вкусу."
                />

                <div className="mt-5 flex flex-wrap gap-3">
                  {cuisines.map((cuisine) => (
                    <button
                      key={cuisine}
                      type="button"
                      className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"
                    >
                      {cuisine}
                    </button>
                  ))}
                </div>
              </div>

              <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                <SectionHeader
                  step="Шаг 3"
                  title="Исключения и ограничения"
                  description="Укажите важные ограничения заранее, чтобы исключить неподходящие блюда из рекомендаций."
                />

                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <Field label="Аллергии / непереносимости">
                    <textarea
                      rows={5}
                      placeholder="Например: лактоза, арахис, морепродукты"
                      className={inputClassName()}
                    />
                  </Field>

                  <div>
                    <span className="mb-2 block text-sm font-medium text-slate-700">
                      Нелюбимые продукты
                    </span>
                    <div className="flex h-full flex-wrap gap-3 rounded-2xl border border-slate-200 bg-white p-4">
                      {dislikes.map((item) => (
                        <button
                          key={item}
                          type="button"
                          className="rounded-full bg-slate-100 px-3 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200"
                        >
                          {item}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                <SectionHeader
                  step="Шаг 4"
                  title="Образ жизни"
                  description="Эти параметры помогут точнее подобрать сложность блюд и режим питания."
                />

                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <Field label="Уровень активности">
                    <select className={inputClassName()}>
                      <option>Низкий</option>
                      <option>Умеренный</option>
                      <option>Высокий</option>
                    </select>
                  </Field>

                  <Field label="Кулинарные навыки">
                    <select className={inputClassName()}>
                      <option>Начинающий</option>
                      <option>Средний</option>
                      <option>Продвинутый</option>
                    </select>
                  </Field>
                </div>
              </div>

              <div className="flex flex-col gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
                <p className="max-w-2xl text-sm leading-6 text-slate-500">
                  После сохранения профиля можно будет сгенерировать
                  персональный рацион на день или неделю.
                </p>

                <button
                  type="submit"
                  className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                >
                  Сохранить и продолжить
                </button>
              </div>
            </form>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
              <h2 className="text-xl font-semibold">Что даст эта анкета</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-200">
                {benefits.map((benefit) => (
                  <div key={benefit} className="rounded-2xl bg-white/10 p-4">
                    {benefit}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Что заполнить в MVP</h2>
              <div className="mt-5 space-y-3 text-sm">
                {roadmap.map((item) => (
                  <div
                    key={item}
                    className="flex items-start gap-3 rounded-2xl bg-slate-50 px-4 py-3 text-slate-600"
                  >
                    <span className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-500" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
