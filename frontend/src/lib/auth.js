const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export { API_BASE_URL };

export async function parseApiError(response) {
  try {
    const data = await response.json();
    return {
      message: data.detail ?? "Произошла ошибка",
      errors: data.errors ?? {},
    };
  } catch {
    return {
      message: "Не удалось выполнить запрос",
      errors: {},
    };
  }
}

async function requestJson(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
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

export function createAuthSession(payload) {
  return {
    accessToken: payload.access_token,
    refreshToken: payload.refresh_token,
    tokenType: payload.token_type,
    expiresIn: payload.expires_in,
    user: payload.user,
  };
}

export function validateLoginForm(form) {
  const errors = {};

  if (!form.email.trim()) {
    errors.email = "Введите email";
  }

  if (!form.password.trim()) {
    errors.password = "Введите пароль";
  }

  return errors;
}

export function validateRegisterForm(form) {
  const errors = {};
  const password = form.password.trim();

  if (!form.name.trim()) {
    errors.name = "Введите имя";
  }

  if (!form.email.trim()) {
    errors.email = "Введите email";
  }

  if (password.length < 8) {
    errors.password = "Пароль должен быть не короче 8 символов";
  } else {
    if (!/[A-Za-zА-Яа-я]/.test(password)) {
      errors.password = "Пароль должен содержать хотя бы одну букву";
    }
    if (!/\d/.test(password)) {
      errors.password = "Пароль должен содержать хотя бы одну цифру";
    }
  }

  if (!form.confirmPassword.trim()) {
    errors.confirmPassword = "Повторите пароль";
  } else if (form.password !== form.confirmPassword) {
    errors.confirmPassword = "Пароли не совпадают";
  }

  return errors;
}

export function loginRequest(form) {
  return requestJson("/auth/login", {
    method: "POST",
    body: JSON.stringify(form),
  });
}

export function registerRequest(form) {
  return requestJson("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      name: form.name,
      email: form.email,
      password: form.password,
    }),
  });
}

export function refreshSession(refreshToken) {
  return requestJson("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({
      refresh_token: refreshToken,
    }),
  });
}

export function fetchCurrentUser(accessToken) {
  return requestJson("/users/me", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}
