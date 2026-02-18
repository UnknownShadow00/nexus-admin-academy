import { useMemo, useState } from "react";
import { AlertCircle, CheckCircle, Upload } from "lucide-react";
import { uploadEvidence } from "../services/api";

function UploadPreview({ upload }) {
  const isValid = upload.validation?.valid;
  return (
    <div className={`rounded border p-3 ${isValid ? "border-green-200 bg-green-50" : upload.status === "error" ? "border-red-200 bg-red-50" : "border-slate-200 bg-slate-50"}`}>
      <div className="flex items-center gap-2">
        {upload.status === "uploading" ? <span>⏳</span> : null}
        {isValid ? <CheckCircle className="text-green-600" size={18} /> : null}
        {upload.status === "validated" && !isValid ? <AlertCircle className="text-amber-600" size={18} /> : null}
        <div className="flex-1">
          <div className="text-sm font-medium">{upload.file.name}</div>
          {upload.validation?.issues?.length ? (
            <div className="mt-1 text-xs text-amber-700">
              {upload.validation.issues.map((issue, idx) => (
                <div key={idx}>- {issue}</div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function EvidenceUploader({ ticketId, requiredEvidence = [], onComplete }) {
  const [uploads, setUploads] = useState([]);

  const handleFileSelect = async (event, evidenceType) => {
    const files = Array.from(event.target.files || []);
    for (const file of files) {
      const preview = { id: Date.now() + Math.random(), file, type: evidenceType, status: "uploading" };
      setUploads((prev) => [...prev, preview]);
      try {
        const res = await uploadEvidence({ file, ticketId, artifactType: evidenceType });
        setUploads((prev) =>
          prev.map((u) =>
            u.id === preview.id
              ? {
                  ...u,
                  status: "validated",
                  artifact_id: res.data?.artifact_id,
                  validation: res.data?.validation,
                }
              : u
          )
        );
      } catch {
        setUploads((prev) => prev.map((u) => (u.id === preview.id ? { ...u, status: "error", error: "Upload failed" } : u)));
      }
    }
  };

  const complete = useMemo(() => {
    return requiredEvidence.every((req) => {
      const validCount = uploads.filter((u) => u.type === req.type && u.validation?.valid).length;
      return validCount >= (req.min_count || 1);
    });
  }, [requiredEvidence, uploads]);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Required Evidence</h3>
      {requiredEvidence.map((req) => (
        <div key={`${req.type}-${req.description}`} className="rounded border p-4 dark:border-slate-700">
          <div className="mb-2 flex items-center justify-between">
            <div>
              <p className="font-medium capitalize">{req.type}</p>
              <p className="text-sm text-slate-600 dark:text-slate-300">{req.description}</p>
            </div>
            <label className="cursor-pointer rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700">
              <Upload size={14} className="mr-1 inline" />
              Upload
              <input type="file" className="hidden" onChange={(e) => handleFileSelect(e, req.type)} multiple />
            </label>
          </div>
          <div className="space-y-2">
            {uploads
              .filter((u) => u.type === req.type)
              .map((upload) => (
                <UploadPreview key={upload.id} upload={upload} />
              ))}
          </div>
        </div>
      ))}
      <button
        className="w-full rounded bg-green-600 py-3 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
        disabled={!complete}
        onClick={() => onComplete(uploads)}
      >
        {complete ? "Evidence Complete" : "Upload All Required Evidence"}
      </button>
    </div>
  );
}

