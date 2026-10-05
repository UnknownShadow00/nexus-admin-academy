import { useEffect, useRef, useState } from "react";
import { StatusBadge } from "../../components/ui/Badge";
import { buildApiUrl, getAdminV2PracticalReviews, reviewAdminV2Practical } from "../../services/api";

const noteLabels = ["Reported", "Checked", "Found", "Verified / Not verified", "Next step"];

export function parseSupportNote(notes) {
  if (!notes) return null;
  const matches = [...notes.matchAll(/^(Reported|Checked|Found|Verified \/ Not verified|Next step):\s*/gm)];
  if (matches.length !== noteLabels.length || matches.some((match, index) => match[1] !== noteLabels[index])) return null;
  return matches.map((match, index) => ({
    label: match[1],
    value: notes.slice(match.index + match[0].length, matches[index + 1]?.index ?? notes.length).trim(),
  }));
}

function EvidencePreview({ artifact }) {
  const dialog = useRef(null);
  const opener = useRef(null);
  const [imageError, setImageError] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const url = buildApiUrl(artifact.file_url);
  const image = /^image\/(png|jpeg|webp)$/i.test(artifact.mime_type || "") && !imageError;
  const name = artifact.original_filename || `Evidence ${artifact.id}`;
  const close = () => dialog.current?.close();
  useEffect(() => {
    if (!image) return undefined;
    const modal = dialog.current;
    const onClose = () => { setPreviewOpen(false); document.body.style.overflow = ""; opener.current?.focus(); };
    modal?.addEventListener("close", onClose);
    return () => { modal?.removeEventListener("close", onClose); document.body.style.overflow = ""; };
  }, [image]);
  const open = () => { setPreviewOpen(true); dialog.current?.showModal(); document.body.style.overflow = "hidden"; };

  return (
    <li className="mentor-evidence-item">
      {image ? (
        <button ref={opener} type="button" className="mentor-evidence-preview" onClick={open} aria-label={`Preview ${name}`}>
          <img src={url} alt="" loading="lazy" decoding="async" onError={() => setImageError(true)} />
        </button>
      ) : <span className="mentor-evidence-file" aria-hidden="true">{imageError ? "NO PREVIEW" : "FILE"}</span>}
      <div className="mentor-evidence-meta">
        <strong>{name}</strong>
        <small>{artifact.artifact_type || artifact.mime_type || "Evidence"}{artifact.file_size_bytes != null ? ` · ${Math.ceil(artifact.file_size_bytes / 1024)} KB` : ""}</small>
        <a href={url} rel="noreferrer" target="_blank">Open file</a>
      </div>
      {image ? (
        <dialog ref={dialog} className="mentor-evidence-dialog" aria-label={`Preview ${name}`} onClick={(event) => { if (event.target === dialog.current) close(); }}>
          <div>
            <div className="mentor-evidence-dialog-header"><strong>{name}</strong><button className="btn-secondary" type="button" onClick={close}>Close preview</button></div>
            {previewOpen ? <img src={url} alt={`Evidence: ${name}`} /> : null}
          </div>
        </dialog>
      ) : null}
    </li>
  );
}

export default function MentorPracticalReview() {
  const [reviews, setReviews] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [decisionError, setDecisionError] = useState("");
  const [result, setResult] = useState(null);
  const [feedbackById, setFeedbackById] = useState({});
  const [rubricById, setRubricById] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [confirmDecision, setConfirmDecision] = useState(null);
  const confirmButton = useRef(null);
  const approveButton = useRef(null);
  const changesButton = useRef(null);

  const load = async ({ initial = false } = {}) => {
    if (initial) setLoading(true);
    setLoadError("");
    try {
      const { data } = await getAdminV2PracticalReviews({ suppressToast: true });
      const next = data || [];
      setReviews(next);
      setSelectedId((current) => next.some((item) => item.lab_run_id === current) ? current : initial ? next[0]?.lab_run_id ?? null : null);
    } catch (error) {
      setReviews([]);
      setSelectedId(null);
      setLoadError(error?.userMessage || "Pending reviews could not be loaded. Try again.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load({ initial: true }); }, []);
  useEffect(() => { if (confirmDecision) confirmButton.current?.focus(); }, [confirmDecision]);
  const selected = reviews.find((item) => item.lab_run_id === selectedId);
  const rubric = Object.entries(selected?.mentor_rubric || {});
  const checks = rubricById[selectedId] || {};
  const feedback = feedbackById[selectedId] || "";
  const canApprove = rubric.every(([key]) => checks[key]);
  const note = parseSupportNote(selected?.notes);

  const submit = async () => {
    if (!selected || !confirmDecision || submitting) return;
    const trimmed = feedback.trim();
    if (!trimmed) { setDecisionError("Write mentor feedback before making a decision."); setConfirmDecision(null); return; }
    const decision = confirmDecision;
    if (decision === "approve" && !canApprove) { setDecisionError("Confirm each rubric criterion before approving."); setConfirmDecision(null); return; }
    setSubmitting(true);
    setDecisionError("");
    try {
      await reviewAdminV2Practical(selected.lab_run_id, { decision, feedback: trimmed, rubric_results: checks });
      setResult({ decision, message: `${decision === "approve" ? "Approved" : "Changes requested for"} ${selected.student_name}’s ${selected.lab_title}. The learner will see your feedback.` });
      setFeedbackById((current) => { const next = { ...current }; delete next[selected.lab_run_id]; return next; });
      setRubricById((current) => { const next = { ...current }; delete next[selected.lab_run_id]; return next; });
      setSelectedId(null);
      await load();
      window.dispatchEvent(new Event("v2-practical-reviews-changed"));
    } catch (error) {
      setDecisionError(error?.userMessage || "The decision could not be saved. Your feedback is still here. Try again.");
      if (error?.response?.status === 409) setDecisionError("This submission changed during review. Your feedback is still here. Refresh the queue before deciding again.");
    } finally {
      setConfirmDecision(null);
      setSubmitting(false);
    }
  };

  return (
    <section id="pending-reviews" className="mentor-review scroll-mt-24" aria-labelledby="mentor-review-heading">
      <div className="mentor-review-heading">
        <div>
          <p className="mentor-review-eyebrow">Mentor workspace</p>
          <h2 id="mentor-review-heading">Pending practical reviews</h2>
          <p>Review the learner’s evidence and support note before deciding.</p>
        </div>
        <button className="btn-secondary" type="button" onClick={() => load({ initial: true })} disabled={loading || submitting}>Refresh queue</button>
      </div>
      {result ? <p className={`notice ${result.decision === "approve" ? "notice-success" : "notice-correction"}`} role="status">{result.message}</p> : null}
      {loadError ? <div className="notice notice-error" role="alert">{loadError}</div> : null}
      {loading ? <p className="mentor-review-empty" role="status">Loading pending reviews…</p> : loadError && !reviews.length ? null : !reviews.length ? (
        <p className="mentor-review-empty">No practicals are waiting for review.</p>
      ) : (
        <div className="mentor-review-grid">
          <nav className="mentor-review-queue" aria-label="Pending practical submissions">
            <div className="mentor-review-section-head"><h3>Queue</h3><span>{reviews.length} waiting</span></div>
            <ol>{reviews.map((item) => (
              <li key={item.lab_run_id}>
                <button type="button" className="mentor-review-queue-row" aria-current={selectedId === item.lab_run_id ? "true" : undefined} onClick={() => {
                  setSelectedId(item.lab_run_id);
                  setDecisionError("");
                  setResult(null);
                  setConfirmDecision(null);
                }}>
                  <strong>{item.student_name}</strong>
                  <span>{item.stage_title || item.module_key} · {item.lab_title}</span>
                  <small>{item.submitted_at ? `Submitted ${new Date(item.submitted_at).toLocaleString()}` : "Submitted for review"}</small>
                </button>
              </li>
            ))}</ol>
          </nav>
          {selected ? <>
            <article className="mentor-review-submission" aria-labelledby="mentor-submission-heading">
              <div className="mentor-review-section-head"><span>Submission</span><StatusBadge status="awaiting_mentor_review" label="Pending review" /></div>
              <h3 id="mentor-submission-heading">{selected.lab_title}</h3>
              <p className="mentor-review-context">{selected.student_name} · {selected.stage_title || selected.module_key}</p>
              {selected.submitted_at ? <p className="mentor-review-meta">Submitted {new Date(selected.submitted_at).toLocaleString()}</p> : null}
              <section>
                <h4>Evidence</h4>
                {selected.artifacts?.length ? (
                  <ul className="mentor-evidence-list">{selected.artifacts.map((artifact) => <EvidencePreview artifact={artifact} key={artifact.id} />)}</ul>
                ) : <p className="mentor-review-empty-inline">No uploaded evidence appears with this submission.</p>}
              </section>
              <section>
                <h4>Learner support note</h4>
                {note ? <dl className="mentor-note">{note.map(({ label, value }) => <div key={label}><dt>{label}</dt><dd>{value || "—"}</dd></div>)}</dl> : (
                  <p className="mentor-note-raw">{selected.notes || "No support note supplied."}</p>
                )}
              </section>
            </article>
            <aside className="mentor-review-decision" aria-labelledby="mentor-decision-heading">
              <div className="mentor-review-decision-inner">
                <p className="mentor-review-eyebrow">Mentor evaluation</p>
                <h3 id="mentor-decision-heading">Decision</h3>
                <fieldset>
                  <legend>Rubric</legend>
                  {rubric.length ? rubric.map(([key, description]) => (
                    <label className="mentor-rubric-row" key={key}>
                      <input type="checkbox" checked={Boolean(checks[key])} onChange={(event) => setRubricById((current) => ({
                        ...current, [selectedId]: { ...current[selectedId], [key]: event.target.checked },
                      }))} />
                      <span><strong>{key.replaceAll("_", " ")}</strong><small>{description}</small></span>
                    </label>
                  )) : <p className="mentor-review-meta">No rubric criteria were provided for this practical.</p>}
                </fieldset>
                <label className="mentor-feedback-label" htmlFor="mentor-feedback">Mentor feedback</label>
                <textarea id="mentor-feedback" className="input-field" maxLength={4000} value={feedback} onChange={(event) => setFeedbackById((current) => ({
                  ...current, [selectedId]: event.target.value,
                }))} aria-describedby="mentor-feedback-help" />
                <p id="mentor-feedback-help" className="mentor-review-meta">The learner will see this after your decision. Required for both actions.</p>
                {decisionError ? <p className="notice notice-error" role="alert">{decisionError}</p> : null}
                {confirmDecision ? (
                  <div className="mentor-review-confirm" role="group" aria-label="Confirm decision">
                    <p>{confirmDecision === "approve" ? `Approve ${selected.student_name}’s practical?` : `Request changes to ${selected.student_name}’s practical?`}</p>
                    <p className="mentor-review-meta">Your feedback will be sent to the learner.</p>
                    <div>
                      <button ref={confirmButton} className={confirmDecision === "approve" ? "btn-primary" : "btn-secondary mentor-request-button"} type="button" disabled={submitting || (confirmDecision === "approve" && !canApprove)} onClick={submit}>{submitting ? "Saving decision…" : "Confirm decision"}</button>
                      <button className="btn-quiet" type="button" disabled={submitting} onClick={() => {
                        const previous = confirmDecision;
                        setConfirmDecision(null);
                        requestAnimationFrame(() => (previous === "approve" ? approveButton : changesButton).current?.focus());
                      }}>Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="mentor-review-actions">
                    <button ref={approveButton} className="btn-primary" type="button" disabled={submitting || !canApprove} onClick={() => {
                      setDecisionError("");
                      feedback.trim() ? setConfirmDecision("approve") : setDecisionError("Write mentor feedback before approving.");
                    }}>Approve practical</button>
                    <button ref={changesButton} className="btn-secondary mentor-request-button" type="button" disabled={submitting} onClick={() => {
                      setDecisionError("");
                      feedback.trim() ? setConfirmDecision("reject") : setDecisionError("Write mentor feedback before requesting changes.");
                    }}>Request changes</button>
                  </div>
                )}
                {!canApprove ? <p className="mentor-review-meta">Confirm each rubric criterion to approve. You may request changes without checking every criterion.</p> : null}
              </div>
            </aside>
          </> : <p className="mentor-review-empty">Select a submission to review.</p>}
        </div>
      )}
    </section>
  );
}
