import { Link } from "react-router-dom";

// Service Desk is a separate Next.js application on the same origin. Its
// routes must trigger a document navigation; React Router owns only Nexus.
export function TrainingDestination({ activity, to, children, state, ...props }) {
  const destination = to || activity?.destination_route;
  if (!destination) return null;
  if (activity?.activity_type === "service_desk_scenario") {
    return <a href={destination} {...props}>{children}</a>;
  }
  return <Link to={destination} state={state} {...props}>{children}</Link>;
}
