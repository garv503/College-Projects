/* =====================================================================
   Admin console
   =====================================================================
   Four panels behind tabs: cohort overview, student list, CSV import and
   the audit log.

   The whole console was previously a single "Add Student" form. There
   was no way to list students, no way to see class performance, and the
   page was reachable by anyone who typed its filename because nothing
   checked a role - on the page or in the API.
   ===================================================================== */

import { api, requireSession, signOut } from "./api.js";
import {
  $,
  confirmDialog,
  el,
  emptyState,
  formatDateTime,
  initials,
  modal,
  notify,
  num,
  ordinal,
  pct,
  relativeTime,
  reportError,
  riskBadge,
  setText,
  skeletonRows,
} from "./ui.js";
import { gradeDistributionChart, passRateChart } from "./charts.js";

$("#logoutBtn").addEventListener("click", signOut);

/* Shared filter + paging state. Kept in one object so every panel reads
   the same cohort and a filter change can refresh whatever is visible. */
const state = {
  view: "overview",
  branchId: "",
  semester: "",
  search: "",
  risk: "",
  sort: "roll_no",
  order: "asc",
  page: 1,
  auditPage: 1,
  auditAction: "",
  role: "admin",
};

let searchTimer = null;

/* --- Boot -------------------------------------------------------------- */

(async function init() {
  let user;
  try {
    user = await requireSession({ role: ["admin", "faculty"] });
  } catch {
    return;
  }

  state.role = user.role;
  $("#userAvatar").textContent = initials(user.name);
  setText("#userName", user.name);
  setText("#userRole", user.role);

  // Faculty can read analytics and enter marks but not manage accounts,
  // so the controls they cannot use are removed rather than left to fail
  // with a 403 when clicked. The API enforces this independently - this
  // is only about not offering a dead end.
  if (user.role !== "admin") {
    $("#addStudentBtn").remove();
    $("#auditTab").remove();
  }

  await loadBranches();
  wireEvents();
  await refresh();
})();

async function loadBranches() {
  try {
    const branches = await api.get("/api/branches");
    const select = $("#branchFilter");
    for (const branch of branches) {
      select.append(
        el("option", { value: branch.branch_id },
           `${branch.code} — ${branch.name} (${branch.student_count})`)
      );
    }
  } catch (error) {
    reportError(error, "Could not load branches");
  }
}

/* --- Events ------------------------------------------------------------ */

function wireEvents() {
  document.querySelectorAll(".tab").forEach((tab) =>
    tab.addEventListener("click", () => switchView(tab.dataset.view))
  );

  $("#branchFilter").addEventListener("change", (e) => {
    state.branchId = e.target.value;
    state.page = 1;
    refresh();
  });

  $("#semesterFilter").addEventListener("change", (e) => {
    state.semester = e.target.value;
    state.page = 1;
    refresh();
  });

  // Debounced so typing a name is one request when the user stops, not
  // one per keystroke.
  $("#searchInput").addEventListener("input", (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.search = e.target.value.trim();
      state.page = 1;
      loadStudents();
    }, 300);
  });

  document.querySelectorAll("[data-risk]").forEach((button) =>
    button.addEventListener("click", () => {
      document
        .querySelectorAll("[data-risk]")
        .forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
      state.risk = button.dataset.risk;
      state.page = 1;
      loadStudents();
    })
  );

  document.querySelectorAll("th.sortable").forEach((th) =>
    th.addEventListener("click", () => {
      const column = th.dataset.sort;
      if (state.sort === column) {
        state.order = state.order === "asc" ? "desc" : "asc";
      } else {
        state.sort = column;
        state.order = "desc";
      }
      document
        .querySelectorAll("th.sortable")
        .forEach((other) => other.removeAttribute("aria-sort"));
      th.setAttribute(
        "aria-sort",
        state.order === "asc" ? "ascending" : "descending"
      );
      loadStudents();
    })
  );

  $("#prevPage").addEventListener("click", () => {
    if (state.page > 1) { state.page -= 1; loadStudents(); }
  });
  $("#nextPage").addEventListener("click", () => { state.page += 1; loadStudents(); });

  $("#viewAllRisk").addEventListener("click", () => {
    state.risk = "high";
    document
      .querySelectorAll("[data-risk]")
      .forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.risk === "high")));
    switchView("students");
  });

  $("#exportBtn").addEventListener("click", exportCohort);
  $("#addStudentBtn")?.addEventListener("click", openAddStudent);
  $("#templateBtn").addEventListener("click", downloadTemplate);

  wireDropzone("#marksDrop", "#marksFile", "#marksResult", "/api/admin/import/marks");
  wireDropzone("#attendanceDrop", "#attendanceFile", "#attendanceResult",
               "/api/admin/import/attendance");

  $("#actionFilter")?.addEventListener("change", (e) => {
    state.auditAction = e.target.value;
    state.auditPage = 1;
    loadAudit();
  });
  $("#auditPrev")?.addEventListener("click", () => {
    if (state.auditPage > 1) { state.auditPage -= 1; loadAudit(); }
  });
  $("#auditNext")?.addEventListener("click", () => { state.auditPage += 1; loadAudit(); });
}

function switchView(view) {
  state.view = view;
  document.querySelectorAll(".tab").forEach((tab) =>
    tab.setAttribute("aria-selected", String(tab.dataset.view === view))
  );
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.panel !== view;
  });

  // The branch/semester filters describe a cohort, which is meaningless
  // for the import screen and the audit log. Leaving them on those tabs
  // implies they filter something there, and they do not.
  $(".filters").hidden = view === "import" || view === "audit";

  refresh();
}

function refresh() {
  if (state.view === "overview") return loadOverview();
  if (state.view === "students") return loadStudents();
  if (state.view === "audit") return loadAudit();
  return Promise.resolve();
}

const cohortParams = () => ({ branch_id: state.branchId, semester: state.semester });

/* --- Overview ---------------------------------------------------------- */

async function loadOverview() {
  $("#atRiskTable").replaceChildren(skeletonRows(4, 6));
  $("#subjectStatsTable").replaceChildren(skeletonRows(4, 6));

  try {
    const data = await api.get("/api/admin/overview", cohortParams());
    renderKpis(data.summary);
    renderAtRisk(data.at_risk);
    renderSubjectStats(data.subject_stats);

    if (data.grade_distribution?.length) {
      gradeDistributionChart("gradeChart", data.grade_distribution);
    }
    if (data.subject_stats?.length) {
      passRateChart("passRateChart", data.subject_stats.slice(0, 10));
    }
  } catch (error) {
    reportError(error, "Could not load the overview");
  }
}

function renderKpis(summary = {}) {
  const count = summary.student_count || 0;

  setText("#kpiStudents", num(count));
  setText(
    "#kpiStudentsMeta",
    summary.students_with_backlogs
      ? `${summary.students_with_backlogs} carrying backlogs`
      : "No backlogs recorded"
  );

  $("#kpiMarks").replaceChildren(
    document.createTextNode(
      summary.avg_mark_percent == null ? "—" : Number(summary.avg_mark_percent).toFixed(1)
    ),
    el("span", { class: "unit", text: summary.avg_mark_percent == null ? "" : "%" })
  );
  setText("#kpiMarksMeta", "Credit-weighted class average");

  $("#kpiAttendance").replaceChildren(
    document.createTextNode(
      summary.avg_attendance_percent == null
        ? "—"
        : Number(summary.avg_attendance_percent).toFixed(1)
    ),
    el("span", {
      class: "unit",
      text: summary.avg_attendance_percent == null ? "" : "%",
    })
  );
  setText("#kpiAttendanceMeta", "75% is the requirement");

  const high = summary.high_risk_count || 0;
  const medium = summary.medium_risk_count || 0;
  setText("#kpiRisk", num(high + medium));

  const meta = $("#kpiRiskMeta");
  meta.replaceChildren();
  if (high) {
    meta.append(el("span", { class: "badge badge-critical", text: `${high} high` }));
  }
  if (medium) {
    meta.append(el("span", { class: "badge badge-warning", text: `${medium} medium` }));
  }
  if (!high && !medium) meta.textContent = "Everyone on track";
}

function renderAtRisk(students = []) {
  const body = $("#atRiskTable");
  body.replaceChildren();

  if (!students.length) {
    body.append(
      el("tr", {}, el("td", { colspan: "6" },
        emptyState({ icon: "✓", title: "No students flagged",
                     text: "Everyone in this cohort is meeting the requirements." })))
    );
    return;
  }

  for (const student of students) {
    body.append(
      el(
        "tr",
        {},
        el("td", {},
          el("div", { class: "primary-cell", text: student.student_name }),
          el("div", { class: "text-xs muted", text: student.roll_no })),
        el("td", { class: "text-sm", text: `${student.branch_code} · Sem ${student.semester}` }),
        el("td", { class: "num tabular", text: pct(student.avg_mark_percent) }),
        el("td", { class: "num tabular", text: pct(student.avg_attendance_percent) }),
        el("td", { class: "num" },
          el("span", { class: "risk-score", text: String(Math.round(student.risk_score)) }),
          el("div", {}, riskBadge(student.risk_band))),
        // The reason is what turns a ranked list into something someone
        // can act on. Set as text, never innerHTML.
        el("td", { class: "why-cell", text: (student.reasons || [])[0] || "—" })
      )
    );
  }
}

function renderSubjectStats(subjects = []) {
  const body = $("#subjectStatsTable");
  body.replaceChildren();

  if (!subjects.length) {
    body.append(el("tr", {}, el("td", { colspan: "6" },
      emptyState({ title: "No subject data", text: "No marks have been recorded yet." }))));
    return;
  }

  for (const subject of subjects) {
    const rate = Number(subject.pass_rate);
    const badge =
      rate >= 75 ? "badge-good" : rate >= 60 ? "badge-warning" : "badge-critical";

    body.append(
      el(
        "tr",
        {},
        el("td", {},
          el("div", { class: "primary-cell", text: subject.subject_name }),
          el("div", { class: "text-xs muted",
                      text: `${subject.subject_code} · ${subject.branch_code} Sem ${subject.semester}` })),
        el("td", { class: "num tabular", text: num(subject.enrolled_count) }),
        el("td", { class: "num tabular", text: pct(subject.avg_mark_percent) }),
        // Standard deviation: a high spread means the class is splitting
        // into two groups, which an average alone hides completely.
        el("td", { class: "num tabular muted",
                   text: subject.stddev_mark_percent == null
                     ? "—" : `±${Number(subject.stddev_mark_percent).toFixed(1)}` }),
        el("td", { class: "num tabular", text: pct(subject.avg_attendance_percent) }),
        el("td", { class: "num" },
          el("span", { class: `badge ${badge}`, text: pct(subject.pass_rate, 0) }))
      )
    );
  }
}

/* --- Students ---------------------------------------------------------- */

async function loadStudents() {
  const body = $("#studentsTable");
  body.replaceChildren(skeletonRows(8, 9));

  try {
    const data = await api.get("/api/students", {
      ...cohortParams(),
      q: state.search,
      risk: state.risk,
      sort: state.sort,
      order: state.order,
      page: state.page,
      per_page: 20,
    });

    renderStudents(data.students);

    const { page, pages, total } = data.pagination;
    setText("#studentCount", `${num(total)} student${total === 1 ? "" : "s"}`);
    setText("#pageInfo", total ? `Page ${page} of ${pages || 1}` : "No results");
    $("#prevPage").disabled = page <= 1;
    $("#nextPage").disabled = page >= (pages || 1);
  } catch (error) {
    reportError(error, "Could not load students");
  }
}

function renderStudents(students = []) {
  const body = $("#studentsTable");
  body.replaceChildren();

  if (!students.length) {
    body.append(el("tr", {}, el("td", { colspan: "9" },
      emptyState({ icon: "🔍", title: "No students match",
                   text: "Try clearing the search or the filters." }))));
    return;
  }

  for (const student of students) {
    const actionButtons = el("div", { class: "row", style: "gap: var(--sp-2)" });
    const actions = el("td", { class: "nowrap" }, actionButtons);

    if (state.role === "admin") {
      actionButtons.append(
        el("button", {
          class: "btn btn-sm",
          text: "View password",
          onclick: () => viewCredentials(student),
        }),
        el("button", {
          class: "btn btn-sm",
          text: "Reset password",
          onclick: () => resetPassword(student),
        })
      );
    }

    body.append(
      el(
        "tr",
        {},
        el("td", {},
          el("div", { class: "primary-cell", text: student.student_name }),
          el("div", { class: "text-xs muted", text: student.roll_no })),
        el("td", { class: "text-sm", text: `${student.branch_code} · Sem ${student.semester}` }),
        el("td", { class: "num tabular", text: pct(student.avg_mark_percent) }),
        el("td", { class: "num tabular", text: pct(student.avg_attendance_percent) }),
        el("td", { class: "num tabular",
                   text: student.class_rank
                     ? `${ordinal(student.class_rank)}/${student.cohort_size}` : "—" }),
        el("td", { class: "num" },
          el("span", { class: "risk-score", text: String(Math.round(student.risk_score)) })),
        el("td", {}, riskBadge(student.risk_band)),
        lastSeenCell(student.last_login_at),
        actions
      )
    );
  }
}

/**
 * The "Last seen" cell.
 *
 * "Never" is the point of this column, not a missing value - it means the
 * student was issued credentials and has not used them, which is usually
 * a handover problem rather than an academic one. So it gets a badge
 * rather than an em dash, and the exact timestamp goes in the tooltip.
 */
function lastSeenCell(lastLoginAt) {
  const relative = relativeTime(lastLoginAt);

  if (!relative) {
    return el(
      "td",
      { class: "nowrap" },
      el("span", { class: "badge badge-warning", text: "Never" })
    );
  }

  return el(
    "td",
    { class: "text-sm muted nowrap", title: formatDateTime(lastLoginAt) },
    relative
  );
}

async function resetPassword(student) {
  const confirmed = await confirmDialog({
    title: "Reset password?",
    message: `A new random password will be generated for ${student.student_name} (${student.roll_no}). Their current password stops working immediately.`,
    confirmLabel: "Reset password",
    danger: true,
  });
  if (!confirmed) return;

  try {
    const result = await api.post(
      `/api/admin/students/${student.student_id}/reset-password`
    );
    await showCredentials(
      "Password reset",
      result.username,
      result.password,
      "Their old password no longer works."
    );
  } catch (error) {
    reportError(error, "Could not reset the password");
  }
}

/* --- Add student -------------------------------------------------------- */

async function openAddStudent() {
  const branches = await api.get("/api/branches").catch(() => []);

  const created = await modal({
    title: "Add student",
    render: (close) => {
      const name = el("input", { class: "input", placeholder: "Priya Nair" });
      const rollNo = el("input", { class: "input", placeholder: "CSE2023042" });
      const email = el("input", { class: "input", type: "email",
                                  placeholder: "priya@college.edu" });
      const branch = el("select", { class: "select" },
        ...branches.map((b) => el("option", { value: b.branch_id }, `${b.code} — ${b.name}`)));
      const semester = el("select", { class: "select" },
        ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => el("option", { value: n }, String(n))));
      const year = el("input", { class: "input", type: "number",
                                 value: String(new Date().getFullYear()) });
      const error = el("p", { class: "field-error hidden" });

      const submit = el("button", {
        class: "btn btn-primary",
        text: "Create student",
        onclick: async () => {
          error.classList.add("hidden");
          submit.classList.add("is-loading");
          submit.disabled = true;
          try {
            const result = await api.post("/api/admin/students", {
              name: name.value.trim(),
              roll_no: rollNo.value.trim(),
              email: email.value.trim(),
              branch_id: Number(branch.value),
              semester: Number(semester.value),
              admission_year: Number(year.value),
            });
            close(result);
          } catch (err) {
            error.textContent = err.message;
            error.classList.remove("hidden");
          } finally {
            submit.classList.remove("is-loading");
            submit.disabled = false;
          }
        },
      });

      const field = (label, control, hint) =>
        el("div", { class: "field" },
           el("label", { class: "label", text: label }),
           control,
           hint ? el("div", { class: "field-hint", text: hint }) : null);

      return el(
        "div",
        {},
        el("div", { class: "modal-body stack-sm" },
          field("Full name", name),
          field("Roll number", rollNo, "Becomes their username. Must be unique."),
          field("Email", email),
          el("div", { class: "grid", style: "grid-template-columns: 1fr 1fr" },
             field("Branch", branch), field("Semester", semester)),
          field("Admission year", year),
          el("div", { class: "callout callout-info" },
             el("span", { class: "callout-icon", text: "ℹ" }),
             el("span", { text: "They will be enrolled automatically in every subject for that branch and semester." })),
          error),
        el("div", { class: "modal-footer" },
           el("button", { class: "btn btn-outline", text: "Cancel", onclick: () => close(null) }),
           submit)
      );
    },
  });

  if (!created) return;

  await showCredentials(
    `${created.name} added`,
    created.credentials.username,
    created.credentials.password,
    `Enrolled in ${created.subjects_enrolled} subject${created.subjects_enrolled === 1 ? "" : "s"}. ` +
      "You can look this password up again from the student list."
  );
  refresh();
}

async function viewCredentials(student) {
  try {
    const result = await api.get(
      `/api/admin/students/${student.student_id}/credentials`
    );
    await showCredentials(
      `${student.student_name}'s login`,
      result.username,
      result.password
    );
  } catch (error) {
    reportError(error, "Could not look up the password");
  }
}

/**
 * Show a student's username and password.
 *
 * Passwords are stored as plain text in this build (see
 * backend/security.py), so - unlike a hashed password - this can be
 * called again later from the student list, not just once at creation.
 * The callout still says the quiet part out loud: whoever reads this
 * screen can sign in as this student.
 */
function showCredentials(title, username, password, note) {
  return modal({
    title,
    render: (close) =>
      el(
        "div",
        {},
        el("div", { class: "modal-body stack-sm" },
          note ? el("p", { class: "text-sm muted", text: note }) : null,
          el("div", { class: "callout callout-warning" },
             el("span", { class: "callout-icon", text: "⚠" }),
             el("span", { text: "Anyone with this password can sign in as this student. Share it only with them." })),
          el("div", { class: "credentials" },
             el("div", { class: "credential-row" },
                el("span", { class: "credential-label", text: "Username" }),
                el("code", { class: "credential-value", text: username })),
             el("div", { class: "credential-row" },
                el("span", { class: "credential-label", text: "Password" }),
                el("code", { class: "credential-value", text: password })))),
        el("div", { class: "modal-footer" },
           el("button", {
             class: "btn btn-outline",
             text: "Copy",
             onclick: async (event) => {
               try {
                 await navigator.clipboard.writeText(`${username} / ${password}`);
                 event.currentTarget.textContent = "Copied ✓";
               } catch {
                 // The clipboard API needs a secure context, so it fails
                 // over plain http on a LAN address. The value is
                 // selectable (user-select: all) as the fallback.
                 notify.warning("Could not copy — select the text instead");
               }
             },
           }),
           el("button", { class: "btn btn-primary", text: "Done", onclick: () => close(true) }))
      ),
  });
}

/* --- Import ------------------------------------------------------------- */

function wireDropzone(dropSelector, inputSelector, resultSelector, endpoint) {
  const dropzone = $(dropSelector);
  const input = $(inputSelector);
  const result = $(resultSelector);
  if (!dropzone) return;

  dropzone.addEventListener("click", () => input.click());
  dropzone.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      input.click();
    }
  });

  // dragover must be prevented or the browser navigates to the file.
  ["dragenter", "dragover"].forEach((type) =>
    dropzone.addEventListener(type, (event) => {
      event.preventDefault();
      dropzone.classList.add("is-dragging");
    })
  );
  ["dragleave", "drop"].forEach((type) =>
    dropzone.addEventListener(type, () => dropzone.classList.remove("is-dragging"))
  );

  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    const file = event.dataTransfer?.files?.[0];
    if (file) upload(file);
  });

  input.addEventListener("change", () => {
    if (input.files?.[0]) upload(input.files[0]);
  });

  async function upload(file) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      notify.error("Only .csv files are accepted");
      return;
    }

    dropzone.classList.add("is-busy");
    result.replaceChildren(el("div", { class: "skeleton skeleton-line" }));

    try {
      const outcome = await api.upload(endpoint, file);
      result.replaceChildren(
        el("div", { class: "callout callout-good" },
           el("span", { class: "callout-icon", text: "✓" }),
           el("span", { text: `Imported ${outcome.imported} row${outcome.imported === 1 ? "" : "s"} from ${file.name}.` }))
      );
      notify.success(`Imported ${outcome.imported} rows`);
      if (state.view === "overview") loadOverview();
    } catch (error) {
      renderImportErrors(result, error, file.name);
    } finally {
      dropzone.classList.remove("is-busy");
      input.value = ""; // let the same file be re-selected after a fix
    }
  }
}

function renderImportErrors(container, error, filename) {
  const rows = error.details?.errors || [];

  container.replaceChildren(
    el("div", { class: "callout callout-critical" },
       el("span", { class: "callout-icon", text: "✕" }),
       el("span", { text: rows.length
         ? `${filename}: ${rows.length} row${rows.length === 1 ? "" : "s"} rejected. Nothing was imported.`
         : error.message })),
    rows.length
      ? el("div", { class: "import-errors", style: "margin-top: var(--sp-3)" },
           ...rows.map((row) =>
             el("div", { class: "import-error-row" },
                el("span", { class: "import-error-line", text: `line ${row.line}` }),
                el("span", { text: row.message }))))
      : null
  );
}

async function downloadTemplate(event) {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await api.download("/api/admin/import/template.csv");
    notify.success("Template downloaded");
  } catch (error) {
    reportError(error, "Could not download the template");
  } finally {
    button.disabled = false;
  }
}

async function exportCohort(event) {
  const button = event.currentTarget;
  button.classList.add("is-loading");
  button.disabled = true;
  try {
    const filename = await api.download("/api/admin/export/cohort.csv", cohortParams());
    notify.success(`Downloaded ${filename}`);
  } catch (error) {
    reportError(error, "Could not export");
  } finally {
    button.classList.remove("is-loading");
    button.disabled = false;
  }
}

/* --- Audit log ---------------------------------------------------------- */

async function loadAudit() {
  const body = $("#auditTable");
  if (!body) return;
  body.replaceChildren(skeletonRows(10, 4));

  try {
    const data = await api.get("/api/admin/audit-log", {
      action: state.auditAction,
      page: state.auditPage,
      per_page: 25,
    });

    body.replaceChildren();

    if (!data.entries.length) {
      body.append(el("tr", {}, el("td", { colspan: "4" },
        emptyState({ title: "No entries", text: "Nothing matches this filter yet." }))));
    }

    for (const entry of data.entries) {
      body.append(
        el(
          "tr",
          {},
          el("td", { class: "text-sm nowrap muted", text: formatDateTime(entry.created_at) }),
          el("td", { class: "text-sm" },
             entry.actor
               ? el("span", { class: "primary-cell", text: entry.actor })
               : el("span", { class: "muted", text: "system" })),
          el("td", {}, el("span", { class: "badge badge-plain", text: entry.action })),
          el("td", { class: "text-sm muted mono", text: formatDetails(entry.details) })
        )
      );
    }

    const { page, pages, total } = data.pagination;
    setText("#auditPageInfo", `${num(total)} entries · page ${page} of ${pages || 1}`);
    $("#auditPrev").disabled = page <= 1;
    $("#auditNext").disabled = page >= (pages || 1);
  } catch (error) {
    reportError(error, "Could not load the audit log");
  }
}

/** Render the JSON `details` column as a compact key=value line. */
function formatDetails(details) {
  if (!details) return "—";
  let value = details;
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch {
      return value;
    }
  }
  if (typeof value !== "object") return String(value);

  return Object.entries(value)
    .map(([key, v]) => `${key}=${typeof v === "object" ? JSON.stringify(v) : v}`)
    .join("  ");
}
