import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import V2ResourceCard from "./V2ResourceCard";
import { recordV2Resource } from "../../services/api";

vi.mock("../../services/api", async (original) => ({ ...await original(), recordV2Resource: vi.fn().mockResolvedValue({ data: {} }) }));
afterEach(cleanup);
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
