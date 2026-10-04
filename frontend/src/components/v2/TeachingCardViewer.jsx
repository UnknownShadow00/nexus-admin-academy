import { Minus, Plus, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

export default function TeachingCardViewer({ title, src, opener, onClose }) {
  const dialog = useRef(null);
  const closeButton = useRef(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const headingId = useId();
  const descriptionId = useId();
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    const node = dialog.current;
    const previousOverflow = document.body.style.overflow;
    const siblings = Array.from(document.body.children)
      .filter((child) => child !== node)
      .map((child) => [child, child.inert]);
    siblings.forEach(([child]) => { child.inert = true; });
    document.body.style.overflow = "hidden";
    closeButton.current?.focus();

    function onKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const focusable = Array.from(node.querySelectorAll('button:not([disabled]), [tabindex="0"]'));
      if (!focusable.length) return;
      const current = focusable.indexOf(document.activeElement);
      const next = current < 0 ? 0 : (current + (event.shiftKey ? -1 : 1) + focusable.length) % focusable.length;
      event.preventDefault();
      focusable[next].focus();
    }
    function keepFocus(event) {
      if (!node.contains(event.target)) closeButton.current?.focus();
    }
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("focusin", keepFocus);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("focusin", keepFocus);
      siblings.forEach(([child, wasInert]) => { child.inert = wasInert; });
      document.body.style.overflow = previousOverflow;
      opener.current?.focus();
    };
  }, [opener]);

  return createPortal(
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby={headingId} aria-describedby={descriptionId}
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/75 p-0 sm:p-4"
      onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden bg-[var(--nexus-surface-raised)] text-[var(--nexus-text)] shadow-2xl sm:h-[min(90vh,60rem)] sm:max-w-5xl sm:rounded-xl sm:border sm:border-[var(--nexus-border-strong)]">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 p-3 dark:border-slate-700 sm:p-4">
          <div className="min-w-0 flex-1"><h2 id={headingId} className="break-words text-lg font-bold text-slate-900 dark:text-slate-100">{title}</h2><p id={descriptionId} className="text-xs text-slate-600 dark:text-slate-300">Teaching card. Scroll to read the full image; use the zoom controls to enlarge it.</p></div>
          <button ref={closeButton} aria-label="Close teaching card" className="btn-quiet shrink-0" onClick={onClose} type="button"><X size={20} aria-hidden="true" /> Close</button>
        </div>
        <div className="flex items-center gap-2 border-b border-slate-200 px-3 py-2 dark:border-slate-700 sm:px-4" aria-label="Teaching card zoom controls">
          <button aria-label="Zoom out" className="btn-secondary" disabled={zoom === 1} onClick={() => setZoom((value) => Math.max(1, value - 0.5))} type="button"><Minus size={18} aria-hidden="true" /></button>
          <span className="min-w-12 text-center text-sm font-semibold" aria-live="polite">{Math.round(zoom * 100)}%</span>
          <button aria-label="Zoom in" className="btn-secondary" disabled={zoom === 2} onClick={() => setZoom((value) => Math.min(2, value + 0.5))} type="button"><Plus size={18} aria-hidden="true" /></button>
        </div>
        <div className="teaching-card-viewport focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-blue-600 dark:focus-visible:outline-blue-300"
          tabIndex={0} role="region" aria-label={`${title} image, scrollable`}>
          <img alt={title} className="teaching-card-image" src={src} style={{ minWidth: `${704 * zoom}px`, width: `${100 * zoom}%` }} />
        </div>
      </div>
    </div>, document.body,
  );
}
