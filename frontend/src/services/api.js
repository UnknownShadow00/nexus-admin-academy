import axios from "axios";
import toast from "react-hot-toast";
import { getCurrentStudent, getToken } from "../hooks/useAuth";

const COLD_START_RETRY_DELAY_MS = 1500;
const RETRYABLE_STATUS_CODES = new Set([502, 503, 504]);

function isBrowser() {
  return typeof window !== "undefined";
}

function isLocalHost() {
  if (!isBrowser()) return false;
  return ["localhost", "127.0.0.1"].includes(window.location.hostname);
}

function trimTrailingSlash(value) {
  return (value || "").replace(/\/+$/, "");
}

export function getApiBaseUrl() {
  const configured = trimTrailingSlash(import.meta.env.VITE_API_URL || "");
  if (configured) return configured;
  if (isLocalHost()) return "http://localhost:8000";
  return "";
}

export const API_BASE_URL = getApiBaseUrl();

export function buildApiUrl(path = "") {
  if (!path) return API_BASE_URL || "";
  if (!API_BASE_URL) return path;
  return `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
}

const clientConfig = {
  baseURL: API_BASE_URL || undefined,
  timeout: 30000,
  withCredentials: true,
};

const api = axios.create(clientConfig);
const adminApi = axios.create(clientConfig);

let warmupPromise = null;

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = "Bearer " + token;
  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (isBrowser() && [401, 403].includes(error?.response?.status)) {
      window.dispatchEvent(new Event("nexus:admin-session-invalid"));
    }
    return Promise.reject(error);
  }
);

function unwrap(response) {
  const body = response?.data;
  if (body?.success === true) {
    return body;
  }
  return { success: true, data: body };
}

function currentStudentId() {
  return getCurrentStudent()?.id;
}

function isRetriableError(error) {
  if (!axios.isAxiosError(error)) return false;
  if (error.code === "ECONNABORTED") return true;
  if (!error.response) return true;
  return RETRYABLE_STATUS_CODES.has(error.response.status);
}

function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (error?.response) {
    return error.response.data?.error || (typeof detail === "string" ? detail : detail?.error) || "Request failed";
  }
  if (error?.code === "ECONNABORTED") {
    return "The server is taking too long to respond. If the backend is waking up, wait a few seconds and try again.";
  }
  if (error?.request) {
    return "Unable to reach the server. If this is the first request, the backend may still be waking up.";
  }
  return "Unexpected request error";
}

async function delay(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function warmBackend() {
  if (warmupPromise) {
    return warmupPromise;
  }
  warmupPromise = api
    .get("/health", { timeout: 10000, headers: { "X-Nexus-Warmup": "1" } })
    .catch(() => null)
    .finally(() => {
      warmupPromise = null;
    });
  return warmupPromise;
}

async function callWithRetry(clientCall, options = {}) {
  const retries = options.retries ?? 0;
  let attempt = 0;

  while (true) {
    try {
      return await clientCall();
    } catch (error) {
      if (!isRetriableError(error) || attempt >= retries) {
        throw error;
      }
      attempt += 1;
      if (options.warmupOnRetry) {
        await warmBackend();
      }
      await delay(COLD_START_RETRY_DELAY_MS * attempt);
    }
  }
}

function handleError(error, options = {}) {
  const message = getErrorMessage(error);
  error.userMessage = message;
  if (!options.suppressToast) {
    toast.error(message);
  }
  throw error;
}

async function request(clientCall, options = {}) {
  try {
    const response = await callWithRetry(clientCall, options);
    return unwrap(response);
  } catch (error) {
    return handleError(error, options);
  }
}

async function requestData(clientCall, options = {}) {
  try {
    const response = await callWithRetry(clientCall, options);
    return response?.data;
  } catch (error) {
    return handleError(error, options);
  }
}

export const getDashboard = (studentId, requestOptions) =>
  request(() => api.get(`/api/students/${studentId}/dashboard`), requestOptions);
export const getStudentStats = async (studentId, requestOptions) => {
  const res = await request(() => api.get(`/api/students/${studentId}/stats`), requestOptions);
  if (res?.data) return res;
  return { ...res, data: res };
};
export const checkInStudent = (studentId, requestOptions) =>
  request(() => api.post(`/api/students/${studentId}/check-in`), requestOptions);
export const getCertReadiness = (studentId, requestOptions) =>
  request(() => api.get(`/api/students/${studentId}/certification-readiness`), requestOptions);
export const getStudents = (requestOptions) => request(() => api.get("/api/students"), requestOptions);
export const getStudentMastery = (studentId, requestOptions) =>
  request(() => api.get(`/api/students/${studentId}/mastery`), requestOptions);
export const getLearningPath = (studentId, requestOptions) =>
  request(() => api.get(`/api/students/${studentId}/learning-path`), requestOptions);
export const getPromotionStatus = (studentId, requestOptions) =>
  request(() => api.get(`/api/students/${studentId}/promotion-status`), requestOptions);

export const getQuizzes = (weekNumber, studentId = currentStudentId(), requestOptions) =>
  request(() => api.get("/api/quizzes", { params: { week_number: weekNumber, student_id: studentId } }), requestOptions);
export const getQuiz = (quizId, studentId = currentStudentId(), requestOptions) =>
  request(() => api.get(`/api/quizzes/${quizId}`, { params: { student_id: studentId } }), requestOptions);
export const getQuizReview = (quizId, studentId = currentStudentId(), requestOptions) =>
  request(() => api.get(`/api/quizzes/${quizId}/review/${studentId}`), requestOptions);
export const submitQuiz = (quizId, payload, requestOptions) =>
  request(() => api.post(`/api/quizzes/${quizId}/submit`, payload), requestOptions);
export const getLabs = (weekNumber, requestOptions) =>
  request(() => api.get("/api/labs", { params: { week_number: weekNumber } }), requestOptions);
export const getLab = (labId, requestOptions) => request(() => api.get(`/api/labs/${labId}`), requestOptions);
export const startLab = (labId, requestOptions) => request(() => api.post(`/api/labs/${labId}/start`), requestOptions);
export const getLabVmStatus = (labId, requestOptions) =>
  request(() => api.get(`/api/labs/${labId}/vm-status`), requestOptions);
export const createLabVmAccess = (labId, requestOptions) =>
  request(() => api.post(`/api/labs/${labId}/vm-access`), requestOptions);
export const submitLab = (labId, payload, requestOptions) =>
  request(() => api.post(`/api/labs/${labId}/submit`, payload), requestOptions);
export const getCliLabs = (requestOptions) => request(() => api.get("/api/cli-labs"), requestOptions);
export const getCliLab = (labId, requestOptions) => request(() => api.get(`/api/cli-labs/${labId}`), requestOptions);
export const completeCliLab = (labId, payload, requestOptions) =>
  request(() => api.post(`/api/cli-labs/${labId}/complete`, payload), requestOptions);
export const uploadLabEvidence = (labRunId, file, artifactType = "screenshot", requestOptions) => {
  const form = new FormData();
  form.append("file", file);
  form.append("artifact_type", artifactType);
  return request(
    () => api.post(`/api/labs/${labRunId}/evidence`, form, { headers: { "Content-Type": "multipart/form-data" } }),
    requestOptions
  );
};
export const getCapstones = (weekNumber, requestOptions) =>
  request(() => api.get("/api/capstones", { params: { week_number: weekNumber } }), requestOptions);
export const getCapstone = (capstoneId, requestOptions) => request(() => api.get(`/api/capstones/${capstoneId}`), requestOptions);
export const startCapstone = (capstoneId, requestOptions) =>
  request(() => api.post(`/api/capstones/${capstoneId}/start`), requestOptions);
export const submitCapstone = (capstoneId, payload, requestOptions) =>
  request(() => api.post(`/api/capstones/${capstoneId}/submit`, payload), requestOptions);
export const getCurriculum = (requestOptions) => request(() => api.get("/api/study-tracker/curriculum"), requestOptions);
export const getCurriculumLinkStatus = (requestOptions) =>
  request(() => adminApi.get("/api/study-tracker/curriculum/link-status"), requestOptions);
export const getStudyTracker = (studentId = currentStudentId(), requestOptions) =>
  request(() => api.get(`/api/study-tracker/${studentId}`), requestOptions);
export const markVideoWatched = (videoKey, studentId = currentStudentId(), requestOptions) =>
  request(() => api.post(`/api/study-tracker/${studentId}/watch/${encodeURIComponent(videoKey)}`), requestOptions);
export const unmarkVideoWatched = (videoKey, studentId = currentStudentId(), requestOptions) =>
  request(() => api.delete(`/api/study-tracker/${studentId}/watch/${encodeURIComponent(videoKey)}`), requestOptions);
export const updateCurriculumVideo = (videoId, data, requestOptions) =>
  request(() => adminApi.patch(`/api/study-tracker/curriculum/${videoId}`, data), requestOptions);

export const getTickets = (weekNumber, studentId = currentStudentId(), requestOptions) =>
  request(() => api.get("/api/tickets", { params: { week_number: weekNumber, student_id: studentId } }), requestOptions);
export const getTicket = (ticketId, requestOptions) => request(() => api.get(`/api/tickets/${ticketId}`), requestOptions);
export const revealTicketHint = (ticketId, requestOptions) =>
  request(() => api.post(`/api/tickets/${ticketId}/hint`), requestOptions);
export const getWeekPlan = (week, requestOptions) =>
  request(() => api.get(`/api/students/me/week-plan${week ? `?week=${week}` : ""}`), requestOptions);
export const submitTicket = (ticketId, payload, requestOptions) =>
  request(() => api.post(`/api/tickets/${ticketId}/submit`, payload), requestOptions);
export const getSubmission = (submissionId, requestOptions) =>
  request(() => api.get(`/api/submissions/${submissionId}`), requestOptions);

export const uploadScreenshots = (files, requestOptions) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request(
    () => api.post("/api/tickets/uploads", formData, { headers: { "Content-Type": "multipart/form-data" } }),
    requestOptions
  );
};
export const uploadEvidence = ({ file, ticketId, artifactType }, requestOptions) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("ticket_id", String(ticketId));
  formData.append("artifact_type", artifactType);
  return request(
    () => api.post("/api/evidence/upload", formData, { headers: { "Content-Type": "multipart/form-data" } }),
    requestOptions
  );
};
export const uploadOrientationEvidence = (file, requestOptions) => {
  const formData = new FormData();
  formData.append("file", file);
  return request(
    () => api.post("/api/evidence/orientation-upload", formData, { headers: { "Content-Type": "multipart/form-data" } }),
    requestOptions
  );
};

export const searchCommands = (q, requestOptions) =>
  request(() => api.get("/api/commands/search", { params: { q } }), requestOptions);
export const getCommands = (params, requestOptions) =>
  request(() => api.get("/api/commands", { params }), requestOptions);
export const getLessonNote = (lessonId, requestOptions) =>
  request(() => api.get(`/api/lessons/${lessonId}/notes`), requestOptions);
export const saveLessonNote = (lessonId, content, requestOptions) =>
  request(() => api.put(`/api/lessons/${lessonId}/notes`, { content }), requestOptions);
export const getOrientationProgress = (requestOptions) =>
  request(() => api.get("/api/onboarding"), requestOptions);
export const saveOrientationPractice = (response, requestOptions) =>
  request(() => api.put("/api/onboarding/practice-response", { response }), requestOptions);
export const globalSearch = (q, requestOptions) =>
  request(() => api.get("/api/search/global", { params: { q } }), requestOptions);

export const adminSessionStatus = (requestOptions) =>
  request(() => adminApi.get("/api/admin/session/status"), { retries: 2, warmupOnRetry: true, ...requestOptions });
export const adminSessionLogin = (credentials, requestOptions) =>
  request(() => adminApi.post("/api/admin/session/login", credentials), { retries: 2, warmupOnRetry: true, ...requestOptions });
export const adminSessionLogout = (requestOptions) =>
  request(() => adminApi.post("/api/admin/session/logout"), requestOptions);
export const getStudentTokenAsAdmin = (requestOptions) =>
  request(() => adminApi.get("/api/admin/session/student-token"), requestOptions);

export const generateQuiz = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/quiz/generate", payload), requestOptions);
export const getQuizList = (params = {}, requestOptions) =>
  request(() => adminApi.get("/api/admin/quizzes", { params }), requestOptions);
export const getEditorialQuizQueue = (params = {}, requestOptions) =>
  request(() => adminApi.get("/api/admin/quizzes/editorial-queue", { params }), requestOptions);
export const deleteQuiz = (id, requestOptions) => request(() => adminApi.delete(`/api/admin/quizzes/${id}`), requestOptions);
export const updateQuiz = (quizId, payload, requestOptions) =>
  request(() => adminApi.patch(`/api/admin/quizzes/${quizId}`, payload), requestOptions);
export const scrapeQuizPreview = (url, requestOptions) =>
  request(() => adminApi.post("/api/admin/quiz/scrape-preview", { url }), requestOptions);
export const scrapeQuizSave = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/quiz/scrape-save", payload), requestOptions);
export const bookmarkletImport = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/quiz/bookmarklet-import", payload), requestOptions);
export const getQuizQuestions = (quizId, requestOptions) =>
  request(() => adminApi.get(`/api/admin/quizzes/${quizId}/questions`), requestOptions);
export const getAdminFlaggedAttempts = (requestOptions) =>
  request(() => adminApi.get("/api/admin/quiz-attempts/flagged"), requestOptions);
export const updateQuestion = (questionId, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/questions/${questionId}`, payload), requestOptions);
export const createTicket = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/tickets", payload), requestOptions);
export const getSubmissions = (requestOptions) => request(() => adminApi.get("/api/admin/submissions"), requestOptions);
export const getSubmissionDetail = (id, requestOptions) =>
  request(() => adminApi.get(`/api/admin/submissions/${id}`), requestOptions);
export const createResource = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/resources", payload), requestOptions);
export const deleteResource = (id, requestOptions) =>
  request(() => adminApi.delete(`/api/admin/resources/${id}`), requestOptions);
export const getAdminReviewQueue = (requestOptions) => request(() => adminApi.get("/api/admin/review"), requestOptions);
export const getAdminSubmission = (id, requestOptions) =>
  request(() => adminApi.get(`/api/admin/submissions/${id}`), requestOptions);
export const verifySubmission = (id, comment, requestOptions) =>
  request(
    () => adminApi.put(`/api/admin/submissions/${id}/verify-proof`, null, { params: comment ? { comment } : {} }),
    requestOptions
  );
export const rejectSubmission = (id, comment, requestOptions) =>
  request(
    () => adminApi.put(`/api/admin/submissions/${id}/reject-proof`, null, { params: comment ? { comment } : {} }),
    requestOptions
  );
export const overrideScore = (id, new_score, comment, requestOptions) =>
  request(() => adminApi.put(`/api/admin/submissions/${id}/override`, { new_score, comment }), requestOptions);
export const getStudentsOverview = (requestOptions) =>
  request(() => adminApi.get("/api/admin/students/overview"), requestOptions);
export const getStudentActivity = (id, requestOptions) =>
  request(() => adminApi.get(`/api/admin/students/${id}/activity`), requestOptions);
export const createStudent = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/students", payload), requestOptions);
export const updateStudent = (id, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/students/${id}`, payload), requestOptions);
export const deleteStudent = (id, requestOptions) =>
  request(() => adminApi.delete(`/api/admin/students/${id}`), requestOptions);
export const bulkGenerateTickets = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/tickets/bulk-generate", payload), requestOptions);
export const bulkPublishTickets = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/tickets/bulk-publish", payload), requestOptions);
export const getAIUsageStats = (requestOptions) =>
  request(() => adminApi.get("/api/admin/ai-usage"), requestOptions);
export const getAdminLabTemplates = (requestOptions) =>
  request(() => adminApi.get("/api/admin/labs/templates"), requestOptions);
export const getAdminVmAssignments = (requestOptions) =>
  request(() => adminApi.get("/api/admin/vms/assignments"), requestOptions);
export const createAdminLabTemplate = (data, requestOptions) =>
  request(() => adminApi.post("/api/admin/labs/templates", data), requestOptions);
export const updateAdminLabTemplate = (id, data, requestOptions) =>
  request(() => adminApi.put(`/api/admin/labs/templates/${id}`, data), requestOptions);
export const deleteAdminLabTemplate = (id, requestOptions) =>
  request(() => adminApi.delete(`/api/admin/labs/templates/${id}`), requestOptions);
export const getAdminCapstoneTemplates = (requestOptions) =>
  request(() => adminApi.get("/api/admin/capstones/templates"), requestOptions);
export const createAdminCapstoneTemplate = (data, requestOptions) =>
  request(() => adminApi.post("/api/admin/capstones/templates", data), requestOptions);
export const updateAdminCapstoneTemplate = (id, data, requestOptions) =>
  request(() => adminApi.put(`/api/admin/capstones/templates/${id}`, data), requestOptions);
export const deleteAdminCapstoneTemplate = (id, requestOptions) =>
  request(() => adminApi.delete(`/api/admin/capstones/templates/${id}`), requestOptions);
export const recomputeWeeklyLeads = (requestOptions) =>
  request(() => adminApi.post("/api/admin/weekly-domain-leads/recompute"), requestOptions);
export const getWeeklyLeads = (requestOptions) =>
  request(() => adminApi.get("/api/admin/weekly-domain-leads"), requestOptions);
export const getRecentCVEs = (keyword = "windows", requestOptions) =>
  request(() => adminApi.get("/api/admin/cve/recent", { params: { keyword } }), requestOptions);
export const createTicketFromCVE = (cveId, requestOptions) =>
  request(() => adminApi.post("/api/admin/tickets/from-cve", null, { params: { cve_id: cveId } }), requestOptions);
export const getModules = (requestOptions) => request(() => adminApi.get("/api/admin/modules"), requestOptions);
export const createModule = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/modules", payload), requestOptions);
export const updateModule = (id, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/modules/${id}`, payload), requestOptions);
export const getLessons = (moduleId, requestOptions) =>
  request(() => adminApi.get("/api/admin/lessons", { params: { module_id: moduleId } }), requestOptions);
export const createLesson = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/lessons", payload), requestOptions);
export const updateLesson = (id, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/lessons/${id}`, payload), requestOptions);
export const getEvidence = (status, requestOptions) =>
  request(() => adminApi.get("/api/admin/evidence", { params: { status } }), requestOptions);
export const reviewEvidence = (id, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/evidence/${id}`, payload), requestOptions);
export const updateTicketAnswerKey = (ticketId, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/tickets/${ticketId}/answer-key`, payload), requestOptions);
export const getAdminCommands = (requestOptions) =>
  request(() => adminApi.get("/api/admin/commands"), requestOptions);
export const createAdminCommand = (payload, requestOptions) =>
  request(() => adminApi.post("/api/admin/commands", payload), requestOptions);
export const updateAdminCommand = (id, payload, requestOptions) =>
  request(() => adminApi.put(`/api/admin/commands/${id}`, payload), requestOptions);
export const deleteAdminCommand = (id, requestOptions) =>
  request(() => adminApi.delete(`/api/admin/commands/${id}`), requestOptions);
export const getAdminCurriculumVideos = (requestOptions) =>
  request(() => adminApi.get("/api/admin/curriculum/videos"), requestOptions);
export const updateAdminCurriculumVideoTag = (id, payload, requestOptions) =>
  request(() => adminApi.patch(`/api/admin/curriculum/videos/${id}`, payload), requestOptions);
export const authLogin = (data, requestOptions) =>
  requestData(() => api.post("/auth/login", data), { retries: 2, warmupOnRetry: true, ...requestOptions });
export const authMe = (requestOptions) =>
  request(() => api.get("/auth/me"), { retries: 1, warmupOnRetry: true, ...requestOptions });
export const authLogout = (requestOptions) => request(() => api.post("/auth/logout"), requestOptions);

export const getDueFlashcards = (requestOptions) => request(() => api.get("/api/flashcards/due"), requestOptions);
export const rateFlashcard = (cardId, rating, requestOptions) =>
  request(() => api.post(`/api/flashcards/${cardId}/rate`, { rating }), requestOptions);

export default api;
