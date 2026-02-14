import AdminDashboard from "../components/AdminDashboard";

export default function AdminHome() {
  return (
    <main className="mx-auto max-w-6xl p-6">
      <h1 className="mb-4 text-2xl font-bold text-slate-900 dark:text-slate-100">Admin Dashboard</h1>
      <AdminDashboard />
    </main>
  );
}
