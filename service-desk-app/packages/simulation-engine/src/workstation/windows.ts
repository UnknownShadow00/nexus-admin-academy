import type {
  RemoteDesktopAppId,
  WorkstationState,
  WorkstationWindowBounds,
} from '@service-desk/shared';

export const MAXIMIZED_WORKSTATION_BOUNDS: WorkstationWindowBounds = {
  x: 0,
  y: 0,
  width: 1280,
  height: 720,
};

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
