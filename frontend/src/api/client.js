const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
let authorizationHeader = null;

export function setBasicCredentials(username, password) {
  authorizationHeader = `Basic ${btoa(`${username}:${password}`)}`;
}

export function clearCredentials() {
  authorizationHeader = null;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(authorizationHeader ? { Authorization: authorizationHeader } : {}),
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }

  return response.json();
}

export function apiGet(path) {
  return request(path);
}

export function apiPost(path, payload) {
  return request(path, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}