export const INSTALL_COMMAND = "python -m pip install perfect-playlist";

export const AGENT_ONBOARDING_PROMPT = `Learn and use Perfect Playlist for deterministic Spotify playlist work.

Official site: https://perfectplaylist.dev
Official PyPI package: https://pypi.org/project/perfect-playlist/
Repository and documentation: https://github.com/devin-thomas/perfect-playlist
Agent skill: https://perfectplaylist.dev/SKILL.md

Install the official CLI and Python package with:
python -m pip install perfect-playlist

Start by reading SKILL.md and the repository README. Use Search and Inspect for discovery, save inspected canonical Spotify track URIs in a durable YAML, JSON, or TXT Source, then Build and Verify. Preserve order and duplicates. Never substitute, reorder, silently skip, overwrite, or automatically retry a partial write. Check authentication before Spotify-backed work, keep credentials local, and ask before installing software or making a Spotify write.`;

async function writeToClipboard(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const temporaryInput = document.createElement("textarea");
  temporaryInput.value = value;
  temporaryInput.setAttribute("readonly", "");
  temporaryInput.style.position = "fixed";
  temporaryInput.style.opacity = "0";
  document.body.append(temporaryInput);
  temporaryInput.select();
  const copied = document.execCommand("copy");
  temporaryInput.remove();

  if (!copied) {
    throw new Error("Clipboard access is unavailable in this browser.");
  }
}

function announce(message, tone = "success") {
  const status = document.querySelector("[data-copy-status]");
  if (!status) {
    return;
  }

  status.textContent = message;
  status.dataset.tone = tone;
  status.hidden = false;
  window.clearTimeout(announce.timeoutId);
  announce.timeoutId = window.setTimeout(() => {
    status.hidden = true;
  }, 3200);
}

announce.timeoutId = 0;

function setCopiedState(button, copiedLabel) {
  const label = button.querySelector("[data-button-label]");
  const originalLabel = label?.textContent ?? button.textContent;
  button.dataset.copied = "true";
  if (label) {
    label.textContent = copiedLabel;
  }

  window.setTimeout(() => {
    delete button.dataset.copied;
    if (label) {
      label.textContent = originalLabel;
    }
  }, 2400);
}

async function handleCopy(button) {
  const copyType = button.dataset.copy;
  const value = copyType === "onboarding" ? AGENT_ONBOARDING_PROMPT : INSTALL_COMMAND;
  const copiedLabel = copyType === "onboarding" ? "Onboarding prompt copied" : "Install command copied";

  try {
    await writeToClipboard(value);
    setCopiedState(button, copiedLabel);
    announce(copiedLabel);
  } catch (error) {
    console.error(error);
    announce("Copy failed. Open the text version instead.", "error");
  }
}

function revealPage() {
  document.documentElement.classList.add("is-ready");

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.12 },
  );

  for (const element of document.querySelectorAll("[data-reveal]")) {
    observer.observe(element);
  }
}

if (typeof document !== "undefined") {
  for (const button of document.querySelectorAll("[data-copy]")) {
    button.addEventListener("click", () => handleCopy(button));
  }

  if ("IntersectionObserver" in window) {
    revealPage();
  } else {
    document.documentElement.classList.add("is-ready");
    for (const element of document.querySelectorAll("[data-reveal]")) {
      element.classList.add("is-visible");
    }
  }
}
