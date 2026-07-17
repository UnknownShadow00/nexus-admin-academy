export default function FilterBar({ children }) {
  return (
    <div className="panel panel-compact flex flex-wrap items-end gap-2 sm:gap-3">
      {children}
    </div>
  );
}
