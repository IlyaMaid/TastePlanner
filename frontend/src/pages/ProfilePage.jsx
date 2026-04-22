import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { fetchMyProfile } from "../lib/profile";

const REGION_LABELS = {
  "RU-MOW": "Москва",
  "RU-SPE": "Санкт-Петербург",
  "RU-MOS": "Московская область",
  "RU-KDA": "Краснодарский край",
  "RU-SVE": "Свердловская область",
  "RU-TA": "Республика Татарстан",
  "RU-NVS": "Новосибирская область",
};

function InfoCard({ label, value }) {
  return (
    <div className="rounded-2xl bg-slate-50 p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function formatGoal(goal) {
  const map = {
    lose_weight: "Снижение веса",
    maintain: "Поддержание веса",
    gain_weight: "Набор массы",
  };

  return map[goal] ?? "Не указана";
}

function formatActivity(value) {
  const map = {
    low: "Низкая",
    moderate: "Умеренная",
    high: "Высокая",
  };

  return map[value] ?? "Не указан";
}

function formatSex(value) {
  const map = {
    male: "Мужской",
    female: "Женский",
  };

  return map[value] ?? "Не указан";
}

function formatRegion(value) {
  if (!value) {
    return "Не выбран";
  }

  return REGION_LABELS[value] ?? value;
}

export default function ProfilePage({ authSession }) {
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

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
        const data = await fetchMyProfile(authSession.accessToken);
        if (isActive) {
          setProfile(data);
          setErrorMessage("");
        }
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

  const email = authSession?.user?.email ?? "Пользователь";
  const displayName = useMemo(
    () => authSession?.user?.display_name || email.split("@")[0] || "User",
    [authSession?.user?.display_name, email],
  );
  const initials = displayName.slice(0, 1).toUpperCase();

  const stats = [
    { label: "Email", value: email },
    { label: "Цель", value: formatGoal(profile?.goal) },
    { label: "Активность", value: formatActivity(profile?.activity_level) },
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
              Здесь собрана основная информация о вашем профиле, которая будет
              использоваться для подбора рациона и персональных рекомендаций.
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

        {errorMessage ? (
          <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {errorMessage}
          </div>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-emerald-100 text-2xl font-bold text-emerald-700">
                  {initials}
                </div>

                <div>
                  <h2 className="text-2xl font-semibold">{displayName}</h2>
                  <p className="mt-1 text-sm text-slate-500">{email}</p>
                </div>
              </div>
            </div>

            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Основные параметры</h2>

              {isLoading ? (
                <p className="mt-5 text-sm text-slate-500">Загружаем профиль...</p>
              ) : (
                <div className="mt-5 grid gap-4 sm:grid-cols-2">
                  <InfoCard label="Пол" value={formatSex(profile?.sex)} />
                  <InfoCard
                    label="Возраст"
                    value={profile?.age ?? "Не указан"}
                  />
                  <InfoCard
                    label="Рост"
                    value={
                      profile?.height_cm ? `${profile.height_cm} см` : "Не указан"
                    }
                  />
                  <InfoCard
                    label="Вес"
                    value={
                      profile?.weight_kg ? `${profile.weight_kg} кг` : "Не указан"
                    }
                  />
                  <InfoCard
                    label="Цель питания"
                    value={formatGoal(profile?.goal)}
                  />
                  <InfoCard
                    label="Уровень активности"
                    value={formatActivity(profile?.activity_level)}
                  />
                  <InfoCard
                    label="Приемов пищи в день"
                    value={profile?.meals_per_day ?? "Не указано"}
                  />
                  <InfoCard
                    label="Регион"
                    value={formatRegion(profile?.region_code)}
                  />
                </div>
              )}
            </div>
          </section>

          <aside className="space-y-6">
            <div className="rounded-3xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
              <h2 className="text-xl font-semibold">Краткая сводка</h2>

              <div className="mt-5 space-y-3">
                {stats.map((stat) => (
                  <div
                    key={stat.label}
                    className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3"
                  >
                    <span className="text-sm text-slate-600">{stat.label}</span>
                    <strong className="max-w-[14rem] text-right text-sm text-slate-900">
                      {stat.value}
                    </strong>
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
                  Изменить анкету
                </Link>

                <Link
                  to="/meal-plan"
                  className="rounded-2xl bg-white/10 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/20"
                >
                  Посмотреть рацион
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
