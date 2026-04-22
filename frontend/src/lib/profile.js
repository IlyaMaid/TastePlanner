import { API_BASE_URL, parseApiError } from "./auth";

async function requestProfile(path, accessToken, options = {}) {
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

export function fetchMyProfile(accessToken) {
  return requestProfile("/users/me/profile", accessToken);
}

export function updateMyProfile(accessToken, profile) {
  return requestProfile("/users/me/profile", accessToken, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}
