import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import BackLink from "../BackLink";
import Banner from "../ui/Banner";
import PageContainer from "../ui/PageContainer";
import PageHeader from "../ui/PageHeader";
import PrerequisiteLock from "../PrerequisiteLock";
import V2NextStep from "../v2/V2NextStep";
import V2Status from "../v2/V2Status";

const sections = [
  ["brief", "Brief"], ["task", "Do the task"], ["evidence", "Capture evidence"],
  ["support-note", "Support note"], ["review", "Review & send"],
];

const evidenceLabels = {
  file_path: "File and path",
  windows_observation: "Windows/application observation",
};
const provisioningStatuses = new Set(["provisioning", "starting", "waiting_for_ip", "configuring_connection"]);

export default function Stage4PracticalWorkspace({
  lab, moduleKey, fields, guidedNote, fieldErrors, onFieldChange, onStart, onSubmit,
  busy, evidenceFile, onEvidenceFileChange, evidenceKind, onEvidenceKindChange,
  evidenceArtifacts, evidenceMessage, evidenceError, evidenceBusy, evidenceInputKey,
  onEvidenceUpload, canUploadEvidence, prerequisiteLock, error, vmAssignment, guacUrl,
}) {
  const waitingReview = lab.review?.status === "awaiting_mentor_review";
  const needsCorrection = lab.review?.status === "needs_correction";
  const approved = lab.review?.status === "passed" && lab.status === "submitted";
  const readOnly = Boolean(prerequisiteLock) || busy || waitingReview || approved;
  const hasFile = evidenceArtifacts.some((item) => item.artifact_type === "file_path");
  const hasObservation = evidenceArtifacts.some((item) => item.artifact_type === "windows_observation");
  const missingFields = fields.filter(([key]) => !guidedNote[key]?.trim());
  const ready = hasFile && hasObservation && missingFields.length === 0;
  const practiceFileUrl = lab.success_criteria?.practice_file_url;
  const [selectedPreview, setSelectedPreview] = useState(null);
  const [activeSection, setActiveSection] = useState("brief");

  useEffect(() => {
    if (typeof IntersectionObserver !== "function") return undefined;
    const observer = new IntersectionObserver((entries) => {
      const current = entries.find((entry) => entry.isIntersecting);
      if (current) setActiveSection(current.target.id.replace("practical-", ""));
    }, { rootMargin: "-15% 0px -65% 0px" });
    sections.forEach(([id]) => { const section = document.getElementById(`practical-${id}`); if (section) observer.observe(section); });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!evidenceFile || !evidenceFile.type.startsWith("image/") || typeof URL.createObjectURL !== "function") {
      setSelectedPreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(evidenceFile);
    setSelectedPreview({ file: evidenceFile, url });
    return () => URL.revokeObjectURL?.(url);
  }, [evidenceFile]);

  const sectionClass = "practical-section";
  return <PageContainer width="standard" className="practical-page">
    <BackLink fallbackLabel="Back to Stage 4" fallbackTo={`/learning-v2/modules/${moduleKey}`} />
    <PageHeader
      eyebrow="Guided practical"
      title={lab.title}
      description="Observe the issue, capture evidence, and record a technician support note."
      status={<V2Status status={waitingReview ? "awaiting_mentor_review" : needsCorrection ? "needs_correction" : approved ? "approved" : lab.run_id ? "in_progress" : "not_started"} />}
    />
    <PrerequisiteLock lock={prerequisiteLock} />
    {needsCorrection ? <section className="practical-follow-up practical-follow-up-correction" role="status" aria-labelledby="practical-mentor-title">
      <h2 id="practical-mentor-title">Changes requested</h2>
      <p>Your mentor left feedback on this practical. Your course remains available while you update it.</p>
      {lab.review.feedback ? <p className="practical-feedback"><strong>Mentor feedback</strong><br />{lab.review.feedback}</p> : null}
      <a className="btn-secondary" href="#practical-support-note">Update your practical</a>
    </section> : null}
    {waitingReview ? <section className="practical-follow-up practical-follow-up-mentor" role="status" aria-labelledby="practical-mentor-title">
      <h2 id="practical-mentor-title">With your mentor</h2>
      <V2NextStep moduleKey={moduleKey} pendingReview />
      <p className="practical-readonly-hint">Your submitted evidence and note are below for reference. Editing resumes if your mentor requests changes.</p>
    </section> : null}
    {approved ? <section className="practical-follow-up practical-follow-up-approved" role="status" aria-labelledby="practical-mentor-title">
      <h2 id="practical-mentor-title">Approved</h2>
      <p>Your mentor approved this practical. Your stage is mastered only when the remaining requirements are complete.</p>
      <V2NextStep moduleKey={moduleKey} />
    </section> : null}
    {error ? <Banner variant="error">{error}</Banner> : null}
    {provisioningStatuses.has(vmAssignment?.status) ? <Banner variant="info">Preparing the lab environment: {vmAssignment.status.replaceAll("_", " ")}…</Banner> : null}
    {vmAssignment?.status === "failed" ? <Banner variant="error">{vmAssignment.provisioning_error || "Lab environment provisioning failed."}</Banner> : null}
    {guacUrl ? <div className="practical-section"><h2>Lab environment</h2><a href={guacUrl} rel="noopener noreferrer" target="_blank">Open in new tab</a><iframe allowFullScreen className="mt-3 h-[60vh] w-full rounded-lg border" src={guacUrl} title="Lab VM" /></div> : null}

    <div className="practical-layout">
      <nav className="practical-rail" aria-label="Practical sections"><p className="type-label">WORKSPACE</p><ol>{sections.map(([id, label], index) => <li key={id}><a href={`#practical-${id}`} aria-current={activeSection === id ? "location" : undefined} onClick={() => setActiveSection(id)}><span aria-hidden="true">{index + 1}</span>{label}</a></li>)}</ol></nav>
      <div className="practical-content">
        <section id="practical-brief" className={sectionClass} aria-labelledby="practical-brief-title">
          <p className="type-label">01 / CONTEXT</p><h2 id="practical-brief-title">Brief</h2>
          <p>{lab.description}</p>
          <div className="practical-inset"><h3>Work boundary</h3><p>{lab.setup_instructions}</p></div>
          {!lab.run_id && !prerequisiteLock ? <button className="btn-primary" onClick={onStart} disabled={busy} type="button">{busy ? "Starting…" : "Start practical"}</button> : null}
        </section>

        <section id="practical-task" className={sectionClass} aria-labelledby="practical-task-title">
          <p className="type-label">02 / WORK</p><h2 id="practical-task-title">Do the task</h2>
          <p>Use the approved Windows computer and record only what you actually observe.</p>
          {Array.isArray(lab.success_criteria?.tasks) && lab.success_criteria.tasks.length ? <ol className="practical-task-list">{lab.success_criteria.tasks.map((task) => <li key={task}>{task}</li>)}</ol> : null}
          {typeof practiceFileUrl === "string" && practiceFileUrl.startsWith("/v2-interactions/") ? <a className="btn-secondary" href={practiceFileUrl} download={lab.success_criteria?.practice_file_name || undefined}>Download practice file</a> : null}
        </section>

        <section id="practical-evidence" className={sectionClass} aria-labelledby="practical-evidence-title">
          <p className="type-label">03 / PROOF</p><h2 id="practical-evidence-title">Capture evidence</h2>
          <p>Upload a redacted screenshot of the file and path, then one of the Windows or application view you checked.</p>
          <Banner variant="info">Before uploading, cover passwords, MFA codes, keys, full account names, personal details, and unrelated private content.</Banner>
          <div className="practical-evidence-slots" aria-label="Required screenshots">
            <div><strong>File and path</strong><span>{hasFile ? "Uploaded" : "Needed"}</span></div>
            <div><strong>Windows/application observation</strong><span>{hasObservation ? "Uploaded" : "Needed"}</span></div>
          </div>
          {canUploadEvidence && !prerequisiteLock ? <div className="practical-upload">
            <label htmlFor="stage4-evidence-kind">Evidence shown in this screenshot</label>
            <select id="stage4-evidence-kind" className="input-field" value={evidenceKind} onChange={(event) => onEvidenceKindChange(event.target.value)}><option value="file_path">File and path</option><option value="windows_observation">Windows/application observation</option></select>
            <label htmlFor="stage4-evidence-file">Choose a screenshot</label>
            <input key={evidenceInputKey} id="stage4-evidence-file" accept="image/jpeg,image/png,image/webp" className="input-field" onChange={(event) => onEvidenceFileChange(event.target.files?.[0] || null)} type="file" />
            <p className="practical-helper">Choose a JPEG, PNG, or WebP screenshot.</p>
            {selectedPreview?.file === evidenceFile ? <figure className="practical-selected-preview"><img src={selectedPreview.url} alt={`Selected screenshot: ${evidenceFile.name}`} /><figcaption>Selected file preview · {evidenceFile.name} · <a href={selectedPreview.url} rel="noopener noreferrer" target="_blank">Open full size</a></figcaption></figure> : null}
            {evidenceFile ? <button className="btn-quiet" onClick={() => onEvidenceFileChange(null, true)} type="button">Clear selected file</button> : null}
            <button className="btn-secondary" disabled={!evidenceFile || evidenceBusy} onClick={onEvidenceUpload} type="button">{evidenceBusy ? "Uploading…" : "Upload screenshot"}</button>
          </div> : !lab.run_id ? <p className="practical-helper">Start the practical to upload evidence.</p> : null}
          {evidenceMessage ? <Banner variant={evidenceError ? "error" : "success"}>{evidenceMessage}</Banner> : null}
          <h3>Uploaded screenshots</h3>
          {evidenceArtifacts.length ? <ul className="practical-artifacts">{evidenceArtifacts.map((item) => <li key={item.artifact_id || item.id || item.storage_key}><span aria-hidden="true">▧</span><span><strong>{evidenceLabels[item.artifact_type] || "Screenshot"}</strong><small>{item.original_filename || "Uploaded screenshot"}</small></span></li>)}</ul> : <p className="practical-empty">No screenshots uploaded yet.</p>}
          <p className="practical-helper">Check each screenshot before uploading. To replace one already uploaded, ask your mentor how to proceed.</p>
        </section>

        <section id="practical-support-note" className={sectionClass} aria-labelledby="practical-note-title">
          <p className="type-label">04 / TECHNICIAN RECORD</p><h2 id="practical-note-title">Write a support note</h2>
          <p>Keep each field brief and factual. Separate what was reported from what you checked and verified.</p>
          <div className="practical-note-fields">{fields.map(([key, label, hint], index) => <div key={key} className="practical-field"><div className="practical-field-heading"><span aria-hidden="true">{index + 1}</span><label htmlFor={`practical-${key}`}>{label}</label></div><p id={`practical-${key}-hint`} className="practical-helper">{hint}</p><textarea id={`practical-${key}`} className="input-field" aria-invalid={Boolean(fieldErrors[key])} aria-describedby={`practical-${key}-hint${fieldErrors[key] ? ` practical-${key}-error` : ""}`} value={guidedNote[key] || ""} readOnly={readOnly} onChange={(event) => onFieldChange(key, event.target.value)} />{fieldErrors[key] ? <p id={`practical-${key}-error`} className="practical-field-error" role="alert">{fieldErrors[key]}</p> : null}</div>)}</div>
          {!waitingReview && !approved && !prerequisiteLock ? <p className="practical-helper">Draft note text is kept in this browser until you send it. Uploaded evidence is saved separately.</p> : null}
        </section>

        <section id="practical-review" className={sectionClass} aria-labelledby="practical-review-title">
          <p className="type-label">05 / HANDOFF</p><h2 id="practical-review-title">Review & send</h2>
          <p>Check that the screenshots and note describe the work you actually did.</p>
          <div className="practical-review-summary">
            <div><strong>Evidence</strong><span>{hasFile && hasObservation ? "Both screenshot types uploaded" : "Screenshots still needed"}</span></div>
            <div><strong>Support note</strong><span>{missingFields.length ? `${missingFields.length} field${missingFields.length === 1 ? "" : "s"} still empty` : "Five fields ready"}</span></div>
          </div>
          {missingFields.length && !waitingReview && !approved ? <p className="practical-helper">Complete: {missingFields.map(([, label]) => label).join(", ")}.</p> : null}
          {waitingReview ? <p className="practical-readonly-hint">With your mentor · This submission is read-only during review.</p> : approved ? <p className="practical-readonly-hint">Approved practical · Stage mastery is shown separately in My Course.</p> : <button className="btn-primary practical-send" disabled={busy || Boolean(prerequisiteLock) || !lab.run_id} onClick={onSubmit} type="button">{busy ? "Sending…" : needsCorrection ? "Resubmit to mentor" : "Send to mentor"}</button>}
          {!ready && !waitingReview && !approved ? <p className="practical-helper">You can review your work now. Missing items will be checked before submission.</p> : null}
          <Link className="btn-quiet" to={`/learning-v2/modules/${moduleKey}`}>Back to Stage 4</Link>
        </section>
      </div>
    </div>
  </PageContainer>;
}
