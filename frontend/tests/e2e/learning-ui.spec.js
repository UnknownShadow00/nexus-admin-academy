import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

const moduleKey = "module.nexus.beginner.stage4";
const lessonKey = "lesson.nexus.beginner.s4.find_protect";
const lessonRoute = `/learning-v2/modules/${moduleKey}/lessons/${lessonKey}`;
const interactionRoute = (type) => `/learning-v2/modules/${moduleKey}/interactions/interaction.pr8.${type}`;
const checkpointRoute = `/learning-v2/modules/${moduleKey}/assessments/assess.nexus.beginner.s4.find_protect`;
const lessonSource = readFileSync(new URL("../../../backend/content/curriculum/nexus-beginner-aplus-v1/stage-4/01-find-protect.md", import.meta.url), "utf8");
const lessonMarkdown = lessonSource.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
const interactionData = {
  matching: { title: "Match the tool to one observation", instructions: "Match each Windows view to a read-only clue it can show.", content: { left: [{ id: "explorer", text: "File Explorer" }, { id: "task_manager", text: "Task Manager" }], right: [{ id: "path", text: "The supplied folder and file name" }, { id: "process", text: "Whether its process is listed" }] } },
  image_identification: { title: "Identify a basic port", instructions: "Read the numbered shape descriptions or look at the diagram, then choose what fits port 1.", content: { image_url: "/v2-interactions/beginner-s2-connections.svg", image_alt: "Simplified teaching diagram of three numbered ports.", question: "What would commonly connect to port 1?", choices: [{ id: "keyboard", label: "A keyboard with a matching USB plug" }, { id: "monitor", label: "A monitor using an HDMI plug" }] } },
  ordering: { title: "Locate the supplied file safely", instructions: "Put the safe locating steps in order. No file change is needed.", content: { steps: [{ id: "protect", text: "Notice unsaved work and leave it open; ask the user to save before any later disruptive step." }, { id: "context", text: "Confirm the authorized account, named file, and supplied path." }, { id: "follow", text: "Follow the supplied path in File Explorer without moving the file." }, { id: "record", text: "Record the folder checked and whether the named file was visible." }] } },
  command_output: { title: "Optional preview — read an account name", instructions: "You do not need to run a command. Just read the example output.", content: { command: "whoami", output: "LAPTOP-17\\Sam", question: "Which part names the account currently running the command?", choices: [{ id: "sam", label: "Sam" }, { id: "laptop", label: "LAPTOP-17" }] } },
  typed_answer: { title: "Recall the saved-information term", instructions: "Type one word from the lesson.", content: { question: "What do we call saved information such as a document or photo?" } },
  safe_action: { title: "Respect an access boundary", instructions: "Choose what to do after an access-denied message.", content: { scenario: "The supplied path opens, but Windows denies access to one folder. Your normal account cannot read it. What next?", safety_critical: true, choices: [{ id: "escalate", label: "Record the denied location and ask the authorized owner or support channel." }, { id: "borrow", label: "Use a coworker's sign-in to check the folder." }] } },
};

async function fixture(page, state) {
  await page.addInitScript(() => {
    localStorage.setItem("selected_profile", JSON.stringify({ id: 42, name: "Taylor", email: "taylor@example.invalid" }));
    if (!localStorage.getItem("theme")) localStorage.setItem("theme", "light");
  });
  await page.route("**/auth/**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data: { student_id: 42, name: "Taylor" } }) }));
  await page.route("**/api/**", (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    const method = route.request().method();
    let data;
    if (path === "/api/v2/curriculum/access") data = { master_enabled: true, student_enabled: true, mode: "beginner" };
    else if (path.endsWith(`/lessons/${lessonKey}`)) data = {
      certification: { name: "Nexus Beginner A+", version: { key: "nexus_beginner_aplus_v1" } }, module: { key: moduleKey, title: "Stage 4 — Observe Windows safely" },
      lesson: { key: lessonKey, title: "Find and protect work", summary: "Follow a supplied path, identify the file, and leave the user's work safe.", importance: "job_critical", content_markdown: lessonMarkdown, progress: { status: "not_started" }, group_status: state.resourceOpened ? "viewed" : "not_started", resources: [{ key: "res.nexus.beginner.s4.find_protect", title: "Find and protect work — path picture", type: "reference", provider: "Nexus", required: true, url: "/v2-interactions/beginner-s4-find-protect.svg", status: state.resourceOpened ? "viewed" : "not_started", opened_at: state.resourceOpened ? "2026-10-05T00:00:00Z" : null }], quick_check: { key: "assess.nexus.beginner.s4.find_protect", title: "Find and protect work Quick Check", question_count: 1, available: true, progress: { status: "not_started" } } },
      interactions: [{ interaction: { key: "interaction.pr8.ordering", title: interactionData.ordering.title, required: true }, progress: { status: state.interactionPassed ? "passed" : "not_started", passed: state.interactionPassed } }], previous_lesson_key: null, next_lesson_key: null,
    };
    else if (path.endsWith("/resources/res.nexus.beginner.s4.find_protect/activity")) { state.resourceOpened = true; data = { status: "viewed" }; }
    else if (path.includes("/interactions/interaction.pr8.")) {
      const type = path.split("interaction.pr8.")[1].split("/")[0];
      const detail = interactionData[type];
      const submitting = path.endsWith("/submit") && method === "POST";
      if (submitting) {
        state.interactionAttempts += 1;
        const response = JSON.parse(route.request().postData() || "{}").response || {};
        state.interactionPassed = type === "ordering" && response.order?.join(",") === "context,protect,follow,record";
      }
      data = { interaction: { key: `interaction.pr8.${type}`, version_id: 77, type, title: detail.title, instructions: detail.instructions, required: true, content: detail.content }, progress: { status: state.interactionPassed ? "passed" : state.interactionAttempts ? "in_progress" : "not_started", attempt_count: state.interactionAttempts, passed: state.interactionPassed } };
      if (submitting) data.submission_result = { passed: state.interactionPassed, score: state.interactionPassed ? 100 : 0, feedback: state.interactionPassed ? "Establish context and protect work, then inspect the specified folder and report only what you saw." : "Check the order of the safe locating steps.", correct_answer: state.interactionPassed ? ["Confirm the authorized account, named file, and supplied path.", "Notice unsaved work and leave it open."] : null };
    }
    else if (path.endsWith("/assessments/assess.nexus.beginner.s4.find_protect")) data = { assessment: { key: "assess.nexus.beginner.s4.find_protect", title: "Find and protect work Quick Check", role: "quick_check", pass_percent: 60 }, attempt: { id: state.attemptId, attempt_number: state.attemptId - 98 }, questions: [{ id: 42, type: "multiple_choice", is_multi_select: false, question_text: "A named file is absent from the folder you were given. What can you report?", options: [{ key: "A", text: "Not seen in the folder you checked" }, { key: "B", text: "It is missing from the computer" }, { key: "C", text: "The application deleted it" }, { key: "D", text: "The user saved it in another folder" }] }] };
    else if (path.endsWith("/assessments/assess.nexus.beginner.s4.find_protect/submit")) {
      const answer = JSON.parse(route.request().postData() || "{}").answers?.["42"];
      const passed = answer === "A";
      state.checkpointPassed = passed;
      data = { attempt_id: state.attemptId, score: passed ? 100 : 0, passed, grading_state: "graded", pass_percent: 60, results: [{ question_id: 42, question_text: "A named file is absent from the folder you were given. What can you report?", is_correct: passed, correct_answer: ["A"], explanation: "You checked one folder. Record that limit; another authorized location may still contain the file." }] };
    }
    else if (path.endsWith("/assessments/assess.nexus.beginner.s4.find_protect/attempts")) { state.attemptId += 1; data = { assessment: { key: "assess.nexus.beginner.s4.find_protect", title: "Find and protect work Quick Check", role: "quick_check", pass_percent: 60 }, attempt: { id: state.attemptId, attempt_number: 2 }, questions: [{ id: 42, type: "multiple_choice", is_multi_select: false, question_text: "A named file is absent from the folder you were given. What can you report?", options: [{ key: "A", text: "Not seen in the folder you checked" }, { key: "B", text: "It is missing from the computer" }, { key: "C", text: "The application deleted it" }, { key: "D", text: "The user saved it in another folder" }] }] }; }
    else if (path === `/api/v2/curriculum/modules/${moduleKey}`) data = { continue: state.checkpointPassed ? { kind: "practical", label: "Start the practical", route: `/learning-v2/modules/${moduleKey}/practical/assess.nexus.beginner.s4.windows_observation` } : { kind: state.interactionPassed ? "quick_check" : "interaction", label: state.interactionPassed ? "Continue with Quick Check" : "Try interactive practice", route: state.interactionPassed ? checkpointRoute : interactionRoute("ordering") } };
    else if (path === "/api/students/42/stats") data = { name: "Taylor" };
    else if (path === "/api/training") data = { current_module: { title: "Nexus Orientation", route: "/learning-path" } };
    else if (path === "/api/students/42/check-in") data = {};
    else return route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ success: true, data }) });
  });
}

async function capture(page, name) {
  const directory = process.env.NEXUS_PR8_CAPTURE;
  if (!directory) return;
  await mkdir(directory, { recursive: true });
  await page.screenshot({ path: join(directory, `${name}.png`), fullPage: !name.startsWith("viewer-") && name !== "zoom-200-viewer" });
}

async function setMode(page, width, theme) {
  await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
  await page.evaluate((value) => localStorage.setItem("theme", value), theme);
  await page.reload();
  await expect(page.locator("html")).toHaveClass(theme === "dark" ? /dark/ : /^(?!.*dark)/);
}

async function noOverflow(page) {
  const measure = await page.evaluate(() => ({
    width: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
    offenders: [...document.querySelectorAll("body *")].filter((node) => node.getBoundingClientRect().right > window.innerWidth + 2).slice(0, 8).map((node) => ({ tag: node.tagName, className: typeof node.className === "string" ? node.className.slice(0, 80) : "", right: Math.round(node.getBoundingClientRect().right) })),
  }));
  expect(measure, JSON.stringify(measure)).toMatchObject({ scroll: measure.width });
}

const modes = [[1440, "light"], [1440, "dark"], [375, "light"], [375, "dark"]];

for (const [width, theme] of modes) {
  test(`authored lesson and teaching viewer ${width} ${theme}`, async ({ page }) => {
    const state = { resourceOpened: false, interactionAttempts: 0, interactionPassed: false, checkpointPassed: false, attemptId: 99 };
    await fixture(page, state);
    await page.goto(lessonRoute);
    await setMode(page, width, theme);
    await expect(page.getByRole("heading", { name: "Find and protect work", level: 1 })).toBeVisible();
    await expect(page.getByText("Locate before changing")).toBeVisible();
    await noOverflow(page);
    await capture(page, `lesson-${width}-${theme}`);
    const opener = page.getByRole("button", { name: "View teaching card" });
    await opener.click();
    await expect(page.getByRole("dialog", { name: "Find and protect work — path picture" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Close teaching card" })).toBeFocused();
    await noOverflow(page);
    await capture(page, `viewer-${width}-${theme}`);
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.getByRole("button", { name: "View again" })).toBeFocused();
    await expect(page.getByText("Mastered")).toHaveCount(0);
  });

  test(`ordering feedback and retry ${width} ${theme}`, async ({ page }) => {
    const state = { resourceOpened: false, interactionAttempts: 0, interactionPassed: false, checkpointPassed: false, attemptId: 99 };
    await fixture(page, state);
    await page.goto(interactionRoute("ordering"));
    await setMode(page, width, theme);
    await expect(page.getByRole("heading", { name: interactionData.ordering.title, level: 1 })).toBeVisible();
    await noOverflow(page);
    await capture(page, `ordering-initial-${width}-${theme}`);
    await page.getByRole("button", { name: "Check answer" }).click();
    await expect(page.getByRole("status")).toContainText("Not quite");
    await noOverflow(page);
    await capture(page, `ordering-not-quite-${width}-${theme}`);
    await page.getByRole("button", { name: "Try again" }).click();
    await capture(page, `ordering-retry-${width}-${theme}`);
    await page.getByRole("button", { name: "Move Confirm the authorized account, named file, and supplied path. up" }).click();
    await page.getByRole("button", { name: "Check answer" }).click();
    await expect(page.getByRole("status")).toContainText("Correct");
    await capture(page, `ordering-correct-${width}-${theme}`);
  });

  test(`checkpoint question, Not quite and Passed ${width} ${theme}`, async ({ page }) => {
    const state = { resourceOpened: false, interactionAttempts: 0, interactionPassed: true, checkpointPassed: false, attemptId: 99 };
    await fixture(page, state);
    await page.goto(checkpointRoute);
    await setMode(page, width, theme);
    await expect(page.getByRole("heading", { name: "A named file is absent from the folder you were given. What can you report?" })).toBeVisible();
    await noOverflow(page);
    await capture(page, `checkpoint-question-${width}-${theme}`);
    await page.getByRole("radio", { name: "B. It is missing from the computer" }).check();
    await page.getByRole("button", { name: "Submit answers" }).click();
    await expect(page.getByRole("heading", { name: "Not quite" })).toBeVisible();
    await capture(page, `checkpoint-not-quite-${width}-${theme}`);
    await page.getByRole("button", { name: "Try again" }).click();
    await page.getByRole("radio", { name: "A. Not seen in the folder you checked" }).check();
    await page.getByRole("button", { name: "Submit answers" }).click();
    await expect(page.getByRole("heading", { name: "Passed" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Start the practical/ })).toBeVisible();
    await expect(page.getByText("Mastered")).toHaveCount(0);
    await noOverflow(page);
    await capture(page, `checkpoint-passed-${width}-${theme}`);
  });
}

test("all six authored native input layouts", async ({ page }) => {
  const state = { resourceOpened: false, interactionAttempts: 0, interactionPassed: false, checkpointPassed: false, attemptId: 99 };
  await fixture(page, state);
  for (const type of Object.keys(interactionData)) {
    await page.goto(interactionRoute(type));
    await expect(page.getByRole("heading", { name: interactionData[type].title, level: 1 })).toBeVisible();
    await noOverflow(page);
    await capture(page, `interaction-${type}-initial`);
  }
});

test("learning surfaces remain operable at a 200% equivalent CSS viewport with reduced motion", async ({ page }) => {
  const state = { resourceOpened: false, interactionAttempts: 0, interactionPassed: true, checkpointPassed: false, attemptId: 99 };
  await fixture(page, state);
  await page.setViewportSize({ width: 720, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(lessonRoute);
  await expect(page.getByRole("heading", { name: "Find and protect work", level: 1 })).toBeVisible();
  await noOverflow(page);
  await capture(page, "zoom-200-lesson");
  await page.getByRole("button", { name: "View teaching card" }).click();
  await expect(page.getByRole("button", { name: "Close teaching card" })).toBeVisible();
  await noOverflow(page);
  await capture(page, "zoom-200-viewer");
  await page.keyboard.press("Escape");
  await page.goto(interactionRoute("ordering"));
  await expect(page.getByRole("button", { name: "Check answer" })).toBeVisible();
  await noOverflow(page);
  await capture(page, "zoom-200-interaction");
  await page.goto(checkpointRoute);
  await expect(page.getByRole("button", { name: "Submit answers" })).toBeVisible();
  await noOverflow(page);
  await capture(page, "zoom-200-checkpoint");
});
