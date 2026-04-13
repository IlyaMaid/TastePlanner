import { useState } from "react";

export default function AuthPage() {
  const [mode, setMode] = useState("login");

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-6xl items-center px-6 py-10 lg:grid-cols-2 lg:gap-10">
        <section className="hidden lg:block">
          <div className="rounded-[2rem] bg-slate-900 p-10 text-white shadow-sm">
            <span className="inline-flex rounded-full bg-white/10 px-3 py-1 text-sm font-medium">
              TastePlanner
            </span>

            <h1 className="mt-6 text-4xl font-bold leading-tight">
              Персональный помощник для планирования рациона
            </h1>

            <p className="mt-4 max-w-xl text-slate-300">
              Создавайте индивидуальный план питания на основе ваших вкусов,
              ограничений, образа жизни и целей. Удобно, быстро и персонально.
            </p>

            <div className="mt-8 space-y-4 text-sm text-slate-200">
              <div className="rounded-2xl bg-white/10 p-4">
                Индивидуальные рекомендации по питанию
              </div>
              <div className="rounded-2xl bg-white/10 p-4">
                Подбор блюд с учетом аллергий и предпочтений
              </div>
              <div className="rounded-2xl bg-white/10 p-4">
                Автоматическое формирование списка покупок
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-md">
          <div className="rounded-[2rem] bg-white p-8 shadow-sm ring-1 ring-slate-200">
            <div className="mb-8 flex rounded-2xl bg-slate-100 p-1">
              <button
                type="button"
                onClick={() => setMode("login")}
                className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                  mode === "login"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500"
                }`}
              >
                Вход
              </button>

              <button
                type="button"
                onClick={() => setMode("register")}
                className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                  mode === "register"
                    ? "bg-white text-slate-900 shadow-sm"
                    : "text-slate-500"
                }`}
              >
                Регистрация
              </button>
            </div>

            {mode === "login" ? (
              <div>
                <h2 className="text-3xl font-bold tracking-tight">С возвращением</h2>
                <p className="mt-2 text-sm text-slate-500">
                  Войдите, чтобы продолжить работу с персональным рационом.
                </p>

                <form className="mt-8 space-y-5">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Email</span>
                    <input
                      type="email"
                      placeholder="example@mail.com"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Пароль</span>
                    <input
                      type="password"
                      placeholder="Введите пароль"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <button
                    type="submit"
                    className="w-full rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                  >
                    Войти
                  </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-500">
                  Нет аккаунта?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("register")}
                    className="font-semibold text-slate-900"
                  >
                    Зарегистрироваться
                  </button>
                </p>
              </div>
            ) : (
              <div>
                <h2 className="text-3xl font-bold tracking-tight">Создание аккаунта</h2>
                <p className="mt-2 text-sm text-slate-500">
                  Зарегистрируйтесь, чтобы сохранять предпочтения и планы питания.
                </p>

                <form className="mt-8 space-y-5">
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Имя</span>
                    <input
                      type="text"
                      placeholder="Ваше имя"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Email</span>
                    <input
                      type="email"
                      placeholder="example@mail.com"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Пароль</span>
                    <input
                      type="password"
                      placeholder="Придумайте пароль"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">
                      Подтверждение пароля
                    </span>
                    <input
                      type="password"
                      placeholder="Повторите пароль"
                      className="w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none transition focus:border-slate-400"
                    />
                  </label>

                  <button
                    type="submit"
                    className="w-full rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90"
                  >
                    Зарегистрироваться
                  </button>
                </form>

                <p className="mt-6 text-center text-sm text-slate-500">
                  Уже есть аккаунт?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    className="font-semibold text-slate-900"
                  >
                    Войти
                  </button>
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}