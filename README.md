# TastePlanner

TastePlanner - полнофункциональное веб-приложение для персонального планирования питания. Пользователь заполняет профиль, получает рекомендации рецептов, собирает план на день или неделю, оценивает калории, БЖУ и примерную стоимость продуктов, а затем формирует список покупок.

Приложение ориентировано на русскоязычный сценарий использования: рецепты, анкета, продуктовый каталог, пояснения рекомендаций и сводки по плану питания отображаются на русском языке.

## Возможности

- Регистрация, вход, обновление JWT-сессии и загрузка профиля текущего пользователя.
- Анкета пользователя: цель, активность, регион, бюджет, количество приемов пищи, аллергии, нелюбимые и любимые продукты.
- Рекомендации рецептов с калориями, БЖУ, примерной стоимостью, ингредиентами, шагами приготовления, тегами и объяснением причины рекомендации.
- План питания на день и неделю с распределением блюд по приемам пищи.
- Варианты замены блюда внутри плана питания.
- Список покупок с группировкой ингредиентов и приблизительной ценой.
- Поддержка российского продуктового каталога с пищевой ценностью и ценами.
- Техническая страница `/readiness` для проверки готовности данных, обратной связи и модели.
- Гибридная рекомендательная логика: профиль пользователя, признаки рецептов, обратная связь, similarity scoring и модельное ранжирование.

## Стек

- Backend: FastAPI, SQLAlchemy, Pydantic, PostgreSQL.
- Frontend: React, Vite, React Router, Tailwind CSS.
- ML и обработка данных: pandas, numpy, scikit-learn, scipy, joblib, matplotlib.
- Опционально для обучения моделей: CatBoost или XGBoost, если установлены в окружении.

## Структура проекта

```text
backend/      FastAPI-приложение, API-роутеры, схемы, SQLAlchemy-модели, сервисы
frontend/     клиентское React/Vite-приложение
postgress/    SQL-схемы и миграции
scripts/      импорт данных, построение признаков, обучение моделей, отчеты
datasets/     локальные CSV-датасеты, не коммитятся
artifacts/    сгенерированные выборки, отчеты, графики и модели, не коммитятся
```

## Требования

- Python 3.11 или новее.
- Node.js 20 или новее.
- PostgreSQL 14 или новее.
- Команды ниже рассчитаны на Windows PowerShell и путь проекта `D:\TastePlanner`.

## Переменные окружения

Backend читает настройки из `backend/.env`. Настоящий `.env` не должен попадать в GitHub, поэтому перед запуском создайте его из примера:

```powershell
Copy-Item backend\.env.example backend\.env
```

Затем отредактируйте `backend\.env`:

```env
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tasteplanner
SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
FRONTEND_BASE_URL=http://localhost:5173
```

`DEBUG` по умолчанию `false` (безопасно для продакшна) — для локальной разработки держите `DEBUG=true`.

Восстановление пароля (`/auth/forgot-password`) отправляет письмо со ссылкой сброса через SMTP. Если переменные `SMTP_HOST` и т.д. не заданы, ссылка вместо отправки просто пишется в лог backend (уровень WARNING) — этого достаточно для локальной разработки. Для реальной отправки писем заполните `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_USE_TLS` в `.env` (см. `backend/.env.example`).

Frontend может запускаться без env-файла: по умолчанию он обращается к `http://localhost:8000`. Если нужно указать другой адрес API, создайте `frontend/.env`:

```powershell
Copy-Item frontend\.env.example frontend\.env
```

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Запуск backend

Создайте виртуальное окружение и установите зависимости:

```powershell
cd D:\TastePlanner
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r scripts\requirements.txt
```

Создайте базу PostgreSQL `tasteplanner`, затем примените SQL-файлы из `postgress/` под нужное состояние схемы. Приложению нужны таблицы пользователей, профилей, рецептов, ингредиентов, ограничений, сезонности, регионов, логов рекомендаций и сигналов обратной связи для обучения.

Начиная с этой версии, новые изменения схемы (например, избранные рецепты, восстановление пароля) применяются через Alembic, а не файлы в `postgress/`. После применения SQL-файлов из `postgress/` накатите Alembic-миграции:

```powershell
cd D:\TastePlanner\backend
..\.venv\Scripts\python.exe -m alembic upgrade head
```

Таблицы, которыми управляет `postgress/*.sql` (recipes, ingredients и т.д.), Alembic не трогает — `alembic/env.py` явно исключает их из автогенерации, чтобы не предлагать их удаление или изменение.

Запускайте backend из папки `backend`, чтобы `.env` корректно подхватился:

```powershell
cd D:\TastePlanner\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Проверка:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"status":"ok"}
```

## Запуск frontend

```powershell
cd D:\TastePlanner\frontend
npm install
npm run dev
```

Обычно приложение доступно по адресу:

```text
http://localhost:5173
```

## Данные и обучение модели

Локальные датасеты и сгенерированные ML-артефакты намеренно исключены из git. Исходные CSV храните в `datasets/`, а модели, отчеты и графики - в `artifacts/`.

Полный пайплайн обновления рекомендательной системы:

```powershell
cd D:\TastePlanner
.\.venv\Scripts\python.exe scripts\retrain_recommender.py
```

Пайплайн может:

- импортировать curated Russian recipes;
- построить признаки рецептов;
- сгенерировать bootstrap-обратную связь;
- экспортировать обучающий датасет;
- разделить данные на train/validation/test;
- обучить content ranker;
- посчитать baseline;
- сгенерировать графики;
- обновить отчет о качестве данных.

Если рецепты уже есть в базе, импорт можно пропустить:

```powershell
.\.venv\Scripts\python.exe scripts\retrain_recommender.py --skip-import
```

Основные сгенерированные файлы:

```text
artifacts/recommender/tasteplanner_content_ranker.joblib
artifacts/recommender/tasteplanner_content_ranker_report.json
artifacts/recommender/retrain_summary.json
artifacts/recommender/training_plots/
artifacts/training/tasteplanner_training_dataset.csv
artifacts/training/tasteplanner_data_quality_report.json
```

## Проверки перед публикацией

Проверка backend:

```powershell
cd D:\TastePlanner
.\.venv\Scripts\python.exe -m py_compile backend\app\main.py backend\app\api\recommendations.py backend\app\api\recipes.py backend\app\services\recommender.py
```

Проверка frontend:

```powershell
cd D:\TastePlanner\frontend
npm run lint
npm run build
```

Проверка репозитория:

```powershell
cd D:\TastePlanner
git status --short
```

Перед отправкой на GitHub убедитесь, что не коммитятся:

- `backend/.env` и другие реальные env-файлы;
- `.venv/`, `venv/`, `frontend/node_modules/`, `frontend/dist/`;
- `datasets/` с приватными или тяжелыми исходными данными;
- `artifacts/` с моделями, отчетами, скриншотами и обучающими выборками;
- личные coursework-скрипты и временные файлы обработки документов.

## Публикация на GitHub

Один из вариантов публикации текущей ветки:

```powershell
cd D:\TastePlanner
git status --short
git add README.md .gitignore backend\.env.example frontend\.env.example
git commit -m "Prepare project for GitHub"
git remote add origin https://github.com/<your-login>/<repo-name>.git
git push -u origin newback
```

Если remote уже добавлен:

```powershell
git remote -v
git push -u origin newback
```
