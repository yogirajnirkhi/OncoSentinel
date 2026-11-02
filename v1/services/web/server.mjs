import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
const root = path.dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT || 4173);
const mime = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".md": "text/plain; charset=utf-8",
};
http
  .createServer(async (req, res) => {
    try {
      const url = new URL(req.url, "http://localhost");
      if (url.pathname.startsWith("/api/")) {
        res.writeHead(503, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            detail:
              "No backend is attached to the static frontend server. Set the API origin in Workspace connection, or serve these files with your backend.",
          }),
        );
        return;
      }
      const pathname = decodeURIComponent(url.pathname);
      if (
        pathname
          .split("/")
          .some(
            (s) =>
              s.startsWith(".") ||
              [
                "node_modules",
                "tests",
                "test-results",
                "playwright-report",
              ].includes(s),
          )
      ) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      let file = path.resolve(root, "." + pathname);
      if (!file.startsWith(root + path.sep) && file !== root) {
        res.writeHead(403);
        res.end("Forbidden");
        return;
      }
      if ((await stat(file)).isDirectory())
        file = path.join(file, "index.html");
      const content = await readFile(file);
      res.writeHead(200, {
        "Content-Type": mime[path.extname(file)] || "application/octet-stream",
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "same-origin",
        "Content-Security-Policy":
          "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: blob: http: https:; connect-src 'self' http: https:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'",
      });
      res.end(content);
    } catch {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not found");
    }
  })
  .listen(port, "0.0.0.0", () =>
    console.log(`OncoSentinel frontend: http://localhost:${port}`),
  );
