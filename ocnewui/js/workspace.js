/* Progressive workspace interactions. Core diagnostic controller remains in app.js. */
document.addEventListener("DOMContentLoaded", () => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const $$ = (s) => [...document.querySelectorAll(s)];
  const config = window.OncoConfig;
  const demo = config.mode === "demo";
  $("#printBriefing")?.addEventListener("click", () => window.print());
  const chip = $("#connectionChip");
  $("#environmentBanner").hidden = !demo;
  $$("[data-demo-only]").forEach((el) => (el.hidden = !demo));
  chip.classList.toggle("connected", demo);
  chip.lastChild.textContent = demo ? "Local preview" : "Not connected";
  $("#resetDemo").addEventListener("click", () => {
    if (
      confirm(
        "Reset the fictional sample records and discard local demonstration changes?",
      )
    )
      window.OncoDemo.reset();
  });
  $$(".dialog-close").forEach((button) =>
    button.addEventListener("click", () => button.closest("dialog").close()),
  );
  $$(".workspace-dialog, .glass-modal").forEach((dialog) =>
    dialog.addEventListener("click", (e) => {
      if (e.target === dialog) {
        const b = dialog.getBoundingClientRect();
        if (
          e.clientX < b.left ||
          e.clientX > b.right ||
          e.clientY < b.top ||
          e.clientY > b.bottom
        )
          dialog.close();
      }
    }),
  );
  const settings = $("#settingsDialog");
  $("#openSettings").addEventListener("click", () => {
    $("#connectionMode").value = config.mode;
    $("#apiOrigin").value = config.apiOrigin;
    settings.showModal();
  });
  $("#settingsForm").addEventListener("submit", (e) => {
    e.preventDefault();
    const value = $("#apiOrigin").value.trim().replace(/\/$/, "");
    if (value) {
      const url = new URL(value);
      if (
        !["http:", "https:"].includes(url.protocol) ||
        url.pathname !== "/" ||
        url.search ||
        url.hash
      ) {
        $("#apiOrigin").setCustomValidity(
          "Enter only the API origin, for example https://api.example.com.",
        );
        $("#apiOrigin").reportValidity();
        return;
      }
    }
    localStorage.setItem("onco.mode", $("#connectionMode").value);
    localStorage.setItem("onco.apiOrigin", value);
    location.reload();
  });
  $("#apiOrigin").addEventListener("input", (e) =>
    e.target.setCustomValidity(""),
  );
  $("#studioHelp").addEventListener("click", () =>
    $("#guideDialog").showModal(),
  );
  const menu = $("#mobileMenu");
  const closeNavigation = () => {
    document.body.classList.remove("nav-open");
    menu.setAttribute("aria-expanded", "false");
  };
  menu.addEventListener("click", (e) => {
    e.stopPropagation();
    document.body.classList.toggle("nav-open");
    menu.setAttribute(
      "aria-expanded",
      String(document.body.classList.contains("nav-open")),
    );
  });
  document.addEventListener("click", (e) => {
    if (
      document.body.classList.contains("nav-open") &&
      !e.target.closest(".app-sidebar") &&
      !e.target.closest("#mobileMenu")
    )
      closeNavigation();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeNavigation();
  });
  const nav = $$(".side-nav-btn");
  function navigate(button) {
    if (button && button.style.display !== "none") button.click();
  }
  nav.forEach((button) =>
    button.addEventListener("click", () => {
      if (!button.classList.contains("active")) return;
      closeNavigation();
      nav.forEach((b) =>
        b.setAttribute("aria-current", b === button ? "page" : "false"),
      );
      $$(".nav-section-title").forEach((title) => {
        const group = title.nextElementSibling;
        title.hidden =
          group?.matches("nav") &&
          ![...group.children].some((b) => b.style.display !== "none");
      });
      const hash = "#" + button.dataset.view.replace("view-", "");
      if (location.hash !== hash) history.replaceState(null, "", hash);
      if (button.dataset.view === "view-ai-studio") updateContext();
      window.scrollTo({ top: 0, behavior: "instant" });
    }),
  );
  const command = $("#commandDialog"),
    input = $("#commandInput"),
    results = $("#commandResults");
  function renderCommands() {
    const term = input.value.toLowerCase().trim();
    results.replaceChildren();
    const matches = nav.filter(
      (b) =>
        b.style.display !== "none" &&
        b.textContent.toLowerCase().includes(term),
    );
    for (const target of matches) {
      const row = document.createElement("button");
      row.className = "command-result";
      row.type = "button";
      const icon = target.querySelector("svg").cloneNode(true);
      row.append(
        icon,
        document.createTextNode(target.querySelector("span").textContent),
      );
      const end = document.createElement("small");
      end.textContent = "↵";
      row.append(end);
      row.addEventListener("click", () => {
        command.close();
        navigate(target);
      });
      results.append(row);
    }
    if (!matches.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "No matching workspace is available to your role.";
      results.append(empty);
    }
  }
  function openCommand() {
    input.value = "";
    renderCommands();
    command.showModal();
    input.focus();
  }
  $("#openCommand").addEventListener("click", openCommand);
  input.addEventListener("input", renderCommands);
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      if (command.open) command.close();
      else openCommand();
    }
  });
  command.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const buttons = [...results.querySelectorAll("button")];
      const current = buttons.indexOf(document.activeElement);
      const step = e.key === "ArrowDown" ? 1 : -1;
      buttons[(current + step + buttons.length) % buttons.length]?.focus();
    }
    if (e.key === "Enter" && document.activeElement === input) {
      e.preventDefault();
      results.querySelector("button")?.click();
    }
  });
  function selectEvidence(name) {
    $$("[data-evidence]").forEach((b) => {
      const on = b.dataset.evidence === name;
      b.classList.toggle("active", on);
      b.setAttribute("aria-selected", String(on));
      b.tabIndex = on ? 0 : -1;
    });
    $$(".evidence-pane").forEach((p) =>
      p.classList.toggle("active", p.id === "evidence-" + name),
    );
  }
  $$("[data-evidence]").forEach((button) => {
    button.addEventListener("click", () =>
      selectEvidence(button.dataset.evidence),
    );
    button.addEventListener("keydown", (e) => {
      if (["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) {
        e.preventDefault();
        const buttons = $$("[data-evidence]");
        let i = buttons.indexOf(button);
        i =
          e.key === "Home"
            ? 0
            : e.key === "End"
              ? buttons.length - 1
              : (i + (e.key === "ArrowRight" ? 1 : -1) + buttons.length) %
                buttons.length;
        buttons[i].click();
        buttons[i].focus();
      }
    });
  });
  selectEvidence("overview");
  let patients = [];
  const patientBody = $("#patientsTable tbody");
  let sortAscending = true;
  function filterPatients() {
    const term = $("#patientSearch").value.trim().toLowerCase();
    let visible = 0;
    for (const row of [...patientBody.rows]) {
      const matches = row.textContent.toLowerCase().includes(term);
      row.hidden = !matches;
      if (matches) visible++;
    }
    const summary = `${visible} of ${patientBody.rows.length}`;
    if ($("#registryVisibleCount").textContent !== summary)
      $("#registryVisibleCount").textContent = summary;
    let empty = $("#registryNoMatches");
    if (!empty) {
      empty = document.createElement("div");
      empty.id = "registryNoMatches";
      empty.className = "empty-state";
      empty.textContent = "No patients match your search.";
      $("#patientsTable").closest(".table-responsive").after(empty);
    }
    empty.hidden = visible > 0;
  }
  $("#patientSearch").addEventListener("input", filterPatients);
  $("#patientSort").addEventListener("click", () => {
    const rows = [...patientBody.rows].sort((a, b) => {
      const left = a.cells[1]?.textContent || "",
        right = b.cells[1]?.textContent || "";
      return left.localeCompare(right) * (sortAscending ? 1 : -1);
    });
    patientBody.append(...rows);
    $("#patientSort").textContent = sortAscending ? "Name A–Z ↓" : "Name Z–A ↑";
    sortAscending = !sortAscending;
    filterPatients();
  });
  new MutationObserver(filterPatients).observe(patientBody, {
    childList: true,
  });
  function updateContext() {
    const mrn = $("#caseIdInput").value;
    const p = patients.find((p) => p.mrn === mrn);
    const option = $("#caseIdSelect").selectedOptions[0];
    const fallback =
      option?.value === mrn ? option.textContent.split(" (")[0] : null;
    const name = p
      ? `${p.given_name} ${p.family_name}`
      : fallback || "Custom case";
    $("#contextName").textContent = name;
    $("#contextMrn").textContent = mrn || "No patient selected";
    $("#caseAvatar").textContent = name
      .split(" ")
      .map((x) => x[0])
      .slice(0, 2)
      .join("");
    const category =
      $("#categorySelect").selectedOptions[0]?.textContent?.split(" ·")[0] ||
      "Not selected";
    $("#contextModality").textContent =
      ($("#modalitySelect").value || "").toUpperCase() +
      " · " +
      category.replace(/ Cancer| Tumor/g, "");
    $("#openCaseTimeline").hidden =
      nav.find((b) => b.dataset.view === "view-timeline")?.style.display ===
      "none";
  }
  [
    "caseIdSelect",
    "quickSelectPatient",
    "categorySelect",
    "modalitySelect",
    "presetScenarios",
  ].forEach((id) =>
    $("#" + id)?.addEventListener("change", () => {
      updateContext();
      selectEvidence("overview");
    }),
  );
  $("#loadExecutePresetBtn").addEventListener("click", updateContext);
  $("#openCaseTimeline").addEventListener("click", () =>
    navigate(nav.find((b) => b.dataset.view === "view-timeline")),
  );
  $("#dropzone").addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      $("#fileInput").click();
    }
  });

  $("#removeImageBtn").addEventListener("click", () =>
    window.dispatchEvent(new Event("onco:reset-case")),
  );
  $("#textQueryInput").addEventListener("input", () =>
    window.dispatchEvent(new Event("onco:reset-case")),
  );
  const heatImage = $("#heatmapImage");
  $("#heatmapOverlayToggle").addEventListener("change", () => {
    $("#heatmapEmpty").hidden = Boolean(heatImage.getAttribute("src"));
  });
  heatImage.addEventListener("error", () => {
    heatImage.removeAttribute("src");
    $("#heatmapEmpty").hidden = false;
    $("#heatmapEmpty").firstChild.textContent =
      "The localization artifact could not be loaded.";
  });
  // Load authenticated artifacts via the same transport and token as the diagnostic API.
  let lastArtifact = "",
    artifactBlob = "";
  new MutationObserver(async () => {
    const source = heatImage.getAttribute("src") || "";
    if (
      source.startsWith("/api/v2/artifacts/heatmaps/") &&
      source !== lastArtifact
    ) {
      lastArtifact = source;
      try {
        const res = await fetch(source, {
          headers: {
            Authorization: "Bearer " + localStorage.getItem(config.tokenKey),
          },
        });
        if (!res.ok) throw new Error("Artifact unavailable");
        if (artifactBlob) URL.revokeObjectURL(artifactBlob);
        artifactBlob = URL.createObjectURL(await res.blob());
        heatImage.src = artifactBlob;
        $("#heatmapEmpty").hidden = true;
      } catch {
        heatImage.removeAttribute("src");
        $("#heatmapEmpty").hidden = false;
      }
    }
  }).observe(heatImage, { attributes: true, attributeFilter: ["src"] });
  let hydrated = false;
  async function hydrate() {
    const headers = {
      "Content-Type": "application/json",
      Authorization: "Bearer " + localStorage.getItem(config.tokenKey),
    };
    try {
      const res = await fetch("/api/v2/hms/patients/query", {
        method: "POST",
        headers,
        body: JSON.stringify({ filters: {}, limit: 100 }),
      });
      if (res.ok) {
        const page = await res.json();
        patients = page.items || [];
        if (!demo) {
          const select = $("#caseIdSelect"),
            previous = select.value;
          select.replaceChildren();
          for (const p of patients) {
            const opt = document.createElement("option");
            opt.value = p.mrn;
            opt.textContent = `${p.given_name} ${p.family_name} (${p.mrn})`;
            select.append(opt);
          }
          const custom = document.createElement("option");
          custom.value = "CUSTOM";
          custom.textContent = "Custom upload";
          select.append(custom);
          select.value = patients.some((p) => p.mrn === previous)
            ? previous
            : patients[0]?.mrn || "CUSTOM";
          select.dispatchEvent(new Event("change", { bubbles: true }));
        }
      }
    } catch {}
    if (!demo) {
      try {
        const res = await fetch("/api/v2/training/queue", { headers });
        if (res.ok) {
          const data = await res.json();
          const tasks = data.tasks || [];
          const active = tasks.filter(
            (t) =>
              t.is_active || t.status === "ACTIVE" || t.status === "EVALUATED",
          ).length;
          $("#platformPhaseText").textContent = tasks.length
            ? `${active} of ${tasks.length} models active`
            : "No model deployment data";
          $("#platformPhaseIndicator .status-dot").classList.toggle(
            "online",
            active > 0,
          );
        }
      } catch {}
    } else
      $("#platformPhaseText").textContent =
        "Model readiness requires a live connection";
    updateContext();
    const fromHash = location.hash.slice(1);
    if (fromHash)
      navigate(nav.find((b) => b.dataset.view === "view-" + fromHash));
    nav
      .find((b) => b.classList.contains("active"))
      ?.setAttribute("aria-current", "page");
  }
  window.addEventListener("onco:request", (e) => {
    const { path, ok, status } = e.detail;
    if (!demo) {
      if (!ok && (status === 404 || status === 422 || status === 400)) {
        // Individual resource response; does not mean server is disconnected
        return;
      }
      chip.className = "connection-chip " + (ok ? "connected" : "error");
      chip.lastChild.textContent = ok
        ? "API connected"
        : status === 401
          ? "Sign-in required"
          : status === 0
            ? "API unavailable"
            : "API error";
    }
    if (/\/auth\/(me|login|register|dev-switch)$/.test(path) && ok) {
      hydrated = true;
      setTimeout(hydrate, 50);
    }
    if (path === "/api/v2/analyze") {
      $("#workflowAnalyze").classList.toggle("current", ok);
      if (!ok) $("#workflowReview").classList.remove("current");
    }
  });

  // Heartbeat keep-alive check to ensure API connected status stays active
  if (!demo) {
    setInterval(async () => {
      try {
        const res = await fetch("/api/v2/health", { signal: AbortSignal.timeout(5000) });
        if (res.ok) {
          chip.className = "connection-chip connected";
          chip.lastChild.textContent = "API connected";
        }
      } catch (_) {}
    }, 15000);
  }
  new MutationObserver(() => {
    const status = $("#aggregateDecisionBadge").textContent;
    const standby = ["AWAITING INPUT", "STANDBY"].includes(status);
    $("#evidenceEmptyGraphic").hidden = !standby;
    $("#workflowAnalyze").classList.toggle("current", !standby);
    $("#workflowReview").classList.toggle(
      "current",
      !standby && status !== "SAFETY REFUSAL",
    );
  }).observe($("#aggregateDecisionBadge"), { childList: true, subtree: true });
  // Dynamic legacy templates use text-only iconography and no internal requirement IDs.
  function labelControls(root) {
    if (root.nodeType !== Node.ELEMENT_NODE) return;
    for (const label of root.querySelectorAll("label:not([for])")) {
      const control =
        label.querySelector("input,select,textarea") ||
        label.parentElement?.querySelector(
          "input:not([type=hidden]),select,textarea",
        );
      if (control?.id) label.htmlFor = control.id;
    }
  }
  labelControls(document.body);
  const cleanText = (node) => {
    if (node.nodeType === Node.TEXT_NODE) {
      if (
        ["SCRIPT", "STYLE", "PRE", "CODE", "TEXTAREA", "OPTION"].includes(
          node.parentElement?.tagName,
        )
      )
        return;
      const clean = node.textContent
        .replace(/[\u{1F000}-\u{1FAFF}\uFE0F]/gu, "")
        .replace(/\s*\((?:NFR|FR|SRS)-?\d+\)/g, "");
      if (clean !== node.textContent) node.textContent = clean;
    } else if (
      node.nodeType === Node.ELEMENT_NODE &&
      !["SCRIPT", "STYLE", "PRE", "CODE", "TEXTAREA"].includes(node.tagName)
    )
      for (const child of [...node.childNodes]) cleanText(child);
  };
  new MutationObserver((records) => {
    for (const r of records)
      for (const node of r.addedNodes) {
        cleanText(node);
        labelControls(node);
      }
  }).observe(document.body, { childList: true, subtree: true });
  updateContext();
});
