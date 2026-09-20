import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCliLab } from "../services/api";
import CliLabPage from "./CliLabPage";

vi.mock("../services/api", () => ({ getCliLab: vi.fn() }));
vi.mock("../features/cli-labs/components/LabRunner", () => ({
  default: () => <div data-testid="lab-runner">Lab runner</div>,
}));
vi.mock("../monitoring/sentry", () => ({ setMonitoringContext: vi.fn() }));

describe("CliLabPage", () => {
  beforeEach(() => {
    getCliLab.mockReset();
  });

  it("renders a prerequisite lock without mounting the runner when GET returns 403", async () => {
    getCliLab.mockRejectedValue({
      response: {
        status: 403,
        data: {
          detail: {
            code: "PREREQUISITE_NOT_MET",
            error: "Complete the required work in CompTIA A+ first.",
            data: { next_action_route: "/training" },
          },
        },
      },
    });

    render(
      <MemoryRouter initialEntries={["/cli-labs/dev-sw-act-04"]}>
        <Routes>
          <Route path="/cli-labs/:labId" element={<CliLabPage />} />
        </Routes>
      </MemoryRouter>,
    );

    expect(await screen.findByText("Complete the required work in CompTIA A+ first.")).toBeVisible();
    expect(screen.queryByTestId("lab-runner")).not.toBeInTheDocument();
  });
});
