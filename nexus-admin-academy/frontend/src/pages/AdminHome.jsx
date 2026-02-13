import AdminDashboard from "../components/AdminDashboard";

export default function AdminHome() {
  return (
    <main className="mx-auto max-w-7xl space-y-4 p-6">
      <section className="rounded-lg bg-gradient-to-r from-slate-900 to-slate-800 p-6 text-white shadow-md">
        <h1 className="text-3xl font-bold">Admin Control Center</h1>
        <p className="mt-2 text-sm text-slate-200">Create weekly content, review graded work, and keep learner progress on track.</p>
      </section>
      <AdminDashboard />
    </main>
  );
}
