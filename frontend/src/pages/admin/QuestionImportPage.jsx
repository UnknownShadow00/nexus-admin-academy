import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Download, Upload } from "lucide-react";
import {
  confirmQuestionImport,
  downloadQuestionImportErrorReport,
  downloadQuestionImportTemplate,
  previewQuestionImport,
} from "../../services/api";
import PageHeader from "../../components/ui/PageHeader";

function triggerDownload(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export default function QuestionImportPage() {
  const fileInputRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [previewing, setPreviewing] = useState(false);
  const [duplicatePolicy, setDuplicatePolicy] = useState("skip");
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleTemplateDownload = async () => {
    const blob = await downloadQuestionImportTemplate();
    triggerDownload(blob, "question_import_template.csv");
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setPreview(null);
    setResult(null);
    setError("");
  };

  const handlePreview = async () => {
    if (!selectedFile) return;
    setPreviewing(true);
    setError("");
    setResult(null);
    try {
      const res = await previewQuestionImport(selectedFile, { suppressToast: true });
      setPreview(res.data);
    } catch (err) {
      setError(err?.userMessage || "Preview failed.");
      setPreview(null);
    } finally {
      setPreviewing(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview?.valid_rows?.length) return;
    setConfirming(true);
    setError("");
    try {
      const res = await confirmQuestionImport(
        {
          rows: preview.valid_rows.map((row) => row.raw_row),
          duplicate_policy: duplicatePolicy,
          source_filename: preview.filename || selectedFile?.name || "unknown",
        },
        { suppressToast: true }
      );
      setResult(res.data);
      setPreview(null);
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    } catch (err) {
      setError(err?.userMessage || "Import failed and was rolled back.");
    } finally {
      setConfirming(false);
    }
  };

  const handleErrorReportDownload = async () => {
    if (!preview?.invalid_rows?.length) return;
    const blob = await downloadQuestionImportErrorReport(preview.invalid_rows);
    triggerDownload(blob, "question_import_errors.csv");
  };

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-6">
      <PageHeader
        title="Import Questions"
        subtitle="Upload a CSV or XLSX file of questions. Nothing is saved until you review the preview and confirm."
      />

      <div className="panel space-y-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex flex-wrap items-center gap-3">
          <button type="button" className="btn-secondary" onClick={handleTemplateDownload}>
            <Download size={16} className="mr-1 inline" aria-hidden="true" />
            Download template
          </button>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            quiz_title, question_type, question_text, option_a-h, correct_answers (e.g. "A|C|E"), explanation,
            difficulty, tags, source, published
          </span>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx"
            aria-label="Question import file"
            onChange={handleFileChange}
            className="input-field max-w-xs"
          />
          <button type="button" className="btn-primary" onClick={handlePreview} disabled={!selectedFile || previewing}>
            <Upload size={16} className="mr-1 inline" aria-hidden="true" />
            {previewing ? "Previewing..." : "Preview"}
          </button>
        </div>

        {error ? (
          <div className="flex items-center gap-2 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/30 dark:text-red-200">
            <AlertTriangle size={16} aria-hidden="true" />
            {error}
          </div>
        ) : null}

        {result ? (
          <div className="flex items-center gap-2 rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
            <CheckCircle2 size={16} aria-hidden="true" />
            Import complete: {result.created} created, {result.updated} updated, {result.skipped_duplicates}{" "}
            duplicate(s) skipped, {result.skipped_invalid} invalid row(s) skipped.
          </div>
        ) : null}
      </div>

      {preview ? (
        <div className="space-y-4">
          <div className="panel dark:border-slate-700 dark:bg-slate-900">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              {preview.total_rows} row(s) parsed from <strong>{preview.filename}</strong>: {preview.valid_count} valid
              {preview.duplicate_count ? `, ${preview.duplicate_count} matching an existing question` : ""},{" "}
              {preview.invalid_count} invalid.
            </p>

            <div className="mt-3 flex flex-wrap items-center gap-3">
              <label className="text-sm font-medium text-slate-700 dark:text-slate-200">
                If a row matches an existing question:
                <select
                  className="input-field ml-2 inline-block w-auto"
                  value={duplicatePolicy}
                  onChange={(e) => setDuplicatePolicy(e.target.value)}
                >
                  <option value="skip">Skip duplicates</option>
                  <option value="update_draft">Update drafts (never overwrites published)</option>
                </select>
              </label>
              <button
                type="button"
                className="btn-primary"
                onClick={handleConfirm}
                disabled={!preview.valid_rows.length || confirming}
              >
                {confirming ? "Importing..." : `Confirm import of ${preview.valid_rows.length} question(s)`}
              </button>
              {preview.invalid_rows.length ? (
                <button type="button" className="btn-secondary" onClick={handleErrorReportDownload}>
                  <Download size={16} className="mr-1 inline" aria-hidden="true" />
                  Download error report
                </button>
              ) : null}
            </div>
          </div>

          {preview.valid_rows.length ? (
            <div className="panel dark:border-slate-700 dark:bg-slate-900">
              <h2 className="mb-2 text-sm font-semibold text-slate-800 dark:text-slate-100">
                Valid rows ({preview.valid_rows.length})
              </h2>
              <div className="max-h-80 overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 dark:text-slate-400">
                      <th className="py-1 pr-3">Row</th>
                      <th className="py-1 pr-3">Question</th>
                      <th className="py-1 pr-3">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.valid_rows.map((row) => (
                      <tr key={row.row_number} className="border-t border-slate-100 dark:border-slate-800">
                        <td className="py-1 pr-3 text-slate-500 dark:text-slate-400">{row.row_number}</td>
                        <td className="py-1 pr-3 text-slate-800 dark:text-slate-200">{row.payload.question_text}</td>
                        <td className="py-1 pr-3 text-xs text-amber-600 dark:text-amber-400">
                          {row.is_duplicate ? `Matches question #${row.existing_question_id}. ` : ""}
                          {[...row.warnings, ...row.info].join(" ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}

          {preview.invalid_rows.length ? (
            <div className="panel border-red-200 dark:border-red-900 dark:bg-slate-900">
              <h2 className="mb-2 text-sm font-semibold text-red-800 dark:text-red-200">
                Invalid rows ({preview.invalid_rows.length}) — will not be imported
              </h2>
              <div className="max-h-80 overflow-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="text-xs text-slate-500 dark:text-slate-400">
                      <th className="py-1 pr-3">Row</th>
                      <th className="py-1 pr-3">Question text</th>
                      <th className="py-1 pr-3">Errors</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.invalid_rows.map((row) => (
                      <tr key={row.row_number} className="border-t border-slate-100 dark:border-slate-800">
                        <td className="py-1 pr-3 text-slate-500 dark:text-slate-400">{row.row_number}</td>
                        <td className="py-1 pr-3 text-slate-800 dark:text-slate-200">
                          {row.raw_row?.question_text || "(missing)"}
                        </td>
                        <td className="py-1 pr-3 text-xs text-red-700 dark:text-red-300">{row.errors.join(" ")}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>
      ) : null}
    </main>
  );
}
