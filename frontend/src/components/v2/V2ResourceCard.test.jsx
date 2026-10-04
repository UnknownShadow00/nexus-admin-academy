import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import V2ResourceCard from "./V2ResourceCard";
import { recordV2Resource } from "../../services/api";

vi.mock("../../services/api", async (original) => ({ ...await original(), recordV2Resource: vi.fn().mockResolvedValue({ data: {} }) }));
afterEach(() => { cleanup(); vi.clearAllMocks(); });
const resource = { key: "res.stage4", title: "Teaching card", type: "reference", provider: "Nexus", url: "/v2-interactions/beginner-s4-clues.svg", required: true, status: "not_started" };

it("opens a Stage 4 teaching card in a closable, keyboard accessible drawer", async () => {
  const onChanged = vi.fn().mockResolvedValue(undefined);
  recordV2Resource.mockResolvedValueOnce({ data: { status: "viewed" } });
  render(<V2ResourceCard resource={resource} moduleKey="stage4" onChanged={onChanged} />);
  const opener = screen.getByRole("button", { name: "View teaching card" });
  fireEvent.click(opener);
  expect(screen.getByRole("dialog", { name: "Teaching card" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Close teaching card" })).toHaveFocus();
  fireEvent.keyDown(document, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
  expect(recordV2Resource).toHaveBeenCalledWith("stage4", "res.stage4", { opened: true }, { suppressToast: true });
  expect(await screen.findByText("Viewed / Opened")).toBeVisible();
  expect(screen.getByRole("button", { name: "View again" })).toBeVisible();
});

it("traps Tab in both directions, makes the page inert, and restores scrolling and opener focus", async () => {
  const user = userEvent.setup();
  render(<V2ResourceCard resource={resource} moduleKey="stage4" onChanged={vi.fn()} />);
  const opener = screen.getByRole("button", { name: "View teaching card" });
  opener.focus();
  await user.keyboard("{Enter}");
  const dialog = screen.getByRole("dialog", { name: "Teaching card" });
  const close = screen.getByRole("button", { name: "Close teaching card" });
  const zoomIn = screen.getByRole("button", { name: "Zoom in" });
  const viewport = screen.getByRole("region", { name: "Teaching card image, scrollable" });
  expect(dialog).toHaveAttribute("aria-modal", "true");
  expect(close).toHaveFocus();
  expect(opener.closest("body > div").inert).toBe(true);
  expect(document.body.style.overflow).toBe("hidden");
  await user.keyboard("{Shift>}{Tab}{/Shift}");
  expect(viewport).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(close).toHaveFocus();
  await user.keyboard("{Tab}");
  expect(zoomIn).toHaveFocus(); // Disabled Zoom out is skipped.
  opener.focus(); // Even programmatic background focus is returned to the viewer.
  expect(close).toHaveFocus();
  await user.click(close);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(opener).toHaveFocus();
  expect(opener.closest("body > div").inert).toBeFalsy();
  expect(document.body.style.overflow).toBe("");
});

it("zooms a teaching card without changing its view tracking", async () => {
  const user = userEvent.setup();
  render(<V2ResourceCard resource={resource} moduleKey="stage4" onChanged={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "View teaching card" }));
  expect(screen.getByRole("button", { name: "Zoom out" })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: "Zoom in" }));
  expect(screen.getByText("150%")).toBeVisible();
  expect(recordV2Resource).toHaveBeenCalledWith("stage4", "res.stage4", { opened: true }, { suppressToast: true });
  expect(recordV2Resource).toHaveBeenCalledTimes(1);
});

it("keeps third-party resources as external links", () => {
  render(<V2ResourceCard resource={{ ...resource, url: "https://example.org/lesson" }} moduleKey="stage4" onChanged={vi.fn()} />);
  expect(screen.getByRole("link", { name: /Open resource/ })).toHaveAttribute("target", "_blank");
  expect(screen.queryByRole("button", { name: "View teaching card" })).not.toBeInTheDocument();
});

it("keeps an opened video in progress until watched is reported", async () => {
  recordV2Resource.mockResolvedValueOnce({ data: { status: "in_progress" } });
  render(<V2ResourceCard resource={{ ...resource, type: "video", provider: "External", url: "https://example.org/video" }} moduleKey="stage4" onChanged={vi.fn()} />);
  fireEvent.click(screen.getByRole("link", { name: /Open video/ }));
  expect(await screen.findByText("In progress")).toBeVisible();
  expect(screen.queryByText("Viewed / Opened")).not.toBeInTheDocument();
});
