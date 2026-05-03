import { API_BASE_URL, parseApiError } from "./auth";

async function requestRecommendations(path, accessToken, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw await parseApiError(response);
  }

  return response.json();
}

export function fetchRecommendations(accessToken, options = {}) {
  const params = new URLSearchParams();

  if (options.limit) {
    params.set("limit", String(options.limit));
  }

  if (options.demoUserIndex !== undefined && options.demoUserIndex !== null) {
    params.set("demo_user_index", String(options.demoUserIndex));
  }

  const query = params.toString();
  return requestRecommendations(
    `/recommendations${query ? `?${query}` : ""}`,
    accessToken,
  );
}

export function saveRecommendationFeedback(accessToken, payload) {
  return requestRecommendations("/recommendations/feedback", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveUserEvent(accessToken, payload) {
  return requestRecommendations("/recommendations/events", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchReadiness(accessToken) {
  return requestRecommendations("/recommendations/readiness", accessToken);
}

export function fetchMealPlan(accessToken, options = {}) {
  const params = new URLSearchParams();

  if (options.limit) {
    params.set("limit", String(options.limit));
  }

  if (options.mealsPerDay) {
    params.set("meals_per_day", String(options.mealsPerDay));
  }

  const query = params.toString();
  return requestRecommendations(
    `/recommendations/meal-plan${query ? `?${query}` : ""}`,
    accessToken,
  );
}

export function swapMeal(accessToken, payload) {
  return requestRecommendations("/recommendations/meal-plan/swap", accessToken, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchShoppingList(accessToken, options = {}) {
  const params = new URLSearchParams();

  if (options.days) {
    params.set("days", String(options.days));
  }

  if (options.mealsPerDay) {
    params.set("meals_per_day", String(options.mealsPerDay));
  }

  const query = params.toString();
  return requestRecommendations(
    `/recommendations/shopping-list${query ? `?${query}` : ""}`,
    accessToken,
  );
}

export function fetchRecipeCatalog(accessToken, options = {}) {
  const params = new URLSearchParams();

  if (options.limit) {
    params.set("limit", String(options.limit));
  }

  if (options.offset) {
    params.set("offset", String(options.offset));
  }

  if (options.search?.trim()) {
    params.set("search", options.search.trim());
  }

  if (options.source?.trim()) {
    params.set("source", options.source.trim());
  }

  const query = params.toString();
  return requestRecommendations(`/recipes${query ? `?${query}` : ""}`, accessToken);
}
