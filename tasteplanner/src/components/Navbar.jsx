import { Link } from "react-router-dom";

function LogoIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      xmlns="http://www.w3.org/2000/svg"
      className="h-6 w-6 text-emerald-600"
    >
      <path d="M3 11h18" />
      <path d="M5 11a7 7 0 0 0 14 0" />
      <path d="M12 11V5" />
      <path d="M10 7c0-1.5 1-3 2-4 1 1 2 2.5 2 4" />
    </svg>
  );
}

export default function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link
          to="/"
          className="flex items-center gap-2 text-xl font-bold text-slate-900"
        >
          <LogoIcon />
          TastePlanner
        </Link>

        <nav className="flex items-center gap-6 text-sm font-medium text-slate-600">
          <Link to="/" className="hover:text-slate-900">Главная</Link>
          <Link to="/auth" className="hover:text-slate-900">Войти</Link>
          <Link to="/onboarding" className="hover:text-slate-900">Анкета</Link>
          <Link to="/meal-plan" className="hover:text-slate-900">План питания</Link>
          <Link to="/shopping-list" className="hover:text-slate-900">Покупки</Link>
          <Link to="/profile" className="hover:text-slate-900">Профиль</Link>
        </nav>
      </div>
    </header>
  );
}