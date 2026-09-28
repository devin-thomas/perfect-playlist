import { cp, mkdir, rm } from "node:fs/promises";

const files = ["index.html", "page.css", "page.js", "scrollcraft.css", "scrollcraft.js"];
const output = new URL("../public/", import.meta.url);

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
for (const file of files) {
  await cp(new URL(`../${file}`, import.meta.url), new URL(file, output));
}

console.log(`Prepared ${files.length} preview assets.`);
