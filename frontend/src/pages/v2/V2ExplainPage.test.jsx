import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ getV2Explain: vi.fn(), submitV2Explain: vi.fn() }));
vi.mock("../../services/api", () => api);
import V2ExplainPage from "./V2ExplainPage";

describe("V2ExplainPage", () => {
  beforeEach(() => { api.getV2Explain.mockResolvedValue({ data: { module_key: "module.dynamic", prompt: { key: "prompt.dynamic", text: "Explain DHCP." }, submissions: [] } }); api.submitV2Explain.mockResolvedValue({ data: { state: "pending", message: "Your response was saved and is waiting to be graded.", score: null } }); });
  it("labels and persists a response before showing honest pending state", async () => {
    render(<MemoryRouter initialEntries={["/learning-v2/modules/module.dynamic/explain/prompt.dynamic"]}><Routes><Route path="/learning-v2/modules/:moduleKey/explain/:promptKey" element={<V2ExplainPage />} /></Routes></MemoryRouter>);
    const textarea = await screen.findByLabelText("Your response");
    await userEvent.type(textarea, "DHCP gives a workstation its network settings and I would verify the lease.");
    await userEvent.click(screen.getByRole("button", { name: "Submit response" }));
    expect(await screen.findByRole("heading", { name: "Waiting for grading" })).toBeVisible();
    expect(screen.getByText(/Your response was saved. Grading is still in progress/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Submit response" })).not.toBeInTheDocument();
  });
});
