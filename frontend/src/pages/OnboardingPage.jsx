import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchMyProfile, updateMyProfile } from "../lib/profile";
import { ALLERGY_CATEGORIES, PRODUCT_CATEGORIES } from "../lib/productCatalog";
import { REGION_GROUPS, getFoodZoneByRegion } from "../lib/regions";

function ProductPicker({ title, description, categories, selected, onChange }) {
  const [openCategory, setOpenCategory] = useState(null);
  const selectedSet = new Set(selected);

  const toggleProduct = (product) => {
    if (selectedSet.has(product)) {
      onChange(selected.filter((item) => item !== product));
      return;
    }
    onChange([...selected, product]);
  };

  return (
    <div className="rounded-2xl bg-white p-4 ring-1 ring-slate-200">
      <div>
        <p className="font-semibold text-slate-900">{title}</p>
        {description ? (
          <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
        ) : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {categories.map((category) => (
          <button
            key={category.id}
            type="button"
            onClick={() =>
              setOpenCategory((current) =>
                current === category.id ? null : category.id,
              )
            }
            className={`rounded-2xl border px-4 py-2 text-sm font-medium transition ${
              openCategory === category.id
                ? "border-emerald-300 bg-emerald-50 text-emerald-700"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
            }`}
          >
            {category.label}
          </button>
        ))}
      </div>

      {openCategory ? (
        <div className="mt-4 rounded-2xl bg-slate-50 p-3">
          <div className="flex flex-wrap gap-2">
            {categories
              .find((category) => category.id === openCategory)
              ?.products.map((product) => (
                <button
                  key={product}
                  type="button"
                  onClick={() => toggleProduct(product)}
                  className={`rounded-xl border px-3 py-2 text-sm transition ${
                    selectedSet.has(product)
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {product}
                </button>
              ))}
          </div>
        </div>
      ) : null}

      <div className="mt-4 min-h-8">
        {selected.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {selected.map((product) => (
              <button
                key={product}
                type="button"
                onClick={() => toggleProduct(product)}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700 transition hover:bg-slate-200"
              >
                {product} ×
              </button>
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">Пока ничего не выбрано</p>
        )}
      </div>
    </div>
  );
}

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

function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-medium text-slate-700">
        {label}
      </span>
      {children}
      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
    </label>
  );
}

function inputClassName(hasError = false) {
  return `w-full rounded-2xl border bg-white px-4 py-3 text-sm text-slate-900 outline-none transition placeholder:text-slate-400 ${
    hasError
      ? "border-red-300 focus:border-red-400"
      : "border-slate-200 focus:border-slate-400"
  }`;
}

function toNullableNumber(value) {
  if (value === "") {
    return null;
  }

  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return null;
  }

  return parsed < 0 ? 0 : parsed;
}

function normalizeNumberInput(value) {
  if (value === "") {
    return "";
  }

  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "";
  }

  return String(Math.max(0, parsed));
}

function validateProfile(form) {
  const errors = {};

  if (form.age !== "" && Number(form.age) > 120) {
    errors.age = "Возраст должен быть в диапазоне от 0 до 120";
  }

  if (form.meals_per_day !== "" && Number(form.meals_per_day) < 1) {
    errors.meals_per_day = "Укажите хотя бы 1 прием пищи";
  }

  return errors;
}

export default function TastePlannerOnboardingPage({ authSession }) {
  const [form, setForm] = useState({
    sex: "",
    age: "",
    height_cm: "",
    weight_kg: "",
    goal: "",
    activity_level: "",
    region_code: "",
    daily_budget_rub: "",
    weekly_budget_rub: "",
    meals_per_day: "",
    favorite_products_json: [],
    disliked_products_json: [],
    allergies_json: [],
  });
  const [fieldErrors, setFieldErrors] = useState({});
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let isActive = true;

    async function loadProfile() {
      if (!authSession?.accessToken) {
        if (isActive) {
          setIsLoading(false);
        }
        return;
      }

      try {
        const profile = await fetchMyProfile(authSession.accessToken);
        if (!isActive) {
          return;
        }

        setForm({
          sex: profile.sex ?? "",
          age: profile.age ?? "",
          height_cm: profile.height_cm ?? "",
          weight_kg: profile.weight_kg ?? "",
          goal: profile.goal ?? "",
          activity_level: profile.activity_level ?? "",
          region_code: profile.region_code ?? "",
          daily_budget_rub: profile.daily_budget_rub ?? "",
          weekly_budget_rub: profile.weekly_budget_rub ?? "",
          meals_per_day: profile.meals_per_day ?? "",
          favorite_products_json: profile.favorite_products_json ?? [],
          disliked_products_json: profile.disliked_products_json ?? [],
          allergies_json: profile.allergies_json ?? [],
        });
      } catch (error) {
        if (isActive) {
          setErrorMessage(error.message);
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    }

    loadProfile();

    return () => {
      isActive = false;
    };
  }, [authSession?.accessToken]);

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
    setSuccessMessage("");
  };

  const handleNumberChange = (field, value) => {
    handleChange(field, normalizeNumberInput(value));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage("");
    setSuccessMessage("");

    const errors = validateProfile(form);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }

    setIsSaving(true);

    try {
      await updateMyProfile(authSession.accessToken, {
        sex: form.sex || null,
        age: toNullableNumber(form.age),
        height_cm: toNullableNumber(form.height_cm),
        weight_kg: toNullableNumber(form.weight_kg),
        goal: form.goal || null,
        activity_level: form.activity_level || null,
        region_code: form.region_code || null,
        daily_calorie_target: null,
        daily_budget_rub: toNullableNumber(form.daily_budget_rub),
        weekly_budget_rub: toNullableNumber(form.weekly_budget_rub),
        meals_per_day: toNullableNumber(form.meals_per_day),
        favorite_products_json: form.favorite_products_json,
        disliked_products_json: form.disliked_products_json,
        allergies_json: form.allergies_json,
      });

      setSuccessMessage("Профиль сохранен");
      setTimeout(() => navigate("/profile"), 500);
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSaving(false);
    }
  };
  const selectedFoodZone = getFoodZoneByRegion(form.region_code);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            TastePlanner • Профиль питания
          </span>
          <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight text-slate-950">
            Заполните анкету, чтобы мы собрали ваш персональный профиль
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Эти данные нужны для базовой персонализации. Калорийность мы позже
            сможем рассчитать автоматически, без ручного ввода.
          </p>
        </div>

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        {successMessage ? (
          <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
            {successMessage}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
            {isLoading ? (
              <p className="text-sm text-slate-500">
                Загружаем текущие данные профиля...
              </p>
            ) : (
              <form className="space-y-8" onSubmit={handleSubmit}>
                <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                  <SectionHeader
                    step="Шаг 1"
                    title="Базовые параметры"
                    description="Укажите основные данные, чтобы система могла точнее подбирать рекомендации."
                  />

                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <Field label="Пол" error={fieldErrors.sex}>
                      <select
                        value={form.sex}
                        onChange={(e) => handleChange("sex", e.target.value)}
                        className={inputClassName(Boolean(fieldErrors.sex))}
                      >
                        <option value="">Не указан</option>
                        <option value="male">Мужской</option>
                        <option value="female">Женский</option>
                      </select>
                    </Field>

                    <Field label="Возраст" error={fieldErrors.age}>
                      <input
                        type="number"
                        min="0"
                        max="120"
                        inputMode="numeric"
                        value={form.age}
                        onChange={(e) => handleNumberChange("age", e.target.value)}
                        placeholder="Например, 27"
                        className={inputClassName(Boolean(fieldErrors.age))}
                      />
                    </Field>

                    <Field label="Рост, см" error={fieldErrors.height_cm}>
                      <input
                        type="number"
                        min="0"
                        inputMode="decimal"
                        value={form.height_cm}
                        onChange={(e) =>
                          handleNumberChange("height_cm", e.target.value)
                        }
                        placeholder="168"
                        className={inputClassName(Boolean(fieldErrors.height_cm))}
                      />
                    </Field>

                    <Field label="Вес, кг" error={fieldErrors.weight_kg}>
                      <input
                        type="number"
                        min="0"
                        inputMode="decimal"
                        value={form.weight_kg}
                        onChange={(e) =>
                          handleNumberChange("weight_kg", e.target.value)
                        }
                        placeholder="60"
                        className={inputClassName(Boolean(fieldErrors.weight_kg))}
                      />
                    </Field>
                  </div>
                </div>

                <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                  <SectionHeader
                    step="Шаг 2"
                    title="Цель, режим и бюджет"
                    description="Эти параметры помогут рассчитать калорийность, число приемов пищи и ориентир по стоимости рациона."
                  />

                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <Field label="Цель" error={fieldErrors.goal}>
                      <select
                        value={form.goal}
                        onChange={(e) => handleChange("goal", e.target.value)}
                        className={inputClassName(Boolean(fieldErrors.goal))}
                      >
                        <option value="">Не указана</option>
                        <option value="lose_weight">Снижение веса</option>
                        <option value="maintain">Поддержание веса</option>
                        <option value="gain_weight">Набор массы</option>
                      </select>
                    </Field>

                    <Field
                      label="Уровень активности"
                      error={fieldErrors.activity_level}
                    >
                      <select
                        value={form.activity_level}
                        onChange={(e) =>
                          handleChange("activity_level", e.target.value)
                        }
                        className={inputClassName(Boolean(fieldErrors.activity_level))}
                      >
                        <option value="">Не указан</option>
                        <option value="low">Низкий</option>
                        <option value="moderate">Умеренный</option>
                        <option value="high">Высокий</option>
                      </select>
                    </Field>

                    <Field
                      label="Приемов пищи в день"
                      error={fieldErrors.meals_per_day}
                    >
                      <input
                        type="number"
                        min="1"
                        inputMode="numeric"
                        value={form.meals_per_day}
                        onChange={(e) =>
                          handleNumberChange("meals_per_day", e.target.value)
                        }
                        placeholder="4"
                        className={inputClassName(Boolean(fieldErrors.meals_per_day))}
                      />
                    </Field>

                    <Field label="Бюджет на день, ₽" error={fieldErrors.daily_budget_rub}>
                      <input
                        type="number"
                        min="0"
                        inputMode="decimal"
                        value={form.daily_budget_rub}
                        onChange={(e) =>
                          handleNumberChange("daily_budget_rub", e.target.value)
                        }
                        placeholder="700"
                        className={inputClassName(Boolean(fieldErrors.daily_budget_rub))}
                      />
                    </Field>

                    <Field label="Бюджет на неделю, ₽" error={fieldErrors.weekly_budget_rub}>
                      <input
                        type="number"
                        min="0"
                        inputMode="decimal"
                        value={form.weekly_budget_rub}
                        onChange={(e) =>
                          handleNumberChange("weekly_budget_rub", e.target.value)
                        }
                        placeholder="4900"
                        className={inputClassName(Boolean(fieldErrors.weekly_budget_rub))}
                      />
                    </Field>
                  </div>
                </div>

                <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                  <SectionHeader
                    step="Шаг 3"
                    title="Предпочтения и ограничения"
                    description="Выберите продукты, которые пользователь любит, не любит или не может есть из-за аллергии."
                  />

                  <div className="mt-5 space-y-4">
                    <ProductPicker
                      title="Любимые продукты"
                      description="Эти продукты будут чаще учитываться в рекомендациях."
                      categories={PRODUCT_CATEGORIES}
                      selected={form.favorite_products_json}
                      onChange={(value) =>
                        handleChange("favorite_products_json", value)
                      }
                    />
                    <ProductPicker
                      title="Нелюбимые продукты"
                      description="Такие продукты лучше понижать в выдаче или избегать."
                      categories={PRODUCT_CATEGORIES}
                      selected={form.disliked_products_json}
                      onChange={(value) =>
                        handleChange("disliked_products_json", value)
                      }
                    />
                    <ProductPicker
                      title="Аллергии"
                      description="Аллергены должны исключаться из будущего рациона."
                      categories={ALLERGY_CATEGORIES}
                      selected={form.allergies_json}
                      onChange={(value) => handleChange("allergies_json", value)}
                    />
                  </div>
                </div>

                <div className="rounded-3xl bg-slate-50 p-5 sm:p-6">
                  <SectionHeader
                    step="Шаг 4"
                    title="Регион"
                    description="Вместо кода региона выберите понятный вариант из списка. Это пригодится для локализации рецептов и сезонности."
                  />

                  <div className="mt-5 grid gap-4 sm:grid-cols-2">
                    <Field label="Ваш регион" error={fieldErrors.region_code}>
                      <select
                        value={form.region_code}
                        onChange={(e) =>
                          handleChange("region_code", e.target.value)
                        }
                        className={inputClassName(Boolean(fieldErrors.region_code))}
                      >
                        <option value="">Не выбран</option>
                        {REGION_GROUPS.map((group) => (
                          <optgroup key={group.label} label={group.label}>
                            {group.options.map((option) => (
                              <option key={option.value} value={option.value}>
                                {option.label}
                              </option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                    </Field>
                  </div>

                  {selectedFoodZone ? (
                    <div className="mt-5 rounded-2xl bg-white p-4 text-sm text-slate-600 ring-1 ring-slate-200">
                      <p className="font-semibold text-slate-900">
                        {selectedFoodZone.name}
                      </p>
                      <p className="mt-2">
                        Типичные продукты: {selectedFoodZone.products.join(", ")}.
                      </p>
                    </div>
                  ) : null}
                </div>

                <div className="flex flex-col gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <p className="max-w-2xl text-sm leading-6 text-slate-500">
                    После сохранения профиля можно будет строить рацион на день.
                    Калорийность позже будет считаться автоматически, поэтому
                    пользователю не нужно знать ее заранее.
                  </p>

                  <button
                    type="submit"
                    disabled={isSaving}
                    className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {isSaving ? "Сохраняем..." : "Сохранить профиль"}
                  </button>
                </div>
              </form>
            )}
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Сводка анкеты</h2>
              <div className="mt-5 space-y-3 text-sm">
                <div className="rounded-2xl bg-slate-50 px-4 py-3 text-slate-600">
                  <span className="font-medium text-slate-900">Бюджет: </span>
                  {form.daily_budget_rub
                    ? `${form.daily_budget_rub} ₽ в день`
                    : form.weekly_budget_rub
                      ? `${form.weekly_budget_rub} ₽ в неделю`
                      : "не указан"}
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3 text-slate-600">
                  <span className="font-medium text-slate-900">Любимые продукты: </span>
                  {form.favorite_products_json.length > 0
                    ? form.favorite_products_json.join(", ")
                    : "не выбраны"}
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3 text-slate-600">
                  <span className="font-medium text-slate-900">Нелюбимые продукты: </span>
                  {form.disliked_products_json.length > 0
                    ? form.disliked_products_json.join(", ")
                    : "не выбраны"}
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3 text-slate-600">
                  <span className="font-medium text-slate-900">Аллергии: </span>
                  {form.allergies_json.length > 0
                    ? form.allergies_json.join(", ")
                    : "не выбраны"}
                </div>
              </div>
            </div>

            {selectedFoodZone ? (
              <div className="rounded-3xl bg-slate-900 p-6 text-white shadow-sm">
                <h2 className="text-xl font-semibold">Региональный профиль</h2>
                <p className="mt-3 text-sm font-medium text-emerald-200">
                  {selectedFoodZone.name}
                </p>
                <p className="mt-4 text-sm leading-6 text-slate-200">
                  В рекомендациях можно учитывать продукты, которые чаще встречаются
                  в выбранной зоне: {selectedFoodZone.products.join(", ")}.
                </p>
              </div>
            ) : null}
          </aside>
        </div>
      </div>
    </div>
  );
}
