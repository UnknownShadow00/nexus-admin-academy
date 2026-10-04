import { Link } from "react-router-dom";
import V2Status from "./V2Status";
import { practicalDisplayStatus } from "../ui/statusFoundation";

const assessmentNames = {
  module_quiz: "Final checkpoint",
  practical: "Practical",
  service_desk: "Service Desk task",
};

// Use the ordered module response. The server owns availability and progress.
export function stageSequenceItems(data, { summary = false } = {}) {
  const moduleKey = data.module.key;
  const base = `/learning-v2/modules/${moduleKey}`;
  const beginner = data.certification.version?.key === "nexus_beginner_aplus_v1";
  const interactions = data.interactions || [];
  const items = [];

  for (const lesson of data.lessons || []) {
    const lessonRoute = `${base}/lessons/${lesson.key}`;
    items.push({ key: `lesson-${lesson.key}`, kind: "lesson", type: "Learn", title: lesson.title,
      status: beginner ? lesson.group_status || lesson.progress?.status : lesson.progress?.status,
      route: lessonRoute, available: true });
    if (summary) continue;
    for (const resource of lesson.resources || []) {
      items.push({ key: `resource-${lesson.key}-${resource.key}`, kind: "resource", type: resource.required ? "Teaching resource" : "Optional resource",
        title: resource.title, status: resource.status, route: lessonRoute, available: true });
    }
    for (const entry of interactions.filter(({ interaction }) => interaction.lesson_key === lesson.key)) {
      items.push({ key: `interaction-${entry.interaction.key}`, kind: "interaction", type: entry.interaction.required ? "Practice" : "Optional practice",
        title: entry.interaction.title, status: entry.progress?.passed ? "passed" : entry.progress?.status,
        route: `${base}/interactions/${entry.interaction.key}`, available: true });
    }
    if (lesson.quick_check) {
      const check = lesson.quick_check;
      items.push({ key: `check-${check.key}`, kind: "quick_check", type: "Quick Check", title: check.title,
        status: check.progress?.status, route: `${base}/assessments/${check.key}`, available: check.available !== false,
        unavailable: check.unavailable });
    }
  }

  if (!summary) {
    for (const entry of interactions.filter(({ interaction }) => !interaction.lesson_key)) {
      items.push({ key: `interaction-${entry.interaction.key}`, kind: "interaction", type: entry.interaction.required ? "Practice" : "Optional practice",
        title: entry.interaction.title, status: entry.progress?.passed ? "passed" : entry.progress?.status,
        route: `${base}/interactions/${entry.interaction.key}`, available: true });
    }
  }
  for (const assessment of data.assessments || []) {
    if (!(assessment.role in assessmentNames)) continue;
    const routePart = assessment.role === "module_quiz" ? "assessments" : assessment.role === "service_desk" ? "service-desk" : "practical";
    items.push({ key: `assessment-${assessment.key}`, kind: assessment.role, type: assessmentNames[assessment.role], title: assessment.title,
      status: assessment.role === "practical" ? practicalDisplayStatus(assessment.progress, beginner) : assessment.progress?.status,
      route: `${base}/${routePart}/${assessment.key}`, available: assessment.available !== false,
      unavailable: assessment.unavailable });
  }
  if (!summary) {
    for (const prompt of data.explain_prompts || []) {
      items.push({ key: `explain-${prompt.key}`, kind: "explain", type: "Explain", title: prompt.prompt,
        status: prompt.progress?.status, route: `${base}/explain/${prompt.key}`, available: true });
    }
  }
  return items;
}

export default function V2StageSequence({ data, summary = false, next = null }) {
  const items = stageSequenceItems(data, { summary });
  const workName = data.certification.version?.key === "nexus_beginner_aplus_v1" ? "stage" : "module";
  return <ol className={`stage-sequence ${summary ? "stage-sequence-summary" : ""}`} aria-label={summary ? `Current ${workName} overview` : `${workName === "stage" ? "Stage" : "Module"} learning sequence`}>
    {items.map((item) => {
      const upNext = next?.route === item.route && next?.title === item.title && item.available && !["review_pending", "correction", "complete", "blocked"].includes(next.kind);
      return <li className={`stage-sequence-row ${upNext ? "stage-sequence-up-next" : ""}`} key={item.key} aria-current={upNext ? "step" : undefined} aria-label={!item.available ? `${item.title} unavailable` : undefined}>
        <div className="stage-sequence-copy">
          <p className="type-label">{item.type}</p>
          {item.available ? <Link className="stage-sequence-title" to={item.route}>{item.title}</Link>
            : <span className="stage-sequence-title">{item.title}</span>}
          {!item.available && item.unavailable?.reason ? <p className="type-meta mt-1">{item.unavailable.reason}</p> : null}
          {!item.available && item.unavailable?.required_action ? <p className="type-meta mt-1">{item.unavailable.required_action}</p> : null}
        </div>
        <V2Status status={upNext ? "up_next" : item.available ? item.status : "locked"} />
      </li>;
    })}
  </ol>;
}
