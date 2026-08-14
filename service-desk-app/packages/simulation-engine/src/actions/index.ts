import type {
  AssetStatus,
  DeploymentBootSource,
  DeploymentCable,
  DeploymentPort,
  IdentityVerificationMethod,
  PcShelfDeviceState,
  PcShelfNetworkStatus,
  RemoteDesktopAppId,
  RemoteDesktopLearningMode,
  ShippingDepartment,
  ShippingEquipmentName,
  ShippingSpeed,
  TicketStatus,
  WorkstationWindowBounds,
} from '@service-desk/shared';

interface TicketActionPayload {
  ticketId: string;
}

interface DirectoryActionPayload {
  directoryUserId: string;
}

interface ChatActionPayload {
  contactId: string;
}

interface AssetActionPayload {
  assetTag: string;
}

interface PcShelfActionPayload {
  assetTag: string;
}

interface ServerRoomActionPayload {
  nodeId: string;
}

interface RemoteDesktopActionPayload {
  assetTag: string;
}

interface RemoteDesktopTicketPayload extends RemoteDesktopActionPayload {
  ticketId: string;
}

interface DeploymentRunActionPayload {
  runId: string;
}

export interface AssignTicketAction {
  type: 'ticket.assign';
  payload: TicketActionPayload;
}

export interface UnassignTicketAction {
  type: 'ticket.unassign';
  payload: TicketActionPayload;
}

export interface ChangeTicketStatusAction {
  type: 'ticket.change_status';
  payload: TicketActionPayload & {
    status: TicketStatus;
  };
}

export interface AddTicketNoteAction {
  type: 'ticket.add_note';
  payload: TicketActionPayload & {
    body: string;
  };
}

export interface EscalateTicketAction {
  type: 'ticket.escalate';
  payload: TicketActionPayload;
}

export interface RevealTicketHintAction {
  type: 'ticket.reveal_hint';
  payload: TicketActionPayload & {
    step: number;
  };
}

export interface CloseTicketAction {
  type: 'ticket.close';
  payload: TicketActionPayload & {
    resolutionNote: string;
    verifiedResolved: boolean;
  };
}

export interface UnlockDirectoryAccountAction {
  type: 'directory.unlock_account';
  payload: DirectoryActionPayload;
}

export interface ResetDirectoryPasswordAction {
  type: 'directory.reset_password';
  payload: DirectoryActionPayload & { requireChangeAtNextSignIn?: boolean };
}

export interface InspectDirectoryAccountAction {
  type: 'directory.inspect_account';
  payload: DirectoryActionPayload;
}

export interface VerifyDirectoryIdentityAction {
  type: 'directory.verify_identity';
  payload: DirectoryActionPayload & { method: IdentityVerificationMethod };
}

export interface TestDirectoryPrimaryAuthAction {
  type: 'directory.test_primary_auth';
  payload: DirectoryActionPayload & { result: 'succeeds' | 'blocked' };
}

export interface RecordDirectoryDiagnosisAction {
  type: 'directory.record_diagnosis';
  payload: DirectoryActionPayload & {
    diagnosis: 'account-locked' | 'password-expired' | 'mfa-factor-unavailable';
  };
}

export interface VerifyDirectoryAccessAction {
  type: 'directory.verify_access';
  payload: DirectoryActionPayload & {
    check:
      | 'account-unlocked'
      | 'temporary-password-issued'
      | 'mfa-reregistration-ready';
  };
}

export interface EnableDirectoryAccountAction {
  type: 'directory.enable_account';
  payload: DirectoryActionPayload;
}

export interface DisableDirectoryAccountAction {
  type: 'directory.disable_account';
  payload: DirectoryActionPayload;
}

export interface ResetDirectoryMfaAction {
  type: 'directory.reset_mfa';
  payload: DirectoryActionPayload;
}

export interface UpdateDirectoryGroupsAction {
  type: 'directory.update_groups';
  payload: DirectoryActionPayload & {
    add: string[];
    remove: string[];
  };
}

export interface SendChatMessageAction {
  type: 'chat.send_message';
  payload: ChatActionPayload & {
    body: string;
  };
}

export interface VerifyIdentityInChatAction {
  type: 'chat.verify_identity';
  payload: ChatActionPayload & {
    method: IdentityVerificationMethod;
    ticketId: string;
  };
}

export interface RequestResolutionConfirmationAction {
  type: 'chat.request_resolution_confirmation';
  payload: ChatActionPayload & { ticketId: string };
}

export interface MarkChatPinnedAction {
  type: 'chat.mark_pinned';
  payload: ChatActionPayload & {
    pinned: boolean;
  };
}

export interface OpenChatThreadAction {
  type: 'chat.open_thread';
  payload: ChatActionPayload;
}

export interface AssignAssetAction {
  type: 'asset.assign';
  payload: AssetActionPayload & {
    directoryUserId: string;
  };
}

export interface UnassignAssetAction {
  type: 'asset.unassign';
  payload: AssetActionPayload;
}

export interface ChangeAssetStatusAction {
  type: 'asset.change_status';
  payload: AssetActionPayload & {
    status: AssetStatus;
  };
}

export type HeadsetIsolationTest =
  | 'affected-headset-known-good-workstation'
  | 'known-good-headset-affected-workstation'
  | 'alternate-usb-port'
  | 'replacement-clean-audio';

export interface RecordAssetIsolationAction {
  type: 'asset.record_isolation';
  payload: AssetActionPayload & {
    test: HeadsetIsolationTest;
  };
}

export interface AddPcShelfComputerAction {
  type: 'pc_shelf.add';
  payload: PcShelfActionPayload;
}

export interface RemovePcShelfComputerAction {
  type: 'pc_shelf.remove';
  payload: PcShelfActionPayload;
}

export interface ChangePcShelfNetworkStatusAction {
  type: 'pc_shelf.change_network_status';
  payload: PcShelfActionPayload & {
    networkStatus: PcShelfNetworkStatus;
  };
}

export interface ChangePcShelfDeviceStateAction {
  type: 'pc_shelf.change_device_state';
  payload: PcShelfActionPayload & {
    deviceState: PcShelfDeviceState;
  };
}

export interface AssignPcShelfComputerAction {
  type: 'pc_shelf.assign';
  payload: PcShelfActionPayload & {
    directoryUserId: string;
  };
}

export interface UnassignPcShelfComputerAction {
  type: 'pc_shelf.unassign';
  payload: PcShelfActionPayload;
}

export interface RestartServerRoomDeviceAction {
  type: 'server_room.restart_device';
  payload: ServerRoomActionPayload;
}

export interface RestartServerRoomServiceAction {
  type: 'server_room.restart_service';
  payload: ServerRoomActionPayload & {
    serviceName: string;
  };
}

export interface RestartServerRoomServerAction {
  type: 'server_room.restart_server';
  payload: ServerRoomActionPayload;
}

export interface RestartRemoteDesktopComputerAction {
  type: 'remote_desktop.restart_computer';
  payload: RemoteDesktopActionPayload;
}

export interface ResetRemoteDesktopNetworkAction {
  type: 'remote_desktop.network_reset';
  payload: RemoteDesktopActionPayload;
}

export interface RestartRemoteDesktopServiceAction {
  type: 'remote_desktop.restart_service';
  payload: RemoteDesktopActionPayload & {
    serviceName: string;
  };
}

export interface ConnectRemoteDesktopAction {
  type: 'remote_desktop.connect';
  payload: RemoteDesktopTicketPayload;
}

export interface BeginRemoteDesktopLoginAction {
  type: 'remote_desktop.begin_login';
  payload: RemoteDesktopTicketPayload;
}

export interface AuthenticateRemoteDesktopAction {
  type: 'remote_desktop.authenticate';
  payload: RemoteDesktopTicketPayload & {
    passwordEntered: boolean;
    usernameEntered: boolean;
  };
}

export interface CancelRemoteDesktopConnectionAction {
  type: 'remote_desktop.cancel_connection';
  payload: RemoteDesktopActionPayload;
}

export interface DisconnectRemoteDesktopAction {
  type: 'remote_desktop.disconnect';
  payload: RemoteDesktopActionPayload;
}

export interface OpenRemoteDesktopAppAction {
  type: 'remote_desktop.open_app';
  payload: RemoteDesktopActionPayload & { appId: RemoteDesktopAppId };
}

export interface CloseRemoteDesktopAppAction {
  type: 'remote_desktop.close_app';
  payload: RemoteDesktopActionPayload & { appId: RemoteDesktopAppId };
}

export interface FocusRemoteDesktopAppAction {
  type: 'remote_desktop.focus_app';
  payload: RemoteDesktopActionPayload & { appId: RemoteDesktopAppId };
}

export interface MinimizeRemoteDesktopAppAction {
  type: 'remote_desktop.minimize_app';
  payload: RemoteDesktopActionPayload & { appId: RemoteDesktopAppId };
}

export interface MoveRemoteDesktopWindowAction {
  type: 'remote_desktop.move_window';
  payload: RemoteDesktopActionPayload & {
    appId: RemoteDesktopAppId;
    bounds: WorkstationWindowBounds;
  };
}

export interface ToggleRemoteDesktopWindowMaximizeAction {
  type: 'remote_desktop.toggle_window_maximize';
  payload: RemoteDesktopActionPayload & { appId: RemoteDesktopAppId };
}

export interface SetRemoteDesktopStartMenuAction {
  type: 'remote_desktop.set_start_menu';
  payload: RemoteDesktopActionPayload & { open: boolean };
}

export interface ToggleRemoteDesktopTrainingModeAction {
  type: 'remote_desktop.toggle_training_mode';
  payload: RemoteDesktopActionPayload & { enabled: boolean };
}

export interface SetRemoteDesktopLearningModeAction {
  type: 'remote_desktop.set_learning_mode';
  payload: RemoteDesktopActionPayload & { mode: RemoteDesktopLearningMode };
}

export interface AddRemoteDesktopInternalNoteAction {
  type: 'remote_desktop.add_internal_note';
  payload: RemoteDesktopTicketPayload & { text: string };
}

export interface PerformRemoteDesktopScenarioStepAction {
  type: 'remote_desktop.perform_scenario_step';
  payload: RemoteDesktopTicketPayload & { stepId: string };
}

export interface RunRemoteDesktopTerminalCommandAction {
  type: 'remote_desktop.run_terminal_command';
  payload: RemoteDesktopActionPayload & { command: string };
}

export interface NavigateRemoteDesktopExplorerAction {
  type: 'remote_desktop.explorer_navigate';
  payload: RemoteDesktopActionPayload & { path: string };
}

export interface ReconnectRemoteDesktopExplorerDriveAction {
  type: 'remote_desktop.explorer_reconnect_drive';
  payload: RemoteDesktopActionPayload & { driveLetter: string };
}

export interface RefreshRemoteDesktopExplorerAction {
  type: 'remote_desktop.explorer_refresh';
  payload: RemoteDesktopActionPayload;
}

export interface MapRemoteDesktopDriveAction {
  type: 'remote_desktop.map_drive';
  payload: RemoteDesktopActionPayload & {
    letter: string;
    uncPath: string;
    reconnectAtSignIn: boolean;
    credentialTarget: string | null;
  };
}

export interface AddRemoteDesktopCredentialAction {
  type: 'remote_desktop.credential_add';
  payload: RemoteDesktopActionPayload & {
    target: string;
    username: string;
  };
}

export interface DeleteRemoteDesktopCredentialAction {
  type: 'remote_desktop.credential_delete';
  payload: RemoteDesktopActionPayload & { target: string };
}

export interface ConnectRemoteDesktopVpnAction {
  type: 'remote_desktop.vpn_connect';
  payload: RemoteDesktopActionPayload;
}

export interface CompleteRemoteDesktopVpnConnectionAction {
  type: 'remote_desktop.vpn_complete_connection';
  payload: RemoteDesktopActionPayload;
}

export interface DisconnectRemoteDesktopVpnAction {
  type: 'remote_desktop.vpn_disconnect';
  payload: RemoteDesktopActionPayload;
}

export interface UpdateRemoteDesktopDnsAction {
  type: 'remote_desktop.settings_update_dns';
  payload: RemoteDesktopActionPayload & {
    primaryDns: string;
    secondaryDns: string;
  };
}

export interface StartRemoteDesktopServiceAction {
  type: 'remote_desktop.start_service';
  payload: RemoteDesktopActionPayload & { serviceName: string };
}

export interface StopRemoteDesktopServiceAction {
  type: 'remote_desktop.stop_service';
  payload: RemoteDesktopActionPayload & { serviceName: string };
}

export interface InstallRemoteDesktopUpdateAction {
  type: 'remote_desktop.update_install';
  payload: RemoteDesktopActionPayload;
}

export interface CompleteRemoteDesktopUpdateInstallAction {
  type: 'remote_desktop.update_complete_install';
  payload: RemoteDesktopActionPayload;
}

export interface RestartRemoteDesktopAfterUpdateAction {
  type: 'remote_desktop.update_restart';
  payload: RemoteDesktopActionPayload;
}

export interface StartDeploymentAction {
  type: 'deployment.start';
  payload: Record<string, never>;
}

export interface SelectDeploymentDeviceTypeAction {
  type: 'deployment.select_device_type';
  payload: DeploymentRunActionPayload & { deviceType: string };
}

export interface ConnectDeploymentCableAction {
  type: 'deployment.connect_cable';
  payload: DeploymentRunActionPayload & {
    cable: DeploymentCable;
    port: DeploymentPort;
  };
}

export interface PressDeploymentF12Action {
  type: 'deployment.press_f12';
  payload: DeploymentRunActionPayload & {
    timing: 'early' | 'window' | 'late';
  };
}

export interface SelectDeploymentBootSourceAction {
  type: 'deployment.select_boot_source';
  payload: DeploymentRunActionPayload & { source: DeploymentBootSource };
}

export interface AuthenticateDeploymentShareAction {
  type: 'deployment.authenticate_share';
  payload: DeploymentRunActionPayload & { password: string };
}

export interface SetDeploymentHostnameAction {
  type: 'deployment.set_hostname';
  payload: DeploymentRunActionPayload & { hostname: string };
}

export interface RunDeploymentTaskSequenceAction {
  type: 'deployment.run_task_sequence';
  payload: DeploymentRunActionPayload;
}

export interface RebootDeploymentAction {
  type: 'deployment.reboot';
  payload: DeploymentRunActionPayload;
}

export interface LoginDeploymentDomainAction {
  type: 'deployment.domain_login';
  payload: DeploymentRunActionPayload & {
    domain: string;
    username: string;
    password: string;
  };
}

export interface CreateShipmentAction {
  type: 'shipping.create';
  payload: {
    recipientDirectoryUserId: string;
    recipientName: string;
    street: string;
    city: string;
    state: string;
    postalCode: string;
    senderDepartment: ShippingDepartment;
    equipment: Array<{ name: ShippingEquipmentName; quantity: number }>;
    computerAssetTag: string | null;
    speed: ShippingSpeed;
    includeReturnLabel: boolean;
  };
}

export interface CancelShipmentAction {
  type: 'shipping.cancel';
  payload: { shipmentId: string };
}

export type ChatSimulationAction =
  | SendChatMessageAction
  | VerifyIdentityInChatAction
  | RequestResolutionConfirmationAction
  | MarkChatPinnedAction
  | OpenChatThreadAction;

export type DirectorySimulationAction =
  | InspectDirectoryAccountAction
  | VerifyDirectoryIdentityAction
  | TestDirectoryPrimaryAuthAction
  | RecordDirectoryDiagnosisAction
  | VerifyDirectoryAccessAction
  | UnlockDirectoryAccountAction
  | ResetDirectoryPasswordAction
  | EnableDirectoryAccountAction
  | DisableDirectoryAccountAction
  | ResetDirectoryMfaAction
  | UpdateDirectoryGroupsAction;

export type TicketSimulationAction =
  | AssignTicketAction
  | UnassignTicketAction
  | ChangeTicketStatusAction
  | AddTicketNoteAction
  | EscalateTicketAction
  | RevealTicketHintAction
  | CloseTicketAction;

export type AssetSimulationAction =
  | AssignAssetAction
  | UnassignAssetAction
  | ChangeAssetStatusAction
  | RecordAssetIsolationAction;

export type PcShelfSimulationAction =
  | AddPcShelfComputerAction
  | RemovePcShelfComputerAction
  | ChangePcShelfNetworkStatusAction
  | ChangePcShelfDeviceStateAction
  | AssignPcShelfComputerAction
  | UnassignPcShelfComputerAction;

export type ServerRoomSimulationAction =
  | RestartServerRoomDeviceAction
  | RestartServerRoomServiceAction
  | RestartServerRoomServerAction;

export type RemoteDesktopSimulationAction =
  | RestartRemoteDesktopComputerAction
  | ResetRemoteDesktopNetworkAction
  | RestartRemoteDesktopServiceAction
  | ConnectRemoteDesktopAction
  | BeginRemoteDesktopLoginAction
  | AuthenticateRemoteDesktopAction
  | CancelRemoteDesktopConnectionAction
  | DisconnectRemoteDesktopAction
  | OpenRemoteDesktopAppAction
  | CloseRemoteDesktopAppAction
  | FocusRemoteDesktopAppAction
  | MinimizeRemoteDesktopAppAction
  | MoveRemoteDesktopWindowAction
  | ToggleRemoteDesktopWindowMaximizeAction
  | SetRemoteDesktopStartMenuAction
  | ToggleRemoteDesktopTrainingModeAction
  | SetRemoteDesktopLearningModeAction
  | AddRemoteDesktopInternalNoteAction
  | PerformRemoteDesktopScenarioStepAction
  | RunRemoteDesktopTerminalCommandAction
  | NavigateRemoteDesktopExplorerAction
  | ReconnectRemoteDesktopExplorerDriveAction
  | RefreshRemoteDesktopExplorerAction
  | MapRemoteDesktopDriveAction
  | AddRemoteDesktopCredentialAction
  | DeleteRemoteDesktopCredentialAction
  | ConnectRemoteDesktopVpnAction
  | CompleteRemoteDesktopVpnConnectionAction
  | DisconnectRemoteDesktopVpnAction
  | UpdateRemoteDesktopDnsAction
  | StartRemoteDesktopServiceAction
  | StopRemoteDesktopServiceAction
  | InstallRemoteDesktopUpdateAction
  | CompleteRemoteDesktopUpdateInstallAction
  | RestartRemoteDesktopAfterUpdateAction;

export type DeploymentSimulationAction =
  | StartDeploymentAction
  | SelectDeploymentDeviceTypeAction
  | ConnectDeploymentCableAction
  | PressDeploymentF12Action
  | SelectDeploymentBootSourceAction
  | AuthenticateDeploymentShareAction
  | SetDeploymentHostnameAction
  | RunDeploymentTaskSequenceAction
  | RebootDeploymentAction
  | LoginDeploymentDomainAction;

export type ShippingSimulationAction =
  | CreateShipmentAction
  | CancelShipmentAction;

export type SimulationAction =
  | TicketSimulationAction
  | DirectorySimulationAction
  | ChatSimulationAction
  | AssetSimulationAction
  | PcShelfSimulationAction
  | ServerRoomSimulationAction
  | RemoteDesktopSimulationAction
  | DeploymentSimulationAction
  | ShippingSimulationAction;
