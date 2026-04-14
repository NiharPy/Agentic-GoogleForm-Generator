const API_BASE = 'http://localhost:8020';

/**
 * API service for communicating with the FormFlow backend.
 * Handles authentication headers and all conversation endpoints.
 */

function getAuthHeaders() {
  const token = localStorage.getItem('jwt_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Start a new conversation (first prompt)
 * POST /conversations/start
 */
export async function startConversation(prompt) {
  const response = await fetch(`${API_BASE}/conversations/start`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ prompt }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Continue an existing conversation (follow-up prompts)
 * POST /conversations/{conversation_id}/continue
 */
export async function continueConversation(conversationId, message, documents = null) {
  const body = { message };
  if (documents) body.documents = documents;

  const response = await fetch(`${API_BASE}/conversations/${conversationId}/continue`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get all conversations for the current user
 * GET /conversations/
 */
export async function getConversations() {
  const response = await fetch(`${API_BASE}/conversations/`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get a single conversation by ID
 * GET /conversations/{conversation_id}
 */
export async function getConversation(conversationId) {
  const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Delete a conversation
 * DELETE /conversations/{conversation_id}
 */
export async function deleteConversation(conversationId) {
  const response = await fetch(`${API_BASE}/conversations/${conversationId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Initiate Google OAuth login
 * Redirects user to the backend's /auth/login endpoint
 */
export function initiateGoogleLogin() {
  window.location.href = `${API_BASE}/auth/login`;
}

/**
 * Exchange Google OAuth code for JWT
 * POST /auth/google
 */
export async function exchangeGoogleCode(code) {
  const response = await fetch(`${API_BASE}/auth/google`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }

  return response.json();
}

/**
 * Check if user is authenticated
 */
export function isAuthenticated() {
  return !!localStorage.getItem('jwt_token');
}

/**
 * Save JWT token
 */
export function saveToken(token) {
  localStorage.setItem('jwt_token', token);
}

/**
 * Clear JWT token (logout)
 */
export function logout() {
  localStorage.removeItem('jwt_token');
}
