import { mkdir, copyFile, cp, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
await rm(path.join(root, "dist"), { recursive: true, force: true });
await mkdir(path.join(root, "dist"), { recursive: true });
for (const file of ["index.html", "openapi.json"])
  await copyFile(path.join(root, file), path.join(root, "dist", file));
for (const folder of ["css", "js"])
  await cp(path.join(root, folder), path.join(root, "dist", folder), {
    recursive: true,
  });
console.log(
  "Static frontend built in dist/. Configure js/config.js for production live mode before deployment.",
);
