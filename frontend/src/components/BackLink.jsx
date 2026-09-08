import { ChevronLeft } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { activityOrigin } from "../utils/activityOrigin";
export default function BackLink({
  className = "inline-flex items-center gap-1 text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline",
  fallbackLabel,
  fallbackTo,
}) {
  const origin = activityOrigin(useLocation());
  return (
    <Link className={className} to={origin?.route || fallbackTo}>
      <ChevronLeft size={16} />
      {origin ? `Back to ${origin.label}` : fallbackLabel}
    </Link>
  );
}
