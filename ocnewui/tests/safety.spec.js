const { test, expect } = require("@playwright/test");
const { AxeBuilder } = require("@axe-core/playwright");
async function live(page, analyze) {
  await page.addInitScript(() => {
    localStorage.setItem("onco.mode", "live");
    localStorage.setItem("oncosentinel_jwt", "test-jwt");
  });
  await page.route("**/api/v2/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    if (p.endsWith("/analyze")) return analyze(route);
    const data = p.endsWith("/auth/me")
      ? { full_name: "Test Clinician", username: "test", role: "CLINICIAN" }
      : p.endsWith("/training/queue")
        ? { tasks: [] }
        : {
            items: [
              {
                id: "p1",
                mrn: "MRN-2026-KD-001",
                given_name: "Eleanor",
                family_name: "Vance",
              },
              {
                id: "p2",
                mrn: "MRN-2026-OR-002",
                given_name: "Robert",
                family_name: "Kovacs",
              },
            ],
          };
    return route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  });
  await page.goto("/");
  await expect(page.locator("#userFullName")).toHaveText("Test Clinician");
  await expect(page.locator("#caseIdSelect option")).toHaveCount(3);
}
const prediction = {
  prediction_id: "backend-prediction",
  category: "kidney",
  route: "ML_INFERENCE",
  safety_state: "REVIEW",
  top1_class: "tumor",
  top1_confidence: 0.81,
  calibrated_probabilities: { tumor: 0.81, normal: 0.19 },
  uncertainty: {
    predictive_uncertainty: 0.32,
    ood_score: 0.1,
    data_uncertainty: 0.08,
  },
  explanation: { why: [], model_evidence_section: "Test backend result" },
  cited_sources: ["Test citation"],
};
test("initial Studio has no automated WCAG A/AA violations", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("#badgePatientCount")).toHaveText("9");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(results.violations).toEqual([]);
});
test("a late backend response cannot overwrite a newly selected case", async ({
  page,
}) => {
  let release,
    entered = false;
  const gate = new Promise((resolve) => (release = resolve));
  await live(page, async (route) => {
    entered = true;
    await gate;
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(prediction),
    });
  });
  await page.locator("#executePipelineBtn").click();
  await expect.poll(() => entered).toBe(true);
  await page.selectOption("#caseIdSelect", "MRN-2026-OR-002");
  release();
  await expect(page.locator("#executePipelineBtn")).toBeEnabled();
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("");
  await expect(page.locator("#aggregateDecisionBadge")).toHaveText(
    "AWAITING INPUT",
  );
  await expect(page.locator("#contextName")).toHaveText("Robert Kovacs");
  await expect(page.locator("#imagePreviewContainer")).toBeHidden();
});
test("untrained refusal after a successful prediction clears previous evidence and review target", async ({
  page,
}) => {
  await live(page, (route) =>
    route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(prediction),
    }),
  );
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("81.0%");
  await expect(page.locator("#ragCitationsContainer")).toContainText(
    "Test citation",
  );
  await page.selectOption("#categorySelect", "breast");
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#top1ClassName")).toContainText("REFUSED");
  await expect(page.locator("#ragCitationsContainer")).toBeEmpty();
  await page.locator("#tab-review").click();
  await page.locator('[data-action="ACCEPT"]').click();
  await expect(page.locator("#toast")).toContainText("recorded prediction");
});
test("an unavailable live backend never falls back to fictional data", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem("onco.mode", "live");
    localStorage.setItem("oncosentinel_jwt", "test-jwt");
  });
  await page.route("**/api/v2/**", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator("#authOverlay")).toBeVisible();
  await expect(page.locator("#environmentBanner")).toBeHidden();
  expect(
    await page.evaluate(() => localStorage.getItem("onco.demo.database.v1")),
  ).toBeNull();
});
