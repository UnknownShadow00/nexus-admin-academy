import { ChevronLeft } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { activityOrigin } from "../utils/activityOrigin";
export default function BackLink({
  className = "inline-flex items-center gap-1 text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline",
  fallbackLabel,
  fallbackTo,
  beforeNavigate,
}) {
  const origin = activityOrigin(useLocation());
  const navigate = useNavigate();
  const target = origin?.route || fallbackTo;
  return (
    <Link
      className={className}
      onClick={
        beforeNavigate
          ? async (event) => {
              event.preventDefault();
              await beforeNavigate();
              navigate(target);
            }
          : undefined
      }
      to={target}
    >
      <ChevronLeft size={16} />
      {origin ? `Back to ${origin.label}` : fallbackLabel}
    </Link>
  );
}
