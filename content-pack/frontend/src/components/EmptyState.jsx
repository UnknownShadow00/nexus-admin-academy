export default function EmptyState({ icon, title, message }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 p-12 text-center dark:border-slate-700">
      <div className="mb-4">{typeof icon === "string" ? <span className="text-4xl">{icon}</span> : icon}</div>
      <h3 className="text-lg font-semibold text-slate-700 dark:text-slate-300">{title}</h3>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{message}</p>
    </div>
  );
}
