/* =====================================================================
   UI helpers: toasts, modals, formatting, safe rendering
   ===================================================================== */

/* --- Escaping --------------------------------------------------------- *
 * The original code built table rows with
 *     html += `<td>${d.subject_name}</td>`
 * and assigned them with innerHTML. A student named
 *     <img src=x onerror=alert(1)>
 * would then run script in every teacher's browser that opened the page.
 * That is stored XSS, and it needs only one malicious value in the
 * database to affect every viewer.
 *
 * Two defences are used in this project:
 *   - `text()` / `setText()` for anything that goes in as text, which
 *     never parses markup at all;
 *   - `escapeHtml()` for the few places a template literal is genuinely
 *     the clearest way to build a row.
 * ---------------------------------------------------------------------- */

export function escapeHtml(value) {
  if (value === null || value === undefined) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Create an element. Text is set via textContent, so it cannot inject. */
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key === "html") node.innerHTML = value;
    else if (key.startsWith("on") && typeof value === "function") {
      node.addEventListener(key.slice(2).toLowerCase(), value);
    } else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(child));
  }
  return node;
}

export function $(selector, scope = document) {
  return scope.querySelector(selector);
}

export function setText(selector, value, scope = document) {
  const node = $(selector, scope);
  if (node) node.textContent = value;
  return node;
}

export function show(selector, visible = true, scope = document) {
  const node = $(selector, scope);
  if (node) node.classList.toggle("hidden", !visible);
  return node;
}

/* --- Toasts ----------------------------------------------------------- */

const TOAST_ICON = {
  success: "✓",
  error: "✕",
  warning: "⚠",
  info: "ℹ",
};

function toastRegion() {
  let region = $(".toast-region");
  if (!region) {
    region = el("div", {
      class: "toast-region",
      role: "status",
      // polite: announced when the screen reader finishes its sentence,
      // rather than interrupting mid-word.
      "aria-live": "polite",
      "aria-atomic": "false",
    });
    document.body.append(region);
  }
  return region;
}

export function toast(message, { type = "info", title, duration = 4200 } = {}) {
  const node = el(
    "div",
    { class: `toast toast-${type}` },
    el("span", { class: "toast-icon", text: TOAST_ICON[type] || TOAST_ICON.info }),
    el(
      "div",
      { class: "toast-body" },
      title ? el("div", { class: "toast-title", text: title }) : null,
      el("div", { class: "toast-msg", text: message })
    ),
    el("button", {
      class: "toast-close",
      "aria-label": "Dismiss",
      text: "✕",
      onclick: () => dismiss(),
    })
  );

  function dismiss() {
    node.classList.add("leaving");
    node.addEventListener("animationend", () => node.remove(), { once: true });
  }

  toastRegion().append(node);
  if (duration) setTimeout(dismiss, duration);
  return dismiss;
}

export const notify = {
  success: (msg, title) => toast(msg, { type: "success", title }),
  error: (msg, title) => toast(msg, { type: "error", title, duration: 7000 }),
  warning: (msg, title) => toast(msg, { type: "warning", title, duration: 6000 }),
  info: (msg, title) => toast(msg, { type: "info", title }),
};

/** Report an ApiError to the user with its server-supplied message. */
export function reportError(error, fallback = "Something went wrong") {
  console.error(error);
  notify.error(error?.message || fallback);
}

/* --- Modal ------------------------------------------------------------ */

/**
 * Show a modal and resolve with its result.
 *
 * `render` receives a `close(value)` function. Escape and a backdrop
 * click both close with `null`, and focus moves into the dialog so a
 * keyboard user is not left tabbing through the page behind it.
 */
export function modal({ title, render, size = "" }) {
  return new Promise((resolve) => {
    const previouslyFocused = document.activeElement;

    const close = (value = null) => {
      backdrop.remove();
      document.removeEventListener("keydown", onKey);
      previouslyFocused?.focus?.();
      resolve(value);
    };

    const onKey = (event) => {
      if (event.key === "Escape") close(null);
    };

    const dialog = el(
      "div",
      {
        class: `modal ${size}`,
        role: "dialog",
        "aria-modal": "true",
        "aria-label": title || "Dialog",
      },
      title
        ? el("div", { class: "modal-header" }, el("h2", { text: title }))
        : null
    );

    dialog.append(render(close));

    const backdrop = el(
      "div",
      {
        class: "modal-backdrop",
        onclick: (event) => {
          if (event.target === backdrop) close(null);
        },
      },
      dialog
    );

    document.body.append(backdrop);
    document.addEventListener("keydown", onKey);

    // Focus the first control, or the dialog itself if it has none.
    const focusable = dialog.querySelector(
      "input, select, textarea, button:not(.toast-close)"
    );
    (focusable || dialog).focus?.();
  });
}

/** A yes/no dialog. Replaces window.confirm. */
export function confirmDialog({
  title = "Are you sure?",
  message,
  confirmLabel = "Confirm",
  danger = false,
}) {
  return modal({
    title,
    render: (close) =>
      el(
        "div",
        {},
        el("div", { class: "modal-body" }, el("p", { text: message })),
        el(
          "div",
          { class: "modal-footer" },
          el("button", {
            class: "btn btn-outline",
            text: "Cancel",
            onclick: () => close(false),
          }),
          el("button", {
            class: `btn ${danger ? "btn-danger" : "btn-primary"}`,
            text: confirmLabel,
            onclick: () => close(true),
          })
        )
      ),
  });
}

/* --- Formatting ------------------------------------------------------- */

/** Format a percentage. Returns an em dash for null, never "null%". */
export function pct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return `${Number(value).toFixed(digits)}%`;
}

export function num(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "—";
  }
  return Number(value).toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function ordinal(n) {
  if (n === null || n === undefined) return "—";
  const value = Number(n);
  const remainder = value % 100;
  if (remainder >= 11 && remainder <= 13) return `${value}th`;
  return `${value}${["th", "st", "nd", "rd"][value % 10] || "th"}`;
}

export function formatDate(value, opts = { day: "numeric", month: "short" }) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleDateString(undefined, opts);
}

export function formatDateTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString(undefined, {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * A short "how long ago" label, e.g. "3d ago".
 *
 * Returns null for a missing value rather than a dash, so the caller can
 * decide how to present "never" - which in the student list is a
 * meaningful state, not just absent data.
 */
export function relativeTime(value) {
  if (!value) return null;

  const then = new Date(value);
  if (Number.isNaN(then.getTime())) return null;

  const seconds = Math.floor((Date.now() - then.getTime()) / 1000);
  if (seconds < 60) return "just now";

  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;

  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;

  return `${Math.floor(months / 12)}y ago`;
}

export function initials(name) {
  if (!name) return "?";
  return name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("");
}

/* --- Domain-specific display rules ------------------------------------ *
 * The mapping from a risk band to a badge lives here so that every table,
 * tile and list labels a "high" risk identically.                        */

export const RISK_BADGE = {
  high: { class: "badge-critical", label: "High risk" },
  medium: { class: "badge-warning", label: "Medium risk" },
  low: { class: "badge-good", label: "On track" },
  unknown: { class: "badge-neutral", label: "No data" },
};

export function riskBadge(band) {
  const spec = RISK_BADGE[band] || RISK_BADGE.unknown;
  return el("span", { class: `badge ${spec.class}`, text: spec.label });
}

export const TREND_DISPLAY = {
  improving: { class: "up", arrow: "↑", label: "Improving" },
  declining: { class: "down", arrow: "↓", label: "Declining" },
  stable: { class: "flat", arrow: "→", label: "Stable" },
  insufficient_data: { class: "flat", arrow: "", label: "Not enough data" },
};

/** Colour a meter by how the value sits against its requirement. */
export function meterState(value, threshold) {
  if (value === null || value === undefined) return "";
  if (value >= threshold) return "good";
  if (value >= threshold * 0.8) return "warning";
  return "critical";
}

/* --- Skeletons -------------------------------------------------------- */

export function skeletonRows(count, columns) {
  const fragment = document.createDocumentFragment();
  for (let i = 0; i < count; i += 1) {
    const row = el("tr");
    for (let c = 0; c < columns; c += 1) {
      row.append(el("td", {}, el("div", { class: "skeleton skeleton-line" })));
    }
    fragment.append(row);
  }
  return fragment;
}

export function emptyState({ icon = "\u{1F4ED}", title, text }) {
  return el(
    "div",
    { class: "empty" },
    el("div", { class: "empty-icon", text: icon }),
    el("div", { class: "empty-title", text: title }),
    text ? el("div", { class: "empty-text", text }) : null
  );
}

/** Read a CSS custom property, for handing theme colours to Chart.js. */
export function cssVar(name, fallback = "") {
  const value = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim();
  return value || fallback;
}
