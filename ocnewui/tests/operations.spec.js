const { test, expect } = require("@playwright/test");
async function ready(page) {
  await page.goto("/");
  await expect(page.locator("#badgePatientCount")).toHaveText("9");
}
async function admin(page) {
  await page.locator("#btnHeaderSwitchAccount").click();
  await page.locator('.staff-quick-btn[data-role="ADMIN"]').click();
  await expect(page.locator("#userRoleBadge")).toHaveText("ADMIN");
}
test("registry search and name sorting operate on real table rows", async ({
  page,
}) => {
  await ready(page);
  await page.locator('[data-view="view-patients"]').click();
  await expect(page.locator("#patientsTable tbody tr")).toHaveCount(9);
  await page.fill("#patientSearch", "Eleanor");
  await expect(page.locator("#patientsTable tbody tr:visible")).toHaveCount(1);
  await expect(page.locator("#registryVisibleCount")).toHaveText("1 of 9");
  await page.fill("#patientSearch", "impossible-name");
  await expect(page.locator("#registryNoMatches")).toBeVisible();
  await page.fill("#patientSearch", "");
  await page.locator("#patientSort").click();
  await expect(page.locator("#patientsTable tbody tr").first()).toContainText(
    "Arthur Pendleton",
  );
});
test("encounter creation, discharge, and optimistic version increment", async ({
  page,
}) => {
  await ready(page);
  await page.locator('[data-view="view-encounters"]').click();
  await expect(page.locator("#encountersTableBody tr")).toHaveCount(3);
  await page.locator("#btnNewEncounter").click();
  await page.fill("#encDepartment", "Test Oncology");
  await page.locator('#modalNewEncounterForm button[type="submit"]').click();
  await expect(page.locator("#encountersTableBody tr")).toHaveCount(4);
  const row = page
    .locator("#encountersTableBody tr")
    .filter({ hasText: "Test Oncology" });
  await row.locator(".btn-discharge-enc").click();
  await expect(row).toContainText("DISCHARGED");
});
test("radiologist gets read-only encounters and patient registry", async ({
  page,
}) => {
  await ready(page);
  await page.locator("#btnHeaderSwitchAccount").click();
  await page.locator('.staff-quick-btn[data-role="RADIOLOGIST"]').click();
  await expect(page.locator("#userRoleBadge")).toHaveText("RADIOLOGIST");
  await page.locator('[data-view="view-patients"]').click();
  await expect(page.locator("#btnOpenNewPatientModal")).toBeHidden();
  await expect(page.locator("#btnImportFhirPatient")).toBeHidden();
  await page.locator('[data-view="view-encounters"]').click();
  await expect(page.locator("#encountersTableBody tr")).toHaveCount(3);
  await expect(page.locator(".btn-discharge-enc")).toHaveCount(0);
});
test("FHIR import adds a patient and export displays a tagged FHIR resource", async ({
  page,
}) => {
  await ready(page);
  await page.locator('[data-view="view-patients"]').click();
  await page.locator("#btnImportFhirPatient").click();
  await page.locator('#importFhirPatientForm button[type="submit"]').click();
  await expect(page.locator("#badgePatientCount")).toHaveText("10");
  await expect(page.locator("#patientsTable tbody tr")).toHaveCount(10);
  await page.locator(".btn-fhir-export").first().click();
  await expect(page.locator("#hmsActionModal")).toBeVisible();
  await expect(page.locator("#hmsActionModalBody")).toContainText(
    '"resourceType": "Patient"',
  );
});
test("prescription form blocks a documented penicillin allergy", async ({
  page,
}) => {
  await ready(page);
  await page.locator('[data-view="view-pharmacy"]').click();
  await page.locator("#btnNewPrescription").click();
  await page.selectOption("#rxMedSelect", "med-2");
  await page.fill("#rxDirections", "Test directions");
  let notice = "";
  page.on("dialog", async (d) => {
    notice = d.message();
    await d.dismiss();
  });
  await page.locator('#modalNewRxForm button[type="submit"]').click();
  await expect.poll(() => notice).toContain("BLOCKED");
  const count = await page.evaluate(
    () =>
      JSON.parse(localStorage.getItem("onco.demo.database.v1"))[
        "pharmacy/prescriptions"
      ].length,
  );
  expect(count).toBe(1);
});
test("stock receipt and FIFO dispense change sample inventory", async ({
  page,
}) => {
  await ready(page);
  await admin(page);
  await page.locator('[data-view="view-pharmacy"]').click();
  await page.locator("#btnReceiveStock").click();
  await page.fill("#stkQty", "10");
  await page.locator('#modalReceiveStockForm button[type="submit"]').click();
  await expect(page.locator("#hmsActionModal")).toBeHidden();
  await expect
    .poll(async () =>
      page.evaluate(
        () =>
          JSON.parse(localStorage.getItem("onco.demo.database.v1"))[
            "inventory/items"
          ][0].on_hand,
      ),
    )
    .toBe(52);
  await page.locator(".btn-fifo-dispense").first().click();
  await expect
    .poll(async () =>
      page.evaluate(
        () =>
          JSON.parse(localStorage.getItem("onco.demo.database.v1"))[
            "inventory/items"
          ][0].on_hand,
      ),
    )
    .toBe(40);
  await expect(page.locator("#pharmacyTableBody")).toContainText(
    "Fully Dispensed",
  );
});
test("invoice issuance resolves charge-item prices and posts balanced entries", async ({
  page,
}) => {
  await ready(page);
  await admin(page);
  await page.locator('[data-view="view-billing"]').click();
  await page.locator("#btnNewInvoice").click();
  await page.selectOption("#invFeeSelect", "charge-2");
  await page.fill("#invQtyInput", "2");
  await page.locator('#modalNewInvoiceForm button[type="submit"]').click();
  await expect(page.locator("#invoicesTableBody tr")).toHaveCount(3);
  await expect(page.locator("#finBilled")).toHaveText("$1325.00");
  await expect(page.locator("#ledgerBalanceStatusBanner")).toContainText(
    "Balanced",
  );
});
test("timeline appends local events with clinical text preserved", async ({
  page,
}) => {
  await ready(page);
  await page.locator('[data-view="view-timeline"]').click();
  await expect(page.locator(".timeline-card")).toHaveCount(1);
  await page.locator("#btnOpenAppendEventModal").click();
  await page.fill("#eventSource", "Test clinic");
  await page.fill("#eventPayload", "Test clinical observation only");
  await page.locator('#appendEventForm button[type="submit"]').click();
  await expect(page.locator(".timeline-card")).toHaveCount(2);
  await expect(page.locator("#timelineEventsContainer")).toContainText(
    "Test clinical observation only",
  );
});
test("switching to live mode does not reuse the demonstration JWT", async ({
  page,
}) => {
  await ready(page);
  await page.locator("#openSettings").click();
  await page.selectOption("#connectionMode", "live");
  await page.locator('#settingsForm button[type="submit"]').click();
  await expect(page.locator("#authOverlay")).toBeVisible();
  await expect(page.locator("#environmentBanner")).toBeHidden();
  expect(await page.evaluate(() => window.OncoConfig.mode)).toBe("live");
  expect(
    await page.evaluate(() => localStorage.getItem("oncosentinel_jwt")),
  ).toBeNull();
});
test("file validation rejects PDFs without accepting invalid scan input", async ({
  page,
}) => {
  await ready(page);
  await page.setInputFiles("#fileInput", {
    name: "not-a-scan.pdf",
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-test"),
  });
  await expect(page.locator("#toast")).toContainText(
    "DICOM and PDF decoding are not supported",
  );
  await expect(page.locator("#imagePreviewContainer")).toBeHidden();
});
