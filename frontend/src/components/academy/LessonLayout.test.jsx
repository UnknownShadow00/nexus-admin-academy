import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useNavigate } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import LessonLayout from "./LessonLayout";

const steps = [
  { id: "lesson-understand", label: "Understand" },
  { id: "lesson-resources", label: "Watch the video" },
  { id: "lesson-practice", label: "Practice exercise" },
  { id: "lesson-completion", label: "Next lesson" },
];
function HistoryControls() { const navigate = useNavigate(); return <button onClick={() => navigate(-1)}>Previous section</button>; }
function page(props = {}) {
  return <MemoryRouter initialEntries={["/#lesson-understand", window.location.hash ? `/${window.location.hash}` : "/"]}><HistoryControls /><LessonLayout title="Real lesson" resources practice steps={steps} {...props}>
    {steps.map(step => <section key={step.id} id={step.id} tabIndex={-1}><h2>{step.label}</h2></section>)}
  </LessonLayout></MemoryRouter>;
}
function sections() { return screen.getByRole("navigation", { name: "Lesson sections" }); }
function rail() { return screen.getByRole("complementary", { name: "Lesson guide" }); }

describe("lesson section navigation", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    Element.prototype.scrollIntoView = vi.fn();
  });
  afterEach(() => { cleanup(); window.history.replaceState({}, "", "/"); });

  it("keeps the initial tab and step on the same resource section", () => {
    render(page());
    expect(within(sections()).getByRole("link", { name: "Resources" })).toHaveAttribute("aria-current", "location");
    expect(within(rail()).getByRole("link", { name: /Watch the video/ })).toHaveAttribute("aria-current", "location");
  });
  it("synchronizes tabs and steps for mouse and keyboard navigation", async () => {
    render(page());
    await userEvent.click(within(sections()).getByRole("link", { name: "Try it" }));
    expect(within(rail()).getByRole("link", { name: /Practice exercise/ })).toHaveAttribute("aria-current", "location");
    expect(within(sections()).getByRole("link", { name: "Try it" })).toHaveClass("selected");
    expect(document.getElementById("lesson-practice")).toHaveFocus();
    const learn = within(rail()).getByRole("link", { name: /Understand/ });
    learn.focus(); await userEvent.keyboard("{Enter}");
    expect(within(sections()).getByRole("link", { name: "Learn" })).toHaveAttribute("aria-current", "location");
    expect(document.getElementById("lesson-understand")).toHaveFocus();
  });
  it("restores an existing section hash and browser history changes", async () => {
    window.history.replaceState({}, "", "/#lesson-practice");
    render(page());
    expect(within(sections()).getByRole("link", { name: "Try it" })).toHaveAttribute("aria-current", "location");
    await userEvent.click(screen.getByRole("button", { name: "Previous section" }));
    expect(within(sections()).getByRole("link", { name: "Learn" })).toHaveAttribute("aria-current", "location");
  });
  it("does not preserve an unavailable section when the next lesson changes", async () => {
    const { rerender } = render(page());
    await userEvent.click(within(sections()).getByRole("link", { name: "Try it" }));
    rerender(page({ title: "Next real lesson", resources: false, practice: false, steps: steps.filter(step => !["lesson-practice", "lesson-resources"].includes(step.id)) }));
    expect(within(rail()).getByRole("link", { name: /Understand/ })).toHaveAttribute("aria-current", "location");
    expect(within(sections()).getByRole("link", { name: "Learn" })).toHaveAttribute("aria-current", "location");
  });
});
