import axios from 'axios';

const resolveApiBaseUrl = () => {
  if (typeof window !== 'undefined' && window.myAgentDesktop?.backendBaseUrl) {
    return window.myAgentDesktop.backendBaseUrl;
  }

  return import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
};

const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  timeout: 600000,
});

const SESSION_STORAGE_KEY = 'my-agent-session-id';

const createSessionId = () => {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }

  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

const getClientSessionId = () => {
  if (typeof window === 'undefined') {
    return 'default';
  }

  let sessionId = window.localStorage.getItem(SESSION_STORAGE_KEY);
  if (!sessionId) {
    sessionId = createSessionId();
    window.localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
  }

  return sessionId;
};

const resolveSessionId = (sessionId) => {
  if (sessionId && String(sessionId).trim()) {
    return String(sessionId).trim();
  }
  return getClientSessionId();
};

export const checkHealth = () => api.get('/health');
export const getProfile = () => api.get('/api/profile');
export const getTasks = () => api.get('/api/tasks');
export const getPetState = () => api.get('/api/pet/state');
export const sendPetEvent = (event, payload = {}) => api.post('/api/pet/event', {
  event,
  payload
});
export const getCompanionSummary = () => api.get('/api/companion/summary');
export const sendCompanionCheckIn = (mood = '', note = '') => api.post('/api/companion/check-in', {
  mood,
  note
});
export const getMcpStatus = () => api.get('/api/mcp/status');
export const getMcpTools = () => api.get('/api/mcp/tools');
export const reloadMcp = () => api.post('/api/mcp/reload');
export const getActionQueue = () => api.get('/api/actions');
export const approveAction = (actionId, execute = true) => api.post(`/api/actions/${actionId}/approve`, {
  execute
});
export const rejectAction = (actionId, reason = '') => api.post(`/api/actions/${actionId}/reject`, {
  reason
});
export const runAction = (actionId) => api.post(`/api/actions/${actionId}/run`);
export const getAppSettings = () => api.get('/api/settings');
export const saveAppSettings = (settings) => api.put('/api/settings', settings);
export const getTodayDailyReport = () => api.get('/api/daily-report/today');
export const generateDailyReport = () => api.post('/api/daily-report/generate');
export const getReminderStatus = () => api.get('/api/reminders/status');
export const getRecentLogs = (maxLines = 160) => api.get('/api/logs/recent', {
  params: { max_lines: maxLines }
});
export const getChatHistory = (sessionId = null) => api.get('/api/chat/history', {
  params: { session_id: resolveSessionId(sessionId) }
});
export const clearChat = (sessionId = null) => api.post('/api/chat/clear', {
  session_id: resolveSessionId(sessionId)
});
export const sendMessage = (message, sessionId = null, image_base64 = null) => {
  return api.post('/api/chat', {
    session_id: resolveSessionId(sessionId),
    message,
    image_base64
  });
};

export const getDocuments = () => api.get('/api/knowledge');
export const deleteDocument = (docId) => api.delete(`/api/knowledge/${docId}`);
export const uploadDocument = (file) => {
  const formData = new FormData();
  formData.append('file', file);
  return api.post('/api/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
};

export default api;
