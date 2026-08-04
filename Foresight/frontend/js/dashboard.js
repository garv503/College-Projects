/* =====================================================================
   Student dashboard
   =====================================================================
   Renders `GET /api/students/me` - one request that returns the summary,
   risk assessment, trend, subjects, timeline and cohort comparison.

   Note what the page never does: it does not read a student id from the
   URL or from localStorage. The server identifies the student from the
   signed token, so there is nothing here for a user to tamper with.
   ===================================================================== */

import { api, requireSession, signOut } from "./api.js";
import {
  $,
  el,
  formatDate,
  initials,
  meterState,
  modal,
  notify,
  num,
  ordinal,
  pct,
  reportError,
  riskBadge,
  setText,
  TREND_DISPLAY,
} from "./ui.js";
import {
  attendanceChart,
  renderLegend,
  seriesColor,
  subjectComparisonChart,
  trendChart,
} from "./charts.js";

const ATTENDANCE_REQUIREMENT = 75;

$("#logoutBtn").addEventListener("click", signOut);

let currentStudentId = null;

/* --- Boot ------------------------------------------------------------- */

(async function init() {
  let user;
  try {
    user = await requireSession({ role: ["student", "admin", "faculty"] });
  } catch {
    return; // requireSession has already redirected.
  }

  $("#userAvatar").textContent = initials(user.name);

  if (sessionStorage.getItem("fs.mustChangePassword")) {
    sessionStorage.removeItem("fs.mustChangePassword");
    notify.warning(
      "You are still using the password you were issued. Change it now.",
      "Set your own password"
    );
  }

  // Staff who land here have no student record of their own, so send
  // them to the console that does apply to them.
  if (user.role !== "student") {
    location.replace("admin.html");
    return;
  }

  await loadDashboard();
})();

async function loadDashboard() {
  try {
    const data = await api.get("/api/students/me");
    currentStudentId = data.student.student_id;
    render(data);
  } catch (error) {
    if (error.status === 404) {
      renderEmpty();
      return;
    }
    reportError(error, "Could not load your dashboard");
  }
}

/* --- Render ----------------------------------------------------------- */

function render(data) {
  const { student, summary, risk, trend, subjects, timeline, comparison } = data;

  // Identity
  setText("#studentName", student.name);
  setText(
    "#studentMeta",
    `${student.roll_no} · ${student.branch} · Semester ${student.semester}`
  );
  $("#riskBadgeSlot").replaceChildren(riskBadge(risk.band));

  // --- Stat tiles ---
  renderMarks(summary);
  renderAttendance(summary);
  renderRank(summary);
  renderTrend(trend);

  // --- Risk explanation ---
  renderRisk(risk);

  // --- Charts ---
  if (comparison.length) {
    subjectComparisonChart("comparisonChart", comparison);
    renderLegend("#comparisonLegend", [
      { label: "You", color: seriesColor(0) },
      { label: "Class average", color: seriesColor(1) },
    ]);
  }

  if (timeline.length) {
    trendChart("trendChart", timeline);
    // One legend entry per subject, in the same first-seen order the
    // chart assigns its colours.
    const codes = [...new Set(timeline.map((t) => t.subject_code))];
    renderLegend(
      "#trendLegend",
      codes.map((code, index) => ({ label: code, color: seriesColor(index) })),
      { line: true }
    );
  }

  if (subjects.length) {
    attendanceChart("attendanceChart", subjects, ATTENDANCE_REQUIREMENT);
    setText(
      "#attendanceSub",
      `${ATTENDANCE_REQUIREMENT}% is required. Bars below it are highlighted.`
    );
  }

  // --- Table ---
  renderSubjectTable(subjects);
}

function renderMarks(summary) {
  const value = summary.average_marks;
  $("#statMarks").innerHTML = "";
  $("#statMarks").append(
    document.createTextNode(value === null ? "—" : Number(value).toFixed(1)),
    el("span", { class: "unit", text: value === null ? "" : "%" })
  );

  const parts = [];
  if (summary.highest_subject !== null) {
    parts.push(`Best ${pct(summary.highest_subject)}`);
  }
  if (summary.lowest_subject !== null) {
    parts.push(`lowest ${pct(summary.lowest_subject)}`);
  }
  setText("#statMarksMeta", parts.join(" · "));
}

function renderAttendance(summary) {
  const value = summary.average_attendance;
  $("#statAttendance").innerHTML = "";
  $("#statAttendance").append(
    document.createTextNode(value === null ? "—" : Number(value).toFixed(1)),
    el("span", { class: "unit", text: value === null ? "" : "%" })
  );

  const meta = $("#statAttendanceMeta");
  meta.replaceChildren();
  if (value !== null) {
    const short = value < ATTENDANCE_REQUIREMENT;
    meta.append(
      el("span", {
        class: `stat-delta ${short ? "down" : "up"}`,
        text: short
          ? `↓ ${(ATTENDANCE_REQUIREMENT - value).toFixed(1)} below requirement`
          : `↑ meets the ${ATTENDANCE_REQUIREMENT}% requirement`,
      })
    );
  }
}

function renderRank(summary) {
  if (!summary.class_rank) {
    setText("#statRank", "—");
    return;
  }
  $("#statRank").textContent = ordinal(summary.class_rank);
  setText(
    "#statRankMeta",
    `of ${num(summary.cohort_size)} · top ${Math.max(
      1,
      Math.round(100 - (summary.percentile ?? 0))
    )}%`
  );
}

function renderTrend(trend) {
  const display = TREND_DISPLAY[trend.direction] || TREND_DISPLAY.stable;
  $("#statTrend").textContent = display.label;
  $("#statTrend").style.fontSize = "var(--fs-xl)";

  const meta = $("#statTrendMeta");
  meta.replaceChildren();

  if (trend.direction === "insufficient_data") {
    meta.textContent = trend.message;
    return;
  }

  meta.append(
    el("span", {
      class: `stat-delta ${display.class}`,
      text: `${display.arrow} ${Math.abs(trend.change).toFixed(1)} pts`,
    }),
    document.createTextNode("vs earlier assessments")
  );
}

function renderRisk(risk) {
  const card = $("#riskCard");
  card.hidden = false;

  const bandText = {
    high: "Needs immediate attention",
    medium: "Worth keeping an eye on",
    low: "On track",
    unknown: "Not enough data yet",
  };

  // The score is only shown when it is non-zero. A student can sit in
  // the medium band on the warning threshold (below 55%) while
  // triggering none of the scored signals, and "worth keeping an eye
  // on · risk score 0/100" reads as a contradiction.
  const label = bandText[risk.band] || "";
  setText(
    "#riskSubtitle",
    risk.score > 0 ? `${label} · risk score ${risk.score}/100` : label
  );

  $("#riskReasons").replaceChildren(
    ...risk.reasons.map((reason) => el("div", { class: "reason-item", text: reason }))
  );

  const recommendations = $("#riskRecommendations");
  recommendations.replaceChildren();

  if (risk.recommendations.length) {
    const tone =
      risk.band === "high"
        ? "callout-critical"
        : risk.band === "medium"
        ? "callout-warning"
        : "callout-good";

    recommendations.append(
      el(
        "div",
        { class: `callout ${tone}` },
        el("span", { class: "callout-icon", text: risk.band === "low" ? "✓" : "→" }),
        el(
          "div",
          {},
          el("strong", { text: "Suggested next steps" }),
          el(
            "ul",
            { class: "list-reset", style: "margin-top:4px" },
            ...risk.recommendations.map((r) => el("li", { text: `· ${r}` }))
          )
        )
      )
    );
  }
}

function renderSubjectTable(subjects) {
  const body = $("#subjectTable");
  body.replaceChildren();

  if (!subjects.length) {
    body.append(
      el("tr", {}, el("td", { colspan: "5" }, el("div", { class: "empty", text: "No subjects enrolled yet" })))
    );
    return;
  }

  for (const subject of subjects) {
    const attendance = subject.attendance_percent;
    const state = meterState(attendance, ATTENDANCE_REQUIREMENT);

    const resultBadge = {
      pass: { class: "badge-good", label: "Pass" },
      fail: { class: "badge-critical", label: "Fail" },
      pending: { class: "badge-neutral", label: "Pending" },
    }[subject.result] || { class: "badge-neutral", label: "—" };

    body.append(
      el(
        "tr",
        {},
        el(
          "td",
          {},
          el("div", { class: "primary-cell", text: subject.subject_name }),
          el("div", {
            class: "text-xs muted",
            text: `${subject.subject_code} · ${subject.assessment_count} assessment${
              subject.assessment_count === 1 ? "" : "s"
            }`,
          })
        ),
        el("td", { class: "num tabular", text: String(subject.credits) }),
        el("td", { class: "num tabular", text: pct(subject.mark_percent) }),
        el(
          "td",
          { style: "min-width:150px" },
          el(
            "div",
            { class: "row", style: "gap: var(--sp-3)" },
            el(
              "div",
              { class: "meter", style: "flex:1", title: `${ATTENDANCE_REQUIREMENT}% required` },
              el("div", {
                class: `meter-fill ${state}`,
                style: `width:${Math.min(100, Number(attendance) || 0)}%`,
              }),
              // Marks where the bar needs to reach - this is what makes
              // it a meter rather than a decorative progress bar.
              el("div", {
                class: "meter-mark",
                style: `left:${ATTENDANCE_REQUIREMENT}%`,
              })
            ),
            el("span", {
              class: "text-sm tabular nowrap muted",
              text: pct(attendance, 0),
            })
          ),
          el("div", {
            class: "text-xs muted",
            text:
              subject.total_classes
                ? `${subject.attended_classes}/${subject.total_classes} classes`
                : "No classes recorded",
          })
        ),
        el("td", {}, el("span", { class: `badge ${resultBadge.class}`, text: resultBadge.label }))
      )
    );
  }
}

function renderEmpty() {
  setText("#studentName", "No records yet");
  setText("#studentMeta", "");
  $("#riskCard").hidden = true;
  notify.info("Your marks have not been uploaded yet.");
}

/* --- Report card download --------------------------------------------- */

$("#downloadBtn").addEventListener("click", async (event) => {
  const button = event.currentTarget;
  if (!currentStudentId) return;

  button.classList.add("is-loading");
  button.disabled = true;
  try {
    const filename = await api.download(
      `/api/students/${currentStudentId}/report-card.csv`
    );
    notify.success(`Downloaded ${filename}`);
  } catch (error) {
    reportError(error, "Could not download your report card");
  } finally {
    button.classList.remove("is-loading");
    button.disabled = false;
  }
});

/* --- Change password --------------------------------------------------- */

$("#passwordBtn").addEventListener("click", async () => {
  const policy = await api.get("/api/auth/password-policy").catch(() => null);

  await modal({
    title: "Change password",
    render: (close) => {
      const current = el("input", {
        class: "input",
        type: "password",
        autocomplete: "current-password",
      });
      const next = el("input", {
        class: "input",
        type: "password",
        autocomplete: "new-password",
      });
      const confirm = el("input", {
        class: "input",
        type: "password",
        autocomplete: "new-password",
      });
      const error = el("p", { class: "field-error hidden" });

      const submit = el("button", {
        class: "btn btn-primary",
        text: "Update password",
        onclick: async () => {
          error.classList.add("hidden");

          if (next.value !== confirm.value) {
            error.textContent = "The two new passwords do not match";
            error.classList.remove("hidden");
            return;
          }

          submit.classList.add("is-loading");
          submit.disabled = true;
          try {
            await api.post("/api/auth/change-password", {
              current_password: current.value,
              new_password: next.value,
            });
            notify.success("Password updated");
            close(true);
          } catch (err) {
            error.textContent = err.message;
            error.classList.remove("hidden");
          } finally {
            submit.classList.remove("is-loading");
            submit.disabled = false;
          }
        },
      });

      return el(
        "div",
        {},
        el(
          "div",
          { class: "modal-body stack-sm" },
          el("div", { class: "field" }, el("label", { class: "label", text: "Current password" }), current),
          el("div", { class: "field" }, el("label", { class: "label", text: "New password" }), next),
          el("div", { class: "field" }, el("label", { class: "label", text: "Confirm new password" }), confirm),
          policy
            ? el("div", {
                class: "field-hint",
                text: `Requires: ${policy.requirements.join(", ").toLowerCase()}.`,
              })
            : null,
          error
        ),
        el(
          "div",
          { class: "modal-footer" },
          el("button", { class: "btn btn-outline", text: "Cancel", onclick: () => close(null) }),
          submit
        )
      );
    },
  });
});
