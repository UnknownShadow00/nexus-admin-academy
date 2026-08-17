import { ChevronLeft } from "lucide-react";
import { Link, useLocation } from "react-router-dom";

function labelForReturnTo(returnTo, returnToLabel) {
  if (returnToLabel) return returnToLabel;
  const match = returnTo?.match(/\/training\/week\/(\d+)\/?$/);
  return match ? `Back to Week ${match[1]}` : "Back to training";
}

export default function BackLink({ className = "inline-flex items-center gap-1 text-sm font-semibold text-blue-600", fallbackLabel, fallbackTo }) {
  const { state } = useLocation();
  const returnTo = typeof state?.returnTo === "string" ? state.returnTo : null;

  return <Link className={className} to={returnTo || fallbackTo}><ChevronLeft size={16} />{returnTo ? labelForReturnTo(returnTo, state?.returnToLabel) : fallbackLabel}</Link>;
}
