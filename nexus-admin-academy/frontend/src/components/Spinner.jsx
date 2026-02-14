export default function Spinner({ size = "md", text }) {
  const sizeClass = size === "sm" ? "h-4 w-4" : size === "lg" ? "h-10 w-10" : "h-7 w-7";
  return (
    <div className="flex items-center gap-2">
      <div className={`${sizeClass} animate-spin rounded-full border-2 border-blue-200 border-t-blue-600`} />
      {text ? <span className="text-sm text-slate-600 dark:text-slate-300">{text}</span> : null}
    </div>
  );
}
