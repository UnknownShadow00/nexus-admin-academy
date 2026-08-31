import { expect, test } from "@playwright/test";

const modules = [
  {
    key: "module.aplus.core1.network_services_troubleshooting",
    title: "Network Services, Devices, Wireless & Troubleshooting",
    lessons: 7,
    resources: [8, 4],
  },
  {
    key: "module.aplus.core1.hardware_fault_isolation",
    title: "PC Hardware, Displays & Fault Isolation",
    lessons: 6,
    resources: [12, 3],
  },
  {
    key: "module.aplus.core1.printers_mfds",
    title: "Printers, MFDs & Print Troubleshooting",
    lessons: 5,
    resources: [6, 9],
    serviceDesk: true,
  },
  {
    key: "module.aplus.core1.virtualization_cloud_foundations",
    title: "Virtualization & Cloud Foundations",
    lessons: 5,
    resources: [5, 3],
    serviceDesk: false,
  },
  {
    key: "module.aplus.core2.windows_admin_cli_networking",
    title: "Windows Administration, Command Line & Client Networking",
    lessons: 6,
    resources: [6, 4],
  },
  {
    key: "module.aplus.core2.cross_platform_app_cloud_support",
    title: "Cross-Platform Desktop, Applications & Cloud Productivity Support",
    lessons: 6,
    resources: [6, 3],
  },
];

async function apiData(page, path, options) {
  return page.evaluate(
    async ({ path: requestPath, options: requestOptions }) => {
      const response = await fetch(requestPath, requestOptions);
      return { status: response.status, body: await response.json() };
    },
    { path, options },
  );
}

async function navigate(page, path) {
  await page.evaluate((target) => {
    window.history.pushState({}, "", target);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

test("reviewed Modules 7-12 render and resolve every authored V2 activity", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/login?next=/learning-v2");
  await page.getByLabel("Username").fill(process.env.NEXUS_E2E_STUDENT_USERNAME);
  await page.getByLabel("Password").fill(process.env.NEXUS_E2E_STUDENT_PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: "CompTIA A+" })).toBeVisible();
  await expect(page).toHaveURL((url) => url.pathname === "/learning-v2");

  const visibleTitles = await page.locator('section[aria-labelledby="modules-heading"] h3').allTextContents();
  const module6 = visibleTitles.indexOf("Module 6 — Mobile Device Hardware, Connectivity & Troubleshooting");
  for (const module of modules) {
    expect(visibleTitles).toContain(module.title);
  }
  expect(
    visibleTitles.indexOf("Windows Administration, Command Line & Client Networking"),
  ).toBeLessThan(
    visibleTitles.indexOf("Cross-Platform Desktop, Applications & Cloud Productivity Support"),
  );

  for (const expected of modules) {
    await navigate(page, `/learning-v2/modules/${expected.key}`);
    await expect(page.getByRole("heading", { name: expected.title, exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: /Take the quiz/ })).toBeVisible();
    await expect(page.getByRole("link", { name: /Open practical/ })).toBeVisible();
    if (expected.serviceDesk !== false) {
      await expect(page.getByRole("link", { name: /Troubleshoot a ticket/ })).toBeVisible();
    }
    await expect(page.getByRole("link", { name: /Open Explain/ })).toBeVisible();

    const moduleResponse = await apiData(page, `/api/v2/curriculum/modules/${expected.key}`);
    expect(moduleResponse.status).toBe(200);
    const module = moduleResponse.body.data;
    expect(module.lessons).toHaveLength(expected.lessons);
    expect(module.lessons.every((lesson) => lesson.quick_check)).toBe(true);
    const resourceLinks = [
      ...module.lessons.flatMap((lesson) => lesson.resources),
      ...module.module_resources,
    ];
    expect(resourceLinks.filter((resource) => resource.required)).toHaveLength(expected.resources[0]);
    expect(resourceLinks.filter((resource) => !resource.required)).toHaveLength(expected.resources[1]);
    if (module.module_resources.length) {
      await expect(page.getByRole("heading", { name: "Module resources" })).toBeVisible();
    }

    const firstLesson = module.lessons[0];
    await navigate(page, `/learning-v2/modules/${expected.key}/lessons/${firstLesson.key}`);
    await expect(
      page.locator("header").getByRole("heading", { name: firstLesson.title, exact: true }),
    ).toBeVisible();
    await expect(page.getByText("Watch / read", { exact: true })).toBeVisible();
    await expect(page.getByRole("link", { name: "Start Quick Check" })).toBeVisible();
    if (firstLesson.resources.some((resource) => resource.required)) {
      await expect(page.getByText("Required", { exact: true }).first()).toBeVisible();
    }
    if (firstLesson.resources.some((resource) => !resource.required)) {
      await expect(page.getByText("Optional", { exact: true }).first()).toBeVisible();
    }

    const quickCheck = await apiData(
      page,
      `/api/v2/curriculum/modules/${expected.key}/assessments/${firstLesson.quick_check.key}`,
    );
    expect(quickCheck.status).toBe(200);
    expect(quickCheck.body.data.questions).toHaveLength(4);
    expect(quickCheck.body.data.questions.every((question) => !("correct_answer" in question))).toBe(true);

    const quiz = module.assessments.find((assessment) => assessment.role === "module_quiz");
    const moduleQuiz = await apiData(
      page,
      `/api/v2/curriculum/modules/${expected.key}/assessments/${quiz.key}`,
    );
    expect(moduleQuiz.status).toBe(200);
    expect(moduleQuiz.body.data.questions).toHaveLength(12);
    expect(new Set(moduleQuiz.body.data.questions.map((question) => question.id)).size).toBe(12);

    const practical = module.assessments.find((assessment) => assessment.role === "practical");
    expect(practical.available).toBe(true);
    expect(practical.lab_id).toBeTruthy();
    const prompt = module.explain_prompts[0];
    await navigate(page, `/learning-v2/modules/${expected.key}/explain/${prompt.key}`);
    await expect(page.getByRole("heading", { name: "Put it in your own words" })).toBeVisible();
    await expect(page.getByLabel("Your response")).toBeVisible();

    const serviceDesk = module.assessments.find((assessment) => assessment.role === "service_desk");
    expect(Boolean(serviceDesk)).toBe(expected.serviceDesk !== false);
    if (serviceDesk) {
      const launch = await page.request.post(
        `/api/v2/curriculum/modules/${expected.key}/service-desk/${serviceDesk.key}/launch`,
        {
          headers: {
            Origin: process.env.NEXUS_E2E_BASE_URL,
            Referer: `${process.env.NEXUS_E2E_BASE_URL}/learning-v2/modules/${expected.key}`,
          },
        },
      );
      expect(launch.status()).toBe(200);
      expect((await launch.json()).data.launch_url).toContain("/service-desk/tickets/");
    }
  }
});

test("mentor selector includes Modules 7-12 and student auth cannot read it", async ({ page }) => {
  const apiUrl = process.env.NEXUS_E2E_API_URL;
  const studentLogin = await page.request.post(`${apiUrl}/auth/login`, {
    data: {
      username: process.env.NEXUS_E2E_STUDENT_USERNAME,
      password: process.env.NEXUS_E2E_STUDENT_PASSWORD,
    },
  });
  const studentToken = (await studentLogin.json()).access_token;
  const denied = await page.request.get(
    `${apiUrl}/api/admin/v2/mentor/cohort/${modules[0].key}`,
    { headers: { Authorization: `Bearer ${studentToken}` } },
  );
  expect(denied.status()).toBe(403);

  await page.goto("/admin-login?redirect=%2Fadmin%2Fv2-progress");
  await page.getByLabel("Username").fill(process.env.NEXUS_E2E_ADMIN_USERNAME);
  await page.getByLabel("Password").fill(process.env.NEXUS_E2E_ADMIN_PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page).toHaveURL(/\/admin\/v2-progress$/);
  const selector = page.getByLabel("Module", { exact: true });
  for (const module of modules) {
    await expect(selector.locator(`option[value="${module.key}"]`)).toHaveText(module.title);
  }
});

test("Modules 11 and 12 reveal all three progressive Service Desk hints", async ({ page }) => {
  test.setTimeout(90000);
  await page.goto("/login?next=/learning-v2");
  await page.getByLabel("Username").fill(process.env.NEXUS_E2E_STUDENT_USERNAME);
  await page.getByLabel("Password").fill(process.env.NEXUS_E2E_STUDENT_PASSWORD);
  await page.getByRole("button", { name: "Login" }).click();
  await expect(page.getByRole("heading", { name: "CompTIA A+" })).toBeVisible();

  for (const expected of modules.slice(-2)) {
    const moduleResponse = await apiData(page, `/api/v2/curriculum/modules/${expected.key}`);
    const assessment = moduleResponse.body.data.assessments.find(
      (item) => item.role === "service_desk",
    );
    const launch = await page.request.post(
      `/api/v2/curriculum/modules/${expected.key}/service-desk/${assessment.key}/launch`,
      {
        headers: {
          Origin: process.env.NEXUS_E2E_BASE_URL,
          Referer: `${process.env.NEXUS_E2E_BASE_URL}/learning-v2/modules/${expected.key}`,
        },
      },
    );
    expect(launch.status()).toBe(200);
    await page.goto((await launch.json()).data.launch_url);
    await page.getByRole("button", { name: /I don't know how to fix this/i }).click();
    await expect(page.getByRole("heading", { name: "How to resolve this" })).toBeVisible();
    const steps = page.getByRole("dialog").locator("ol > li");
    await expect(steps).toHaveCount(1);
    await page.getByRole("button", { name: "Reveal next step (1/3)" }).click();
    await expect(steps).toHaveCount(2);
    await page.getByRole("button", { name: "Reveal next step (2/3)" }).click();
    await expect(steps).toHaveCount(3);
    await expect(page.getByText("All 3 steps revealed")).toBeVisible();
  }
});
