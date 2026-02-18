import axios from "axios";
import toast from "react-hot-toast";
import { getSelectedProfile } from "./profile";

const adminKey = (import.meta.env.VITE_ADMIN_KEY || "").trim();

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

const adminApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

adminApi.interceptors.request.use((config) => {
  const key = (adminKey || localStorage.getItem("admin_key") || "").trim();
  config.headers = config.headers || {};
  config.headers["X-Admin-Key"] = key;
  config.headers["X-ADMIN-KEY"] = key;
  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

function unwrap(response) {
  const body = response?.data;
  if (body?.success === true) {
    return body;
  }
  return { success: true, data: body };
}

function handleError(error) {
  if (error.response) {
    const detail = error.response.data?.detail;
    const message = error.response.data?.error || (typeof detail === "string" ? detail : detail?.error) || "Request failed";
    toast.error(message);
  } else if (error.request) {
    toast.error("Unable to connect to server");
  } else {
    toast.error("Unexpected request error");
  }
  throw error;
}

function currentStudentId(defaultId = 1) {
  return getSelectedProfile()?.id || defaultId;
}

async function request(clientCall) {
  try {
    const response = await clientCall();
    return unwrap(response);
  } catch (error) {
    return handleError(error);
  }
}

export const getDashboard = (studentId) => request(() => api.get(`/api/students/${studentId}/dashboard`));
export const getStudentStats = (studentId) => request(() => api.get(`/api/students/${studentId}/stats`));
export const checkInStudent = (studentId) => request(() => api.post(`/api/students/${studentId}/check-in`));
export const getCertReadiness = (studentId) => request(() => api.get(`/api/students/${studentId}/certification-readiness`));
export const getLeaderboard = () => request(() => api.get("/api/leaderboard"));
export const getStudents = () => request(() => api.get("/api/students"));
export const getStudentMastery = (studentId) => request(() => api.get(`/api/students/${studentId}/mastery`));
export const getSquadDashboard = (studentId) => request(() => api.get("/api/squad/dashboard", { params: { student_id: studentId } }));
export const getLearningPath = (studentId) => request(() => api.get(`/api/students/${studentId}/learning-path`));
export const getPromotionStatus = (studentId) => request(() => api.get(`/api/students/${studentId}/promotion-status`));

export const getQuizzes = (weekNumber, studentId = currentStudentId()) => request(() => api.get("/api/quizzes", { params: { week_number: weekNumber, student_id: studentId } }));
export const getQuiz = (quizId) => request(() => api.get(`/api/quizzes/${quizId}`));
export const submitQuiz = (quizId, payload) => request(() => api.post(`/api/quizzes/${quizId}/submit`, payload));

export const getTickets = (weekNumber, studentId = currentStudentId()) => request(() => api.get("/api/tickets", { params: { week_number: weekNumber, student_id: studentId } }));
export const getTicket = (ticketId) => request(() => api.get(`/api/tickets/${ticketId}`));
export const submitTicket = (ticketId, payload) => request(() => api.post(`/api/tickets/${ticketId}/submit`, payload));
export const getSubmission = (submissionId) => request(() => api.get(`/api/submissions/${submissionId}`));

export const uploadScreenshots = (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request(() => api.post("/api/tickets/uploads", formData, { headers: { "Content-Type": "multipart/form-data" } }));
};
export const uploadEvidence = ({ file, ticketId, artifactType }) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("ticket_id", String(ticketId));
  formData.append("artifact_type", artifactType);
  return request(() => api.post("/api/evidence/upload", formData, { headers: { "Content-Type": "multipart/form-data" } }));
};

export const getResources = (params) => request(() => api.get("/api/resources", { params }));
export const searchCommands = (q) => request(() => api.get("/api/commands/search", { params: { q } }));

export const generateQuiz = (payload) => request(() => adminApi.post("/api/admin/quiz/generate", payload));
export const createTicket = (payload) => request(() => adminApi.post("/api/admin/tickets", payload));
export const getSubmissions = () => request(() => adminApi.get("/api/admin/submissions"));
export const getSubmissionDetail = (id) => request(() => adminApi.get(`/api/admin/submissions/${id}`));
export const overrideSubmission = (id, payload) => request(() => adminApi.put(`/api/admin/submissions/${id}/override`, payload));
export const verifyProof = (id, comment = "") => request(() => adminApi.put(`/api/admin/submissions/${id}/verify-proof`, null, { params: { comment } }));
export const rejectProof = (id, comment = "") => request(() => adminApi.put(`/api/admin/submissions/${id}/reject-proof`, null, { params: { comment } }));

export const createResource = (payload) => request(() => adminApi.post("/api/admin/resources", payload));
export const deleteResource = (id) => request(() => adminApi.delete(`/api/admin/resources/${id}`));
export const getReviewQueue = () => request(() => adminApi.get("/api/admin/review"));
export const getStudentsOverview = () => request(() => adminApi.get("/api/admin/students/overview"));
export const getStudentActivity = (id) => request(() => adminApi.get(`/api/admin/students/${id}/activity`));
export const bulkGenerateTickets = (payload) => request(() => adminApi.post("/api/admin/tickets/bulk-generate", payload));
export const bulkPublishTickets = (payload) => request(() => adminApi.post("/api/admin/tickets/bulk-publish", payload));
export const getAIUsageStats = () => request(() => adminApi.get("/api/admin/ai-usage"));
export const recomputeWeeklyLeads = () => request(() => adminApi.post("/api/admin/weekly-domain-leads/recompute"));
export const getWeeklyLeads = () => request(() => adminApi.get("/api/admin/weekly-domain-leads"));
export const getRecentCVEs = (keyword = "windows") => request(() => adminApi.get("/api/admin/cve/recent", { params: { keyword } }));
export const createTicketFromCVE = (cveId) => request(() => adminApi.post("/api/admin/tickets/from-cve", null, { params: { cve_id: cveId } }));
export const getModules = () => request(() => adminApi.get("/api/admin/modules"));
export const createModule = (payload) => request(() => adminApi.post("/api/admin/modules", payload));
export const updateModule = (id, payload) => request(() => adminApi.put(`/api/admin/modules/${id}`, payload));
export const getLessons = (moduleId) => request(() => adminApi.get("/api/admin/lessons", { params: { module_id: moduleId } }));
export const createLesson = (payload) => request(() => adminApi.post("/api/admin/lessons", payload));
export const getEvidence = (status) => request(() => adminApi.get("/api/admin/evidence", { params: { status } }));
export const reviewEvidence = (id, payload) => request(() => adminApi.put(`/api/admin/evidence/${id}`, payload));
export const updateTicketAnswerKey = (ticketId, payload) => request(() => adminApi.put(`/api/admin/tickets/${ticketId}/answer-key`, payload));

export default api;
