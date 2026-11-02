/* Transport boundary: explicit local demonstration OR real backend. Never falls back to demo. */
(() => {
  "use strict";
  const nativeFetch = window.fetch.bind(window);
  const config = window.OncoConfig;
  const key = "onco.demo.database.v1";
  const now = () => new Date().toISOString();
  const id = () => crypto.randomUUID();
  const accounts = {
    CLINICIAN: {
      full_name: "Dr. Sarah Chen, MD",
      username: "dr_chen",
      department: "Medical Oncology",
    },
    RADIOLOGIST: {
      full_name: "Dr. Rajesh Patel, MD",
      username: "dr_patel",
      department: "Diagnostic Radiology",
    },
    PHARMACIST: {
      full_name: "Alex Rivera, PharmD",
      username: "alex_rivera",
      department: "Oncology Pharmacy",
    },
    BILLING_CLERK: {
      full_name: "Mark Davis, CRCR",
      username: "mark_davis",
      department: "Patient Financial Services",
    },
    ADMIN: {
      full_name: "Clara Vance, MHA",
      username: "clara_vance",
      department: "Hospital Administration",
    },
  };
  function user(role = "CLINICIAN") {
    return {
      display_name: accounts[role].full_name,
      id: "staff-" + role.toLowerCase(),
      role,
      ...accounts[role],
      email: accounts[role].username + "@example.test",
    };
  }
  function seed() {
    const names = [
      ["Eleanor", "Vance", "KD-001", "1957-04-16", "female", "kidney"],
      ["Robert", "Kovacs", "OR-002", "1964-08-22", "male", "oral"],
      ["Maria", "Santos", "BR-003", "1978-02-11", "female", "breast"],
      ["Arthur", "Pendleton", "GI-004", "1959-11-03", "male", "colon"],
      ["David", "Zhao", "LK-005", "1994-06-17", "male", "all_leukemia"],
      ["Elena", "Rostova", "BN-006", "1982-03-09", "female", "brain"],
      ["Marcus", "Vance", "LY-007", "1971-12-05", "male", "lymphoma"],
      ["Priya", "Nair", "CX-008", "1985-05-24", "female", "cervical"],
      ["Samuel", "Okafor", "LG-009", "1966-09-12", "male", "lung"],
    ];
    const patients = names.map(
      ([given_name, family_name, mrn, birth_date, gender, category], i) => ({
        id: "patient-" + (i + 1),
        mrn: "MRN-2026-" + mrn,
        given_name,
        family_name,
        birth_date,
        gender,
        category,
        version: 1,
        consent: { research_opt_in: false, consent_tier: "Clinical care" },
        insurance: {
          payer: "Sample Health Plan",
          policy_id: "DEMO-" + (1000 + i),
        },
        created_at: now(),
        extra: { demonstration: true },
      }),
    );
    const enc = (n, p, department) => ({
      id: "encounter-" + n,
      patient_id: "patient-" + p,
      department,
      attending_id: "staff-clinician",
      status: "active",
      started_at: "2026-11-01T08:30:00Z",
      version: 1,
      extra: { readable_id: "ENC-2026-00" + n },
    });
    const data = {
      patients,
      staff: Object.keys(accounts).map((r) => user(r)),
      encounters: [
        enc(1, 1, "Medical Oncology"),
        enc(2, 2, "Head & Neck Oncology"),
        enc(3, 4, "Gastrointestinal Oncology"),
      ],
      "medical-records": [
        {
          id: "record-1",
          patient_id: "patient-1",
          encounter_id: "encounter-1",
          kind: "allergy",
          content: {
            allergen: "PENICILLIN",
            reaction: "Urticaria",
            severity: "high",
            note: "Fictional allergy record for interaction testing.",
          },
          actor_id: "staff-clinician",
          created_at: "2026-10-29T10:00:00Z",
          version: 1,
        },
        {
          id: "record-2",
          patient_id: "patient-4",
          encounter_id: "encounter-3",
          kind: "allergy",
          content: {
            allergen: "SULFA",
            reaction: "Rash",
            severity: "moderate",
          },
          actor_id: "staff-clinician",
          created_at: "2026-10-30T09:00:00Z",
          version: 1,
        },
      ],
      "scheduling/appointments": [
        {
          id: "appointment-1",
          patient_id: "patient-1",
          provider_id: "staff-clinician",
          start: "2026-11-03T09:00:00Z",
          end: "2026-11-03T09:30:00Z",
          status: "booked",
          kind: "Imaging follow-up",
          version: 1,
        },
      ],
      "radiology/studies": [
        {
          id: "study-1",
          name: "Abdomen & pelvis, contrast-enhanced",
          modality: "CT",
          body_site: "abdomen",
          version: 1,
        },
        {
          id: "study-2",
          name: "Brain, with and without contrast",
          modality: "MRI",
          body_site: "brain",
          version: 1,
        },
      ],
      "radiology/orders": [
        {
          id: "order-1",
          patient_id: "patient-1",
          encounter_id: "encounter-1",
          study_id: "study-1",
          priority: "urgent",
          status: "acquired",
          version: 1,
          extra: { readable_id: "RAD-0001" },
        },
        {
          id: "order-2",
          patient_id: "patient-6",
          encounter_id: "encounter-2",
          study_id: "study-2",
          priority: "routine",
          status: "ordered",
          version: 1,
          extra: { readable_id: "RAD-0002" },
        },
      ],
      "radiology/reports": [],
      "lab/tests": [
        {
          id: "test-1",
          name: "Complete blood count",
          code: "CBC",
          unit: "panel",
          reference_range: "Per analyte",
          version: 1,
        },
        {
          id: "test-2",
          name: "Comprehensive metabolic panel",
          code: "CMP",
          unit: "panel",
          reference_range: "Per analyte",
          version: 1,
        },
      ],
      "lab/orders": [
        {
          id: "laborder-1",
          patient_id: "patient-1",
          encounter_id: "encounter-1",
          test_id: "test-2",
          status: "ordered",
          priority: "routine",
          version: 1,
        },
      ],
      "lab/results": [],
      alerts: [
        {
          id: "alert-1",
          resource_id: "patient-1",
          kind: "review",
          severity: "high",
          message:
            "Demonstration: diagnostic imaging awaiting specialist review.",
          created_at: "2026-11-01T08:45:00Z",
          version: 1,
        },
      ],
      "pharmacy/medications": [
        {
          id: "med-1",
          name: "Ondansetron",
          strength: "8 mg",
          route: "oral",
          drug_class: "5-HT3 antagonist",
          code: "DEMO-OND",
          version: 1,
        },
        {
          id: "med-2",
          name: "Amoxicillin",
          strength: "500 mg",
          route: "oral",
          drug_class: "PENICILLIN",
          code: "DEMO-AMX",
          version: 1,
        },
        {
          id: "med-3",
          name: "Paracetamol",
          strength: "500 mg",
          route: "oral",
          drug_class: "Analgesic",
          version: 1,
        },
      ],
      "pharmacy/prescriptions": [
        {
          id: "prescription-1",
          patient_id: "patient-1",
          encounter_id: "encounter-1",
          medication_id: "med-1",
          quantity: 12,
          refills: 0,
          directions:
            "Sample prescription: 8 mg orally as directed by prescriber.",
          prescriber_id: "staff-clinician",
          extra: { allergy_check_passed: true },
          version: 1,
        },
      ],
      "pharmacy/dispense": [],
      "inventory/items": [
        {
          id: "item-1",
          name: "Ondansetron 8 mg",
          medication_id: "med-1",
          sku: "OND-008",
          unit: "tablet",
          on_hand: 42,
          reorder_point: 20,
          version: 1,
        },
        {
          id: "item-2",
          name: "Amoxicillin 500 mg",
          medication_id: "med-2",
          sku: "AMX-500",
          unit: "capsule",
          on_hand: 86,
          reorder_point: 30,
          version: 1,
        },
      ],
      "inventory/movements": [],
      "billing/charge-items": [
        {
          id: "charge-1",
          code: "CT-ABD",
          name: "Diagnostic imaging",
          amount: 650,
          version: 1,
        },
        {
          id: "charge-2",
          code: "CONSULT",
          name: "Specialist consultation",
          amount: 225,
          version: 1,
        },
      ],
      "inventory/lots": [
        {
          id: "lot-1",
          item_id: "item-1",
          lot_number: "DEMO-LOT-A",
          quantity: 42,
          on_hand: 42,
          expires_on: "2028-06-30",
          received_at: "2026-10-01T10:00:00Z",
          version: 1,
        },
      ],
      "billing/invoices": [
        {
          id: "invoice-1",
          number: "INV-2026-001",
          patient_id: "patient-1",
          encounter_id: "encounter-1",
          total: 650,
          outstanding: 650,
          status: "issued",
          due_date: "2026-11-15",
          lines: [
            {
              code: "CT-ABD",
              description: "Diagnostic imaging",
              quantity: 1,
              amount: 650,
            },
          ],
          version: 1,
        },
        {
          id: "invoice-2",
          number: "INV-2026-002",
          patient_id: "patient-2",
          encounter_id: "encounter-2",
          total: 225,
          outstanding: 0,
          status: "paid",
          due_date: "2026-11-10",
          lines: [
            {
              code: "CONSULT",
              description: "Specialist consultation",
              quantity: 1,
              amount: 225,
            },
          ],
          version: 1,
        },
      ],
      "billing/payments": [
        {
          id: "payment-1",
          invoice_id: "invoice-2",
          amount: 225,
          method: "card",
          reference: "DEMO-PAID",
          version: 1,
        },
      ],
      "ai/reviews": [],
      reviews: [],
      audit: [],
      events: {},
      ledger: [
        {
          transaction_id: "demo-invoice-1",
          account: "Accounts receivable",
          debit: 650,
          credit: 0,
          posted_at: "2026-11-01T09:00:00Z",
        },
        {
          transaction_id: "demo-invoice-1",
          account: "Service revenue",
          debit: 0,
          credit: 650,
          posted_at: "2026-11-01T09:00:00Z",
        },
      ],
    };
    data.audit = [
      {
        event_id: "demo-seed",
        timestamp: now(),
        actor: "system-demo",
        actor_role: "ADMIN",
        action: "DEMONSTRATION_INITIALIZED",
        resource: "Local sample database",
        patient_id: null,
        extra: { demonstration: true },
      },
    ];
    for (const p of patients)
      data.events[p.mrn] = [
        {
          event_id: "event-" + p.id,
          event_type: "PATIENT_REGISTERED",
          timestamp: "2026-10-29T08:00:00Z",
          title: "Patient registered",
          narrative: "Fictional record in the local demonstration workspace.",
          provenance: "Local demonstration fixture",
          actor: "Sample registration",
          source: "demo",
          version: 1,
        },
      ];
    return data;
  }
  let db;
  function database() {
    if (db) return db;
    try {
      db = JSON.parse(localStorage.getItem(key));
    } catch {}
    if (!db) {
      db = seed();
      save();
    }
    return db;
  }
  function save() {
    localStorage.setItem(key, JSON.stringify(db));
  }
  function demoRole() {
    return localStorage.getItem("onco.demo.role") || "CLINICIAN";
  }
  function record(action, resource, patientId) {
    database().audit.unshift({
      event_id: id(),
      timestamp: now(),
      actor: user(demoRole()).username,
      actor_role: demoRole(),
      action,
      resource,
      patient_id: patientId || null,
      extra: { demonstration: true },
    });
    save();
  }
  const response = (body, status = 200) =>
    new Response(JSON.stringify(body), {
      status,
      headers: {
        "Content-Type": "application/json",
        "X-Onco-Data-Mode": "demonstration",
      },
    });
  const fail = (message, status = 400) => response({ detail: message }, status);
  async function mock(path, init = {}) {
    const d = database();
    const method = (init.method || "GET").toUpperCase();
    let body = {};
    try {
      body = JSON.parse(init.body || "{}");
    } catch {}
    const url = new URL(
      path,
      location.origin === "null"
        ? "https://oncosentinel.local"
        : location.origin,
    );
    const route = url.pathname.replace("/api/v2/", "");
    if (route === "auth/me") return response(user(demoRole()));
    if (["auth/login", "auth/dev-switch"].includes(route)) {
      const unameToRole = {
        dr_chen: "CLINICIAN",
        dr_patel: "RADIOLOGIST",
        pharma_alex: "PHARMACIST",
        billing_mark: "BILLING_CLERK",
        admin_clara: "ADMIN",
        admin: "ADMIN",
      };
      const ident = String(body.username || "").trim().toLowerCase();
      const role = body.role || unameToRole[ident] || "CLINICIAN";
      if (!accounts[role]) return fail("Unsupported demonstration role.");
      localStorage.setItem("onco.demo.role", role);
      return response({
        access_token: "demonstration-only-" + role,
        token_type: "bearer",
        user: user(role),
      });
    }
    if (route === "auth/register")
      return fail(
        "Staff registration requires a real backend. Use the Preview role selector to explore local sample accounts.",
        501,
      );
    if (route === "analyze")
      return fail(
        "Diagnostic inference is not simulated. Connect your backend in Workspace connection to run /api/v2/analyze. Untrained-category safety gates can be tested locally.",
        503,
      );
    if (
      route.startsWith("predictions/") ||
      route.startsWith("interop/fhir/diagnostic-report/")
    )
      return fail(
        "No real prediction exists in this demonstration. Connect the diagnostic service first.",
        404,
      );
    if (route === "training/queue")
      return response({
        tasks: [],
        message: "No live model deployment information in demonstration mode.",
      });
    if (route.startsWith("model-cards/") || route === "faculty/briefing")
      return fail("Model evidence requires the live backend.", 501);
    if (route === "audit") {
      let items = d.audit;
      const action = url.searchParams.get("action"),
        patient = url.searchParams.get("patient_id");
      if (demoRole() !== "ADMIN")
        items = items.filter((x) => x.actor === user(demoRole()).username);
      if (action) items = items.filter((x) => x.action === action);
      if (patient) items = items.filter((x) => x.patient_id === patient);
      const actor = url.searchParams.get("actor_id"),
        role = url.searchParams.get("actor_role"),
        mrn = url.searchParams.get("patient_mrn");
      if (actor) items = items.filter((x) => x.actor === actor);
      if (role) items = items.filter((x) => x.actor_role === role);
      if (mrn)
        items = items.filter(
          (x) =>
            x.patient_id === mrn ||
            d.patients.find((p) => p.id === x.patient_id)?.mrn === mrn,
        );
      return response({
        items: items.map((x) => ({
          ...x,
          id: x.event_id,
          actor_id: x.actor,
          patient_mrn:
            d.patients.find((p) => p.id === x.patient_id)?.mrn || x.patient_id,
          created_at: x.timestamp,
        })),
        total: items.length,
      });
    }
    if (route.startsWith("cases/")) {
      const parts = route.split("/");
      const mrn = decodeURIComponent(parts[1]);
      if (parts[2] === "timeline-events" && method === "POST") {
        const item = {
          event_id: id(),
          ...body,
          timestamp: body.event_time || body.timestamp || now(),
          title: body.event_type,
          narrative: body.payload?.clinical_finding || "",
          provenance: "Local demonstration action",
        };
        (d.events[mrn] ||= []).push(item);
        record("TIMELINE_APPENDED", mrn, mrn);
        save();
        return response(item, 201);
      }
      return response({
        case_id: mrn,
        events: d.events[mrn] || [],
        trajectory_summary:
          "Fictional local timeline. Events added here remain in this browser; no clinical system is updated.",
      });
    }
    if (route === "hms/finance/reports") {
      const billed = d["billing/invoices"].reduce(
          (a, v) => a + Number(v.total),
          0,
        ),
        outstanding = d["billing/invoices"].reduce(
          (a, v) => a + Number(v.outstanding),
          0,
        );
      return response({
        billed,
        collected: billed - outstanding,
        net_revenue: billed - outstanding,
        outstanding,
        collection_rate: billed ? (billed - outstanding) / billed : 0,
      });
    }
    if (route === "hms/finance/ledger") return response({ items: d.ledger });
    if (route === "hms/inventory/low-stock")
      return response({
        items: d["inventory/items"].filter((x) => x.on_hand < x.reorder_point),
      });
    if (route.startsWith("hms/pharmacy/fifo-lot/")) {
      const rx = d["pharmacy/prescriptions"].find(
        (x) => x.id === route.split("/").at(-1),
      );
      if (!rx) return fail("Prescription not found", 404);
      const item = d["inventory/items"].find(
        (i) => i.medication_id === rx.medication_id,
      );
      const lots = d["inventory/lots"]
        .filter(
          (l) =>
            l.item_id === item?.id &&
            l.on_hand > 0 &&
            String(l.expires_on || l.expiry) > now().slice(0, 10),
        )
        .sort((a, b) =>
          String(a.received_at).localeCompare(String(b.received_at)),
        );
      const lot = lots[0];
      const dispensed = d["pharmacy/dispense"]
        .filter((x) => x.prescription_id === rx.id)
        .reduce((a, v) => a + Number(v.quantity), 0);
      return response({
        available: Boolean(lot),
        fifo_lot: lot
          ? {
              ...lot,
              lot: lot.lot_number || lot.lot,
              expiry: lot.expires_on || lot.expiry,
              recommended_dispense_quantity: Math.min(
                lot.on_hand,
                Number(rx.quantity) - dispensed,
              ),
            }
          : null,
      });
    }
    if (route === "hms/fhir/patient" && method === "POST") {
      if (body.resourceType !== "Patient" || !body.name?.[0]?.family)
        return fail("Provide a FHIR Patient resource with a name.");
      const p = {
        id: id(),
        mrn: body.identifier?.[0]?.value || "MRN-DEMO-" + id().slice(0, 6),
        given_name: body.name[0].given?.join(" ") || "",
        family_name: body.name[0].family,
        birth_date: body.birthDate,
        gender: body.gender || "unknown",
        version: 1,
        consent: { research_opt_in: false },
        insurance: {},
      };
      d.patients.push(p);
      record("FHIR_IMPORT", "patients", p.id);
      save();
      return response(p, 201);
    }
    if (route.startsWith("hms/fhir/patient/")) {
      const p = d.patients.find((x) => x.id === route.split("/").at(-1));
      if (!p) return fail("Patient not found", 404);
      return response({
        resourceType: "Patient",
        id: p.id,
        meta: { tag: [{ code: "DEMONSTRATION" }] },
        identifier: [{ system: "urn:oncosentinel:mrn", value: p.mrn }],
        name: [{ family: p.family_name, given: [p.given_name] }],
        gender: p.gender,
        birthDate: p.birth_date,
      });
    }
    if (route.startsWith("hms/ai/patient/"))
      return response({
        patient_id: route.split("/").at(-1),
        reviews: [],
        predictions: [],
        advisory:
          "No diagnostic evidence exists in this demonstration workspace.",
      });
    if (!route.startsWith("hms/"))
      return fail(
        "This operation is not available in the local demonstration.",
        501,
      );
    let resource = route.slice(4);
    if (resource.endsWith("/query")) {
      resource = resource.slice(0, -6);
      const all = d[resource];
      if (!Array.isArray(all))
        return fail("Unsupported demonstration resource: " + resource, 501);
      let items = all;
      for (const [field, value] of Object.entries(body.filters || {})) {
        if (value != null && value !== "" && value !== "ALL")
          items = items.filter((x) => String(x[field]) === String(value));
      }
      return response({
        items: items.slice(0, body.limit || 100),
        total: items.length,
      });
    }
    const resources = Object.keys(d)
      .filter((k) => Array.isArray(d[k]))
      .sort((a, b) => b.length - a.length);
    const collection = resources.find(
      (k) => resource === k || resource.startsWith(k + "/"),
    );
    if (!collection)
      return fail("This operation requires the live backend.", 501);
    const collectionId = resource.slice(collection.length + 1);
    if (method === "DELETE") {
      const found = d[collection].findIndex((x) => x.id === collectionId);
      if (found < 0) return fail("Record not found", 404);
      d[collection].splice(found, 1);
      record("DELETE", resource);
      save();
      return response({ ok: true });
    }
    if (method === "PATCH" || method === "PUT") {
      const item = d[collection].find((x) => x.id === collectionId);
      if (!item) return fail("Record not found", 404);
      if (
        body.expected_version != null &&
        body.expected_version !== item.version
      )
        return fail("This record changed. Reload and try again.", 409);
      Object.assign(item, body, {
        version: (item.version || 0) + 1,
        updated_at: now(),
      });
      record("UPDATE", resource, item.patient_id);
      save();
      return response(item);
    }
    if (method === "POST") {
      if (collection === "pharmacy/prescriptions") {
        const med = d["pharmacy/medications"].find(
          (x) => x.id === body.medication_id,
        );
        const allergies = d["medical-records"]
          .filter(
            (x) => x.patient_id === body.patient_id && x.kind === "allergy",
          )
          .map((x) => String(x.content?.allergen || "").toUpperCase());
        if (
          med &&
          allergies.some((a) =>
            String(med.drug_class).toUpperCase().includes(a),
          )
        )
          return fail(
            "Allergy safety gate: this medication conflicts with the patient allergy record.",
            409,
          );
      }
      const item = { id: id(), version: 1, created_at: now(), ...body };
      if (collection === "patients")
        item.mrn ||=
          "MRN-DEMO-" + String(d.patients.length + 1).padStart(3, "0");
      if (collection === "encounters") {
        item.started_at ||= now();
        item.status ||= "active";
      }
      if (collection === "billing/invoices") {
        item.lines = (item.lines || []).map((l) => {
          const charge = d["billing/charge-items"].find(
            (c) => c.id === l.charge_item_id,
          );
          return {
            ...l,
            code: charge?.code || l.code,
            amount: charge?.amount ?? l.amount,
          };
        });
        item.total = (item.lines || []).reduce(
          (s, l) => s + Number(l.amount) * Number(l.quantity),
          0,
        );
        item.outstanding = item.total;
        item.number ||= "INV-DEMO-" + (d[collection].length + 1);
        d.ledger.push(
          {
            transaction_id: item.id,
            account: "Accounts receivable",
            debit: item.total,
            credit: 0,
            posted_at: now(),
          },
          {
            transaction_id: item.id,
            account: "Service revenue",
            debit: 0,
            credit: item.total,
            posted_at: now(),
          },
        );
      }
      if (collection === "billing/payments") {
        const invoice = d["billing/invoices"].find(
          (i) => i.id === body.invoice_id,
        );
        if (!invoice) return fail("Invoice not found");
        const amount = Number(body.amount);
        if (!(amount > 0 && amount <= invoice.outstanding))
          return fail("Invalid payment amount.");
        invoice.outstanding -= amount;
        invoice.version++;
        d.ledger.push(
          {
            transaction_id: item.id,
            account: "Cash",
            debit: amount,
            credit: 0,
            posted_at: now(),
          },
          {
            transaction_id: item.id,
            account: "Accounts receivable",
            debit: 0,
            credit: amount,
            posted_at: now(),
          },
        );
      }
      if (collection === "inventory/movements") {
        const target = d["inventory/items"].find((i) => i.id === body.item_id);
        const qty = Number(body.quantity);
        if (!target || !Number.isFinite(qty) || qty <= 0)
          return fail("Invalid inventory item or quantity.");
        target.on_hand += qty;
        d["inventory/lots"].push({
          id: id(),
          item_id: target.id,
          lot_number: body.lot,
          lot: body.lot,
          expires_on: body.expiry,
          expiry: body.expiry,
          quantity: qty,
          on_hand: qty,
          received_at: now(),
          version: 1,
        });
      }
      if (collection === "inventory/lots") {
        const target = d["inventory/items"].find((i) => i.id === body.item_id);
        if (target)
          target.on_hand += Number(
            body.quantity || body.quantity_received || 0,
          );
        item.on_hand = Number(body.quantity || body.quantity_received || 0);
      }
      if (collection === "pharmacy/dispense") {
        const lot = d["inventory/lots"].find(
          (x) =>
            x.id === body.lot_id ||
            x.lot_number === body.lot ||
            x.lot === body.lot,
        );
        const qty = Number(body.quantity);
        if (!lot || qty <= 0 || qty > lot.on_hand)
          return fail("Insufficient local lot balance.");
        lot.on_hand -= qty;
        lot.quantity = lot.on_hand;
        const invItem = d["inventory/items"].find((i) => i.id === lot.item_id);
        if (invItem) invItem.on_hand -= qty;
      }
      d[collection].push(item);
      record("CREATE", collection, item.patient_id);
      save();
      return response(item, 201);
    }
    const item = d[collection].find((x) => x.id === collectionId);
    return item ? response(item) : fail("Record not found", 404);
  }
  window.fetch = async function (input, init = {}) {
    const raw =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.href
          : input.url;
    const url = new URL(raw, location.href);
    const isApi = url.pathname.startsWith("/api/v2/");
    if (!isApi) return nativeFetch(input, init);
    const started = performance.now();
    try {
      let res;
      if (config.mode === "demo") {
        await new Promise((r) => setTimeout(r, 100));
        res = await mock(url.pathname + url.search, init);
      } else {
        const destination = config.apiOrigin
          ? config.apiOrigin + url.pathname + url.search
          : raw;
        res = await nativeFetch(destination, {
          ...init,
          signal: init.signal || AbortSignal.timeout(30000),
        });
      }
      window.dispatchEvent(
        new CustomEvent("onco:request", {
          detail: {
            path: url.pathname,
            status: res.status,
            ok: res.ok,
            duration: performance.now() - started,
          },
        }),
      );
      return res;
    } catch (error) {
      window.dispatchEvent(
        new CustomEvent("onco:request", {
          detail: { path: url.pathname, ok: false, status: 0 },
        }),
      );
      throw error;
    }
  };
  window.OncoDemo = {
    reset() {
      localStorage.removeItem(key);
      db = null;
      location.reload();
    },
  };
  if (config.mode === "demo" && !localStorage.getItem(config.tokenKey))
    localStorage.setItem(config.tokenKey, "demonstration-only-" + demoRole());
})();
