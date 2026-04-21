import { useState } from "react";

export default function ShoppingListPage() {
  const [items, setItems] = useState([
    { id: 1, name: "Овсяные хлопья", category: "Крупы", quantity: "500 г", bought: false },
    { id: 2, name: "Бананы", category: "Фрукты", quantity: "6 шт", bought: true },
    { id: 3, name: "Куриная грудка", category: "Мясо", quantity: "1 кг", bought: false },
    { id: 4, name: "Гречка", category: "Крупы", quantity: "800 г", bought: false },
    { id: 5, name: "Помидоры", category: "Овощи", quantity: "5 шт", bought: false },
    { id: 6, name: "Огурцы", category: "Овощи", quantity: "4 шт", bought: true },
    { id: 7, name: "Йогурт", category: "Молочные продукты", quantity: "4 шт", bought: false },
    { id: 8, name: "Яблоки", category: "Фрукты", quantity: "6 шт", bought: false },
    { id: 9, name: "Лосось", category: "Рыба", quantity: "400 г", bought: false },
  ]);

  const toggleBought = (id) => {
    setItems((prevItems) =>
      prevItems.map((item) =>
        item.id === id ? { ...item, bought: !item.bought } : item
      )
    );
  };

  const groupedItems = items.reduce((acc, item) => {
    if (!acc[item.category]) {
      acc[item.category] = [];
    }
    acc[item.category].push(item);
    return acc;
  }, {});

  const totalItems = items.length;
  const boughtItems = items.filter((item) => item.bought).length;
  const remainingItems = totalItems - boughtItems;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
              Список покупок
            </span>
            <h1 className="mt-4 text-4xl font-bold tracking-tight">
              Продукты на неделю
            </h1>
            <p className="mt-3 max-w-2xl text-slate-600">
              Список сформирован автоматически на основе выбранного плана питания.
              Продукты сгруппированы по категориям для удобства похода в магазин.
            </p>
          </div>

          <button
            type="button"
            className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
          >
            Сформировать заново
          </button>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-6">
            {Object.entries(groupedItems).map(([category, categoryItems]) => (
              <div
                key={category}
                className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200"
              >
                <h2 className="text-xl font-semibold">{category}</h2>

                <div className="mt-5 space-y-3">
                  {categoryItems.map((item) => (
                    <label
                      key={item.id}
                      className={`flex cursor-pointer items-center justify-between rounded-2xl border px-4 py-3 transition ${
                        item.bought
                          ? "border-emerald-200 bg-emerald-50"
                          : "border-slate-200 bg-white hover:bg-slate-50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <input
                          type="checkbox"
                          checked={item.bought}
                          onChange={() => toggleBought(item.id)}
                          className="h-4 w-4 rounded border-slate-300"
                        />
                        <div>
                          <p
                            className={`font-medium ${
                              item.bought ? "text-slate-400 line-through" : "text-slate-900"
                            }`}
                          >
                            {item.name}
                          </p>
                          <p className="text-sm text-slate-500">{item.quantity}</p>
                        </div>
                      </div>

                      <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
                        {item.category}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Сводка</h2>

              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Всего позиций</span>
                  <strong>{totalItems}</strong>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Куплено</span>
                  <strong>{boughtItems}</strong>
                </div>
                <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                  <span>Осталось купить</span>
                  <strong>{remainingItems}</strong>
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
              <h2 className="text-xl font-semibold">Преимущества модуля</h2>

              <div className="mt-4 space-y-3 text-sm text-slate-200">
                <div className="rounded-2xl bg-white/10 p-4">
                  Автоматическое формирование списка на основе меню
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  Удобная группировка товаров по категориям
                </div>
                <div className="rounded-2xl bg-white/10 p-4">
                  Возможность отмечать уже купленные продукты
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}