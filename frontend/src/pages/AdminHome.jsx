import AdminDashboard from "../components/AdminDashboard";
import PageContainer from "../components/ui/PageContainer";

export default function AdminHome() {
  return (
    <PageContainer width="workspace">
      <h1 className="type-page-title mb-5">Admin Dashboard</h1>
      <AdminDashboard />
    </PageContainer>
  );
}
