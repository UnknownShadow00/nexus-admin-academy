export default function EmptyState({ icon, title, message }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-slate-50 py-14 text-center dark:border-slate-700 dark:bg-slate-900/40">
      <div className="text-5xl">{icon}</div>
      <h3 className="mt-3 text-xl font-semibold text-slate-900 dark:text-slate-100">{title}</h3>
      <p className="mt-2 max-w-lg text-sm text-slate-500 dark:text-slate-400">{message}</p>
    </div>
  );
}
