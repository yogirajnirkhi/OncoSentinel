/* Deployment default: live mode on FastAPI backend; demo fixture mode only on static test harness (port 4173) or explicit ?mode=demo */
(() => {
  const params = new URLSearchParams(window.location.search);
  const paramMode = params.get("mode");
  const paramApi = params.get("api");
  const isStaticHarness = window.location.port === "4173";
  window.ONCO_DEPLOYMENT = {
    mode: isStaticHarness ? "demo" : "live",
    apiOrigin: "",
  };
  const defaults = window.ONCO_DEPLOYMENT;
  if (
    !isStaticHarness &&
    !paramMode &&
    localStorage.getItem("onco.mode") === "demo"
  ) {
    localStorage.removeItem("onco.mode");
  }
  const mode = paramMode || localStorage.getItem("onco.mode") || defaults.mode;
  const apiOrigin = (
    paramApi ||
    localStorage.getItem("onco.apiOrigin") ||
    defaults.apiOrigin
  ).replace(/\/$/, "");
  window.OncoConfig = Object.freeze({
    mode,
    apiOrigin,
    tokenKey: mode === "demo" ? "onco.demo.jwt" : "oncosentinel_jwt",
  });
})();
