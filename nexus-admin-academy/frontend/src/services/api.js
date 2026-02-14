import axios from "axios";
import toast from "react-hot-toast";

const adminKey = import.meta.env.VITE_ADMIN_KEY || "";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

const adminApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
  headers: {
    "X-ADMIN-KEY": adminKey,
  },
});

function unwrap(response) {
  const body = response?.data;
  if (body?.success === true) {
    return body;
  }
  return { success: true, data: body };
}

function handleError(error) {
  if (error.response) {
    const message = error.response.data?.error || error.response.data?.detail || "Request failed";
    toast.error(message);
  } else if (error.request) {
    toast.error("Unable to connect to server");
  } else {
    toast.error("Unexpected request error");
  }
  console.error("API Error:", error);
  throw error;
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
export const getLeaderboard = () => request(() => api.get("/api/leaderboard"));

export const getQuizzes = (weekNumber, studentId = 1) => request(() => api.get("/api/quizzes", { params: { week_number: weekNumber, student_id: studentId } }));
export const getQuiz = (quizId) => request(() => api.get(`/api/quizzes/${quizId}`));
export const submitQuiz = (quizId, payload) => request(() => api.post(`/api/quizzes/${quizId}/submit`, payload));

export const getTickets = (weekNumber, studentId = 1) => request(() => api.get("/api/tickets", { params: { week_number: weekNumber, student_id: studentId } }));
export const getTicket = (ticketId) => request(() => api.get(`/api/tickets/${ticketId}`));
export const submitTicket = (ticketId, payload) => request(() => api.post(`/api/tickets/${ticketId}/submit`, payload));

export const uploadScreenshots = (files) => {
  const formData = new FormData();
  files.forEach((file) => formData.append("files", file));
  return request(() => api.post("/api/tickets/uploads", formData, { headers: { "Content-Type": "multipart/form-data" } }));
};

export const getResources = (params) => request(() => api.get("/api/resources", { params }));

export const generateQuiz = (payload) => request(() => adminApi.post("/api/admin/quiz/generate", payload));
export const createTicket = (payload) => request(() => adminApi.post("/api/admin/tickets", payload));
export const getSubmissions = () => request(() => adminApi.get("/api/admin/submissions"));
export const getSubmissionDetail = (id) => request(() => adminApi.get(`/api/admin/submissions/${id}`));
export const overrideSubmission = (id, payload) => request(() => adminApi.put(`/api/admin/submissions/${id}/override`, payload));

export const createResource = (payload) => request(() => adminApi.post("/api/admin/resources", payload));
export const deleteResource = (id) => request(() => adminApi.delete(`/api/admin/resources/${id}`));
export const getReviewQueue = () => request(() => adminApi.get("/api/admin/review"));
export const getStudentsOverview = () => request(() => adminApi.get("/api/admin/students/overview"));
export const getStudentActivity = (id) => request(() => adminApi.get(`/api/admin/students/${id}/activity`));
export const bulkGenerateTickets = (payload) => request(() => adminApi.post("/api/admin/tickets/bulk-generate", payload));
export const bulkPublishTickets = (payload) => request(() => adminApi.post("/api/admin/tickets/bulk-publish", payload));

export default api;
