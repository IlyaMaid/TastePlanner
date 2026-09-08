import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import {
  resetPasswordRequest,
  validateResetPasswordForm,
} from "../lib/auth";

const inputClassName =
  "w-full rounded-2xl border px-4 py-3 outline-none transition";

function FieldError({ message }) {
  if (!message) {
    return null;
  }

  return <p className="mt-2 text-sm text-red-600">{message}</p>;
}

export default function ResetPasswordPage({ notify }) {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const navigate = useNavigate();

  const [form, setForm] = useState({ password: "", confirmPassword: "" });
  const [fieldErrors, setFieldErrors] = useState({});
  const [errorMessage, setErrorMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");

    const errors = validateResetPasswordForm(form);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSubmitting(true);

    try {
      await resetPasswordRequest({ token, newPassword: form.password });
      setIsDone(true);
      notify?.({
        title: "Пароль изменен",
        message: "Теперь можно войти с новым паролем.",
      });
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto flex min-h-screen max-w-md items-center px-6 py-10">
        <div className="w-full rounded-[2rem] bg-white p-8 shadow-sm ring-1 ring-slate-200">
          {!token ? (
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Ссылка недействительна
              </h1>
              <p className="mt-3 text-sm text-slate-500">
                В ссылке отсутствует токен восстановления пароля. Запросите
                новую ссылку на странице входа.
              </p>
              <Link
                to="/auth"
                className="mt-6 block w-full rounded-2xl bg-emerald-600 px-6 py-3 text-center text-sm font-semibold text-white transition hover:opacity-90"
              >
                Вернуться ко входу
              </Link>
            </div>
          ) : isDone ? (
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Пароль успешно изменен
              </h1>
              <p className="mt-3 text-sm text-slate-500">
                Теперь можно войти в аккаунт с новым паролем.
              </p>
              <button
                type="button"
                onClick={() => navigate("/auth")}
                className="mt-6 block w-full rounded-2xl bg-emerald-600 px-6 py-3 text-center text-sm font-semibold text-white transition hover:opacity-90"
              >
                Войти
              </button>
            </div>
          ) : (
            <div>
              <h1 className="text-2xl font-bold tracking-tight">
                Новый пароль
              </h1>
              <p className="mt-3 text-sm text-slate-500">
                Придумайте новый пароль для входа в аккаунт.
              </p>

              {errorMessage ? (
                <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                  {errorMessage}
                </div>
              ) : null}

              <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
                <label className="block">
                  <span className="mb-2 block text-sm font-medium">
                    Новый пароль
                  </span>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => handleChange("password", e.target.value)}
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
                    value={form.confirmPassword}
                    onChange={(e) =>
                      handleChange("confirmPassword", e.target.value)
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
                  {isSubmitting ? "Сохраняем..." : "Сохранить пароль"}
                </button>
              </form>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
