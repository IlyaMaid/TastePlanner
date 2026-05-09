# TastePlanner

Веб-приложение для планирования персонального рациона с учетом анкеты пользователя, бюджета, сезонности, аллергий, любимых и нелюбимых продуктов.

## Что реализовано

- Авторизация и профиль пользователя.
- Расширенная анкета: цель, активность, регион, бюджет, количество приемов пищи, предпочтения, аллергии.
- Рекомендации рецептов на русском языке.
- Расширенная карточка рецепта: способ приготовления, ингредиенты, стоимость, калории, источник и ML-оценки.
- План питания на день и неделю.
- Список покупок с группировкой продуктов и примерной стоимостью.
- Сезонность продуктов и региональные зоны России.
- Гибридная рекомендательная система:
  - content-based filtering;
  - cosine similarity / KNN-подход по векторам пользователя и блюд;
  - модель предсказания вероятности лайка;
  - оптимизация распределения блюд по приемам пищи через `scipy.optimize`.
- Страница `/readiness` для проверки готовности данных, обратной связи и модели.

## Технологии

- Frontend: React, Vite, React Router, Tailwind CSS.
- Backend: FastAPI, SQLAlchemy, PostgreSQL.
- ML/Data: pandas, numpy, scikit-learn, joblib, scipy.
- Опционально для модели: CatBoost или XGBoost, если установлены в окружении.

## Запуск backend

```powershell
cd D:\TastePlanner
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

Если команда запускается из папки `backend`, можно использовать:

```powershell
cd D:\TastePlanner\backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Запуск frontend

```powershell
cd D:\TastePlanner\frontend
npm install
npm run dev
```

Обычно приложение доступно на `http://localhost:5173/`.

## Подготовка данных и обучение модели

Полный пайплайн подготовки данных и переобучения:

```powershell
cd D:\TastePlanner
.\.venv\Scripts\python.exe scripts\retrain_recommender.py
```

Скрипт последовательно:

1. Импортирует curated Russian recipes.
2. Обновляет признаки рецептов.
3. Генерирует bootstrap-обратную связь.
4. Экспортирует training dataset.
5. Делит данные на train / validation / test.
6. Обучает content-based ranker.
7. Считает baseline.
8. Генерирует графики обучения через matplotlib.
9. Обновляет data quality report.

Основные артефакты:

- `artifacts/recommender/tasteplanner_content_ranker.joblib`
- `artifacts/recommender/tasteplanner_content_ranker_report.json`
- `artifacts/recommender/retrain_summary.json`
- `artifacts/recommender/training_plots/`
- `artifacts/training/tasteplanner_training_dataset.csv`
- `artifacts/training/tasteplanner_data_quality_report.json`

Если нужно переобучить только модель без повторного импорта рецептов:

```powershell
.\.venv\Scripts\python.exe scripts\retrain_recommender.py --skip-import
```

Если CatBoost или XGBoost не установлены, режим `--model auto` использует sklearn-модель.

Отдельно пересоздать только графики обучения:

```powershell
.\.venv\Scripts\python.exe scripts\generate_training_plots.py
```

## Проверки

Backend и scripts:

```powershell
cd D:\TastePlanner
.\.venv\Scripts\python.exe -m py_compile backend\app\api\recommendations.py scripts\retrain_recommender.py scripts\train_content_based_ranker.py
```

Frontend:

```powershell
cd D:\TastePlanner\frontend
npm run lint
npm run build
```

## Структура проекта

```text
backend/      FastAPI backend, API, модели БД, сервис рекомендаций
frontend/     React frontend
scripts/      импорт данных, построение признаков, обучение и отчеты
postgress/    SQL-миграции и схема
datasets/     локальные CSV-датасеты
artifacts/    обучающие выборки, отчеты и ML-модель
```
