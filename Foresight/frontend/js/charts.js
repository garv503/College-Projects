/* =====================================================================
   Charts
   =====================================================================
   Every chart in the app is built here so the styling rules are applied
   once rather than re-argued per chart.

   The rules being followed:

   * The form is chosen by the data's job. Magnitude -> bar with a
     sequential (single-hue) ramp. Identity -> line/bar with categorical
     colours. A single headline number is a stat tile, not a one-bar
     chart, so it is not in this file at all.

   * Categorical colours are assigned in fixed slot order and never
     cycled. A ninth series would fold into "Other" rather than invent a
     hue, because a generated colour is indistinguishable from an
     existing one to a colourblind reader.

   * Never two y-axes. Two measures of different scale get two charts.

   * Marks are thin: 2px lines, bars capped at 24px, gridlines hairline
     and recessive, no drop shadows on data.

   * Colours come from CSS custom properties rather than hardcoded hex,
     so every chart draws from the same palette declared in tokens.css.
   ===================================================================== */

import { cssVar } from "./ui.js";

/** Live registry of mounted charts, keyed by canvas id. */
const registry = new Map();

const SERIES_VARS = [
  "--series-1",
  "--series-2",
  "--series-3",
  "--series-4",
  "--series-5",
];

export function seriesColor(index) {
  // Clamped, not wrapped: the caller should have folded a 6th series into
  // "Other" instead. Repeating slot 1 would silently imply two different
  // things are the same series.
  return cssVar(SERIES_VARS[Math.min(index, SERIES_VARS.length - 1)]);
}

/** Read the chart's chrome colours (gridlines, ink, surface) from CSS. */
function chrome() {
  return {
    text1: cssVar("--text-1", "#10131a"),
    text3: cssVar("--text-3", "#767e8f"),
    grid: cssVar("--grid", "#eceff4"),
    border: cssVar("--border", "#e3e6ec"),
    surface: cssVar("--surface", "#ffffff"),
    accent: cssVar("--accent", "#2a78d6"),
    muted: cssVar("--series-muted", "#c2c8d4"),
  };
}

/**
 * Options shared by every chart.
 *
 * `maintainAspectRatio: false` makes the canvas fill its parent, which
 * is why each one sits inside a `.chart-frame` with an explicit height -
 * a parent that sizes to its content would grow on every animation frame.
 */
function baseOptions() {
  const c = chrome();

  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 420, easing: "easeOutQuart" },
    // Hovering anywhere in the column highlights that column's point,
    // rather than requiring a hit on an 8px dot.
    interaction: { mode: "index", intersect: false },
    plugins: {
      // Legends are rendered as HTML next to the chart, not by Chart.js:
      // real DOM text is selectable, screen-reader visible, and wraps
      // properly on a narrow screen.
      legend: { display: false },
      tooltip: {
        backgroundColor: c.surface,
        titleColor: c.text1,
        bodyColor: c.text1,
        borderColor: c.border,
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        displayColors: true,
        boxWidth: 8,
        boxHeight: 8,
        boxPadding: 4,
        usePointStyle: true,
        titleFont: { family: cssVar("--font"), size: 12, weight: "600" },
        bodyFont: { family: cssVar("--font"), size: 12 },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: c.border },
        ticks: {
          color: c.text3,
          font: { family: cssVar("--font"), size: 11 },
          maxRotation: 0,
          autoSkipPadding: 12,
        },
      },
      y: {
        beginAtZero: true,
        grid: { color: c.grid, drawTicks: false },
        border: { display: false, dash: undefined },
        ticks: {
          color: c.text3,
          font: { family: cssVar("--font"), size: 11 },
          padding: 8,
          maxTicksLimit: 6,
        },
      },
    },
  };
}

/** Merge helper - shallow per section, which is all these options need. */
function merge(base, extra) {
  const out = { ...base, ...extra };
  for (const key of ["plugins", "scales", "interaction", "animation"]) {
    if (base[key] && extra[key]) {
      out[key] = { ...base[key], ...extra[key] };
      for (const inner of Object.keys(base[key])) {
        if (extra[key][inner] && typeof base[key][inner] === "object") {
          out[key][inner] = { ...base[key][inner], ...extra[key][inner] };
        }
      }
    }
  }
  return out;
}

/**
 * Create (or replace) a chart on a canvas.
 *
 * Destroying any previous chart on the same canvas first is what makes
 * these builders safe to call again with fresh data (a filter change, a
 * cohort switch) rather than layering a second chart on top.
 */
function mount(canvasId, build) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  registry.get(canvasId)?.destroy();

  const chart = build(canvas);
  registry.set(canvasId, chart);
  return chart;
}

export function destroyChart(canvasId) {
  registry.get(canvasId)?.destroy();
  registry.delete(canvasId);
}

export function destroyAllCharts() {
  for (const chart of registry.values()) chart?.destroy();
  registry.clear();
}

/* =====================================================================
   Chart builders
   ===================================================================== */

/**
 * Marks per subject, with the class average as a second series.
 *
 * Job: compare one entity against a reference, per category. Two series,
 * so categorical colours - slot 1 for the student, slot 2 for the class.
 * Horizontal, because subject names are long and would otherwise be
 * rotated 45 degrees and become hard to read.
 */
export function subjectComparisonChart(canvasId, rows) {
  return mount(canvasId, (canvas) => {
    const c = chrome();
    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map((r) => r.subject_code),
        datasets: [
          {
            label: "You",
            data: rows.map((r) => toNum(r.student_percent)),
            backgroundColor: seriesColor(0),
            // 4px rounded data-end, square at the baseline.
            borderRadius: { topLeft: 0, topRight: 4, bottomLeft: 0, bottomRight: 4 },
            borderSkipped: "start",
            maxBarThickness: 18,
          },
          {
            label: "Class average",
            data: rows.map((r) => toNum(r.class_average)),
            backgroundColor: seriesColor(1),
            borderRadius: { topLeft: 0, topRight: 4, bottomLeft: 0, bottomRight: 4 },
            borderSkipped: "start",
            maxBarThickness: 18,
          },
        ],
      },
      options: merge(baseOptions(), {
        indexAxis: "y",
        // 2px of surface between the two bars of a pair.
        datasets: { bar: { categoryPercentage: 0.74, barPercentage: 0.88 } },
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            grid: { color: c.grid, drawTicks: false },
            border: { display: false },
            ticks: {
              color: c.text3,
              font: { family: cssVar("--font"), size: 11 },
              callback: (value) => `${value}%`,
              maxTicksLimit: 6,
            },
          },
          y: {
            grid: { display: false },
            border: { color: c.border },
            ticks: { color: c.text3, font: { family: cssVar("--font"), size: 11 } },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: (items) => rows[items[0].dataIndex]?.subject_name || "",
              label: (item) => `${item.dataset.label}: ${fmt(item.parsed.x)}%`,
            },
          },
        },
      }),
    });
  });
}

/**
 * Assessment marks over time, one line per subject.
 *
 * Job: trend, with the subjects as distinguishable identities. Points
 * are 8px minimum with a 2px surface ring so they stay readable where
 * lines cross.
 */
export function trendChart(canvasId, timeline) {
  return mount(canvasId, (canvas) => {
    const c = chrome();

    // Group by subject, preserving first-seen order so colour assignment
    // is stable between renders.
    const bySubject = new Map();
    for (const item of timeline) {
      if (!bySubject.has(item.subject_code)) bySubject.set(item.subject_code, []);
      bySubject.get(item.subject_code).push(item);
    }

    // Every distinct assessment date, sorted, becomes the shared x-axis.
    const dates = [...new Set(timeline.map((t) => t.assessed_on))].sort();

    const datasets = [...bySubject.entries()].map(([code, items], index) => {
      const byDate = new Map(items.map((i) => [i.assessed_on, toNum(i.percent)]));
      return {
        label: code,
        // `null` for a missing date leaves a gap rather than drawing a
        // straight line through an assessment that never happened.
        data: dates.map((d) => (byDate.has(d) ? byDate.get(d) : null)),
        borderColor: seriesColor(index),
        backgroundColor: seriesColor(index),
        borderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        pointBorderColor: c.surface,
        pointBorderWidth: 2,
        tension: 0.3,
        spanGaps: true,
      };
    });

    return new Chart(canvas, {
      type: "line",
      data: { labels: dates.map(shortDate), datasets },
      options: merge(baseOptions(), {
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: c.grid, drawTicks: false },
            border: { display: false },
            ticks: {
              color: c.text3,
              font: { family: cssVar("--font"), size: 11 },
              callback: (value) => `${value}%`,
              maxTicksLimit: 6,
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: { label: (item) => `${item.dataset.label}: ${fmt(item.parsed.y)}%` },
          },
        },
      }),
    });
  });
}

/**
 * Grade distribution.
 *
 * Job: magnitude across an ordered scale, so a sequential single-hue
 * ramp - darker means more students. Not categorical: the grades are an
 * ordered scale, and seven arbitrary hues would imply they are unrelated
 * identities.
 */
export function gradeDistributionChart(canvasId, rows) {
  return mount(canvasId, (canvas) => {
    const c = chrome();
    const counts = rows.map((r) => r.student_count);
    const peak = Math.max(...counts, 1);

    const ramp = ["--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6"];

    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map((r) => r.grade),
        datasets: [
          {
            label: "Students",
            data: counts,
            backgroundColor: counts.map((count) => {
              // Map each bar's share of the peak onto the ramp, so
              // colour reinforces height rather than decorating it.
              const step = Math.round((count / peak) * (ramp.length - 1));
              return cssVar(ramp[Math.max(0, step)]);
            }),
            borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
            borderSkipped: "bottom",
            maxBarThickness: 44,
          },
        ],
      },
      options: merge(baseOptions(), {
        scales: {
          y: {
            beginAtZero: true,
            grid: { color: c.grid, drawTicks: false },
            border: { display: false },
            ticks: {
              color: c.text3,
              font: { family: cssVar("--font"), size: 11 },
              precision: 0,
              maxTicksLimit: 5,
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: (items) => `Grade ${items[0].label}`,
              label: (item) =>
                `${item.parsed.y} student${item.parsed.y === 1 ? "" : "s"}`,
            },
          },
        },
      }),
    });
  });
}

/**
 * Subject pass rates.
 *
 * Job: magnitude, ranked worst-first. Emphasis colouring - subjects
 * below the acceptable line take the critical status colour, the rest
 * stay in one quiet hue - so the eye lands on the problem subjects
 * without seven competing colours. The status colour is paired with the
 * printed percentage in the table beneath, never carrying meaning alone.
 */
export function passRateChart(canvasId, rows, threshold = 75) {
  return mount(canvasId, (canvas) => {
    const c = chrome();
    const critical = cssVar("--critical");
    const warning = cssVar("--warning");

    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map((r) => r.subject_code),
        datasets: [
          {
            label: "Pass rate",
            data: rows.map((r) => toNum(r.pass_rate)),
            backgroundColor: rows.map((r) => {
              const rate = toNum(r.pass_rate);
              if (rate === null) return c.muted;
              if (rate < 60) return critical;
              if (rate < threshold) return warning;
              return cssVar("--seq-4");
            }),
            borderRadius: { topLeft: 0, topRight: 4, bottomLeft: 0, bottomRight: 4 },
            borderSkipped: "start",
            maxBarThickness: 20,
          },
        ],
      },
      options: merge(baseOptions(), {
        indexAxis: "y",
        scales: {
          x: {
            beginAtZero: true,
            max: 100,
            grid: { color: c.grid, drawTicks: false },
            border: { display: false },
            ticks: {
              color: c.text3,
              font: { family: cssVar("--font"), size: 11 },
              callback: (value) => `${value}%`,
              maxTicksLimit: 6,
            },
          },
          y: {
            grid: { display: false },
            border: { color: c.border },
            ticks: { color: c.text3, font: { family: cssVar("--font"), size: 11 } },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: (items) => rows[items[0].dataIndex]?.subject_name || "",
              label: (item) => {
                const row = rows[item.dataIndex];
                return [
                  `Pass rate: ${fmt(item.parsed.x)}%`,
                  `Passed ${row.passed_count} of ${row.enrolled_count}`,
                  `Class average: ${fmt(row.avg_mark_percent)}%`,
                ];
              },
            },
          },
        },
      }),
    });
  });
}

/**
 * Attendance against the requirement, per subject.
 *
 * Job: a ratio against a limit, per category. A dashed threshold line
 * would be a second visual language; instead the requirement is encoded
 * in the bar colour and stated in the caption, and the meters in the
 * subject table carry the same threshold marker.
 */
export function attendanceChart(canvasId, rows, requirement = 75) {
  return mount(canvasId, (canvas) => {
    const c = chrome();
    const good = cssVar("--good");
    const warning = cssVar("--warning");
    const critical = cssVar("--critical");

    return new Chart(canvas, {
      type: "bar",
      data: {
        labels: rows.map((r) => r.subject_code),
        datasets: [
          {
            label: "Attendance",
            data: rows.map((r) => toNum(r.attendance_percent)),
            backgroundColor: rows.map((r) => {
              const value = toNum(r.attendance_percent);
              if (value === null) return c.muted;
              if (value >= requirement) return good;
              if (value >= requirement * 0.8) return warning;
              return critical;
            }),
            borderRadius: { topLeft: 4, topRight: 4, bottomLeft: 0, bottomRight: 0 },
            borderSkipped: "bottom",
            maxBarThickness: 40,
          },
        ],
      },
      options: merge(baseOptions(), {
        scales: {
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: c.grid, drawTicks: false },
            border: { display: false },
            ticks: {
              color: c.text3,
              font: { family: cssVar("--font"), size: 11 },
              callback: (value) => `${value}%`,
              maxTicksLimit: 6,
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              title: (items) => rows[items[0].dataIndex]?.subject_name || "",
              label: (item) => {
                const row = rows[item.dataIndex];
                const state =
                  toNum(row.attendance_percent) >= requirement
                    ? "meets the requirement"
                    : "below the requirement";
                return [
                  `Attendance: ${fmt(item.parsed.y)}% (${state})`,
                  `Attended ${row.attended_classes} of ${row.total_classes} classes`,
                ];
              },
            },
          },
        },
      }),
    });
  });
}

/* --- Legend ----------------------------------------------------------- *
 * Rendered as HTML rather than by Chart.js. The swatch carries the
 * series colour; the text stays in a text token, because a light hue
 * (yellow, aqua) is illegible as text on the page surface.              */

export function renderLegend(container, items, { line = false } = {}) {
  const node =
    typeof container === "string" ? document.querySelector(container) : container;
  if (!node) return;

  node.textContent = "";
  node.className = "legend";

  items.forEach((item, index) => {
    const key = document.createElement("span");
    key.className = `legend-key${line ? " line" : ""}`;
    key.style.background = item.color || seriesColor(index);

    const label = document.createElement("span");
    label.className = "legend-item";
    label.append(key, document.createTextNode(item.label));

    node.append(label);
  });
}

/* --- helpers ---------------------------------------------------------- */

function toNum(value) {
  if (value === null || value === undefined || value === "") return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
}

function fmt(value) {
  return value === null || value === undefined ? "—" : Number(value).toFixed(1);
}

function shortDate(iso) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}
