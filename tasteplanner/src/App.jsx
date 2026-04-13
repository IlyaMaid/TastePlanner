import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar";
import HomePage from "./pages/HomePage";
import AuthPage from "./pages/AuthPage";
import OnboardingPage from "./pages/OnboardingPage";
import MealPlanPage from "./pages/MealPlanPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import ProfilePage from "./pages/ProfilePage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/meal-plan" element={<MealPlanPage />} />
          <Route path="/shopping-list" element={<ShoppingListPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}