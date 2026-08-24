import EvidenceCaseWorkbench from "./EvidenceCaseWorkbench";

/** Compatibility wrapper for the Phase 4B.2 endpoint curriculum. */
export default function EndpointEvidenceWorkbench({ workbench, ...props }) {
  return (
    <EvidenceCaseWorkbench
      workbench={{ title: "Endpoint evidence workbench", ...workbench }}
      {...props}
    />
  );
}
