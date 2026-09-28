const sourceUris = [
  "spotify:track:5Qamlcya1Hz5Z4AgzdQ5q8",
  "spotify:track:5irdISp39LC6kD10muguYh",
  "spotify:track:5Qamlcya1Hz5Z4AgzdQ5q8",
];

const trackDetails = new Map([
  [sourceUris[0], { title: "Call On You", artist: "Corey Lingo" }],
  [sourceUris[1], { title: "gooey", artist: "GOONIE, iayze" }],
]);

let resultUris = [...sourceUris];

function formatUri(uri) {
  return uri.replace("spotify:track:", "");
}

function firstDuplicatePosition(uris, position) {
  return uris.indexOf(uris[position]);
}

function renderRows(list, uris, comparison) {
  if (!(list instanceof HTMLOListElement) || list.children.length !== uris.length) {
    throw new Error("A sample sequence does not match its track rows.");
  }
  for (const [index, row] of [...list.children].entries()) {
    const detail = trackDetails.get(uris[index]);
    const firstPosition = firstDuplicatePosition(uris, index);
    const small = row.querySelector(".track-list__detail small");
    const title = row.querySelector(".track-list__detail strong");
    const code = row.querySelector("code");

    if (!detail || !small || !title || !code) {
      throw new Error(`The comparison row ${index + 1} is missing its sample track markup.`);
    }

    title.textContent = detail.title;
    small.textContent = firstPosition < index
      ? `${detail.artist} · same URI as ${String(firstPosition + 1).padStart(2, "0")}`
      : detail.artist;
    code.textContent = formatUri(uris[index]);

    if (comparison) {
      row.dataset.match = String(sourceUris[index] === uris[index]);
    } else {
      delete row.dataset.match;
    }
  }
}

function setStatus(state, message) {
  const status = document.querySelector("[data-verify-status]");
  const copy = document.querySelector("[data-status-copy]");
  const note = document.querySelector("[data-result-note]");

  if (!status || !copy || !note) {
    throw new Error("The comparison status region is missing.");
  }

  status.dataset.state = state;
  copy.textContent = message;
}

function compareSequences() {
  const sourceList = document.querySelector("[data-source-list]");
  const resultList = document.querySelector("[data-result-list]");
  const note = document.querySelector("[data-result-note]");
  const lines = [...document.querySelectorAll("[data-compare-line]")];
  if (!sourceList || !resultList || !note || lines.length !== sourceUris.length) {
    throw new Error("The sequence alignment is incomplete.");
  }

  let firstDifference = -1;
  for (let index = 0; index < sourceUris.length; index += 1) {
    if (sourceUris[index] !== resultUris[index]) {
      firstDifference = index;
      break;
    }
  }

  renderRows(sourceList, sourceUris, true);
  renderRows(resultList, resultUris, true);

  for (const [index, line] of lines.entries()) {
    line.dataset.state = sourceUris[index] === resultUris[index] ? "match" : "mismatch";
  }

  if (firstDifference === -1) {
    setStatus("match", "Exact sequence matched");
    note.textContent = "3 of 3 ordered references match. The repeated URI is present in both chosen positions.";
    return;
  }

  const sourceUri = formatUri(sourceUris[firstDifference]);
  const resultUri = formatUri(resultUris[firstDifference]);
  setStatus("mismatch", `First difference at position ${firstDifference + 1}`);
  note.textContent = `Source has ${sourceUri}; read-back has ${resultUri}. The first mismatch is identified before any later rows.`;
}

function restoreSample() {
  resultUris = [...sourceUris];
  const sourceList = document.querySelector("[data-source-list]");
  const resultList = document.querySelector("[data-result-list]");
  const lines = [...document.querySelectorAll("[data-compare-line]")];
  if (!sourceList || !resultList || lines.length !== sourceUris.length) {
    throw new Error("The sequence alignment is incomplete.");
  }

  renderRows(sourceList, sourceUris, false);
  renderRows(resultList, resultUris, false);
  for (const line of lines) delete line.dataset.state;
  const note = document.querySelector("[data-result-note]");
  if (!note) throw new Error("The comparison note is missing.");
  note.textContent = "Each row is compared by its canonical URI. Order and duplicates stay in the comparison.";
  setStatus("ready", "Ready to compare");
}

function updateFolio() {
  const number = document.querySelector("[data-folio-number]");
  const title = document.querySelector("[data-folio-title]");
  if (!number || !title) throw new Error("The chapter folio is missing.");

  const chapters = [...document.querySelectorAll("[data-chapter][data-title]")];
  const observer = new IntersectionObserver((entries) => {
    const visible = entries
      .filter((entry) => entry.isIntersecting)
      .sort((first, second) => second.intersectionRatio - first.intersectionRatio)[0];
    if (!visible) return;
    number.textContent = visible.target.dataset.chapter ?? "00";
    title.textContent = visible.target.dataset.title ?? "";
  }, { rootMargin: "-38% 0px -38% 0px", threshold: [0, 0.2, 0.5, 0.8] });

  for (const chapter of chapters) observer.observe(chapter);
}

function reportAlignmentPaint() {
  const stage = document.querySelector(".alignment-stage");
  const lines = [...document.querySelectorAll("[data-compare-line]")];
  if (!stage || lines.length !== sourceUris.length) {
    throw new Error("The rendered alignment state cannot be measured.");
  }

  let animationFrame = 0;
  const observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && animationFrame === 0) {
      const publish = () => {
        const paintedLengths = lines.map((line) => {
          const dash = getComputedStyle(line).strokeDasharray.split(",")[0];
          const pixels = Number.parseFloat(dash);
          return Number.isFinite(pixels) ? Math.round(pixels) : 0;
        });
        stage.setAttribute("data-sc-verify-state", paintedLengths.join("/"));
        animationFrame = requestAnimationFrame(publish);
      };
      publish();
    } else if (!entry.isIntersecting && animationFrame !== 0) {
      cancelAnimationFrame(animationFrame);
      animationFrame = 0;
    }
  }, { threshold: 0 });
  observer.observe(stage);
}

const verifyButton = document.querySelector("[data-verify]");
const swapButton = document.querySelector("[data-swap]");
const restoreButton = document.querySelector("[data-restore]");
if (!verifyButton || !swapButton || !restoreButton) {
  throw new Error("A sequence demonstration control is missing.");
}

verifyButton.addEventListener("click", compareSequences);
swapButton.addEventListener("click", () => {
  resultUris = [resultUris[0], resultUris[2], resultUris[1]];
  const sourceList = document.querySelector("[data-source-list]");
  const resultList = document.querySelector("[data-result-list]");
  if (!sourceList || !resultList) throw new Error("A sample sequence list is missing.");
  renderRows(sourceList, sourceUris, false);
  renderRows(resultList, resultUris, false);
  const sequenceRestored = resultUris.every((uri, index) => uri === sourceUris[index]);
  setStatus("ready", sequenceRestored ? "Sample order restored" : "Sample order changed");
  const note = document.querySelector("[data-result-note]");
  if (!note) throw new Error("The comparison note is missing.");
  note.textContent = sequenceRestored
    ? "The local sample read-back is back in its chosen order. Verify to confirm the match."
    : "The sample read-back was reordered locally. Verify to see the first difference.";
  for (const line of document.querySelectorAll("[data-compare-line]")) delete line.dataset.state;
});
restoreButton.addEventListener("click", restoreSample);

updateFolio();
reportAlignmentPaint();
ScrollCraft.mount(document.body);
