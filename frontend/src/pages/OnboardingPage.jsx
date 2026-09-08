import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { fetchMyProfile, updateMyProfile } from "../lib/profile";
import { ALLERGY_CATEGORIES, PRODUCT_CATEGORIES } from "../lib/productCatalog";
import { REGION_GROUPS, getFoodZoneByRegion } from "../lib/regions";

const STEPS = [
  {
    id: "body",
    title: "Параметры",
    description: "Пол, возраст, рост и вес.",
  },
  {
    id: "goal",
    title: "Режим",
    description: "Цель, активность, бюджет и приемы пищи.",
  },
  {
    id: "products",
    title: "Продукты",
    description: "Любимое, нелюбимое и аллергии.",
  },
  {
    id: "region",
    title: "Регион",
    description: "Локальные продукты и привычки.",
  },
  {
    id: "review",
    title: "Проверка",
    description: "Итог перед сохранением.",
  },
];

const GOAL_OPTIONS = [
  {
    value: "lose_weight",
    title: "Снижение веса",
    text: "Рацион будет осторожнее по калориям.",
  },
  {
    value: "maintain",
    title: "Поддержание",
    text: "Баланс калорий, стоимости и сытости.",
  },
  {
    value: "gain_weight",
    title: "Набор массы",
    text: "Больше калорийных и белковых блюд.",
  },
];

const ACTIVITY_OPTIONS = [
  { value: "low", title: "Низкая", text: "Мало движения в течение дня." },
  { value: "moderate", title: "Умеренная", text: "Регулярные прогулки или тренировки." },
  { value: "high", title: "Высокая", text: "Много движения или частые тренировки." },
];

const MEALS_PER_DAY_OPTIONS = [2, 3, 4, 5, 6];

const STEP_FIELDS = {
  body: ["sex", "age", "height_cm", "weight_kg"],
  goal: ["goal", "activity_level", "meals_per_day", "daily_budget_rub", "weekly_budget_rub"],
  products: ["favorite_products_json", "disliked_products_json", "allergies_json"],
  region: ["region_code"],
  review: [],
};

function ProductPicker({ title, description, categories, selected, onChange }) {
  const [openCategory, setOpenCategory] = useState(categories[0]?.id ?? null);
  const selectedSet = new Set(selected);

  const toggleProduct = (product) => {
    if (selectedSet.has(product)) {
      onChange(selected.filter((item) => item !== product));
      return;
    }

    onChange([...selected, product]);
  };

  const activeCategory = categories.find((category) => category.id === openCategory);

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="font-semibold text-slate-900">{title}</p>
          {description ? (
            <p className="mt-1 text-sm leading-6 text-slate-500">{description}</p>
          ) : null}
        </div>
        <span className="w-fit rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600">
          Выбрано: {selected.length}
        </span>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:overflow-visible lg:pb-0">
          {categories.map((category) => (
            <button
              key={category.id}
              type="button"
              onClick={() => setOpenCategory(category.id)}
              className={`shrink-0 rounded-2xl border px-4 py-3 text-left text-sm font-medium transition ${
                openCategory === category.id
                  ? "border-emerald-600 bg-emerald-600 text-white"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
              }`}
            >
              {category.label}
            </button>
          ))}
        </div>

        <div className="rounded-2xl bg-slate-50 p-3">
          {activeCategory ? (
            <div className="flex flex-wrap gap-2">
              {activeCategory.products.map((product) => (
                <button
                  key={product}
                  type="button"
                  onClick={() => toggleProduct(product)}
                  className={`rounded-xl border px-3 py-2 text-sm transition ${
                    selectedSet.has(product)
                      ? "border-emerald-600 bg-emerald-600 text-white"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300"
                  }`}
                >
                  {product}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      </div>

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

function ChoiceCard({ isSelected, title, text, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-3xl border p-5 text-left transition ${
        isSelected
          ? "border-emerald-600 bg-emerald-600 text-white"
          : "border-slate-200 bg-white text-slate-900 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <span className="block text-sm font-semibold">{title}</span>
      <span
        className={`mt-2 block text-sm leading-6 ${
          isSelected ? "text-slate-200" : "text-slate-500"
        }`}
      >
        {text}
      </span>
    </button>
  );
}

function StepButton({ step, index, isActive, isDone, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
        isActive
          ? "border-emerald-600 bg-emerald-600 text-white"
          : isDone
            ? "border-emerald-200 bg-emerald-50 text-slate-900"
            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
      }`}
    >
      <span className="text-xs font-medium opacity-80">Шаг {index + 1}</span>
      <span className="mt-1 block text-sm font-semibold">{step.title}</span>
      <span className="mt-1 block text-xs leading-5 opacity-75">
        {step.description}
      </span>
    </button>
  );
}

function SummaryRow({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
      <span className="font-medium text-slate-900">{label}: </span>
      {value || "не указано"}
    </div>
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

  if (form.meals_per_day !== "" && Number(form.meals_per_day) > 6) {
    errors.meals_per_day = "Максимум 6 приемов пищи";
  }

  return errors;
}

function getStepCompletion(form, stepId) {
  if (stepId === "body") {
    return ["sex", "age", "height_cm", "weight_kg"].filter((field) => form[field] !== "")
      .length;
  }

  if (stepId === "goal") {
    return ["goal", "activity_level", "meals_per_day", "daily_budget_rub", "weekly_budget_rub"]
      .filter((field) => form[field] !== "").length;
  }

  if (stepId === "products") {
    return [
      form.favorite_products_json.length,
      form.disliked_products_json.length,
      form.allergies_json.length,
    ].filter(Boolean).length;
  }

  if (stepId === "region") {
    return form.region_code ? 1 : 0;
  }

  return 1;
}

function humanGoal(value) {
  return GOAL_OPTIONS.find((option) => option.value === value)?.title;
}

function humanActivity(value) {
  return ACTIVITY_OPTIONS.find((option) => option.value === value)?.title;
}

function humanSex(value) {
  if (value === "male") {
    return "Мужской";
  }

  if (value === "female") {
    return "Женский";
  }

  return "";
}

export default function TastePlannerOnboardingPage({ authSession, notify }) {
  const [activeStepIndex, setActiveStepIndex] = useState(0);
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

  const activeStep = STEPS[activeStepIndex];
  const selectedFoodZone = getFoodZoneByRegion(form.region_code);
  const progressPercent = Math.round(((activeStepIndex + 1) / STEPS.length) * 100);
  const completedFields = useMemo(
    () =>
      STEPS.reduce(
        (sum, step) => sum + Math.min(1, getStepCompletion(form, step.id)),
        0,
      ),
    [form],
  );

  const handleChange = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    setFieldErrors((prev) => ({ ...prev, [field]: "" }));
    setErrorMessage("");
    setSuccessMessage("");
  };

  const handleNumberChange = (field, value) => {
    handleChange(field, normalizeNumberInput(value));
  };

  const moveToStep = (nextIndex) => {
    const errors = validateProfile(form);
    const currentFields = STEP_FIELDS[activeStep.id] ?? [];
    const stepErrors = Object.fromEntries(
      Object.entries(errors).filter(([field]) => currentFields.includes(field)),
    );

    if (nextIndex > activeStepIndex && Object.keys(stepErrors).length > 0) {
      setFieldErrors(stepErrors);
      return;
    }

    setActiveStepIndex(Math.min(Math.max(nextIndex, 0), STEPS.length - 1));
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

      setSuccessMessage("Анкета сохранена");
      notify?.({
        title: "Анкета сохранена",
        message: "Рекомендации будут учитывать новые настройки.",
      });
      setTimeout(() => navigate("/"), 500);
    } catch (error) {
      setErrorMessage(error.message);
      setFieldErrors(error.errors ?? {});
    } finally {
      setIsSaving(false);
    }
  };

  const renderStep = () => {
    if (activeStep.id === "body") {
      return (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
              Базовые параметры
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Эти данные помогают рассчитать ориентир по калориям и сделать рацион
              ближе к реальным потребностям.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
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
                onChange={(e) => handleNumberChange("height_cm", e.target.value)}
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
                onChange={(e) => handleNumberChange("weight_kg", e.target.value)}
                placeholder="60"
                className={inputClassName(Boolean(fieldErrors.weight_kg))}
              />
            </Field>
          </div>
        </div>
      );
    }

    if (activeStep.id === "goal") {
      return (
        <div className="space-y-7">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
              Цель, режим и бюджет
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Пользователь может быстро выбрать режим без ручного ввода сложных
              параметров.
            </p>
          </div>

          <div>
            <p className="mb-3 text-sm font-medium text-slate-700">Цель</p>
            <div className="grid gap-3 md:grid-cols-3">
              {GOAL_OPTIONS.map((option) => (
                <ChoiceCard
                  key={option.value}
                  title={option.title}
                  text={option.text}
                  isSelected={form.goal === option.value}
                  onClick={() => handleChange("goal", option.value)}
                />
              ))}
            </div>
          </div>

          <div>
            <p className="mb-3 text-sm font-medium text-slate-700">
              Активность
            </p>
            <div className="grid gap-3 md:grid-cols-3">
              {ACTIVITY_OPTIONS.map((option) => (
                <ChoiceCard
                  key={option.value}
                  title={option.title}
                  text={option.text}
                  isSelected={form.activity_level === option.value}
                  onClick={() => handleChange("activity_level", option.value)}
                />
              ))}
            </div>
          </div>

          <div className="grid gap-5 md:grid-cols-[0.9fr_1.1fr]">
            <Field label="Приемов пищи в день" error={fieldErrors.meals_per_day}>
              <div className="flex flex-wrap gap-2">
                {MEALS_PER_DAY_OPTIONS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => handleChange("meals_per_day", String(value))}
                    className={`min-h-11 min-w-12 rounded-2xl border px-4 py-2 text-sm font-semibold transition ${
                      Number(form.meals_per_day) === value
                        ? "border-emerald-600 bg-emerald-600 text-white"
                        : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    {value}
                  </button>
                ))}
              </div>
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field
                label="Бюджет на день, ₽"
                error={fieldErrors.daily_budget_rub}
              >
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

              <Field
                label="Бюджет на неделю, ₽"
                error={fieldErrors.weekly_budget_rub}
              >
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
        </div>
      );
    }

    if (activeStep.id === "products") {
      return (
        <div className="space-y-5">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
              Продукты и ограничения
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Категории раскрываются небольшими списками, чтобы выбор не
              перегружал страницу.
            </p>
          </div>

          <ProductPicker
            title="Любимые продукты"
            description="Будут чаще появляться в рекомендациях."
            categories={PRODUCT_CATEGORIES}
            selected={form.favorite_products_json}
            onChange={(value) => handleChange("favorite_products_json", value)}
          />

          <ProductPicker
            title="Нелюбимые продукты"
            description="Такие продукты лучше понижать в выдаче или избегать."
            categories={PRODUCT_CATEGORIES}
            selected={form.disliked_products_json}
            onChange={(value) => handleChange("disliked_products_json", value)}
          />

          <ProductPicker
            title="Аллергии"
            description="Аллергены должны исключаться из будущего рациона."
            categories={ALLERGY_CATEGORIES}
            selected={form.allergies_json}
            onChange={(value) => handleChange("allergies_json", value)}
          />
        </div>
      );
    }

    if (activeStep.id === "region") {
      return (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
              Регион питания
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
              Региональная зона помогает учитывать привычные продукты и будущую
              сезонность.
            </p>
          </div>

          <Field label="Ваш регион" error={fieldErrors.region_code}>
            <select
              value={form.region_code}
              onChange={(e) => handleChange("region_code", e.target.value)}
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

          {selectedFoodZone ? (
            <div className="rounded-3xl border border-emerald-100 bg-emerald-50 p-5 text-sm text-emerald-900">
              <p className="font-semibold">{selectedFoodZone.name}</p>
              <p className="mt-2 leading-6">
                Типичные продукты: {selectedFoodZone.products.join(", ")}.
              </p>
            </div>
          ) : null}
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-950">
            Проверьте анкету
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-500">
            После сохранения главный экран и рекомендации будут использовать эти
            настройки.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <SummaryRow label="Пол" value={humanSex(form.sex)} />
          <SummaryRow label="Возраст" value={form.age ? `${form.age} лет` : ""} />
          <SummaryRow label="Рост" value={form.height_cm ? `${form.height_cm} см` : ""} />
          <SummaryRow label="Вес" value={form.weight_kg ? `${form.weight_kg} кг` : ""} />
          <SummaryRow label="Цель" value={humanGoal(form.goal)} />
          <SummaryRow label="Активность" value={humanActivity(form.activity_level)} />
          <SummaryRow label="Приемов пищи" value={form.meals_per_day} />
          <SummaryRow
            label="Бюджет"
            value={
              form.daily_budget_rub
                ? `${form.daily_budget_rub} ₽ в день`
                : form.weekly_budget_rub
                  ? `${form.weekly_budget_rub} ₽ в неделю`
                  : ""
            }
          />
          <SummaryRow
            label="Любимые продукты"
            value={form.favorite_products_json.join(", ")}
          />
          <SummaryRow
            label="Нелюбимые продукты"
            value={form.disliked_products_json.join(", ")}
          />
          <SummaryRow label="Аллергии" value={form.allergies_json.join(", ")} />
          <SummaryRow label="Зона" value={selectedFoodZone?.name} />
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-6xl px-6 py-10">
        <div className="mb-8">
          <span className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-sm font-medium text-emerald-700">
            TastePlanner • Анкета питания
          </span>
          <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight text-slate-950">
            Настройте персональный профиль
          </h1>
          <p className="mt-3 max-w-2xl text-slate-600">
            Заполняйте анкету по шагам: основные параметры, режим, продукты и
            регион.
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

        <div className="grid gap-6 lg:grid-cols-[0.35fr_0.65fr]">
          <aside className="space-y-5">
            <div className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-medium text-slate-500">Прогресс</p>
                  <p className="mt-1 text-2xl font-bold text-slate-950">
                    {progressPercent}%
                  </p>
                </div>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">
                  {completedFields}/{STEPS.length}
                </span>
              </div>
              <div className="mt-5 h-3 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-emerald-500 transition-all"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              {STEPS.map((step, index) => (
                <StepButton
                  key={step.id}
                  step={step}
                  index={index}
                  isActive={activeStepIndex === index}
                  isDone={getStepCompletion(form, step.id) > 0}
                  onClick={() => moveToStep(index)}
                />
              ))}
            </div>

            {selectedFoodZone ? (
              <div className="rounded-3xl bg-emerald-950 p-5 text-white shadow-sm">
                <h2 className="text-lg font-semibold">Региональный профиль</h2>
                <p className="mt-3 text-sm font-medium text-emerald-200">
                  {selectedFoodZone.name}
                </p>
                <p className="mt-3 text-sm leading-6 text-slate-200">
                  {selectedFoodZone.products.join(", ")}
                </p>
              </div>
            ) : null}
          </aside>

          <section className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200 sm:p-8">
            {isLoading ? (
              <p className="text-sm text-slate-500">
                Загружаем текущие данные профиля...
              </p>
            ) : (
              <form className="space-y-8" onSubmit={handleSubmit}>
                <div className="min-h-[28rem]">{renderStep()}</div>

                <div className="flex flex-col gap-4 border-t border-slate-200 pt-6 sm:flex-row sm:items-center sm:justify-between">
                  <button
                    type="button"
                    onClick={() => moveToStep(activeStepIndex - 1)}
                    disabled={activeStepIndex === 0 || isSaving}
                    className="inline-flex min-h-12 items-center justify-center rounded-2xl border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Назад
                  </button>

                  <div className="flex flex-col gap-3 sm:flex-row">
                    {activeStepIndex < STEPS.length - 1 ? (
                      <button
                        type="button"
                        onClick={() => moveToStep(activeStepIndex + 1)}
                        disabled={isSaving}
                        className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Далее
                      </button>
                    ) : (
                      <button
                        type="submit"
                        disabled={isSaving}
                        className="inline-flex min-h-12 items-center justify-center rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-semibold text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {isSaving ? "Сохраняем..." : "Сохранить анкету"}
                      </button>
                    )}
                  </div>
                </div>
              </form>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
