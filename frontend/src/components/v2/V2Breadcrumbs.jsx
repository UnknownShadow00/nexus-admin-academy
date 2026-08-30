import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

export default function V2Breadcrumbs({ certification, module, lesson }) {
  return <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
    <Link className="hover:text-blue-600" to="/learning-v2">{certification?.name || "Learning"}</Link>
    <ChevronRight size={14} aria-hidden="true" />
    {lesson ? <><Link className="hover:text-blue-600" to={`/learning-v2/modules/${module.key}`}>{module.title}</Link><ChevronRight size={14} aria-hidden="true" /><span aria-current="page">{lesson.title}</span></> : <span aria-current="page">{module?.title}</span>}
  </nav>;
}
