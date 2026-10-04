export default function PageHeader({ breadcrumb, eyebrow, title, description, subtitle, actions, status, children, className = "" }) {
  return <header className={`page-header ${className}`.trim()}>
    <div className="page-header-copy">
      {breadcrumb ? <div className="mb-4">{breadcrumb}</div> : null}
      {eyebrow ? <p className="type-label mb-2">{eyebrow}</p> : null}
      <h1 className="type-page-title">{title}</h1>
      {description || subtitle ? <p className="page-header-description">{description || subtitle}</p> : null}
      {status ? <div className="mt-3 flex flex-wrap gap-2">{status}</div> : null}
      {children}
    </div>
    {actions ? <div className="page-header-actions">{actions}</div> : null}
  </header>;
}
