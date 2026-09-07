import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  createAuthSession,
  forgotPasswordRequest,
  loginRequest,
  registerRequest,
  validateForgotPasswordForm,
  validateLoginForm,
  validateRegisterForm,
} from "../lib/auth";

const inputClassName =
  "w-full rounded-2xl border px-4 py-3 outline-none transition";

function FieldError({ message }) {
  if (!message) {
    return null;
  }

  return <p className="mt-2 text-sm text-red-600">{message}</p>;
}

export default function AuthPage({ onAuthSuccess }) {
  const [mode, setMode] = useState("login");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [loginForm, setLoginForm] = useState({
    email: "",
    password: "",
  });
  const [registerForm, setRegisterForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: "",
  });
  const [forgotForm, setForgotForm] = useState({ email: "" });
  const [forgotSuccessMessage, setForgotSuccessMessage] = useState("");
  const navigate = useNavigate();

  const loginTitle = useMemo(() => "С возвращением", []);
  const registerTitle = useMemo(() => "Создание аккаунта", []);

  const resetErrors = () => {
    setErrorMessage("");
    setFieldErrors({});
  };

  const handleLoginChange = (field, value) => {
    setLoginForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
  };

  const handleRegisterChange = (field, value) => {
    setRegisterForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
  };

  const handleForgotChange = (field, value) => {
    setForgotForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
  };

  const finishAuth = (payload) => {
    onAuthSuccess(createAuthSession(payload));
    navigate("/profile");
  };

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    resetErrors();

    const errors = validateLoginForm(loginForm);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = await loginRequest(loginForm);
      finishAuth(payload);
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotSubmit = async (e) => {
    e.preventDefault();
    resetErrors();
    setForgotSuccessMessage("");

    const errors = validateForgotPasswordForm(forgotForm);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await forgotPasswordRequest(forgotForm.email);
      setForgotSuccessMessage(
        response.message ||
          "Если такой email зарегистрирован, мы отправили на него ссылку для восстановления пароля.",
      );
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    resetErrors();

    const errors = validateRegisterForm(registerForm);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      const payload = await registerRequest(registerForm);
      finishAuth(payload);
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto grid min-h-screen max-w-6xl items-center px-6 py-10 lg:grid-cols-2 lg:gap-10">
        <section className="hidden lg:block">
          <div className="rounded-[2rem] bg-emerald-950 p-10 text-white shadow-sm">
            <span className="inline-flex rounded-full bg-white/10 px-3 py-1 text-sm font-medium">
              TastePlanner
            </span>

            <h1 className="mt-6 text-4xl font-bold leading-tight">
              Персональный помощник для планирования рациона
            </h1>

            <p className="mt-4 max-w-xl text-slate-300">
              Создавайте индивидуальный план питания на основе ваших вкусов,
              ограничений, образа жизни и целей.
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
            {mode !== "forgot" ? (
              <div className="mb-8 flex rounded-2xl bg-slate-100 p-1">
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    resetErrors();
                  }}
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
                  onClick={() => {
                    setMode("register");
                    resetErrors();
                  }}
                  className={`flex-1 rounded-2xl px-4 py-3 text-sm font-semibold transition ${
                    mode === "register"
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-500"
                  }`}
                >
                  Регистрация
                </button>
              </div>
            ) : null}

            {errorMessage ? (
              <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {errorMessage}
              </div>
            ) : null}

            {mode === "login" ? (
              <div>
                <h2 className="text-3xl font-bold tracking-tight">{loginTitle}</h2>
                <p className="mt-2 text-sm text-slate-500">
                  Войдите, чтобы продолжить работу с персональным рационом.
                </p>

                <form className="mt-8 space-y-5" onSubmit={handleLoginSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Email</span>
                    <input
                      type="email"
                      value={loginForm.email}
                      onChange={(e) => handleLoginChange("email", e.target.value)}
                      placeholder="example@mail.com"
                      className={`${inputClassName} ${
                        fieldErrors.email
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-slate-400"
                      }`}
                    />
                    <FieldError message={fieldErrors.email} />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Пароль</span>
                    <input
                      type="password"
                      value={loginForm.password}
                      onChange={(e) => handleLoginChange("password", e.target.value)}
                      placeholder="Введите пароль"
                      className={`${inputClassName} ${
                        fieldErrors.password
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-slate-400"
                      }`}
                    />
                    <FieldError message={fieldErrors.password} />
                  </label>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmitting ? "Входим..." : "Войти"}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setMode("forgot");
                      resetErrors();
                      setForgotSuccessMessage("");
                      setForgotForm({ email: loginForm.email });
                    }}
                    className="block w-full text-center text-sm font-medium text-slate-500 transition hover:text-slate-900"
                  >
                    Забыли пароль?
                  </button>
                </form>
              </div>
            ) : mode === "forgot" ? (
              <div>
                <h2 className="text-3xl font-bold tracking-tight">
                  Восстановление пароля
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  Укажите email, и мы отправим ссылку для восстановления пароля.
                </p>

                {forgotSuccessMessage ? (
                  <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
                    {forgotSuccessMessage}
                  </div>
                ) : (
                  <form className="mt-8 space-y-5" onSubmit={handleForgotSubmit}>
                    <label className="block">
                      <span className="mb-2 block text-sm font-medium">Email</span>
                      <input
                        type="email"
                        value={forgotForm.email}
                        onChange={(e) => handleForgotChange("email", e.target.value)}
                        placeholder="example@mail.com"
                        className={`${inputClassName} ${
                          fieldErrors.email
                            ? "border-red-300 focus:border-red-400"
                            : "border-slate-200 focus:border-slate-400"
                        }`}
                      />
                      <FieldError message={fieldErrors.email} />
                    </label>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {isSubmitting ? "Отправляем..." : "Отправить ссылку"}
                    </button>
                  </form>
                )}

                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    resetErrors();
                    setForgotSuccessMessage("");
                  }}
                  className="mt-6 block w-full text-center text-sm font-medium text-slate-500 transition hover:text-slate-900"
                >
                  Назад ко входу
                </button>
              </div>
            ) : (
              <div>
                <h2 className="text-3xl font-bold tracking-tight">
                  {registerTitle}
                </h2>
                <p className="mt-2 text-sm text-slate-500">
                  Зарегистрируйтесь, чтобы сохранять предпочтения и планы питания.
                </p>

                <form className="mt-8 space-y-5" onSubmit={handleRegisterSubmit}>
                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Имя</span>
                    <input
                      type="text"
                      value={registerForm.name}
                      onChange={(e) => handleRegisterChange("name", e.target.value)}
                      placeholder="Ваше имя"
                      className={`${inputClassName} border-slate-200 focus:border-slate-400`}
                    />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Email</span>
                    <input
                      type="email"
                      value={registerForm.email}
                      onChange={(e) => handleRegisterChange("email", e.target.value)}
                      placeholder="example@mail.com"
                      className={`${inputClassName} ${
                        fieldErrors.email
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-slate-400"
                      }`}
                    />
                    <FieldError message={fieldErrors.email} />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">Пароль</span>
                    <input
                      type="password"
                      value={registerForm.password}
                      onChange={(e) => handleRegisterChange("password", e.target.value)}
                      placeholder="Придумайте пароль"
                      className={`${inputClassName} ${
                        fieldErrors.password
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-slate-400"
                      }`}
                    />
                    <FieldError message={fieldErrors.password} />
                  </label>

                  <label className="block">
                    <span className="mb-2 block text-sm font-medium">
                      Подтверждение пароля
                    </span>
                    <input
                      type="password"
                      value={registerForm.confirmPassword}
                      onChange={(e) =>
                        handleRegisterChange("confirmPassword", e.target.value)
                      }
                      placeholder="Повторите пароль"
                      className={`${inputClassName} ${
                        fieldErrors.confirmPassword
                          ? "border-red-300 focus:border-red-400"
                          : "border-slate-200 focus:border-slate-400"
                      }`}
                    />
                    <FieldError message={fieldErrors.confirmPassword} />
                  </label>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSubmitting ? "Создаем аккаунт..." : "Зарегистрироваться"}
                  </button>
                </form>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
