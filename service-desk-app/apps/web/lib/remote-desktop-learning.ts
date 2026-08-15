import type { ActionEvent } from '@service-desk/simulation-engine';
import type { RemoteDesktopScenarioFixture } from '@service-desk/shared';
import type { RemoteDesktopLearningMode } from '@service-desk/shared';

export function canInspectScenarioRequirements(identity: {
  isAdmin: boolean;
  isMentor: boolean;
}) {
  return identity.isAdmin || identity.isMentor;
}

export function progressiveHints(
  scenario: RemoteDesktopScenarioFixture,
  hintsRevealed: number,
  learningMode: RemoteDesktopLearningMode = 'practice',
  _completed = false,
) {
  if (learningMode === 'assessment') {
    // Assessment attempts never render hint bodies. This remains true after a
    // Guided attempt, completion, refresh, or resume of the same scenario.
    return [];
  }
  return scenario.studentHints.slice(0, hintsRevealed);
}

export function hasAnotherHint(
  scenario: RemoteDesktopScenarioFixture,
  hintsRevealed: number,
  learningMode: RemoteDesktopLearningMode = 'practice',
  completed = false,
) {
  if (learningMode === 'assessment') return false;
  if (completed) return false;
  return hintsRevealed < scenario.studentHints.length;
}

export function shouldProactivelyRevealHint(
  scenario: RemoteDesktopScenarioFixture,
  hintsRevealed: number,
  learningMode: RemoteDesktopLearningMode,
  completed: boolean,
) {
  return (
    learningMode === 'guided' &&
    !completed &&
    hintsRevealed === 0 &&
    scenario.studentHints.length > 0
  );
}

export function scenarioActionLabel(
  scenario: RemoteDesktopScenarioFixture,
  stepId: string,
) {
  return scenario.actionLabels[stepId] ?? 'Completed a troubleshooting action';
}

export function studentFeedbackMessage(
  event: ActionEvent,
  mode: RemoteDesktopLearningMode | boolean,
) {
  const learningMode =
    typeof mode === 'boolean' ? (mode ? 'guided' : 'practice') : mode;
  if (event.success) {
    if (event.type === 'remote_desktop.authenticate') {
      return 'Connected to the simulated computer.';
    }
    if (event.type === 'remote_desktop.disconnect') {
      return 'Remote session disconnected.';
    }
    if (event.type === 'remote_desktop.perform_scenario_step') {
      return 'Your change was saved to the simulated computer.';
    }
    return 'Your change was saved.';
  }

  if (learningMode === 'guided') {
    return 'That did not address the reported issue. Re-read the ticket symptoms and try a tool that can test the affected service.';
  }
  if (learningMode === 'practice') {
    return 'That action was not accepted. You can review the ticket and try another approach.';
  }
  return 'That action was not accepted.';
}

export function mentorScenarioRequirements(
  scenario: RemoteDesktopScenarioFixture,
) {
  if (scenario.workflow) {
    return [
      ...scenario.workflow.diagnose,
      ...scenario.workflow.fix,
      ...scenario.workflow.verify,
    ].flatMap((objective) =>
      objective.anyOf.map((stepId) => ({
        label: scenarioActionLabel(scenario, stepId),
        stepId,
      })),
    );
  }
  return scenario.requiredSteps.map((stepId) => ({
    label: scenarioActionLabel(scenario, stepId),
    stepId,
  }));
}
