import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import OnboardingPage from "./pages/OnboardingPage";
import MealPlanPage from "./pages/MealPlanPage";
import WeeklyMealPlanPage from "./pages/WeeklyMealPlanPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import ProfilePage from "./pages/ProfilePage";
import RecipesPage from "./pages/RecipesPage";
import FavoritesPage from "./pages/FavoritesPage";
import {
  createAuthSession,
  fetchCurrentUser,
  refreshSession,
} from "./lib/auth";

const AUTH_STORAGE_KEY = "tasteplanner.auth";
const FAVORITES_STORAGE_KEY = "favorites";

function ProtectedRoute({ isAuthenticated, isAuthReady, children }) {
  if (!isAuthReady) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-6xl items-center justify-center px-6">
        <div className="rounded-2xl bg-white px-6 py-4 text-sm text-slate-500 ring-1 ring-slate-200">
          Проверяем сессию...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return children;
}

export default function App() {
  const [authSession, setAuthSession] = useState(() => {
    const savedAuth = localStorage.getItem(AUTH_STORAGE_KEY);

    if (!savedAuth) {
      return null;
    }

    try {
      return JSON.parse(savedAuth);
    } catch {
      return null;
    }
  });
  const [isAuthReady, setIsAuthReady] = useState(false);
  const [favorites, setFavorites] = useState(() => {
    const savedFavorites = localStorage.getItem(FAVORITES_STORAGE_KEY);
    return savedFavorites ? JSON.parse(savedFavorites) : [];
  });

  const isAuthenticated = Boolean(authSession?.accessToken);
  const accessToken = authSession?.accessToken;
  const refreshToken = authSession?.refreshToken;

  useEffect(() => {
    if (authSession) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authSession));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  }, [authSession]);

  useEffect(() => {
    localStorage.setItem(FAVORITES_STORAGE_KEY, JSON.stringify(favorites));
  }, [favorites]);

  useEffect(() => {
    let isActive = true;

    async function bootstrapAuth() {
      if (!accessToken) {
        if (isActive) {
          setIsAuthReady(true);
        }
        return;
      }

      try {
        const user = await fetchCurrentUser(accessToken);
        if (isActive) {
          setAuthSession((prev) => (prev ? { ...prev, user } : prev));
          setIsAuthReady(true);
        }
        return;
      } catch {
        if (!refreshToken) {
          if (isActive) {
            setAuthSession(null);
            setIsAuthReady(true);
          }
          return;
        }
      }

      try {
        const refreshed = await refreshSession(refreshToken);
        const nextSession = createAuthSession(refreshed);
        const user = await fetchCurrentUser(nextSession.accessToken);

        if (isActive) {
          setAuthSession({ ...nextSession, user });
          setIsAuthReady(true);
        }
      } catch {
        if (isActive) {
          setAuthSession(null);
          setIsAuthReady(true);
        }
      }
    }

    bootstrapAuth();

    return () => {
      isActive = false;
    };
  }, [accessToken, refreshToken]);

  const handleAuthSuccess = (session) => {
    setAuthSession(session);
    setIsAuthReady(true);
  };

  const handleLogout = () => {
    setAuthSession(null);
    setIsAuthReady(true);
  };

  const toggleFavorite = (recipe) => {
    setFavorites((prev) => {
      const exists = prev.some((item) => item.id === recipe.id);

      if (exists) {
        return prev.filter((item) => item.id !== recipe.id);
      }

      return [...prev, recipe];
    });
  };

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Navbar isAuthenticated={isAuthenticated} onLogout={handleLogout} />

        <Routes>
          <Route path="/" element={<HomePage />} />

          <Route
            path="/auth"
            element={
              isAuthenticated && isAuthReady ? (
                <Navigate to="/profile" replace />
              ) : (
                <AuthPage onAuthSuccess={handleAuthSuccess} />
              )
            }
          />

          <Route
            path="/onboarding"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <OnboardingPage authSession={authSession} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/meal-plan"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <MealPlanPage authSession={authSession} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/meal-plan/week"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <WeeklyMealPlanPage authSession={authSession} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/shopping-list"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <ShoppingListPage authSession={authSession} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/profile"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <ProfilePage authSession={authSession} />
              </ProtectedRoute>
            }
          />

          <Route
            path="/recipes"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <RecipesPage
                  authSession={authSession}
                  favorites={favorites}
                  toggleFavorite={toggleFavorite}
                />
              </ProtectedRoute>
            }
          />

          <Route
            path="/favorites"
            element={
              <ProtectedRoute
                isAuthenticated={isAuthenticated}
                isAuthReady={isAuthReady}
              >
                <FavoritesPage
                  favorites={favorites}
                  toggleFavorite={toggleFavorite}
                />
              </ProtectedRoute>
            }
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
