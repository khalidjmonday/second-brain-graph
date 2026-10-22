"""Render a NetworkX graph as a self-contained interactive HTML file."""

from pathlib import Path
import json
import math
import re

import networkx as nx
from pyvis.network import Network


INTERACTION_SCRIPT = r"""
<script>
(() => {
  const records = JSON.parse(document.getElementById("graph-index").textContent);
  const byId = new Map(records.map((record) => [record.id, record]));
  const labelFor = (id) => byId.get(id)?.label ?? id;
  const search = document.getElementById("note-search");
  const resultBox = document.getElementById("search-results");
  const inspector = document.getElementById("note-inspector");
  const routeBanner = document.getElementById("route-banner");
  const routeMessage = document.getElementById("route-message");
  const routeAction = document.getElementById("route-action");
  const inputIds = new Set(["INPUT", "TEXTAREA", "SELECT"]);
  let activeFilter = "all";
  let showSemantic = true;
  let routeStartId = null;
  let activeRoute = null;
  const originalNodes = nodes.get();
  const originalEdges = edges.get();

  const openReferenceIds = new Set(
    records.filter((record) => !record.exists).map((record) => record.id),
  );
  records.filter((record) => !record.exists).forEach((record) => {
    record.incoming.forEach((sourceId) => openReferenceIds.add(sourceId));
  });
  const filterSets = {
    all: new Set(records.map((record) => record.id)),
    open: openReferenceIds,
    orphans: new Set(records.filter((record) => record.exists && record.explicitDegree === 0).map((record) => record.id)),
    hubs: new Set(records.filter((record) => record.exists && record.degree >= {{ hub_threshold }}).map((record) => record.id)),
  };

  function setFilter(name, shouldFit = true) {
    if (routeStartId !== null || activeRoute !== null) clearRoute();
    activeFilter = name;
    const visible = filterSets[name] || filterSets.all;
    nodes.update(records.map((record) => {
      const isVisible = visible.has(record.id);
      return { id: record.id, hidden: !isVisible, physics: isVisible };
    }));
    edges.update(edges.get().map((edge) => {
      const isVisible = visible.has(edge.from) && visible.has(edge.to)
        && (showSemantic || !edge.semantic || edge.explicit);
      return { id: edge.id, hidden: !isVisible, physics: isVisible };
    }));
    document.querySelectorAll(".filter-button").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.filter === name);
    });
    const selected = network.getSelectedNodes();
    if (selected.some((id) => !visible.has(id))) {
      network.unselectAll();
      inspector.hidden = true;
    }
    if (shouldFit) network.fit({ animation: { duration: 350, easingFunction: "easeInOutQuad" } });
  }

  function renderLinkList(containerId, ids, emptyMessage) {
    const container = document.getElementById(containerId);
    container.replaceChildren();
    if (!ids.length) {
      const empty = document.createElement("p");
      empty.className = "link-empty";
      empty.textContent = emptyMessage;
      container.appendChild(empty);
      return;
    }
    ids.forEach((id) => {
      const record = byId.get(id);
      if (!record) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "linked-note";
      const name = document.createElement("span");
      name.className = "linked-note-name";
      name.textContent = record.label;
      const meta = document.createElement("small");
      meta.textContent = record.exists ? record.path : "Uncreated reference";
      button.append(name, meta);
      button.addEventListener("click", () => focusNote(record.id));
      container.appendChild(button);
    });
  }

  function renderSemanticList(containerId, connections) {
    const container = document.getElementById(containerId);
    container.replaceChildren();
    if (!connections.length) {
      const empty = document.createElement("p");
      empty.className = "link-empty";
      empty.textContent = "No high-confidence semantic matches.";
      container.appendChild(empty);
      return;
    }
    connections.forEach(({ id, similarity }) => {
      const record = byId.get(id);
      if (!record) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = "linked-note semantic-note";
      const name = document.createElement("span");
      name.className = "linked-note-name";
      name.textContent = record.label;
      const meta = document.createElement("small");
      meta.textContent = `Semantic similarity · ${Math.round(similarity * 100)}%`;
      button.append(name, meta);
      button.addEventListener("click", () => focusNote(record.id));
      container.appendChild(button);
    });
  }

  function showDetails(record) {
    inspector.dataset.nodeId = record.id;
    document.getElementById("detail-kind").textContent = record.exists ? "MARKDOWN NOTE" : "UNCREATED TARGET";
    document.getElementById("detail-kind").classList.toggle("is-missing", !record.exists);
    document.getElementById("detail-title").textContent = record.label;
    document.getElementById("detail-path").textContent = record.exists ? record.path : "This note has been linked, but no matching .md file exists yet.";
    document.getElementById("detail-in-count").textContent = record.incoming.length;
    document.getElementById("detail-out-count").textContent = record.outgoing.length;
    document.getElementById("detail-total-count").textContent = record.degree;
    const traceButton = document.getElementById("trace-route");
    traceButton.disabled = !record.exists || record.outgoing.length === 0;
    traceButton.title = traceButton.disabled ? "This note has no outgoing links to follow" : "Choose a destination note to trace a directed path";
    document.getElementById("incoming-count").textContent = record.incoming.length;
    document.getElementById("outgoing-count").textContent = record.outgoing.length;
    renderLinkList("incoming-list", record.incoming, "No notes link here yet.");
    renderLinkList("outgoing-list", record.outgoing, "This note has no outgoing links.");
    renderSemanticList("semantic-list", record.semantic || []);
    inspector.hidden = false;
  }

  function focusNote(id) {
    const record = byId.get(id);
    if (!record) return;
    if (routeStartId !== null || activeRoute !== null) clearRoute();
    if (!filterSets[activeFilter].has(id)) setFilter("all", false);
    search.value = record.label;
    resultBox.hidden = true;
    network.selectNodes([id]);
    network.focus(id, { scale: 1.15, animation: { duration: 550, easingFunction: "easeInOutQuad" } });
    showDetails(record);
  }

  function shortestDirectedPath(startId, endId) {
    const queue = [startId];
    const previous = new Map([[startId, null]]);
    for (let index = 0; index < queue.length; index += 1) {
      const current = queue[index];
      if (current === endId) break;
      const record = byId.get(current);
      for (const neighbor of record?.outgoing || []) {
        if (!previous.has(neighbor)) {
          previous.set(neighbor, current);
          queue.push(neighbor);
        }
      }
    }
    if (!previous.has(endId)) return null;
    const path = [];
    for (let current = endId; current !== null; current = previous.get(current)) path.push(current);
    return path.reverse();
  }

  function clearRoute() {
    routeStartId = null;
    activeRoute = null;
    routeBanner.hidden = true;
    const visible = filterSets[activeFilter] || filterSets.all;
    nodes.update(originalNodes.map((node) => {
      const isVisible = visible.has(node.id);
      return {
        id: node.id, color: node.color, size: node.size, font: node.font,
        hidden: !isVisible, physics: isVisible,
      };
    }));
    edges.update(originalEdges.map((edge) => {
      const endpointsVisible = visible.has(edge.from) && visible.has(edge.to);
      const isVisible = endpointsVisible && (showSemantic || !edge.semantic || edge.explicit);
      return {
        id: edge.id, color: edge.color, width: edge.width,
        hidden: !isVisible, physics: isVisible,
      };
    }));
  }

  function beginRoute() {
    const startId = inspector.dataset.nodeId;
    const record = byId.get(startId);
    if (!record || !record.exists || !record.outgoing.length) return;
    if (activeRoute !== null) clearRoute();
    if (!filterSets[activeFilter].has(startId)) setFilter("all", false);
    routeStartId = startId;
    routeMessage.textContent = `Choose a destination for ${record.label}.`;
    routeAction.textContent = "Cancel";
    routeBanner.hidden = false;
  }

  function highlightRoute(path) {
    activeRoute = path;
    routeStartId = null;
    const pathNodes = new Set(path);
    const pathEdges = new Set(path.slice(1).map((id, index) => `${path[index]}\u0000${id}`));
    nodes.update(originalNodes.map((node) => {
      if (pathNodes.has(node.id)) {
        return { id: node.id, color: node.color, size: (node.size || 25) + 5, hidden: false, physics: false };
      }
      return {
        id: node.id,
        color: { background: "#172033", border: "#27354b", highlight: { background: "#26344a", border: "#4b5c76" } },
        size: Math.max(13, (node.size || 25) * 0.72),
        font: { color: "#64748b" }, hidden: false, physics: false,
      };
    }));
    edges.update(originalEdges.map((edge) => {
      const onPath = pathEdges.has(`${edge.from}\u0000${edge.to}`);
      return {
        id: edge.id,
        color: onPath ? { color: "#67e8f9", highlight: "#ecfeff", hover: "#ecfeff", inherit: false } : "rgba(100, 116, 139, 0.12)",
        width: onPath ? 3.4 : 1,
        hidden: false,
        physics: false,
      };
    }));
    const names = path.map(labelFor);
    routeMessage.textContent = `${path.length - 1} link${path.length === 2 ? "" : "s"}: ${names.join("  \u2192  ")}`;
    routeAction.textContent = "Clear path";
    routeBanner.hidden = false;
    network.fit({ animation: { duration: 500, easingFunction: "easeInOutQuad" } });
  }

  function updateSearchResults() {
    const query = search.value.trim().toLocaleLowerCase();
    resultBox.replaceChildren();
    if (!query) {
      resultBox.hidden = true;
      return;
    }
    const matches = records
      .filter((record) => `${record.label} ${record.path} ${record.id}`.toLocaleLowerCase().includes(query))
      .sort((left, right) => Number(right.exists) - Number(left.exists) || left.label.localeCompare(right.label))
      .slice(0, 8);
    if (!matches.length) {
      const empty = document.createElement("div");
      empty.className = "search-empty";
      empty.textContent = "No matching notes";
      resultBox.appendChild(empty);
    } else {
      matches.forEach((record) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "search-result";
        const name = document.createElement("span");
        name.textContent = record.label;
        const meta = document.createElement("small");
        meta.textContent = record.exists ? record.path : "Uncreated reference";
        button.append(name, meta);
        button.addEventListener("click", () => focusNote(record.id));
        resultBox.appendChild(button);
      });
    }
    resultBox.hidden = false;
  }

  search.addEventListener("input", updateSearchResults);
  search.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    const query = search.value.trim().toLocaleLowerCase();
    const record = records.find((item) => item.label.toLocaleLowerCase() === query)
      || records.find((item) => `${item.label} ${item.path}`.toLocaleLowerCase().includes(query));
    if (record) focusNote(record.id);
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest(".search-shell")) resultBox.hidden = true;
  });
  document.querySelectorAll(".filter-button").forEach((button) => {
    button.addEventListener("click", () => setFilter(button.dataset.filter));
  });
  document.getElementById("fit-graph").addEventListener("click", () => {
    network.fit({ animation: { duration: 450, easingFunction: "easeInOutQuad" } });
  });
  const semanticToggle = document.getElementById("toggle-semantic");
  semanticToggle.addEventListener("click", () => {
    showSemantic = !showSemantic;
    semanticToggle.setAttribute("aria-pressed", String(showSemantic));
    semanticToggle.textContent = `Semantic links ${showSemantic ? "on" : "off"}`;
    semanticToggle.classList.toggle("is-active", showSemantic);
    setFilter(activeFilter, false);
  });
  document.getElementById("reset-graph").addEventListener("click", () => {
    search.value = "";
    resultBox.hidden = true;
    network.unselectAll();
    inspector.hidden = true;
    showSemantic = true;
    semanticToggle.setAttribute("aria-pressed", "true");
    semanticToggle.textContent = "Semantic links on";
    semanticToggle.classList.add("is-active");
    setFilter("all");
  });
  document.getElementById("close-inspector").addEventListener("click", () => {
    inspector.hidden = true;
    network.unselectAll();
  });
  document.getElementById("trace-route").addEventListener("click", beginRoute);
  routeAction.addEventListener("click", clearRoute);
  network.on("click", (event) => {
    if (event.nodes.length) {
      const record = byId.get(event.nodes[0]);
      if (!record) return;
      if (routeStartId !== null) {
        if (record.id === routeStartId) {
          routeMessage.textContent = "Choose a different destination.";
          return;
        }
        const path = shortestDirectedPath(routeStartId, record.id);
        if (path) highlightRoute(path);
        else routeMessage.textContent = `No directed route from ${labelFor(routeStartId)} to ${record.label}.`;
        showDetails(record);
        return;
      }
      showDetails(record);
    } else {
      inspector.hidden = true;
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      search.value = "";
      resultBox.hidden = true;
      inspector.hidden = true;
      network.unselectAll();
      if (routeStartId !== null || activeRoute !== null) clearRoute();
      if (document.activeElement === search) search.blur();
      return;
    }
    if (inputIds.has(event.target.tagName) || event.target.isContentEditable) return;
    if (event.key === "/") {
      event.preventDefault();
      search.focus();
    }
  });
})();
</script>
"""


def export_graph(
    graph: nx.DiGraph,
    output_path: Path = Path("index.html"),
) -> Path:
    """Write an interactive visualization to ``output_path``.

    Pyvis embeds its JavaScript and styling into the output so the graph can
    be opened locally without a CDN connection. Barnes-Hut physics applies
    repulsion between nodes while springs keep connected notes together.
    """
    output_path = output_path.expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    network = Network(
        height="100vh",
        width="100%",
        directed=True,
        bgcolor="#080d18",
        font_color="#e6efff",
        # Pyvis renders its heading twice; the custom toolbar below replaces it.
        heading="",
        notebook=False,
        cdn_resources="in_line",
    )
    network.barnes_hut(
        gravity=-22000,
        central_gravity=0.22,
        spring_length=220,
        spring_strength=0.018,
        damping=0.16,
        overlap=0.18,
    )

    for node_id, attributes in graph.nodes(data=True):
        exists = attributes.get("exists", True)
        degree = graph.degree(node_id)

        # Use restrained, high-contrast colors to distinguish node roles.
        if not exists:
            background, border = "#fb7185", "#fecdd3"
        elif degree >= 4:
            background, border = "#0f766e", "#99f6e4"
        elif graph.out_degree(node_id) == 0 and degree > 0:
            background, border = "#2dd4bf", "#99f6e4"
        elif degree == 0:
            background, border = "#818cf8", "#c7d2fe"
        else:
            background, border = "#38bdf8", "#bae6fd"

        network.add_node(
            node_id,
            label=attributes.get("label", node_id),
            title=attributes.get("path", "Note has not been created yet"),
            color={
                "background": background,
                "border": border,
                "highlight": {"background": "#f8fafc", "border": border},
                "hover": {"background": background, "border": "#ffffff"},
            },
            shape="dot",
            size=(25 + min(degree * 2, 10)) if exists else 22,
            borderWidth=2,
            borderWidthSelected=4,
            shadow={
                "enabled": True,
                "color": _rgba(background, 0.4 if exists else 0.55),
                "size": 18 if exists else 22,
                "x": 0,
                "y": 3,
            },
            font={
                "color": "#f1f5f9",
                "face": "Inter, Segoe UI, Arial, sans-serif",
                "size": 17,
                "bold": {"color": "#ffffff"},
                "strokeWidth": 4,
                "strokeColor": "#080d18",
            },
        )

    for edge_index, (source, target, attributes) in enumerate(graph.edges(data=True)):
        is_explicit = attributes.get("explicit", False)
        is_semantic = attributes.get("semantic", False)
        if is_explicit:
            edge_color = {
                "color": "rgba(96, 165, 250, 0.82)",
                "highlight": "#bfdbfe",
                "hover": "#eff6ff",
                "inherit": False,
            }
            edge_title = "Explicit wikilink"
            if is_semantic:
                edge_title += f" · Semantic similarity: {attributes['similarity']:.0%}"
        else:
            edge_color = {
                "color": "rgba(148, 163, 184, 0.58)",
                "highlight": "#e2e8f0",
                "hover": "#f8fafc",
                "inherit": False,
            }
            edge_title = f"Semantic similarity: {attributes.get('similarity', 0):.0%} · Suggested connection"
        network.add_edge(
            source,
            target,
            id=f"link-{edge_index}",
            arrows="to",
            color=edge_color,
            title=edge_title,
            dashes=not is_explicit,
            width=1.8 if is_explicit else 1.5,
            explicit=is_explicit,
            semantic=is_semantic,
            similarity=attributes.get("similarity"),
            selectionWidth=2.6,
            hoverWidth=2.4,
        )

    # Pyvis 0.3.x opens its HTML file with the Windows locale's default
    # encoding. That can fail on generated Unicode characters under cp1252.
    # Render first, then explicitly save UTF-8 so note names and Pyvis's own
    # HTML symbols are safe on every platform.
    html = network.generate_html()

    # Remove both empty heading blocks emitted by Pyvis, including their
    # vertical spacing, so the graph can use the full viewport.
    html = re.sub(
        r"\s*<center>\s*<h1>\s*</h1>\s*</center>",
        "",
        html,
        flags=re.IGNORECASE,
    )

    # Pyvis's template adds Bootstrap from jsDelivr even in inline mode.
    # This graph does not enable Pyvis's menu widgets, so those optional
    # Bootstrap assets are unused; remove them to keep the page offline-ready.
    html = re.sub(
        r'<link\b(?=[^>]*href="https://cdn\.jsdelivr\.net/npm/bootstrap@)[^>]*/>',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<script\b(?=[^>]*src="https://cdn\.jsdelivr\.net/npm/bootstrap@)[^>]*>.*?</script>',
        "",
        html,
        flags=re.DOTALL,
    )

    note_count = sum(
        1 for _, data in graph.nodes(data=True) if data.get("exists", True)
    )
    missing_count = graph.number_of_nodes() - note_count
    explicit_link_count = sum(
        1 for _, _, data in graph.edges(data=True) if data.get("explicit", False)
    )
    semantic_pair_count = len({
        frozenset((source, target))
        for source, target, data in graph.edges(data=True)
        if data.get("semantic", False)
    })
    node_records = []
    for node_id, attributes in graph.nodes(data=True):
        incoming = sorted(
            source for source in graph.predecessors(node_id)
            if graph.edges[source, node_id].get("explicit", False)
        )
        outgoing = sorted(
            target for target in graph.successors(node_id)
            if graph.edges[node_id, target].get("explicit", False)
        )
        semantic = sorted(
            (
                {"id": target, "similarity": graph.edges[node_id, target]["similarity"]}
                for target in graph.successors(node_id)
                if graph.edges[node_id, target].get("semantic", False)
            ),
            key=lambda item: (-item["similarity"], item["id"]),
        )
        node_records.append(
            {
                "id": str(node_id),
                "label": str(attributes.get("label", node_id)),
                "path": str(attributes.get("path", "")),
                "exists": attributes.get("exists", True),
                "incoming": incoming,
                "outgoing": outgoing,
                "semantic": semantic,
                "explicitDegree": len(set(incoming) | set(outgoing)),
                "degree": graph.degree(node_id),
            }
        )

    highest_degree = max(
        (record["degree"] for record in node_records if record["exists"]),
        default=0,
    )
    hub_threshold = max(2, math.ceil(highest_degree * 0.75))
    orphan_count = sum(
        1 for record in node_records
        if record["exists"] and record["explicitDegree"] == 0
    )
    hub_count = sum(
        1 for record in node_records
        if record["exists"] and record["degree"] >= hub_threshold
    )

    # JSON lives in a non-executable script element. Escape HTML-significant
    # characters as well, so unusual note names cannot break out of the data.
    records_json = json.dumps(node_records, ensure_ascii=False)
    records_json = (
        records_json.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )
    toolbar = f"""
    <header class="graph-toolbar">
      <div class="brand-lockup">
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" fill="none">
            <path d="M7 8.5 16 5l9 4v13l-9 5-9-5v-13Z" stroke="currentColor" stroke-width="1.7"/>
            <circle cx="7" cy="8.5" r="2.2" fill="#67e8f9"/>
          <circle cx="16" cy="5" r="2.2" fill="#93c5fd"/>
            <circle cx="25" cy="9" r="2.2" fill="#67e8f9"/>
          <circle cx="16" cy="27" r="2.2" fill="#93c5fd"/>
            <path d="m9 9 5-3m4 0 5 2m-14 2v9m2 2 5 4m2 0 5-4m2-11v9" stroke="currentColor" stroke-width="1.4" opacity=".8"/>
          </svg>
        </span>
        <span class="brand-copy">
          <strong>SECOND BRAIN</strong>
          <span>LINK MAP</span>
        </span>
      </div>
      <div class="search-shell">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 5 5"/></svg>
        <input id="note-search" type="search" placeholder="Find a note or path..." autocomplete="off" aria-label="Search notes">
        <kbd>/</kbd>
        <div id="search-results" class="search-results" hidden></div>
      </div>
      <div class="graph-stats" aria-label="Graph summary">
        <span class="stat"><strong>{note_count}</strong><small>NOTES</small></span>
        <span class="stat"><strong>{explicit_link_count}</strong><small>WIKILINKS</small></span>
      <span class="stat stat-semantic"><strong>{semantic_pair_count}</strong><small>SIMILAR</small></span>
        <span class="stat stat-open"><i aria-hidden="true"></i><strong>{missing_count}</strong><small>OPEN REFS</small></span>
      </div>
    </header>
    <nav class="filter-rail" aria-label="Graph views">
      <span class="rail-label">EXPLORE</span>
      <button class="filter-button is-active" data-filter="all"><span>All nodes</span><b>{graph.number_of_nodes()}</b></button>
      <button class="filter-button" data-filter="open"><span>Open refs</span><b>{missing_count}</b></button>
      <button class="filter-button" data-filter="orphans"><span>Orphans</span><b>{orphan_count}</b></button>
      <button class="filter-button" data-filter="hubs"><span>Hubs</span><b>{hub_count}</b></button>
    </nav>
    <aside id="note-inspector" class="note-inspector" hidden aria-live="polite">
      <div class="inspector-head">
        <div><span id="detail-kind" class="detail-kind">NOTE</span><h2 id="detail-title">Note details</h2></div>
        <button id="close-inspector" class="icon-button" type="button" aria-label="Close details">×</button>
      </div>
      <p id="detail-path" class="detail-path"></p>
      <div class="detail-counts">
        <span><b id="detail-in-count">0</b><small>INBOUND</small></span>
        <span><b id="detail-out-count">0</b><small>OUTBOUND</small></span>
        <span><b id="detail-total-count">0</b><small>DEGREE</small></span>
      </div>
      <button id="trace-route" class="trace-button" type="button" disabled>Trace a route from this note</button>
      <section class="link-group"><h3>LINKS TO THIS NOTE <span id="incoming-count">0</span></h3><div id="incoming-list" class="link-list"></div></section>
      <section class="link-group"><h3>LINKS FROM THIS NOTE <span id="outgoing-count">0</span></h3><div id="outgoing-list" class="link-list"></div></section>
      <section class="link-group"><h3>SEMANTICALLY SIMILAR</h3><div id="semantic-list" class="link-list"></div></section>
    </aside>
    <div id="route-banner" class="route-banner" hidden role="status" aria-live="polite">
      <span class="route-pulse" aria-hidden="true"></span>
      <span id="route-message">Choose a destination note.</span>
      <button id="route-action" type="button">Cancel</button>
    </div>
    <div class="graph-legend">
      <span><i class="legend-note"></i> Notes</span>
      <span><i class="legend-open"></i> Uncreated reference</span>
      <span><i class="legend-semantic"></i> Semantic suggestion</span>
    </div>
    <div class="graph-actions">
      <button id="toggle-semantic" class="is-active" type="button" title="Show or hide semantic suggestions" aria-pressed="true">Semantic links on</button>
      <button id="fit-graph" type="button" title="Fit the entire graph">Fit map</button>
      <button id="reset-graph" type="button" title="Clear search and filters">Reset</button>
    </div>
    <div class="graph-hint">DRAG TO EXPLORE <b>·</b> SCROLL TO ZOOM</div>
    """
    html = re.sub(
        r"<body\b[^>]*>",
        lambda match: match.group(0) + toolbar,
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    # The source remains ASCII-friendly even when the Windows editor/codepage
    # mangles glyphs, while the browser displays proper HTML entities.
    html = html.replace("\u00c2\u00b7", "&middot;").replace("\u00c3\u2014", "&times;")

    theme = """
    <style id="second-brain-theme">
      :root { color-scheme: dark; font-family: Inter, "Segoe UI", Arial, sans-serif; }
      * { box-sizing: border-box; }
      html, body { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; background: #080d18; }
      body { color: #e2e8f0; }
      .card { width: 100% !important; height: 100%; margin: 0; padding: 0; border: 0 !important; background: transparent !important; }
      .card-body { width: 100%; height: 100%; margin: 0; padding: 0 !important; }
      #mynetwork {
        position: fixed !important; inset: 0 !important;
        width: 100vw !important; height: 100vh !important;
        border: 0 !important;
        background: #0b1220 !important;
      }
      .graph-toolbar {
        position: fixed; z-index: 20; top: 18px; left: 20px; right: 20px;
        display: grid; grid-template-columns: auto minmax(220px, 410px) auto;
        align-items: center; gap: 16px;
        pointer-events: none;
      }
      .brand-lockup, .graph-stats, .search-shell {
        border: 1px solid rgba(148, 163, 184, .19);
        background: rgba(13, 20, 36, .76);
        box-shadow: 0 12px 36px rgba(0, 0, 0, .24);
        backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
      }
      .brand-lockup { display: flex; align-items: center; gap: 11px; padding: 9px 15px 9px 10px; border-radius: 6px; }
      .brand-mark { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 5px; color: #bfdbfe; background: #17263a; }
      .brand-mark svg { width: 25px; height: 25px; }
      .brand-copy { display: grid; gap: 3px; }
      .brand-copy strong { color: #f8fafc; font-size: 11px; font-weight: 750; letter-spacing: .16em; }
      .brand-copy span { color: #94a3b8; font-size: 9px; font-weight: 650; letter-spacing: .2em; }
      .graph-stats { display: flex; align-items: center; gap: 0; padding: 6px; border-radius: 6px; }
      .stat { min-width: 78px; display: grid; grid-template-columns: auto auto; align-items: baseline; justify-content: center; column-gap: 7px; padding: 4px 13px; }
      .stat + .stat { border-left: 1px solid rgba(148, 163, 184, .16); }
      .stat strong { color: #f8fafc; font-size: 15px; font-weight: 700; }
      .stat small { color: #94a3b8; font-size: 8px; font-weight: 700; letter-spacing: .13em; }
      .stat-open i { width: 7px; height: 7px; align-self: center; border-radius: 50%; background: #fb7185; box-shadow: 0 0 12px rgba(251, 113, 133, .75); }
      .stat-semantic strong { color: #67e8f9; }
      .search-shell { position: relative; display: flex; align-items: center; justify-self: center; width: 100%; max-width: 410px; height: 48px; padding: 0 12px; border-radius: 6px; pointer-events: auto; }
      .search-shell > svg { flex: none; width: 17px; height: 17px; fill: none; stroke: #94a3b8; stroke-width: 1.8; }
      .search-shell input { min-width: 0; flex: 1; height: 100%; padding: 0 10px; border: 0; outline: 0; color: #f1f5f9; background: transparent; font: 12px Inter, "Segoe UI", sans-serif; }
      .search-shell input::placeholder { color: #7f8da4; }
      .search-shell input::-webkit-search-cancel-button { cursor: pointer; }
      .search-shell:focus-within { border-color: rgba(103, 232, 249, .55); box-shadow: 0 0 0 3px rgba(34, 211, 238, .09), 0 12px 36px rgba(0, 0, 0, .24); }
      .search-shell kbd { display: grid; place-items: center; min-width: 22px; height: 22px; border: 1px solid rgba(148, 163, 184, .2); border-radius: 6px; color: #91a0b7; font: 10px ui-monospace, monospace; }
      .search-results { position: absolute; z-index: 40; top: calc(100% + 8px); left: 0; right: 0; overflow: hidden; padding: 5px; border: 1px solid rgba(148, 163, 184, .2); border-radius: 6px; background: #101827; box-shadow: 0 20px 50px rgba(0, 0, 0, .45); }
      .search-results[hidden] { display: none; }
      .search-result { display: flex; width: 100%; flex-direction: column; gap: 3px; padding: 10px; border: 0; border-radius: 8px; text-align: left; color: #e2e8f0; background: transparent; cursor: pointer; }
      .search-result:hover, .search-result:focus-visible { outline: none; background: rgba(56, 189, 248, .12); }
      .search-result span { font-size: 12px; font-weight: 650; }
      .search-result small { overflow: hidden; color: #8492a8; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
      .search-empty { padding: 12px 10px; color: #9aa8bc; font-size: 11px; }
      .filter-rail { position: fixed; z-index: 20; top: 84px; left: 20px; display: grid; gap: 5px; width: 154px; padding: 10px; border: 1px solid rgba(148, 163, 184, .15); border-radius: 6px; background: rgba(13, 20, 36, .9); box-shadow: 0 12px 32px rgba(0, 0, 0, .18); backdrop-filter: blur(14px); pointer-events: auto; }
      .rail-label { padding: 2px 8px 5px; color: #73829a; font-size: 8px; font-weight: 750; letter-spacing: .17em; }
      .filter-button { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px; border: 1px solid transparent; border-radius: 4px; color: #aab7ca; background: transparent; text-align: left; font: 11px Inter, "Segoe UI", sans-serif; cursor: pointer; }
      .filter-button b { display: grid; place-items: center; min-width: 21px; height: 19px; border-radius: 6px; color: #95a4bb; background: rgba(148, 163, 184, .1); font-size: 9px; }
      .filter-button:hover { color: #f1f5f9; background: rgba(148, 163, 184, .08); }
      .filter-button.is-active { border-color: rgba(96, 165, 250, .28); color: #dbeafe; background: rgba(59, 130, 246, .13); }
      .filter-button.is-active b { color: #bfdbfe; background: rgba(59, 130, 246, .18); }
      .note-inspector { position: fixed; z-index: 21; top: 84px; right: 20px; display: flex; width: min(330px, calc(100vw - 40px)); max-height: calc(100vh - 158px); flex-direction: column; overflow: auto; padding: 17px; border: 1px solid rgba(148, 163, 184, .19); border-radius: 7px; background: rgba(13, 20, 36, .96); box-shadow: 0 22px 60px rgba(0, 0, 0, .38); backdrop-filter: blur(18px); }
      .note-inspector[hidden] { display: none; }
      .inspector-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
      .detail-kind { color: #67e8f9; font-size: 8px; font-weight: 800; letter-spacing: .16em; }
      .detail-kind.is-missing { color: #fda4af; }
      .inspector-head h2 { max-width: 245px; overflow-wrap: anywhere; margin: 6px 0 0; color: #f8fafc; font-size: 21px; font-weight: 680; line-height: 1.2; }
      .icon-button { flex: none; width: 29px; height: 29px; border: 1px solid rgba(148, 163, 184, .16); border-radius: 4px; color: #9aa8bc; background: rgba(148, 163, 184, .06); font-size: 19px; line-height: 1; cursor: pointer; }
      .icon-button:hover { color: #fff; background: rgba(148, 163, 184, .15); }
      .detail-path { margin: 8px 0 15px; overflow-wrap: anywhere; color: #8492a8; font-size: 10px; line-height: 1.5; }
      .detail-counts { display: grid; grid-template-columns: repeat(3, 1fr); padding: 11px 0; border-top: 1px solid rgba(148, 163, 184, .12); border-bottom: 1px solid rgba(148, 163, 184, .12); }
      .detail-counts span { display: grid; justify-items: center; gap: 4px; }
      .detail-counts span + span { border-left: 1px solid rgba(148, 163, 184, .12); }
      .detail-counts b { color: #e2e8f0; font-size: 16px; }
      .detail-counts small { color: #7f8da4; font-size: 7px; font-weight: 750; letter-spacing: .12em; }
      .trace-button { width: 100%; margin-top: 12px; padding: 9px 11px; border: 1px solid rgba(96, 165, 250, .3); border-radius: 4px; color: #dbeafe; background: rgba(59, 130, 246, .12); text-align: left; font: 10px Inter, "Segoe UI", sans-serif; cursor: pointer; }
      .trace-button:hover:not(:disabled) { border-color: rgba(96, 165, 250, .55); color: #eff6ff; background: rgba(59, 130, 246, .2); }
      .trace-button:disabled { opacity: .4; cursor: not-allowed; }
      .route-banner { position: fixed; z-index: 22; top: 82px; left: 50%; display: flex; align-items: center; gap: 10px; width: max-content; max-width: min(640px, calc(100vw - 32px)); padding: 10px 11px 10px 14px; border: 1px solid rgba(96, 165, 250, .26); border-radius: 5px; color: #dbeafe; background: rgba(10, 20, 36, .96); box-shadow: 0 14px 40px rgba(0, 0, 0, .34); backdrop-filter: blur(16px); transform: translateX(-50%); }
      .route-banner[hidden] { display: none; }
      .route-banner > span:nth-child(2) { overflow: hidden; font-size: 11px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
      .route-pulse { flex: none; width: 7px; height: 7px; border-radius: 50%; background: #67e8f9; box-shadow: 0 0 12px rgba(103, 232, 249, .85); }
      .route-banner button { flex: none; padding: 6px 9px; border: 1px solid rgba(148, 163, 184, .18); border-radius: 4px; color: #9fb0c7; background: rgba(148, 163, 184, .08); font: 9px Inter, "Segoe UI", sans-serif; cursor: pointer; }
      .route-banner button:hover { color: #fff; background: rgba(148, 163, 184, .16); }
      .link-group { margin-top: 17px; }
      .link-group h3 { display: flex; align-items: center; justify-content: space-between; margin: 0 0 8px; color: #9caac0; font-size: 8px; font-weight: 750; letter-spacing: .13em; }
      .link-group h3 span { color: #64748b; }
      .link-list { display: grid; gap: 5px; }
      .linked-note { display: grid; gap: 4px; width: 100%; padding: 9px 10px; border: 1px solid rgba(148, 163, 184, .1); border-radius: 4px; color: #dbeafe; background: rgba(148, 163, 184, .045); text-align: left; cursor: pointer; }
      .linked-note:hover { border-color: rgba(103, 232, 249, .28); background: rgba(34, 211, 238, .08); }
      .semantic-note { border-style: dashed; border-color: rgba(148, 163, 184, .2); }
      .semantic-note .linked-note-name { color: #d4dbe7; }
      .semantic-note small { color: #a7b0c1; }
      .linked-note-name { overflow: hidden; font-size: 11px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
      .linked-note small { overflow: hidden; color: #7f8da4; font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }
      .link-empty { margin: 0; padding: 9px 10px; border: 1px dashed rgba(148, 163, 184, .15); border-radius: 9px; color: #718096; font-size: 10px; }
      .graph-legend, .graph-hint {
        position: fixed; z-index: 20; bottom: 18px; pointer-events: none;
        border: 1px solid rgba(148, 163, 184, .16); border-radius: 5px;
        background: rgba(13, 20, 36, .72); color: #aab7ca;
        box-shadow: 0 8px 24px rgba(0, 0, 0, .18); backdrop-filter: blur(14px);
      }
      .graph-legend { left: 20px; display: flex; gap: 15px; padding: 9px 12px; font-size: 10px; }
      .graph-legend span { display: flex; align-items: center; gap: 7px; }
      .graph-legend i { width: 8px; height: 8px; border-radius: 50%; }
      .legend-note { background: #38bdf8; box-shadow: 0 0 9px rgba(56, 189, 248, .5); }
      .legend-open { background: #fb7185; box-shadow: 0 0 9px rgba(251, 113, 133, .55); }
      .legend-semantic { height: 0 !important; border-top: 2px dashed #94a3b8; border-radius: 0 !important; background: none; }
      .graph-hint { right: 20px; padding: 10px 13px; font-size: 8px; font-weight: 700; letter-spacing: .12em; }
      .graph-hint b { padding: 0 4px; color: #8b9bb4; }
      .graph-actions { position: fixed; z-index: 20; right: 20px; bottom: 58px; display: flex; gap: 6px; pointer-events: auto; }
      .graph-actions button { padding: 8px 11px; border: 1px solid rgba(148, 163, 184, .18); border-radius: 4px; color: #b9c6d8; background: rgba(13, 20, 36, .94); box-shadow: 0 8px 22px rgba(0, 0, 0, .2); backdrop-filter: blur(12px); font: 10px Inter, "Segoe UI", sans-serif; cursor: pointer; }
      .graph-actions button:hover { border-color: rgba(103, 232, 249, .34); color: #f0fdff; background: rgba(18, 36, 57, .92); }
      .graph-actions button.is-active { border-color: rgba(96, 165, 250, .36); color: #bfdbfe; }
      @media (max-width: 560px) {
        .graph-toolbar { top: 10px; left: 10px; right: 10px; display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; }
        .search-shell { order: 3; flex-basis: 100%; max-width: none; height: 42px; }
        .brand-lockup { padding: 7px 9px; gap: 8px; }
        .brand-mark { width: 31px; height: 31px; }
        .graph-stats { padding: 4px; }
        .stat { min-width: 0; padding: 5px 7px; column-gap: 4px; }
        .stat small { font-size: 7px; }
        .filter-rail { top: 110px; left: 10px; width: 132px; padding: 7px; }
        .note-inspector { top: 110px; right: 10px; max-height: calc(100vh - 170px); width: min(300px, calc(100vw - 160px)); padding: 12px; }
        .inspector-head h2 { font-size: 17px; }
        .graph-legend { left: 10px; bottom: 10px; gap: 9px; font-size: 9px; }
        .graph-hint { right: 10px; bottom: 10px; font-size: 7px; }
        .graph-actions { right: 10px; bottom: 44px; }
      }
    </style>
    """
    # A hand-authored SVG keeps the standalone graph branded without external
    # assets or generated imagery. The same vector is provided in the repo for
    # a future website to use at its own domain.
    favicon = (
        '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,'
        "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
        "%3Crect width='32' height='32' rx='4' fill='%23172234'/%3E"
        "%3Cg fill='none' stroke='%2393c5fd' stroke-width='2'%3E"
        "%3Cpath d='M8 9 16 5l8 4v10l-8 6-8-5z'/%3E"
        "%3Cpath d='m9 10 6 10 8-10M16 6v13'/%3E"
        "%3C/g%3E%3Cg fill='%23bfdbfe'%3E"
        "%3Ccircle cx='8' cy='9' r='2'/%3E%3Ccircle cx='16' cy='5' r='2'/%3E"
        "%3Ccircle cx='24' cy='9' r='2'/%3E%3Ccircle cx='16' cy='25' r='2'/%3E"
        '%3C/g%3E%3C/svg%3E">'
    )
    html = re.sub(
        r"</head>",
        lambda match: favicon + theme + match.group(0),
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    interactive_script = INTERACTION_SCRIPT.replace("{{ hub_threshold }}", str(hub_threshold))
    interactive_markup = (
        f'<script id="graph-index" type="application/json">{records_json}</script>'
        f"{interactive_script}"
    )
    html = re.sub(
        r"</body>",
        lambda match: interactive_markup + match.group(0),
        html,
        count=1,
        flags=re.IGNORECASE,
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _rgba(hex_color: str, alpha: float) -> str:
    """Convert a six-digit hex color to CSS rgba for the node glow."""
    red, green, blue = (
        int(hex_color[index : index + 2], 16)
        for index in (1, 3, 5)
    )
    return f"rgba({red}, {green}, {blue}, {alpha})"
