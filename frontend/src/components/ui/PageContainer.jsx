const widths = new Set(["reading", "standard", "workspace"]);

export default function PageContainer({ as: Component = "main", width = "standard", className = "", children, ...props }) {
  const resolvedWidth = widths.has(width) ? width : "standard";
  return <Component className={`page-container page-container-${resolvedWidth} ${className}`.trim()} {...props}>{children}</Component>;
}
