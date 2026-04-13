export default function MealPlanPage() {
  const meals = [
    {
      title: "Завтрак",
      name: "Овсяная каша с бананом и орехами",
      calories: 420,
      proteins: 14,
      fats: 12,
      carbs: 58,
    },
    {
      title: "Обед",
      name: "Куриная грудка с гречкой и овощами",
      calories: 560,
      proteins: 42,
      fats: 14,
      carbs: 61,
    },
    {
      title: "Ужин",
      name: "Запечённая рыба с салатом",
      calories: 390,
      proteins: 32,
      fats: 18,
      carbs: 19,
    },
    {
      title: "Перекус",
      name: "Йогурт и яблоко",
      calories: 180,
      proteins: 8,
      fats: 4,
      carbs: 27,
    },
  ];

  const total = meals.reduce(
    (acc, meal) => {
      acc.calories += meal.calories;
      acc.proteins += meal.proteins;
      acc.fats += meal.fats;
      acc.carbs += meal.carbs;
      return acc;
    },
    { calories: 0, proteins: 0, fats: 0, carbs: 0 }
  );

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            Персональный рацион
          </span>
          <h1 className="mt-4 text-4xl font-bold tracking-tight">
            План питания на день
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Пример сгенерированного меню на основе предпочтений пользователя,
            целей и базового расчёта КБЖУ.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-4">
            {meals.map((meal) => (
              <article
                key={meal.title}
                className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-emerald-700">
                      {meal.title}
                    </p>
                    <h2 className="mt-2 text-xl font-semibold">{meal.name}</h2>
                  </div>
                  <button
                    type="button"
                    className="rounded-2xl border border-slate-200 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50"
                  >
                    Заменить
                  </button>
                </div>

                <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Калории</p>
                    <p className="mt-1 text-lg font-semibold">{meal.calories}</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Белки</p>
                    <p className="mt-1 text-lg font-semibold">{meal.proteins} г</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Жиры</p>
                    <p className="mt-1 text-lg font-semibold">{meal.fats} г</p>
                  </div>
                  <div className="rounded-2xl bg-slate-50 p-4">
                    <p className="text-xs text-slate-500">Углеводы</p>
                    <p className="mt-1 text-lg font-semibold">{meal.carbs} г</p>
                  </div>
                </div>
              </article>
            ))}
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Итог за день</h2>
              <div className="mt-5 space-y-3 text-sm">
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Калории</span>
                  <strong>{total.calories} ккал</strong>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Белки</span>
                  <strong>{total.proteins} г</strong>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Жиры</span>
                  <strong>{total.fats} г</strong>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Углеводы</span>
                  <strong>{total.carbs} г</strong>
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
              <h2 className="text-xl font-semibold">Что дальше</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-200">
                <div className="rounded-2xl bg-white/10 p-4">
                  Можно заменить блюдо на аналогичное по КБЖУ
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  На основе меню формируется список покупок
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  В будущем сюда подключится backend и персональная генерация
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}