import type {
  RemoteDesktopAppId,
  WorkstationState,
  WorkstationWindowBounds,
  WorkstationWindowState,
} from '@service-desk/shared';

export const MAXIMIZED_WORKSTATION_BOUNDS: WorkstationWindowBounds = {
  x: 0,
  y: 0,
  width: 1280,
  height: 720,
};

function defaultWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationWindowState {
  const offset = Object.keys(state.desktop.windows).length % 8;
  return {
    appId,
    open: true,
    minimized: false,
    maximized: false,
    bounds: {
      x: 40 + offset * 28,
      y: 32 + offset * 24,
      width: 760,
      height: 520,
    },
    restoreBounds: null,
    zIndex: state.desktop.nextZIndex,
  };
}

export function focusWorkstationWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationState {
  const windowState = state.desktop.windows[appId];
  if (!windowState?.open) return state;
  return {
    ...state,
    desktop: {
      ...state.desktop,
      activeAppId: appId,
      nextZIndex: state.desktop.nextZIndex + 1,
      windows: {
        ...state.desktop.windows,
        [appId]: {
          ...windowState,
          minimized: false,
          zIndex: state.desktop.nextZIndex,
        },
      },
    },
  };
}

export function openWorkstationWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationState {
  const existing = state.desktop.windows[appId];
  const withOpenWindow: WorkstationState = {
    ...state,
    desktop: {
      ...state.desktop,
      windows: {
        ...state.desktop.windows,
        [appId]: existing
          ? { ...existing, open: true, minimized: false }
          : defaultWindow(state, appId),
      },
    },
  };
  return focusWorkstationWindow(withOpenWindow, appId);
}

export function minimizeWorkstationWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationState {
  const windowState = state.desktop.windows[appId];
  if (!windowState?.open) return state;
  return {
    ...state,
    desktop: {
      ...state.desktop,
      activeAppId:
        state.desktop.activeAppId === appId ? null : state.desktop.activeAppId,
      windows: {
        ...state.desktop.windows,
        [appId]: { ...windowState, minimized: true },
      },
    },
  };
}

export function closeWorkstationWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationState {
  const windowState = state.desktop.windows[appId];
  if (!windowState) return state;
  return {
    ...state,
    desktop: {
      ...state.desktop,
      activeAppId:
        state.desktop.activeAppId === appId ? null : state.desktop.activeAppId,
      windows: {
        ...state.desktop.windows,
        [appId]: { ...windowState, open: false, minimized: false },
      },
    },
  };
}

export function moveWorkstationWindow(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
  bounds: WorkstationWindowBounds,
): WorkstationState {
  const windowState = state.desktop.windows[appId];
  if (!windowState || windowState.maximized) return state;
  return {
    ...state,
    desktop: {
      ...state.desktop,
      windows: {
        ...state.desktop.windows,
        [appId]: { ...windowState, bounds: { ...bounds } },
      },
    },
  };
}

export function toggleWorkstationWindowMaximize(
  state: WorkstationState,
  appId: RemoteDesktopAppId,
): WorkstationState {
  const windowState = state.desktop.windows[appId];
  if (!windowState) return state;
  const maximizing = !windowState.maximized;
  return {
    ...state,
    desktop: {
      ...state.desktop,
      activeAppId: appId,
      nextZIndex: state.desktop.nextZIndex + 1,
      windows: {
        ...state.desktop.windows,
        [appId]: {
          ...windowState,
          bounds: maximizing
            ? MAXIMIZED_WORKSTATION_BOUNDS
            : (windowState.restoreBounds ?? windowState.bounds),
          restoreBounds: maximizing ? windowState.bounds : null,
          maximized: maximizing,
          minimized: false,
          zIndex: state.desktop.nextZIndex,
        },
      },
    },
  };
}

export function setWorkstationStartMenu(
  state: WorkstationState,
  open: boolean,
): WorkstationState {
  return {
    ...state,
    desktop: { ...state.desktop, startMenuOpen: open },
  };
}
