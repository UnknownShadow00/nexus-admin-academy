import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

export const getDashboard = (studentId) => api.get(`/api/students/${studentId}/dashboard`);
export const getLeaderboard = () => api.get("/api/leaderboard");
export const getQuizzes = (weekNumber) => api.get("/api/quizzes", { params: { week_number: weekNumber } });
export const getQuiz = (quizId) => api.get(`/api/quizzes/${quizId}`);
export const submitQuiz = (quizId, payload) => api.post(`/api/quizzes/${quizId}/submit`, payload);
export const getTickets = (weekNumber) => api.get("/api/tickets", { params: { week_number: weekNumber } });
export const getTicket = (ticketId) => api.get(`/api/tickets/${ticketId}`);
export const submitTicket = (ticketId, payload) => api.post(`/api/tickets/${ticketId}/submit`, payload);

export const generateQuiz = (payload) => api.post("/api/admin/quiz/generate", payload);
export const createTicket = (payload) => api.post("/api/admin/tickets", payload);
export const getSubmissions = () => api.get("/api/admin/submissions");
export const getSubmissionDetail = (id) => api.get(`/api/admin/submissions/${id}`);
export const overrideSubmission = (id, payload) => api.put(`/api/admin/submissions/${id}/override`, payload);

export default api;
