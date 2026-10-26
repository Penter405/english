/**
 * English Vocabulary Graph — Interactive Topic Explorer
 *
 * Drill-down navigation:
 *   Level 1 (root):   Life ── domains
 *   Level 2 (domain): Life ─────── Domain ── topics
 *   Click topic → vocabulary view
 */

// ===== State =====
let cy = null;
let graphData = null;
let nodeMap = {};
let domainChildren = {};
let viewLevel = 'root';    // 'root' | 'domain'
let currentDomainId = null;
let currentView = 'graph'; // 'graph' | 'group'
let savedZoom = null;
let savedPan = null;

// Layout constants
const DOMAIN_RADIUS = 300;   // root → domain distance (root view)
const TOPIC_RADIUS = 200;    // domain → topic distance (domain view)
const ROOT_LINK_DIST = 500;  // domain → root distance (domain view, longer)

// Domain color mapping
const DOMAIN_COLORS = {
  home_life:  { main: '#f59e0b', bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.4)' },
  food:       { main: '#ef4444', bg: 'rgba(239,68,68,0.12)',   border: 'rgba(239,68,68,0.4)' },
  transport:  { main: '#3b82f6', bg: 'rgba(59,130,246,0.12)',  border: 'rgba(59,130,246,0.4)' },
  technology: { main: '#06b6d4', bg: 'rgba(6,182,212,0.12)',   border: 'rgba(6,182,212,0.4)' },
  education:  { main: '#8b5cf6', bg: 'rgba(139,92,246,0.12)',  border: 'rgba(139,92,246,0.4)' },
  work:       { main: '#f97316', bg: 'rgba(249,115,22,0.12)',  border: 'rgba(249,115,22,0.4)' },
  society:    { main: '#ec4899', bg: 'rgba(236,72,153,0.12)',  border: 'rgba(236,72,153,0.4)' },
  abstract:   { main: '#a78bfa', bg: 'rgba(167,139,250,0.12)', border: 'rgba(167,139,250,0.4)' },
  science:    { main: '#10b981', bg: 'rgba(16,185,129,0.12)',  border: 'rgba(16,185,129,0.4)' },
  nature:     { main: '#22c55e', bg: 'rgba(34,197,94,0.12)',   border: 'rgba(34,197,94,0.4)' }
};

// ===== Initialization =====
async function initGraph() {
  const loadingEl = document.getElementById('graph-loading');
  const errorEl = document.getElementById('graph-error');
  loadingEl.style.display = 'flex';
  errorEl.style.display = 'none';

  try {
    const res = await fetch('./data/graph.json');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    graphData = await res.json();
    buildNodeMap();
    buildDomainChildren();
    renderGraph();
    loadingEl.style.display = 'none';
  } catch (err) {
    console.error('Failed to load graph:', err);
    loadingEl.style.display = 'none';
    errorEl.style.display = 'flex';
    document.getElementById('error-text').textContent = `Failed to load graph data: ${err.message}`;
  }
}

function buildNodeMap() {
  nodeMap = {};
  for (const node of graphData.graph.nodes) {
    nodeMap[node.id] = node;
  }
}

function buildDomainChildren() {
  domainChildren = {};
  for (const edge of graphData.graph.edges) {
    if (edge.type === 'contains') {
      const src = nodeMap[edge.source];
      const tgt = nodeMap[edge.target];
      if (src && tgt && src.type === 'domain' && tgt.type === 'topic') {
        if (!domainChildren[edge.source]) domainChildren[edge.source] = [];
        domainChildren[edge.source].push(edge.target);
      }
    }
  }
}

function getParentDomain(nodeId) {
  for (const edge of graphData.graph.edges) {
    if (edge.type === 'contains' && edge.target === nodeId) {
      const src = nodeMap[edge.source];
      if (src && src.type === 'domain') return edge.source;
    }
  }
  return null;
}

// ===== Render Graph (one-time setup) =====
function renderGraph() {
  const cyElements = [];

  // Add ALL nodes (positioned at origin initially; view functions set real positions)
  for (const node of graphData.graph.nodes) {
    const domainId = getParentDomain(node.id);
    const colorSet = node.type === 'domain'
      ? (DOMAIN_COLORS[node.id] || { main: '#64748b' })
      : (node.type === 'topic'
        ? (DOMAIN_COLORS[domainId] || { main: '#64748b' })
        : { main: '#f1f5f9' });

    cyElements.push({
      group: 'nodes',
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.type,
        groupId: node.group_id || null,
        color: colorSet.main,
        domainId: domainId
      },
      position: { x: 0, y: 0 }
    });
  }

  // Add ALL edges
  for (const edge of graphData.graph.edges) {
    cyElements.push({
      group: 'edges',
      data: {
        id: `${edge.source}-${edge.target}`,
        source: edge.source,
        target: edge.target,
        edgeType: edge.type
      }
    });
  }

  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: cyElements,
    layout: { name: 'preset' },
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
    autoungrabify: false,
    minZoom: 0.2,
    maxZoom: 3,
    wheelSensitivity: 0.3,
    style: [
      // ── Root node ──
      {
        selector: 'node[nodeType="root"]',
        style: {
          'width': 70,
          'height': 70,
          'background-color': '#0a0e1a',
          'border-width': 3,
          'border-color': '#a78bfa',
          'label': 'data(label)',
          'font-size': 16,
          'font-weight': 800,
          'font-family': 'Inter, sans-serif',
          'color': '#f1f5f9',
          'text-valign': 'center',
          'text-halign': 'center',
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 3,
          'z-index': 10,
          'overlay-opacity': 0,
          'transition-property': 'width, height, border-width, opacity',
          'transition-duration': '0.3s'
        }
      },
      // Root node when shown as breadcrumb in domain view
      {
        selector: 'node[nodeType="root"].breadcrumb',
        style: {
          'width': 44,
          'height': 44,
          'border-width': 2,
          'font-size': 11,
          'opacity': 0.7
        }
      },
      // ── Domain nodes ──
      {
        selector: 'node[nodeType="domain"]',
        style: {
          'width': 56,
          'height': 56,
          'background-color': '#111827',
          'border-width': 2.5,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 13,
          'font-weight': 700,
          'font-family': 'Inter, sans-serif',
          'color': 'data(color)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 10,
          'text-wrap': 'wrap',
          'text-max-width': 110,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2.5,
          'z-index': 8,
          'overlay-opacity': 0,
          'transition-property': 'width, height, border-width',
          'transition-duration': '0.3s'
        }
      },
      // Domain node when it's the focused one in domain view
      {
        selector: 'node[nodeType="domain"].focused',
        style: {
          'width': 68,
          'height': 68,
          'border-width': 3.5,
          'font-size': 15,
          'font-weight': 800,
          'z-index': 20
        }
      },
      // ── Topic nodes ──
      {
        selector: 'node[nodeType="topic"]',
        style: {
          'width': 34,
          'height': 34,
          'background-color': 'data(color)',
          'background-opacity': 0.18,
          'border-width': 1.8,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 10,
          'font-weight': 600,
          'font-family': 'Inter, sans-serif',
          'color': '#e2e8f0',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 7,
          'text-wrap': 'wrap',
          'text-max-width': 90,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2,
          'z-index': 5,
          'overlay-opacity': 0,
          'transition-property': 'background-opacity, width, height',
          'transition-duration': '0.2s'
        }
      },
      // ── Contains edges (hierarchical) ──
      {
        selector: 'edge[edgeType="contains"]',
        style: {
          'width': 1.5,
          'line-color': 'rgba(148, 163, 184, 0.2)',
          'curve-style': 'straight',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 1
        }
      },
      // Breadcrumb edge (root→domain in domain view) — thinner, dashed
      {
        selector: 'edge.breadcrumb-edge',
        style: {
          'width': 1,
          'line-color': 'rgba(167, 139, 250, 0.2)',
          'line-style': 'dashed',
          'line-dash-pattern': [8, 6],
          'z-index': 0
        }
      },
      // ── Related edges (cross-domain) ──
      {
        selector: 'edge[edgeType="related"]',
        style: {
          'width': 0.8,
          'line-color': 'rgba(99, 102, 241, 0.06)',
          'line-style': 'dashed',
          'line-dash-pattern': [6, 4],
          'curve-style': 'unbundled-bezier',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 0
        }
      },
      // ── Hover / active states ──
      {
        selector: 'node:active',
        style: {
          'overlay-opacity': 0.08
        }
      }
    ]
  });

  // ── Event Listeners ──
  cy.on('tap', 'node[nodeType="topic"]', onTopicClick);
  cy.on('tap', 'node[nodeType="domain"]', onDomainClick);
  cy.on('tap', 'node[nodeType="root"]', onRootClick);

  // Cursor pointer on hover
  cy.on('mouseover', 'node', function() { document.getElementById('cy').style.cursor = 'pointer'; });
  cy.on('mouseout', 'node', function() { document.getElementById('cy').style.cursor = 'default'; });

  // Click background → do nothing special
  cy.on('tap', function(e) { if (e.target === cy) { /* no-op */ } });

  // Enter root view (no animation on first load)
  enterRootView(false);
}

// ===== View: Root Level (Life + Domains) =====
function enterRootView(animate) {
  viewLevel = 'root';
  currentDomainId = null;

  // Compute positions
  const positions = {};
  positions['life'] = { x: 0, y: 0 };

  for (const node of graphData.graph.nodes) {
    if (node.type === 'domain') {
      // Use original graph coordinates, scaled to DOMAIN_RADIUS
      const ox = node.x, oy = node.y;
      const dist = Math.sqrt(ox * ox + oy * oy) || 1;
      positions[node.id] = {
        x: (ox / dist) * DOMAIN_RADIUS,
        y: (oy / dist) * DOMAIN_RADIUS
      };
    }
  }

  // Show / hide elements
  cy.batch(() => {
    // Hide everything first
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');

    // Remove all classes
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show root
    cy.getElementById('life').style('display', 'element');

    // Show domains + root→domain edges
    for (const node of graphData.graph.nodes) {
      if (node.type === 'domain') {
        cy.getElementById(node.id).style('display', 'element');
        const edgeId = `life-${node.id}`;
        const edge = cy.getElementById(edgeId);
        if (edge.length) edge.style('display', 'element');
      }
    }
  });

  // Set positions
  applyPositions(positions, animate);

  // Fit
  fitVisible(animate);
}

// ===== View: Domain Level (Domain + Topics, Root as breadcrumb) =====
function enterDomainView(domainId, animate) {
  viewLevel = 'domain';
  currentDomainId = domainId;

  const domainNode = nodeMap[domainId];
  const children = domainChildren[domainId] || [];

  // Compute root position: opposite direction of domain's original position
  const dx = domainNode.x, dy = domainNode.y;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const rootX = (-dx / dist) * ROOT_LINK_DIST;
  const rootY = (-dy / dist) * ROOT_LINK_DIST;

  const positions = {};
  positions['life'] = { x: rootX, y: rootY };
  positions[domainId] = { x: 0, y: 0 };

  // Position topics around domain using their angle_degrees
  for (const childId of children) {
    const childNode = nodeMap[childId];
    if (childNode) {
      const angleDeg = childNode.angle_degrees || 0;
      const angleRad = angleDeg * Math.PI / 180;
      positions[childId] = {
        x: Math.cos(angleRad) * TOPIC_RADIUS,
        y: Math.sin(angleRad) * TOPIC_RADIUS
      };
    }
  }

  // Show / hide elements
  cy.batch(() => {
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show root as breadcrumb
    const rootEle = cy.getElementById('life');
    rootEle.style('display', 'element');
    rootEle.addClass('breadcrumb');

    // Show domain as focused
    const domainEle = cy.getElementById(domainId);
    domainEle.style('display', 'element');
    domainEle.addClass('focused');

    // Show root→domain edge as breadcrumb
    const rootEdge = cy.getElementById(`life-${domainId}`);
    if (rootEdge.length) {
      rootEdge.style('display', 'element');
      rootEdge.addClass('breadcrumb-edge');
    }

    // Show topics + domain→topic edges
    for (const childId of children) {
      cy.getElementById(childId).style('display', 'element');
      const edgeId = `${domainId}-${childId}`;
      const edge = cy.getElementById(edgeId);
      if (edge.length) edge.style('display', 'element');
    }
  });

  // Set positions
  applyPositions(positions, animate);

  // Fit
  fitVisible(animate);
}

// ===== Helpers =====
function applyPositions(positions, animate) {
  for (const [id, pos] of Object.entries(positions)) {
    const ele = cy.getElementById(id);
    if (!ele.length) continue;
    if (animate) {
      ele.animate({ position: pos }, { duration: 450, easing: 'ease-in-out-cubic' });
    } else {
      ele.position(pos);
    }
  }
}

function fitVisible(animate) {
  const visible = cy.elements(':visible');
  if (animate) {
    setTimeout(() => {
      cy.animate({ fit: { eles: visible, padding: 60 } }, { duration: 350, easing: 'ease-in-out-cubic' });
    }, 470);
  } else {
    cy.fit(visible, 60);
  }
}

// ===== Node Click Handlers =====
function onTopicClick(e) {
  const node = e.target;
  const groupId = node.data('groupId');
  if (groupId) {
    openGroup(groupId, node.data('label'), node.data('domainId'));
  }
}

function onDomainClick(e) {
  const domainId = e.target.data('id');
  if (viewLevel === 'domain' && currentDomainId === domainId) {
    // Already viewing this domain — do nothing
    return;
  }
  enterDomainView(domainId, true);
}

function onRootClick() {
  if (viewLevel === 'domain') {
    enterRootView(true);
  } else {
    // Already at root level — just re-fit
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
  }
}

// ===== View Switching (graph ↔ group) =====
function showGroupView() {
  if (cy) {
    savedZoom = cy.zoom();
    savedPan = { ...cy.pan() };
  }
  currentView = 'group';
  document.getElementById('graph-view').classList.remove('active');
  document.getElementById('group-view').classList.add('active');
  document.getElementById('back-btn').style.display = 'flex';
  document.getElementById('graph-controls').style.display = 'none';
}

function showGraph() {
  currentView = 'graph';
  document.getElementById('group-view').classList.remove('active');
  document.getElementById('graph-view').classList.add('active');
  document.getElementById('back-btn').style.display = 'none';
  document.getElementById('graph-controls').style.display = 'flex';

  if (cy && savedZoom !== null && savedPan !== null) {
    cy.viewport({ zoom: savedZoom, pan: savedPan });
  }
}

// ===== Open Group =====
async function openGroup(groupId, label, domainId) {
  showGroupView();

  const container = document.getElementById('group-container');
  container.innerHTML = `
    <div class="group-loading">
      <div class="loader-ring"></div>
      <p class="loader-text">Loading "${label}"…</p>
    </div>
  `;

  const paddedId = String(groupId).padStart(3, '0');
  const url = `./data/groups/group_${paddedId}.json`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderGroup(data, domainId);
  } catch (err) {
    console.error('Failed to load group:', err);
    container.innerHTML = `
      <div class="group-error">
        <span class="error-icon">⚠️</span>
        <p>Could not load vocabulary for "${label}".</p>
        <p style="font-size: 0.85rem; color: var(--text-muted);">${err.message}</p>
        <button class="retry-btn" onclick="openGroup(${groupId}, '${label.replace(/'/g, "\\'")}', '${domainId}')">Retry</button>
      </div>
    `;
  }
}

// ===== Render Group =====
function renderGroup(data, domainId) {
  const container = document.getElementById('group-container');
  const color = DOMAIN_COLORS[domainId] || { main: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.4)' };
  const domainNode = nodeMap[domainId];
  const domainLabel = domainNode ? domainNode.label : '';
  const totalWords = (data.levels.easy?.length || 0) + (data.levels.medium?.length || 0) + (data.levels.hard?.length || 0);

  container.innerHTML = `
    <div class="group-header">
      ${domainLabel ? `<div class="group-domain-badge" style="color: ${color.main}; background: ${color.bg}; border-color: ${color.border};">
        <span>●</span> ${domainLabel}
      </div>` : ''}
      <h1 class="group-name">${data.topic}</h1>
      <p class="group-word-count">${totalWords} words · Group ${data.id}</p>
    </div>
    ${renderDifficultySection('easy', 'Easy', data.levels.easy || [])}
    ${renderDifficultySection('medium', 'Medium', data.levels.medium || [])}
    ${renderDifficultySection('hard', 'Hard', data.levels.hard || [])}
  `;
}

function renderDifficultySection(level, label, words) {
  if (!words.length) return '';
  const chips = words.map(w => `<span class="word-chip ${level}">${w}</span>`).join('');
  return `
    <div class="difficulty-section ${level}">
      <div class="difficulty-header">
        <span class="difficulty-dot"></span>
        <span class="difficulty-label">${label}</span>
        <span class="difficulty-count">${words.length} words</span>
      </div>
      <div class="word-grid">${chips}</div>
    </div>
  `;
}

// ===== Graph Controls =====
function zoomIn() {
  if (!cy) return;
  const w = cy.width(), h = cy.height();
  cy.animate({
    zoom: { level: cy.zoom() * 1.3, renderedPosition: { x: w / 2, y: h / 2 } }
  }, { duration: 200 });
}

function zoomOut() {
  if (!cy) return;
  const w = cy.width(), h = cy.height();
  cy.animate({
    zoom: { level: cy.zoom() * 0.75, renderedPosition: { x: w / 2, y: h / 2 } }
  }, { duration: 200 });
}

function resetView() {
  if (!cy) return;
  if (viewLevel === 'domain') {
    enterRootView(true);
  } else {
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
  }
}

// ===== Init =====
initGraph();
