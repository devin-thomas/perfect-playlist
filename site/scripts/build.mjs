import { cp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { AGENT_ONBOARDING_PROMPT } from "../src/app.js";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const siteDirectory = resolve(scriptDirectory, "..");
const repositoryDirectory = resolve(siteDirectory, "..");
const sourceDirectory = resolve(siteDirectory, "src");
const outputDirectory = resolve(siteDirectory, "dist");

await rm(outputDirectory, { recursive: true, force: true });
await mkdir(outputDirectory, { recursive: true });
await cp(sourceDirectory, outputDirectory, { recursive: true });

const skill = await readFile(resolve(repositoryDirectory, "SKILL.md"), "utf8");
await writeFile(resolve(outputDirectory, "SKILL.md"), skill, "utf8");
await writeFile(
  resolve(outputDirectory, "agent-onboarding.txt"),
  `${AGENT_ONBOARDING_PROMPT}\n`,
  "utf8",
);

console.log("Built Perfect Playlist site with the canonical SKILL.md and onboarding prompt.");
