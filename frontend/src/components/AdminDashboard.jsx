import { useState } from "react";
import toast from "react-hot-toast";
import CohortPanel from "./CohortPanel";
import { createResource, generateQuiz } from "../services/api";

export default function AdminDashboard() {
  const [quizForm, setQuizForm] = useState({ source_url: "", week_number: 1, title: "", domain_id: "1.0" });
  const [resourceForm, setResourceForm] = useState({ title: "", url: "", resource_type: "Video", week_number: 1, category: "" });

  return (
    <div className="space-y-4">
      <CohortPanel />

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Generate Quiz</h2>
          <input className="input-field" placeholder="Source URL" value={quizForm.source_url} onChange={(e) => setQuizForm({ ...quizForm, source_url: e.target.value })} />
          <input className="input-field" placeholder="Title" value={quizForm.title} onChange={(e) => setQuizForm({ ...quizForm, title: e.target.value })} />
          <div className="grid grid-cols-2 gap-2">
            <input className="input-field" type="number" value={quizForm.week_number} onChange={(e) => setQuizForm({ ...quizForm, week_number: Number(e.target.value || 1) })} />
            <select className="input-field" value={quizForm.domain_id} onChange={(e) => setQuizForm({ ...quizForm, domain_id: e.target.value })}>
              <option value="1.0">1.0 Hardware</option>
              <option value="2.0">2.0 Networking</option>
              <option value="3.0">3.0 Software Troubleshooting</option>
              <option value="4.0">4.0 Security / Procedures</option>
            </select>
          </div>
          <button className="btn-primary" onClick={async () => {
            const t = toast.loading("Generating quiz...");
            try {
              await generateQuiz(quizForm);
              toast.success("Quiz created successfully");
            } finally {
              toast.dismiss(t);
            }
          }}>
            Generate Quiz
          </button>
        </article>

      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        <article className="panel space-y-2 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-xl font-semibold">Add Resource</h2>
          <input className="input-field" placeholder="Title" value={resourceForm.title} onChange={(e) => setResourceForm({ ...resourceForm, title: e.target.value })} />
          <input className="input-field" placeholder="URL" value={resourceForm.url} onChange={(e) => setResourceForm({ ...resourceForm, url: e.target.value })} />
          <div className="grid grid-cols-3 gap-2">
            <select className="input-field" value={resourceForm.resource_type} onChange={(e) => setResourceForm({ ...resourceForm, resource_type: e.target.value })}>
              <option>Video</option><option>Article</option><option>Study Guide</option><option>Other</option>
            </select>
            <input className="input-field" type="number" value={resourceForm.week_number} onChange={(e) => setResourceForm({ ...resourceForm, week_number: Number(e.target.value || 1) })} />
            <input className="input-field" placeholder="Category" value={resourceForm.category} onChange={(e) => setResourceForm({ ...resourceForm, category: e.target.value })} />
          </div>
          <button className="btn-primary" onClick={async () => { await createResource(resourceForm); toast.success("Resource created"); }}>
            Save Resource
          </button>
        </article>

      </section>
    </div>
  );
}
