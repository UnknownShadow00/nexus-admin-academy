function IconBase({ children, className = "h-5 w-5" }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export function Trophy(props) {
  return (
    <IconBase {...props}>
      <path d="M8 21h8" />
      <path d="M12 17v4" />
      <path d="M7 4h10v3a5 5 0 0 1-10 0z" />
      <path d="M5 5H3a2 2 0 0 0 2 2" />
      <path d="M19 5h2a2 2 0 0 1-2 2" />
    </IconBase>
  );
}

export function BookOpen(props) {
  return (
    <IconBase {...props}>
      <path d="M2 4h8a3 3 0 0 1 3 3v13H5a3 3 0 0 0-3 3z" />
      <path d="M22 4h-8a3 3 0 0 0-3 3v13h8a3 3 0 0 1 3 3z" />
    </IconBase>
  );
}

export function Ticket(props) {
  return (
    <IconBase {...props}>
      <path d="M3 8a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4z" />
      <path d="M13 6v12" />
    </IconBase>
  );
}

export function Award(props) {
  return (
    <IconBase {...props}>
      <circle cx="12" cy="8" r="5" />
      <path d="m8.2 13.8-1.2 6.2L12 17l5 3-1.2-6.2" />
    </IconBase>
  );
}

export function LayoutDashboard(props) {
  return (
    <IconBase {...props}>
      <rect x="3" y="3" width="7" height="7" />
      <rect x="14" y="3" width="7" height="4" />
      <rect x="14" y="10" width="7" height="11" />
      <rect x="3" y="13" width="7" height="8" />
    </IconBase>
  );
}

export function Shield(props) {
  return (
    <IconBase {...props}>
      <path d="M12 3 4 7v5c0 5 3.5 8.5 8 9 4.5-.5 8-4 8-9V7z" />
    </IconBase>
  );
}

export function Spinner(props) {
  return (
    <IconBase {...props}>
      <path d="M21 12a9 9 0 1 1-6.2-8.6" />
    </IconBase>
  );
}
