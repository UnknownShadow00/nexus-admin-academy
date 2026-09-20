import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getCliLabs } from "../services/api";
import CliLabsPage from "./CliLabsPage";

vi.mock("../services/api", () => ({ getCliLabs: vi.fn() }));

describe("CliLabsPage", () => {
  beforeEach(() => {
    getCliLabs.mockReset();
  });

  it("shows a retryable error instead of claiming the catalog is progression-locked", async () => {
    getCliLabs
      .mockRejectedValueOnce({ userMessage: "Unable to reach the server." })
      .mockResolvedValueOnce({
        data: [{ id: "meet-cli-001", completed: false }],
      });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <CliLabsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Networking labs unavailable")).toBeVisible();
    expect(screen.getByText("Unable to reach the server.")).toBeVisible();
    expect(screen.queryByText("Networking labs unlock later")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Try again" }));

    await waitFor(() => expect(getCliLabs).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Meet the CLI")).toBeVisible();
  });

  it("describes the orientation gate when no CLI labs are unlocked", async () => {
    getCliLabs.mockResolvedValueOnce({ data: [] });

    render(
      <MemoryRouter>
        <CliLabsPage />
      </MemoryRouter>,
    );

    expect(await screen.findByText("Networking labs unlock later")).toBeVisible();
    expect(screen.getByText(/Complete orientation to reach the first CLI lessons/i)).toBeVisible();
    expect(screen.getByText(/first half of your active Network\+ modules/i)).toBeVisible();
  });
});
