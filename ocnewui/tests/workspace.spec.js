const { test, expect } = require("@playwright/test");
async function ready(page) {
  await page.goto("/");
  await expect(page.locator("#userFullName")).toHaveText("Dr. Sarah Chen, MD");
  await expect(page.locator("#authOverlay")).toBeHidden();
  await expect(page.locator("#badgePatientCount")).toHaveText("9");
}
async function role(page, value) {
  await page.selectOption("#devRoleSelect", value);
  await expect(page.locator("#userRoleBadge")).toHaveText(value);
}
test("shell loads without uncaught errors and renders all original view hooks", async ({
  page,
}) => {
  const errors = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await ready(page);
  await expect(page.locator(".workspace-view")).toHaveCount(10);
  await expect(page.locator("#environmentBanner")).toBeVisible();
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("");
  expect(errors).toEqual([]);
  await page.screenshot({
    path: "test-results/studio-desktop.png",
    fullPage: true,
  });
});
test("all ten workspaces load their local records", async ({ page }) => {
  await ready(page);
  await role(page, "ADMIN");
  const expectations = [
    ["view-patients", "#patientsTable tbody tr", "9"],
    ["view-encounters", "#encountersTableBody tr", "3"],
    ["view-radiology", "#radiologyTableBody tr", "2"],
    ["view-pharmacy", "#pharmacyTableBody tr", "1"],
    ["view-billing", "#invoicesTableBody tr", "2"],
  ];
  for (const [view, selector, count] of expectations) {
    await page.locator(`.side-nav-btn[data-view="${view}"]`).click();
    await expect(page.locator(selector)).toHaveCount(Number(count));
    expect(await page.locator("#" + view).innerText()).not.toContain(
      "Failed to load",
    );
  }
  for (const view of [
    "view-rag",
    "view-timeline",
    "view-audit",
    "view-portfolio",
    "view-ai-studio",
  ]) {
    await page.locator(`.side-nav-btn[data-view="${view}"]`).click();
    await expect(page.locator("#" + view)).toBeVisible();
  }
  await page.locator('[data-view="view-patients"]').click();
  await expect(page.locator("#patientsTable tbody tr")).toHaveCount(9);
  await page.screenshot({
    path: "test-results/patients-desktop.png",
    fullPage: true,
  });
});
test("role changes restrict navigation and prescribing controls", async ({
  page,
}) => {
  await ready(page);
  await role(page, "PHARMACIST");
  await expect(page.locator('[data-view="view-ai-studio"]')).toBeHidden();
  await expect(page.locator("#view-pharmacy")).toBeVisible();
  await expect(page.locator("#btnNewPrescription")).toBeHidden();
  await expect(page.locator("#btnReceiveStock")).toBeVisible();
  await role(page, "BILLING_CLERK");
  await expect(page.locator("#view-billing")).toBeVisible();
  await expect(page.locator('[data-view="view-radiology"]')).toBeHidden();
  await expect(page.locator('[data-view="view-audit"]')).toBeVisible();
});
test("command palette supports keyboard navigation", async ({ page }) => {
  await ready(page);
  await page.keyboard.press("Control+k");
  await expect(page.locator("#commandDialog")).toBeVisible();
  await page.fill("#commandInput", "registry");
  await page.keyboard.press("Enter");
  await expect(page.locator("#view-patients")).toBeVisible();
  await expect(page.locator("#commandDialog")).toBeHidden();
});
test("evidence tabs and the help dialog work", async ({ page }) => {
  await ready(page);
  await page.locator("#tab-explain").click();
  await expect(page.locator("#evidence-explain")).toBeVisible();
  await expect(page.locator("#heatmapEmpty")).toBeVisible();
  await page.locator("#tab-review").click();
  await expect(page.locator("#evidence-review")).toBeVisible();
  await page.locator("#studioHelp").click();
  await expect(page.locator("#guideDialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#guideDialog")).toBeHidden();
});
test("untrained models refuse without diagnostic probabilities, stale evidence, or heatmaps", async ({
  page,
}) => {
  await ready(page);
  await page.selectOption("#categorySelect", "breast");
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#top1ClassName")).toContainText("REFUSED");
  await expect(page.locator("#top1ConfidenceValue")).not.toContainText("%");
  await expect(page.locator("#probDistributionBars .prob-fill")).toHaveCount(0);
  await expect(page.locator("#ragCitationsContainer")).toBeEmpty();
  expect(await page.locator("#heatmapImage").getAttribute("src")).toBeNull();
  await page.selectOption("#categorySelect", "lymphoma");
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#calibrationNote")).toContainText("not deployed");
  await expect(page.locator("#calibrationNote")).not.toContainText("necrosis");
});
test("demo never fabricates a diagnostic result or review identifier", async ({
  page,
}) => {
  await ready(page);
  let dialog = "";
  page.on("dialog", async (d) => {
    dialog = d.message();
    await d.dismiss();
  });
  await page.locator("#executePipelineBtn").click();
  await expect
    .poll(() => dialog)
    .toContain("Diagnostic inference is not simulated");
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("");
  await page.locator("#tab-review").click();
  const reviewRequests = [];
  page.on("request", (r) => {
    if (r.url().includes("/predictions/")) reviewRequests.push(r.url());
  });
  await page.locator('[data-action="ACCEPT"]').click();
  await expect(page.locator("#toast")).toContainText("recorded prediction");
  expect(reviewRequests).toEqual([]);
});
test("patient search navigation does not keep a previous prediction", async ({
  page,
}) => {
  await ready(page);
  await page.selectOption("#categorySelect", "breast");
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#top1ClassName")).toContainText("REFUSED");
  await page.selectOption("#caseIdSelect", "MRN-2026-GI-004");
  await expect(page.locator("#contextName")).toHaveText("Arthur Pendleton");
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("");
  await expect(page.locator("#aggregateDecisionBadge")).toHaveText(
    "AWAITING INPUT",
  );
});
test("local patient creation persists across reload", async ({ page }) => {
  await ready(page);
  await page.locator('[data-view="view-patients"]').click();
  await page.locator("#btnOpenNewPatientModal").click();
  await expect(page.locator("#newPatientModal")).toBeVisible();
  await page.fill("#newMrn", "MRN-DEMO-TEST");
  await page.fill("#newGivenName", "Test");
  await page.fill("#newFamilyName", "Patient");
  await page.fill("#newBirthDate", "1990-01-01");
  await page.locator('#newPatientForm button[type="submit"]').click();
  await expect(page.locator("#badgePatientCount")).toHaveText("10");
  await page.reload();
  await expect(page.locator("#badgePatientCount")).toHaveText("10");
  const created = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("onco.demo.database.v1")).patients.find(
      (p) => p.mrn === "MRN-DEMO-TEST",
    ),
  );
  expect(created.consent.research_opt_in).toBe(false);
  expect(created.consent.ai_decision_support_consent).toBe(false);
});
test("local allergy safety gate rejects contraindicated prescription", async ({
  page,
}) => {
  await ready(page);
  const result = await page.evaluate(async () => {
    const r = await fetch("/api/v2/hms/pharmacy/prescriptions", {
      method: "POST",
      body: JSON.stringify({
        patient_id: "patient-1",
        medication_id: "med-2",
        quantity: 10,
      }),
    });
    return { status: r.status, data: await r.json() };
  });
  expect(result.status).toBe(409);
  expect(result.data.detail).toContain("Allergy safety gate");
});
test("payment updates invoice balance and balanced ledger", async ({
  page,
}) => {
  await ready(page);
  await role(page, "ADMIN");
  await page.locator('[data-view="view-billing"]').click();
  await page.locator(".btn-pay-inv").first().click();
  await expect(page.locator("#hmsActionModal")).toBeVisible();
  await page.fill("#payAmountInput", "100");
  await page.locator('#modalPayInvoiceForm button[type="submit"]').click();
  await expect(page.locator("#finOutstanding")).toHaveText("$550.00");
  await expect(page.locator("#ledgerBalanceStatusBanner")).toContainText(
    "Balanced",
  );
});
test("mobile navigation and viewport avoid horizontal page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.locator("#mobileMenu").click();
  await expect(page.locator("#appSidebar")).toBeInViewport();
  await page.locator('[data-view="view-patients"]').click();
  await expect(page.locator("#view-patients")).toBeVisible();
  await expect(page.locator("#mobileMenu")).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/patients-mobile.png",
    fullPage: true,
  });
});
test("live mode preserves analyze payload and renders backend-only evidence", async ({
  page,
}) => {
  await page.addInitScript(() => {
    localStorage.setItem("onco.mode", "live");
    localStorage.setItem("oncosentinel_jwt", "test-jwt");
  });
  let submitted;
  await page.route("**/api/v2/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    let data = { items: [] };
    if (p.endsWith("/auth/me"))
      data = {
        id: "u1",
        full_name: "Test Clinician",
        username: "test",
        role: "CLINICIAN",
        department: "Oncology",
      };
    if (p.endsWith("/patients/query"))
      data = {
        items: [
          {
            id: "p1",
            mrn: "MRN-2026-KD-001",
            given_name: "Eleanor",
            family_name: "Vance",
            birth_date: "1957-04-16",
          },
        ],
      };
    if (p.endsWith("/training/queue"))
      data = {
        tasks: [
          { task_id: "kidney", is_active: true },
          { task_id: "breast", is_active: false },
        ],
      };
    if (p.endsWith("/analyze")) {
      submitted = route.request().postDataJSON();
      data = {
        prediction_id: "real-test-prediction",
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
          reasons: ["Review required"],
        },
        explanation: {
          confidence_narrative: "Test backend response",
          model_evidence_section: "Backend model evidence",
          why: [],
        },
        rag_response: "No matching guideline found",
        cited_sources: [],
      };
    }
    if (p.endsWith("/review")) data = { timestamp: "2026-11-01T12:00:00Z" };
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  });
  await page.goto("/");
  await expect(page.locator("#authOverlay")).toBeHidden();
  await expect(page.locator("#userFullName")).toHaveText("Test Clinician");
  await expect(page.locator("#platformPhaseText")).toHaveText(
    "1 of 2 models active",
  );
  await page.locator("#executePipelineBtn").click();
  await expect(page.locator("#top1ConfidenceValue")).toHaveText("81.0%");
  expect(submitted.category_hint).toBe("kidney");
  expect(submitted.case_id).toBe("MRN-2026-KD-001");
  expect(submitted.patient_context.case_id).toBe("MRN-2026-KD-001");
  expect(submitted).toHaveProperty("image_b64");
  expect(submitted).toHaveProperty("text_query");
  expect(submitted.modality).toBe("ct");
  expect(await page.locator("#heatmapImage").getAttribute("src")).toBeNull();
  await expect(page.locator("#metricFidelity")).toHaveText("Not reported");
  await page.locator("#tab-review").click();
  await page.locator('[data-action="ACCEPT"]').click();
  await expect(page.locator("#reviewConfirmationBanner")).toBeVisible();
});
test("live RAG refuses ungrounded text without citations", async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem("onco.mode", "live");
    localStorage.setItem("oncosentinel_jwt", "test-jwt");
  });
  await page.route("**/api/v2/**", async (route) => {
    const p = new URL(route.request().url()).pathname;
    const data = p.endsWith("/auth/me")
      ? { full_name: "Test", username: "test", role: "CLINICIAN" }
      : p.endsWith("/analyze")
        ? {
            safety_state: "PASS",
            rag_response: "Ungrounded test answer",
            cited_sources: [],
          }
        : p.endsWith("/training/queue")
          ? { tasks: [] }
          : { items: [] };
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify(data),
    });
  });
  await page.goto("/");
  await expect(page.locator("#authOverlay")).toBeHidden();
  await page.locator('[data-view="view-rag"]').click();
  await page.fill("#ragSearchInput", "test query");
  await page.locator('#ragQueryForm button[type="submit"]').click();
  await expect(page.locator("#ragResultsArea")).toContainText(
    "No matching guideline found",
  );
  await expect(page.locator("#ragResultsArea")).not.toContainText("(VERIFIED)");
});
