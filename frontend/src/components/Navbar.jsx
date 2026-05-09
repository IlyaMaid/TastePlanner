import { Link, useLocation, useNavigate } from "react-router-dom";

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

export default function Navbar({ isAuthenticated, onLogout }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    onLogout();
    navigate("/");
  };

  const navigationItems = [
    { to: "/", label: "Сегодня" },
    { to: "/meal-plan", label: "План питания" },
    { to: "/recipes", label: "Рецепты" },
    { to: "/shopping-list", label: "Покупки" },
    { to: "/profile", label: "Профиль" },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-6 py-4 md:flex-row md:items-center md:justify-between">
        <Link
          to="/"
          className="flex items-center gap-2 text-xl font-bold text-slate-900"
        >
          <LogoIcon />
          TastePlanner
        </Link>

        {!isAuthenticated ? (
          <nav className="flex items-center gap-3 text-sm font-medium">
            <Link
              to="/"
              className="rounded-xl px-3 py-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              Главная
            </Link>
            <Link
              to="/auth"
              className="rounded-xl bg-slate-900 px-4 py-2 text-white transition hover:opacity-90"
            >
              Войти
            </Link>
          </nav>
        ) : (
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <nav className="flex max-w-full items-center gap-2 overflow-x-auto rounded-2xl bg-slate-100 p-1">
              {navigationItems.map((item) => {
                const isActive = location.pathname === item.to;

                return (
                  <Link
                    key={item.to}
                    to={item.to}
                    className={`shrink-0 rounded-xl px-4 py-2 text-sm font-medium transition ${
                      isActive
                        ? "bg-white text-slate-900 shadow-sm"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <button
              type="button"
              onClick={() => navigate("/onboarding")}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Анкета
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
            >
              Выйти
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
