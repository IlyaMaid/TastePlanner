import { API_BASE_URL, parseApiError } from "./auth";

async function requestFavorites(path, accessToken, options = {}) {
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

export function fetchFavorites(accessToken) {
  return requestFavorites("/favorites", accessToken);
}

export function addFavorite(accessToken, recipeId) {
  return requestFavorites(`/favorites/${recipeId}`, accessToken, {
    method: "POST",
  });
}

export function removeFavorite(accessToken, recipeId) {
  return requestFavorites(`/favorites/${recipeId}`, accessToken, {
    method: "DELETE",
  });
}
