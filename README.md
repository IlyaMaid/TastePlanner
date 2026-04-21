# TastePlanner

Веб-приложение для курсовой работы на тему: **«Цифровой помощник для планирования рациона на основе анализа предпочтений»**.

## Описание проекта

**TastePlanner** — это многостраничное веб-приложение, которое помогает пользователю формировать персональный рацион с учетом:

- целей питания;
- вкусовых предпочтений;
- нелюбимых продуктов;
- аллергий и ограничений;
- уровня активности;
- бюджета;
- количества приемов пищи.

На текущем этапе реализован пользовательский интерфейс MVP на **React**.

## Реализованные страницы

- **Главная страница**
- **Страница входа / регистрации**
- **Страница анкеты предпочтений**
- **Страница плана питания**
- **Страница списка покупок**
- **Страница личного кабинета**

## Используемые технологии

### Frontend
- **React**
- **Vite**
- **React Router DOM**
- **Tailwind CSS v4**

### Планируемый backend
- **Python**
- **FastAPI**
- **PostgreSQL**

## Структура проекта

```bash
frontend/
├── public/
├── src/
│   ├── components/
│   │   └── Navbar.jsx
│   ├── pages/
│   │   ├── AuthPage.jsx
│   │   ├── HomePage.jsx
│   │   ├── MealPlanPage.jsx
│   │   ├── OnboardingPage.jsx
│   │   ├── ProfilePage.jsx
│   │   └── ShoppingListPage.jsx
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── package.json
├── vite.config.js
└── README.md
```

## Требования для запуска

Перед запуском необходимо установить:

- **Node.js**
- **npm**

Проверить установку можно командами:

```bash
node -v
npm -v
```

## Установка и запуск проекта

### 1. Перейти в папку проекта

```bash
cd frontend
```

### 2. Установить зависимости

```bash
npm install
```

### 3. Запустить проект в режиме разработки

```bash
npm run dev
```

После запуска в терминале появится локальный адрес, например:

```bash
http://localhost:5173/
```

Открой его в браузере.

## Установка дополнительных зависимостей

Если проект создается с нуля, могут понадобиться дополнительные библиотеки:

### React Router
```bash
npm install react-router-dom
```

### Tailwind CSS v4 для Vite
```bash
npm install tailwindcss @tailwindcss/vite
```

## Настройка Tailwind CSS v4

### `vite.config.js`

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

### `src/index.css`

```css
@import "tailwindcss";
```

## Возможные ошибки и решения

### 1. Ошибка PowerShell: выполнение сценариев отключено

Если при запуске `npm` возникает ошибка в PowerShell, выполните:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

После этого подтвердите действие клавишей `Y`.

### 2. Ошибка `Missing script: "dev"`

Эта ошибка означает, что команда запускается не из папки проекта. Нужно перейти в директорию, где находится `package.json`:

```bash
cd frontend
npm run dev
```

### 3. Ошибка с Tailwind `could not determine executable to run`

Для **Tailwind CSS v4** не требуется команда:

```bash
npx tailwindcss init -p
```

Вместо этого нужно установить:

```bash
npm install tailwindcss @tailwindcss/vite
```

И подключить Tailwind через `vite.config.js`.

## Перспективы развития проекта

В дальнейшем приложение можно расширить следующими возможностями:

- подключение backend на **FastAPI**;
- работа с базой данных **PostgreSQL**;
- сохранение профиля пользователя;
- генерация персонального рациона на основе анкеты;
- хранение истории питания;
- рекомендации по рецептам;
- расчет КБЖУ в реальном времени;
- адаптация меню на основе обратной связи пользователя.

## Автор

Проект разработан в рамках курсовой работы по теме:

**«Цифровой помощник для планирования рациона на основе анализа предпочтений»**
