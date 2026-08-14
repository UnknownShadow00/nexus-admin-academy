'use client';

import React from 'react';
import type {
  RemoteDesktopAppId,
  WorkstationWindowBounds,
  WorkstationWindowState,
} from '@service-desk/shared';
import {
  IconArrowsMove,
  IconMaximize,
  IconMinus,
  IconX,
} from '@tabler/icons-react';
import {
  useEffect,
  useState,
  type KeyboardEvent,
  type PointerEvent,
  type ReactNode,
} from 'react';

import { WORKSTATION_APP_REGISTRY } from './app-registry';

interface DragOrigin {
  pointerId: number;
  clientX: number;
  clientY: number;
  bounds: WorkstationWindowBounds;
}

export function WindowFrame({
  appId,
  children,
  focused,
  onClose,
  onFocus,
  onMinimize,
  onMove,
  onToggleMaximize,
  windowState,
}: {
  appId: RemoteDesktopAppId;
  children: ReactNode;
  focused: boolean;
  onClose: () => void;
  onFocus: () => void;
  onMinimize: () => void;
  onMove: (bounds: WorkstationWindowBounds) => void;
  onToggleMaximize: () => void;
  windowState: WorkstationWindowState;
}) {
  const Meta = WORKSTATION_APP_REGISTRY[appId];
  const [dragOrigin, setDragOrigin] = useState<DragOrigin | null>(null);
  const [draftBounds, setDraftBounds] = useState(windowState.bounds);

  useEffect(() => setDraftBounds(windowState.bounds), [windowState.bounds]);

  const moveBy = (deltaX: number, deltaY: number) => {
    if (windowState.maximized) return;
    onMove({
      ...windowState.bounds,
      x: Math.max(0, windowState.bounds.x + deltaX),
      y: Math.max(0, windowState.bounds.y + deltaY),
    });
  };
  const handleKeyboardMove = (event: KeyboardEvent<HTMLElement>) => {
    if (!event.altKey) return;
    const delta = event.shiftKey ? 48 : 16;
    const movement: [number, number] | undefined = {
      ArrowLeft: [-delta, 0],
      ArrowRight: [delta, 0],
      ArrowUp: [0, -delta],
      ArrowDown: [0, delta],
    }[event.key] as [number, number] | undefined;
    if (!movement) return;
    event.preventDefault();
    moveBy(movement[0], movement[1]);
  };
  const handlePointerDown = (event: PointerEvent<HTMLElement>) => {
    if (windowState.maximized || event.button !== 0) return;
    if ((event.target as HTMLElement).closest('[data-window-control]')) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragOrigin({
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      bounds: windowState.bounds,
    });
    onFocus();
  };
  const handlePointerMove = (event: PointerEvent<HTMLElement>) => {
    if (!dragOrigin || dragOrigin.pointerId !== event.pointerId) return;
    setDraftBounds({
      ...dragOrigin.bounds,
      x: Math.max(0, dragOrigin.bounds.x + event.clientX - dragOrigin.clientX),
      y: Math.max(0, dragOrigin.bounds.y + event.clientY - dragOrigin.clientY),
    });
  };
  const finishDrag = (event: PointerEvent<HTMLElement>) => {
    if (!dragOrigin || dragOrigin.pointerId !== event.pointerId) return;
    event.currentTarget.releasePointerCapture(event.pointerId);
    setDragOrigin(null);
    onMove(draftBounds);
  };

  return (
    <section
      aria-label={`${Meta.label} window`}
      className={`absolute flex min-h-0 flex-col overflow-hidden border bg-zinc-100 text-zinc-900 shadow-2xl max-sm:!inset-x-2 max-sm:!bottom-12 max-sm:!top-2 max-sm:!h-auto max-sm:!w-auto ${focused ? 'border-sky-300 ring-2 ring-sky-300/30' : 'border-zinc-500'}`}
      onPointerDown={() => {
        if (!focused) onFocus();
      }}
      style={
        windowState.maximized
          ? { inset: '0.5rem 0.5rem 3rem', zIndex: windowState.zIndex }
          : {
              left: draftBounds.x,
              top: draftBounds.y,
              width: `min(${draftBounds.width}px, calc(100% - 1rem))`,
              height: `min(${draftBounds.height}px, calc(100% - 3.5rem))`,
              zIndex: windowState.zIndex,
            }
      }
    >
      <header
        aria-label={`Move ${Meta.label}. Hold Alt and use arrow keys for keyboard movement.`}
        className="flex touch-none select-none items-center justify-between border-b border-zinc-300 bg-[#e7edf2] px-3 py-1.5 shadow-[0_1px_0_rgba(255,255,255,.8)_inset]"
        onKeyDown={handleKeyboardMove}
        onPointerCancel={finishDrag}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishDrag}
        tabIndex={0}
      >
        <span className="flex items-center gap-2 text-xs font-semibold">
          <Meta.Icon aria-hidden="true" className={`h-4 w-4 ${Meta.tint}`} />
          {Meta.label}
          <IconArrowsMove
            aria-hidden="true"
            className="h-3.5 w-3.5 text-zinc-500 max-sm:hidden"
          />
        </span>
        <span className="flex" data-window-control>
          <button
            aria-label={`Minimize ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-zinc-300"
            onClick={onMinimize}
            type="button"
          >
            <IconMinus aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
          <button
            aria-label={`${windowState.maximized ? 'Restore' : 'Maximize'} ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-zinc-300"
            onClick={onToggleMaximize}
            type="button"
          >
            <IconMaximize aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
          <button
            aria-label={`Close ${Meta.label}`}
            className="rounded-sm p-1 hover:bg-red-500 hover:text-white"
            onClick={onClose}
            type="button"
          >
            <IconX aria-hidden="true" className="h-3.5 w-3.5" />
          </button>
        </span>
      </header>
      <div className="min-h-0 flex-1 overflow-auto bg-white">{children}</div>
    </section>
  );
}
