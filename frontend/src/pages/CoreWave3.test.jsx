import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import LessonPage, { LessonNotes } from "./LessonPage";
import {
  completeLesson,
  getLesson,
  getLessonNote,
  saveLessonNote,
} from "../services/api";

vi.mock("../services/api", () => ({
  completeLesson: vi.fn(),
  getLesson: vi.fn(),
  getLessonNote: vi.fn(),
  saveLessonNote: vi.fn(),
}));

const lesson = {
  id: 7,
  title: "The Client-Side Network Triage Tree",
  summary: "The instructional body.",
  outcomes: ["Explain what DHCP supplies", "Recognize APIPA"],
  is_orientation: false,
  is_complete: false,
  presentation: {
    workplace_purpose:
      "IP configuration helps support technicians narrow a network report.",
    mental_model: [
      "device",
      "local IP configuration",
      "gateway",
      "DNS",
      "remote service",
    ],
    worked_example: {
      symptom: "No service",
      check: "Run ipconfig",
      observation: "169.254.40.7",
      suggests: "Normal DHCP configuration was not obtained.",
      does_not_prove: "This does not prove the DHCP server is down.",
      next_check: "Check the local link.",
    },
    evidence_guidance: "Ping failure does not prove the path is down.",
    understanding_prompt: "What does APIPA establish?",
    readiness: ["explain DHCP", "recognize APIPA", "choose a next check"],
  },
  next_activity: {
    type: "lesson",
    title: "Network Printing Without Tears",
    route: "/lessons/8",
  },
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/lessons/7"]}>
      <Routes>
        <Route path="/lessons/:lessonId" element={<LessonPage />} />
        <Route path="/learning-path" element={<h1>My Course destination</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  getLesson.mockResolvedValue({ data: lesson });
  getLessonNote.mockResolvedValue({ data: { content: "", updated_at: null } });
  saveLessonNote.mockResolvedValue({
    data: { content: "", updated_at: "2026-09-09T00:00:00Z" },
  });
  completeLesson.mockResolvedValue({ data: { is_complete: true } });
});

afterEach(cleanup);

describe("Core Wave 3 lesson presentation", () => {
  it("puts objectives before teaching and renders the reviewed beginner structure", async () => {
    renderPage();
    const objectives = await screen.findByTestId("lesson-objectives");
    const body = screen.getByTestId("lesson-body");
    expect(
      objectives.compareDocumentPosition(body) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    for (const heading of [
      "Why this matters",
      "Core idea / mental model",
      "Worked example",
      "What the evidence means",
      "Quick understanding prompt / next practice",
      "Ready to finish this lesson?",
    ]) {
      expect(screen.getByRole("heading", { name: heading })).toBeVisible();
    }
    expect(
      screen.getByText(/Quizzes and practical work provide separate evidence/),
    ).toBeVisible();
  });

  it("preserves module origin on the actual next activity", async () => {
    getLesson.mockResolvedValue({ data: { ...lesson, is_complete: true } });
    render(
      <MemoryRouter
        initialEntries={[
          "/lessons/7?returnTo=%2Ftraining%2Fmodule%2Fmodule.network&returnToLabel=Networking",
        ]}
      >
        <Routes>
          <Route path="/lessons/:lessonId" element={<LessonPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(
      await screen.findByRole("link", {
        name: "Network Printing Without Tears",
      }),
    ).toHaveAttribute(
      "href",
      "/lessons/8?returnTo=%2Ftraining%2Fmodule%2Fmodule.network&returnToLabel=Networking",
    );
  });

  it("keeps failed completion explicit and recoverable", async () => {
    completeLesson
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { is_complete: true } });
    renderPage();
    fireEvent.click(
      await screen.findByRole("button", { name: "Mark lesson complete" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "We couldn’t save your lesson completion.",
    );
    expect(
      screen.getByRole("button", { name: "Mark lesson complete" }),
    ).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", { name: "Lesson completion saved." }),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Network Printing Without Tears" }),
    ).toBeVisible();
  });

  it("flushes the latest rapid edit before intentional navigation", async () => {
    renderPage();
    const notes = await screen.findByLabelText("Lesson notes");
    fireEvent.change(notes, { target: { value: "first" } });
    fireEvent.change(notes, { target: { value: "latest note" } });
    fireEvent.click(screen.getByRole("link", { name: "My Course" }));
    await screen.findByRole("heading", { name: "My Course destination" });
    expect(saveLessonNote).toHaveBeenCalledTimes(1);
    expect(saveLessonNote).toHaveBeenCalledWith(7, "latest note", "", {
      suppressToast: true,
    });
  });
});

describe("lesson note recovery", () => {
  it("shows failure, retains the draft, and retries safely", async () => {
    let flush;
    saveLessonNote
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce({ data: { content: "keep me" } });
    render(
      <LessonNotes
        lessonId={7}
        registerFlush={(value) => {
          flush = value;
        }}
      />,
    );
    const notes = await screen.findByLabelText("Lesson notes");
    fireEvent.change(notes, { target: { value: "keep me" } });
    await act(async () => {
      await flush();
    });
    expect(screen.getByText("Couldn’t save")).toBeVisible();
    expect(localStorage.getItem("nexus:lesson-note-draft:unknown:7")).toContain(
      "keep me",
    );
    fireEvent.click(screen.getByRole("button", { name: "Try again" }));
    await waitFor(() => expect(screen.getByText("Saved")).toBeVisible());
    expect(
      localStorage.getItem("nexus:lesson-note-draft:unknown:7"),
    ).toBeNull();
  });

  it("restores an unsaved local draft after refresh or return", async () => {
    localStorage.setItem(
      "nexus:lesson-note-draft:unknown:7",
      JSON.stringify({ content: "restored locally" }),
    );
    getLessonNote.mockResolvedValue({
      data: {
        content: "older server text",
        updated_at: "2026-09-08T00:00:00Z",
      },
    });
    render(<LessonNotes lessonId={7} />);
    expect(await screen.findByDisplayValue("restored locally")).toBeVisible();
    expect(screen.getByText("Couldn’t save")).toBeVisible();
  });
});
