/**
 * ReCoMo graph visualization — load static JSON, render graph, replay by turn.
 */

(function () {
  const NODE_COLORS = {
    constraint: "#ef4444",
    goal: "#3b82f6",
    decision: "#22c55e",
    assumption: "#a855f7",
    entity: "#71717a",
  };
  const EDGE_COLORS = {
    violates: "#ef4444",
    satisfies: "#22c55e",
    conflict: "#f59e0b",
    tradeoff: "#f59e0b",
    ambiguity: "#a855f7",
    tension: "#71717a",
  };

  let data = null;
  let cy = null;
  let currentTurn = 1;
  let maxTurn = 1;
  let playInterval = null;

  const graphEl = document.getElementById("graph");
  const turnSlider = document.getElementById("turnSlider");
  const turnDisplay = document.getElementById("turnDisplay");
  const coherenceValue = document.getElementById("coherenceValue");
  const driftAlert = document.getElementById("driftAlert");
  const playBtn = document.getElementById("playBtn");
  const resetBtn = document.getElementById("resetBtn");
  const transcriptEl = document.getElementById("transcript");
  const trajectoryChart = document.getElementById("trajectoryChart");
  const driftsPanel = document.getElementById("driftsPanel");
  const driftsList = document.getElementById("driftsList");
  const liveBadge = document.getElementById("liveBadge");

  function getDriftTurns() {
    if (!data) return new Set();
    const turns = new Set();
    (data.drifts || []).forEach((d) => turns.add(d.turn));
    (data.goal_drifts || []).forEach((d) => turns.add(d.turn));
    (data.decision_conflicts || []).forEach((c) => turns.add(c.turn));
    (data.assumption_drifts || []).forEach((d) => turns.add(d.turn));
    (data.instability_alerts || []).forEach((a) => turns.add(a.turn));
    return turns;
  }

  function initCytoscape() {
    if (!data || !data.nodes || !data.edges) return;
    const nodes = data.nodes.map((n) => ({
      data: {
        id: n.id,
        label: n.label || n.id,
        type: n.type,
        turn: n.turn != null ? n.turn : 0,
        content: n.content || "",
      },
    }));
    const edges = data.edges.map((e, i) => ({
      data: {
        id: "e" + i,
        source: e.source,
        target: e.target,
        type: e.type || "tension",
        turn: e.turn != null ? e.turn : 0,
      },
    }));

    const style = [
      {
        selector: "node",
        style: {
          "cursor": "pointer",
          label: "data(label)",
          "text-valign": "bottom",
          "text-halign": "center",
          "font-size": "10px",
          "text-max-width": "80px",
          "text-wrap": "ellipsis",
          "background-color": (ele) => NODE_COLORS[ele.data("type")] || "#71717a",
          color: "#0f0f12",
          "text-margin-y": 4,
          width: 28,
          height: 28,
          "transition-property": "opacity",
          "transition-duration": "0.35s",
        },
      },
      {
        selector: "edge",
        style: {
          "curve-style": "bezier",
          "target-arrow-shape": "triangle",
          "arrow-scale": 0.7,
          width: 2,
          "line-color": (ele) => EDGE_COLORS[ele.data("type")] || "#71717a",
          "target-arrow-color": (ele) => EDGE_COLORS[ele.data("type")] || "#71717a",
          "transition-property": "opacity",
          "transition-duration": "0.35s",
        },
      },
    ];

    cy = window.cytoscape({
      container: graphEl,
      elements: { nodes, edges },
      style,
      layout: { name: "cose", animate: false },
      minZoom: 0.2,
      maxZoom: 3,
    });

    cy.on("tap", "node", (evt) => {
      const node = evt.target;
      const type = node.data("type");
      const content = node.data("content") || "";
      const typeEl = document.getElementById("nodeDetailType");
      const contentEl = document.getElementById("nodeDetailContent");
      const panel = document.getElementById("nodeDetailPanel");
      if (typeEl && contentEl && panel) {
        typeEl.textContent = type ? type.charAt(0).toUpperCase() + type.slice(1) : "";
        contentEl.textContent = content;
        panel.classList.remove("hidden");
      }
    });
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        const panel = document.getElementById("nodeDetailPanel");
        if (panel) panel.classList.add("hidden");
      }
    });

    updateTurnFilter();
  }

  function updateTurnFilter() {
    if (!cy) return;
    const t = currentTurn;
    cy.nodes().style("display", (n) => (n.data("turn") <= t ? "element" : "none"));
    cy.nodes().style("opacity", (n) => (n.data("turn") <= t ? 1 : 0));
    cy.edges().style("display", (e) => (e.data("turn") <= t ? "element" : "none"));
    cy.edges().style("opacity", (e) => (e.data("turn") <= t ? 1 : 0));
  }

  function setTurn(turn) {
    currentTurn = Math.max(1, Math.min(maxTurn, turn));
    turnSlider.value = currentTurn;
    turnDisplay.textContent = currentTurn;
    updateTurnFilter();
    updateCoherence();
    updateDriftAlert();
    updateTranscript();
    updateTrajectoryMarker();
    renderDrifts();
  }

  function updateCoherence() {
    const traj = data && data.trajectory ? data.trajectory : [];
    const point = traj.find((p) => p.turn === currentTurn);
    if (point != null) {
      coherenceValue.textContent = point.overall_coherence.toFixed(2);
      coherenceValue.style.color = point.overall_coherence >= 0.7 ? "#22c55e" : point.overall_coherence >= 0.4 ? "#f59e0b" : "#ef4444";
    } else {
      coherenceValue.textContent = traj.length ? "—" : "—";
      coherenceValue.style.color = "";
    }
  }

  function updateDriftAlert() {
    const driftTurns = getDriftTurns();
    if (driftTurns.has(currentTurn)) {
      driftAlert.classList.remove("hidden");
    } else {
      driftAlert.classList.add("hidden");
    }
  }

  function renderTranscript() {
    if (!data || !data.trace || !data.trace.turns) {
      transcriptEl.innerHTML = "<p class='text-muted'>No transcript.</p>";
      return;
    }
    const turns = data.trace.turns;
    transcriptEl.innerHTML = turns
      .map(
        (t) =>
          `<div class="turn-item" data-turn="${t.turn_number}">
            <div class="turn-role">${escapeHtml(t.role)} (Turn ${t.turn_number})</div>
            <div class="turn-content">${escapeHtml((t.content || "").slice(0, 300))}${(t.content || "").length > 300 ? "…" : ""}</div>
          </div>`
      )
      .join("");
  }

  function updateTranscript() {
    transcriptEl.querySelectorAll(".turn-item").forEach((el) => {
      const turn = parseInt(el.dataset.turn, 10);
      el.classList.toggle("active", turn === currentTurn);
    });
    const active = transcriptEl.querySelector(".turn-item.active");
    if (active) active.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s;
    return div.innerHTML;
  }

  function renderTrajectory() {
    if (!data || !data.trajectory || data.trajectory.length === 0) {
      trajectoryChart.innerHTML = "<p style='font-size:0.75rem;color:var(--text-muted)'>No trajectory data.</p>";
      return;
    }
    const traj = data.trajectory;
    const w = Math.max(trajectoryChart.clientWidth || 0, 200);
    const h = Math.max(trajectoryChart.clientHeight || 0, 80);
    const padding = { top: 4, right: 4, bottom: 16, left: 4 };
    const innerW = w - padding.left - padding.right;
    const innerH = h - padding.top - padding.bottom;
    const xs = traj.map((_, i) => padding.left + (i / Math.max(1, traj.length - 1)) * innerW);
    const ys = traj.map((p) => padding.top + innerH - p.overall_coherence * innerH);
    const pathD = xs.map((x, i) => `${i === 0 ? "M" : "L"} ${x} ${ys[i]}`).join(" ");
    const markerX = traj.findIndex((p) => p.turn === currentTurn);
    const lineX = markerX >= 0 && markerX < xs.length ? xs[markerX] : null;
    trajectoryChart.innerHTML = `
      <svg width="100%" height="100%" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <path d="${pathD}" fill="none" stroke="var(--accent)" stroke-width="2"/>
        ${lineX != null ? `<line x1="${lineX}" y1="${padding.top}" x2="${lineX}" y2="${h - padding.bottom}" stroke="var(--text-muted)" stroke-width="1" stroke-dasharray="4"/>` : ""}
      </svg>
    `;
  }

  function updateTrajectoryMarker() {
    renderTrajectory();
  }

  function renderDrifts() {
    const items = [];
    if (data && data.drifts && data.drifts.length) {
      data.drifts.forEach((d) => {
        if (d.turn <= currentTurn) {
          items.push(`<div class="drift-item">Turn ${d.turn}: ${escapeHtml((d.constraint_content || "").slice(0, 60))}…</div>`);
        }
      });
    }
    if (data && data.goal_drifts && data.goal_drifts.length) {
      data.goal_drifts.forEach((d) => {
        if (d.turn <= currentTurn) {
          items.push(`<div class="drift-item">Goal drift @ ${d.turn}</div>`);
        }
      });
    }
    if (items.length) {
      driftsPanel.classList.remove("hidden");
      driftsList.innerHTML = items.join("");
    } else {
      driftsPanel.classList.add("hidden");
    }
  }

  function onSliderInput() {
    setTurn(parseInt(turnSlider.value, 10));
  }

  function play() {
    if (playInterval) {
      clearInterval(playInterval);
      playInterval = null;
      playBtn.textContent = "Play";
      return;
    }
    playBtn.textContent = "Pause";
    playInterval = setInterval(() => {
      if (currentTurn >= maxTurn) {
        clearInterval(playInterval);
        playInterval = null;
        playBtn.textContent = "Play";
        return;
      }
      setTurn(currentTurn + 1);
    }, 1500);
  }

  function reset() {
    if (playInterval) {
      clearInterval(playInterval);
      playInterval = null;
      playBtn.textContent = "Play";
    }
    setTurn(1);
    renderDrifts();
  }

  function isLiveMode() {
    return new URLSearchParams(window.location.search).get("live") === "1";
  }

  function applyPayload(payload) {
    data = payload;
    const turns = (data.trace && data.trace.turns) || [];
    maxTurn = turns.length ? Math.max(...turns.map((t) => t.turn_number)) : 1;
    turnSlider.min = 1;
    turnSlider.max = maxTurn;
    turnSlider.value = maxTurn;
    currentTurn = maxTurn;
    turnDisplay.textContent = String(currentTurn);

    renderTranscript();
    renderTrajectory();
    renderDrifts();
    if (cy) {
      cy.destroy();
      cy = null;
    }
    const nodePanel = document.getElementById("nodeDetailPanel");
    if (nodePanel) nodePanel.classList.add("hidden");
    initCytoscape();
    updateCoherence();
    updateDriftAlert();
    updateTranscript();
  }

  function fetchAndApply() {
    const url = "demo_output.json?t=" + Date.now();
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      })
      .then((payload) => {
        const turns = (payload.trace && payload.trace.turns) || [];
        const newLen = turns.length;
        const curLen = (data && data.trace && data.trace.turns) ? data.trace.turns.length : 0;
        if (newLen !== curLen || JSON.stringify(payload.trace) !== JSON.stringify(data && data.trace)) {
          applyPayload(payload);
          if (liveBadge) {
            liveBadge.classList.add("pulse");
            setTimeout(() => liveBadge.classList.remove("pulse"), 500);
          }
        }
      })
      .catch(() => {});
  }

  function init() {
    const live = isLiveMode();
    if (live) {
      const controls = document.querySelector(".controls");
      if (controls) controls.style.display = "none";
      if (liveBadge) liveBadge.classList.remove("hidden");
    }
    const url = "demo_output.json" + (live ? "?t=" + Date.now() : "");
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(r.statusText);
        return r.json();
      })
      .then((payload) => {
        const turns = (payload.trace && payload.trace.turns) || [];
        maxTurn = turns.length ? Math.max(...turns.map((t) => t.turn_number)) : 1;
        turnSlider.min = 1;
        turnSlider.max = maxTurn;
        turnSlider.value = live ? maxTurn : 1;
        currentTurn = live ? maxTurn : 1;
        turnDisplay.textContent = String(currentTurn);
        data = payload;

        renderTranscript();
        renderTrajectory();
        renderDrifts();
        initCytoscape();
        updateCoherence();
        updateDriftAlert();
        updateTranscript();

        turnSlider.addEventListener("input", onSliderInput);
        playBtn.addEventListener("click", play);
        resetBtn.addEventListener("click", reset);

        if (live) {
          setInterval(fetchAndApply, 1500);
        }
      })
      .catch((err) => {
        coherenceValue.textContent = "—";
        transcriptEl.innerHTML = "<p style='color:var(--danger)'>Failed to load demo_output.json. Run: python -m recomo.viz.export_demo</p>";
        console.error(err);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
