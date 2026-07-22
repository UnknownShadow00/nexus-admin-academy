import { NavLink } from "react-router-dom";

const items = [
  { to: "/training", label: "Weekly Plan", end: true },
  { to: "/training/content", label: "All Course Content" },
  { to: "/quizzes", label: "Quiz Library" },
];

export default function TrainingSubnav() {
  return (
    <nav aria-label="My Training sections" className="flex max-w-full gap-1 overflow-x-auto rounded-xl border border-slate-200 bg-white p-1 dark:border-slate-700 dark:bg-slate-900">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `shrink-0 rounded-lg px-3 py-2 text-sm font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${isActive ? "bg-blue-600 text-white" : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  );
}
