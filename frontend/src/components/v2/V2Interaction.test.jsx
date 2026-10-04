import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Interaction: vi.fn(), submitV2Interaction: vi.fn(), getV2Module: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2Interaction from "./V2Interaction";

const choice = [{ id: "right", label: "Safe choice" }, { id: "wrong", label: "Unsafe choice" }];
const contents = {
  matching: { left: [{ id: "a", text: "RAM" }, { id: "b", text: "RJ45" }], right: [{ id: "memory", text: "Memory" }, { id: "ethernet", text: "Ethernet" }] },
  image_identification: { image_url: "/v2-interactions/ethernet-port.svg", image_alt: "A computer port with eight contacts", question: "Which port?", choices: choice },
  ordering: { steps: [{ id: "last", text: "Test connection" }, { id: "first", text: "Ask the user" }] },
  command_output: { command: "ipconfig", output: "IPv4 Address: 169.254.1.1", question: "What happened?", choices: choice },
  typed_answer: { question: "Which command shows IP configuration?" },
  safe_action: { scenario: "A user has no network. What first?", safety_critical: true, choices: choice },
};

function answerData(type) {
  return {
    interaction: { key: `interaction.pilot.${type}`, version: 1, version_id: 77, type, title: "Practice activity", instructions: "Choose or enter your answer.", required: true, content: contents[type] },
    progress: { status: "not_started", attempt_count: 0, best_result: null, passed: false },
  };
}

async function mount(type) {
  api.getV2Interaction.mockResolvedValue({ data: answerData(type) });
  render(<V2Interaction moduleKey="module.demo" interactionKey={`interaction.pilot.${type}`} />);
  await screen.findByRole("heading", { name: "Practice activity" });
}

describe("V2Interaction", () => {
  afterEach(cleanup);
  beforeEach(() => {
    vi.clearAllMocks();
    api.getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2", label: "Continue learning" } } });
    api.submitV2Interaction.mockImplementation(async (_module, _key, _versionId, response) => ({ data: {
      ...answerData("safe_action"),
      progress: { status: "passed", attempt_count: 1, best_result: { passed: true }, passed: true },
      submission_result: { attempt_id: 7, passed: true, score: 100, feedback: "Correct. Safe first step.", correct_answer: "right" },
      response,
    } }));
  });

  it("provides labeled keyboard-select matching controls", async () => {
    await mount("matching");
    await userEvent.selectOptions(screen.getByLabelText("RAM"), "memory");
    await userEvent.selectOptions(screen.getByLabelText("RJ45"), "ethernet");
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.matching", 77, { matches: { a: "memory", b: "ethernet" } }, { suppressToast: true });
  });

  it("reveals readable authored answers after submission", async () => {
    await mount("matching");
    api.getV2Module.mockResolvedValue({ data: { continue: { route: "/learning-v2/modules/module.demo/assessments/quick", label: "Continue with Quick Check", kind: "quick_check" } } });
    api.submitV2Interaction.mockResolvedValueOnce({ data: {
      ...answerData("matching"),
      progress: { status: "passed", attempt_count: 1, best_result: { passed: true }, passed: true },
      submission_result: { passed: true, score: 100, feedback: "Correct.", correct_answer: ["RAM → Memory", "RJ45 → Ethernet"] },
    } });
    await userEvent.selectOptions(screen.getByLabelText("RAM"), "memory");
    await userEvent.selectOptions(screen.getByLabelText("RJ45"), "ethernet");
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(await screen.findByText("RAM → Memory")).toBeVisible();
    expect(screen.getByText("RJ45 → Ethernet")).toBeVisible();
    expect(await screen.findByText("Next: Continue with Quick Check")).toBeVisible();
    expect(screen.getByRole("link", { name: /Continue with Quick Check/ })).toHaveAttribute("href", "/learning-v2/modules/module.demo/assessments/quick");
    expect(screen.queryByText(/Return to the module for your next step/)).not.toBeInTheDocument();
  });

  it.each([
    ["ordering", ["Ask the user", "Test connection"]],
    ["safe_action", "Safe choice"],
    ["matching", ["RAM → Memory", "RJ45 → Ethernet"]],
  ])("keeps a failed %s solution out of the result and allows retry", async (type, solution) => {
    await mount(type);
    api.submitV2Interaction.mockResolvedValueOnce({ data: {
      ...answerData(type),
      progress: { status: "in_progress", attempt_count: 1, passed: false },
      // A stale server response must not make a failed solution visible either.
      submission_result: { passed: false, score: 50, feedback: "Recheck the prompt.", correct_answer: solution },
    } });
    if (type === "safe_action") await userEvent.click(screen.getByRole("radio", { name: "Unsafe choice" }));
    if (type === "matching") {
      await userEvent.selectOptions(screen.getByLabelText("RAM"), "ethernet");
      await userEvent.selectOptions(screen.getByLabelText("RJ45"), "memory");
    }
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    const result = await screen.findByRole("status");
    expect(result).toHaveTextContent("Try again · 50%");
    expect(result).toHaveTextContent("Recheck the prompt.");
    expect(within(result).queryByText("Correct answer:")).not.toBeInTheDocument();
    expect(within(result).getByRole("button", { name: "Retry" })).toBeVisible();
    expect(screen.getByText("1 attempt saved. You can retry without penalty.")).toBeVisible();
    await userEvent.click(within(result).getByRole("button", { name: "Retry" }));
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Check again" })).toBeEnabled();
  });

  it("gives the image meaningful alt text and accessible choices", async () => {
    await mount("image_identification");
    expect(screen.getByRole("img", { name: "A computer port with eight contacts" })).toHaveAttribute("src", "/v2-interactions/ethernet-port.svg");
    await userEvent.click(screen.getByRole("radio", { name: "Safe choice" }));
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.image_identification", 77, { choice_id: "right" }, { suppressToast: true });
    expect(await screen.findByRole("status")).toHaveTextContent("Correct. Safe first step.");
  });

  it("reorders steps using keyboard-operable Move up controls", async () => {
    await mount("ordering");
    const list = screen.getByRole("list", { name: "Steps in your chosen order" });
    const move = within(list).getByRole("button", { name: "Move Ask the user up" });
    move.focus();
    await userEvent.keyboard("{Enter}");
    expect(within(list).getAllByRole("listitem")[0]).toHaveTextContent("Ask the user");
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.ordering", 77, { order: ["first", "last"] }, { suppressToast: true });
  });

  it("renders command output as readable text with choices", async () => {
    await mount("command_output");
    expect(screen.getByText("IPv4 Address: 169.254.1.1")).toBeVisible();
    await userEvent.click(screen.getByRole("radio", { name: "Safe choice" }));
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.command_output", 77, { choice_id: "right" }, { suppressToast: true });
  });

  it("uses a labeled typed answer field", async () => {
    await mount("typed_answer");
    await userEvent.type(screen.getByRole("textbox", { name: "Which command shows IP configuration?" }), "ipconfig");
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.typed_answer", 77, { answer: "ipconfig" }, { suppressToast: true });
  });

  it("labels the safe-action scenario and choice without color dependence", async () => {
    await mount("safe_action");
    expect(screen.getByText("Choose the safest next step.")).toBeVisible();
    await userEvent.click(screen.getByRole("radio", { name: "Safe choice" }));
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(api.submitV2Interaction).toHaveBeenCalledWith("module.demo", "interaction.pilot.safe_action", 77, { choice_id: "right" }, { suppressToast: true });
  });

  it("requires a fresh render after a stale-version conflict", async () => {
    await mount("typed_answer");
    api.submitV2Interaction.mockRejectedValueOnce({ response: { status: 409 }, userMessage: "This interaction changed. Reload it before submitting your answer." });
    await userEvent.type(screen.getByRole("textbox"), "ipconfig");
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload it");
    expect(screen.getByRole("button", { name: "Check answer" })).toBeDisabled();
    const updated = answerData("typed_answer");
    updated.interaction.version_id = 78;
    updated.interaction.version = 2;
    api.getV2Interaction.mockResolvedValueOnce({ data: updated });
    await userEvent.click(screen.getByRole("button", { name: "Reload interaction" }));
    await waitFor(() => expect(api.getV2Interaction).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("textbox")).toHaveValue(""));
    expect(screen.getByRole("button", { name: "Check answer" })).toBeEnabled();
  });

  it("clears old pass feedback when a retry is rejected", async () => {
    await mount("safe_action");
    await userEvent.click(screen.getByRole("radio", { name: "Safe choice" }));
    await userEvent.click(screen.getByRole("button", { name: "Check answer" }));
    expect(await screen.findByRole("status")).toHaveTextContent("Passed");
    api.submitV2Interaction.mockRejectedValueOnce({ response: { status: 422 }, userMessage: "Choose one unique answer." });
    await userEvent.click(screen.getByRole("button", { name: "Check again" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Choose one unique answer.");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
