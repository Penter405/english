/**
 * English Vocabulary Graph — Interactive Exam Topic Explorer
 *
 * Drill-down navigation:
 *   Level 1 (root):   Life ── domains
 *   Level 2 (domain): Life ─────── Domain ── topics
 *   Click topic → vocabulary view directly showing 6 official levels
 */

// ===== State =====
let cy = null;
let graphData = null;
let vocabData = null;
let nodeMap = {};
let childrenMap = {};
let parentMap = {};

let currentPath = ['life']; // e.g. ['life'] or ['life', 'home_life']
let currentView = 'graph';  // 'graph' | 'group'
let savedZoom = null;
let savedPan = null;

// Layout constants from the original web logic
const DOMAIN_RADIUS = 300;   // root → domain distance (root view)
const TOPIC_RADIUS = 200;    // domain → topic distance (domain view)
const ROOT_LINK_DIST = 500;  // domain → root distance (domain view, opposite direction)

// Domain color mapping (10 vibrant, distinct hues)
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

// Level color mapping
const LEVEL_CONFIG = {
  1: { name: 'Level 1 — Basic', cls: 'lv1', color: '#4ade80' },
  2: { name: 'Level 2 — Elementary', cls: 'lv2', color: '#2dd4bf' },
  3: { name: 'Level 3 — Intermediate', cls: 'lv3', color: '#38bdf8' },
  4: { name: 'Level 4 — Upper-Intermediate', cls: 'lv4', color: '#fbbf24' },
  5: { name: 'Level 5 — Advanced', cls: 'lv5', color: '#fb923c' },
  6: { name: 'Level 6 — Expert', cls: 'lv6', color: '#f87171' }
};

// ===== Initialization =====
async function initGraph() {
  const loadingEl = document.getElementById('graph-loading');
  const errorEl = document.getElementById('graph-error');
  loadingEl.style.display = 'flex';
  errorEl.style.display = 'none';

  try {
    const [graphRes, vocabRes] = await Promise.all([
      fetch('./data/graph.json'),
      fetch('./data/vocab_data.json')
    ]);
    if (!graphRes.ok) throw new Error(`Graph HTTP ${graphRes.status}`);
    if (!vocabRes.ok) throw new Error(`Vocab HTTP ${vocabRes.status}`);

    graphData = await graphRes.json();
    vocabData = await vocabRes.json();

    buildNodeMap();
    buildTreeMaps();
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

function buildTreeMaps() {
  childrenMap = {};
  parentMap = {};
  for (const edge of graphData.graph.edges) {
    if (edge.type === 'contains') {
      if (!childrenMap[edge.source]) childrenMap[edge.source] = [];
      childrenMap[edge.source].push(edge.target);
      parentMap[edge.target] = edge.source;
    }
  }
}

function getParentDomain(nodeId) {
  let curr = nodeId;
  while (curr) {
    const node = nodeMap[curr];
    if (node && node.type === 'domain') return curr;
    curr = parentMap[curr];
  }
  return null;
}

// ===== Render Graph (one-time setup) =====
function renderGraph() {
  const cyElements = [];

  for (const node of graphData.graph.nodes) {
    const domainId = getParentDomain(node.id) || node.id;
    const colorSet = DOMAIN_COLORS[domainId] || { main: '#64748b' };

    cyElements.push({
      group: 'nodes',
      data: {
        id: node.id,
        label: node.label,
        nodeType: node.type,
        groupId: node.group_id || null,
        color: colorSet.main,
        domainId: domainId,
        wordCount: node.word_count || (node.words ? node.words.length : 0)
      },
      position: { x: 0, y: 0 }
    });
  }

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
    minZoom: 0.15,
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
      // Root / Parent when shown as breadcrumb
      {
        selector: 'node.breadcrumb',
        style: {
          'width': 44,
          'height': 44,
          'border-width': 2,
          'font-size': 11,
          'opacity': 0.75
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
      // Focused domain or node
      {
        selector: 'node.focused',
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
          'width': 36,
          'height': 36,
          'background-color': 'data(color)',
          'background-opacity': 0.18,
          'border-width': 1.8,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 10.5,
          'font-weight': 600,
          'font-family': 'Inter, sans-serif',
          'color': '#e2e8f0',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 7,
          'text-wrap': 'wrap',
          'text-max-width': 95,
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
          'line-color': 'rgba(148, 163, 184, 0.22)',
          'curve-style': 'straight',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 1
        }
      },
      // Breadcrumb edge (root/parent → current) — dashed
      {
        selector: 'edge.breadcrumb-edge',
        style: {
          'width': 1.2,
          'line-color': 'rgba(167, 139, 250, 0.3)',
          'line-style': 'dashed',
          'line-dash-pattern': [8, 6],
          'z-index': 0
        }
      },
      {
        selector: 'node:active',
        style: { 'overlay-opacity': 0.08 }
      }
    ]
  });

  // ── Event Listeners ──
  cy.on('tap', 'node', onNodeTap);
  cy.on('mouseover', 'node', () => { document.getElementById('cy').style.cursor = 'pointer'; });
  cy.on('mouseout', 'node', () => { document.getElementById('cy').style.cursor = 'default'; });

  // Start at root view
  currentPath = ['life'];
  enterView('life', false);
}

// ===== View Navigation Logic =====

function enterView(nodeId, animate) {
  if (nodeId === 'life') {
    enterRootView(animate);
  } else {
    enterChildView(nodeId, animate);
  }
}

// ===== Root Level (Life + 10 Domains) =====
function enterRootView(animate) {
  currentPath = ['life'];

  const positions = {};
  positions['life'] = { x: 0, y: 0 };

  const domains = childrenMap['life'] || [];
  for (const dId of domains) {
    const node = nodeMap[dId];
    if (node) {
      // Use original graph coordinates scaled to DOMAIN_RADIUS
      const ox = node.x, oy = node.y;
      const dist = Math.sqrt(ox * ox + oy * oy) || 1;
      positions[dId] = {
        x: (ox / dist) * DOMAIN_RADIUS,
        y: (oy / dist) * DOMAIN_RADIUS
      };
    }
  }

  cy.batch(() => {
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show root
    cy.getElementById('life').style('display', 'element');

    // Show domains + edges
    for (const dId of domains) {
      cy.getElementById(dId).style('display', 'element');
      const edge = cy.getElementById(`life-${dId}`);
      if (edge.length) edge.style('display', 'element');
    }
  });

  applyPositions(positions, animate);
  fitVisible(animate);
}

// ===== Non-Root Level (Domain/Category View with Parent as Breadcrumb) =====
function enterChildView(nodeId, animate) {
  const focusedNode = nodeMap[nodeId];
  const parentId = parentMap[nodeId] || 'life';
  const children = childrenMap[nodeId] || [];

  // Compute parent position: opposite direction of node's original position from parent
  const dx = focusedNode.x || 0;
  const dy = focusedNode.y || 0;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const parentX = (-dx / dist) * ROOT_LINK_DIST;
  const parentY = (-dy / dist) * ROOT_LINK_DIST;

  const positions = {};
  positions[parentId] = { x: parentX, y: parentY };
  positions[nodeId] = { x: 0, y: 0 };

  // Position children around focused node using their angle_degrees
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

  cy.batch(() => {
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show parent as breadcrumb
    const parentEle = cy.getElementById(parentId);
    parentEle.style('display', 'element');
    parentEle.addClass('breadcrumb');

    // Show focused node
    const focusedEle = cy.getElementById(nodeId);
    focusedEle.style('display', 'element');
    focusedEle.addClass('focused');

    // Show parent → focused edge as breadcrumb edge
    const parentEdge = cy.getElementById(`${parentId}-${nodeId}`);
    if (parentEdge.length) {
      parentEdge.style('display', 'element');
      parentEdge.addClass('breadcrumb-edge');
    }

    // Show children + edges
    for (const childId of children) {
      cy.getElementById(childId).style('display', 'element');
      const edge = cy.getElementById(`${nodeId}-${childId}`);
      if (edge.length) edge.style('display', 'element');
    }
  });

  applyPositions(positions, animate);
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

// ===== Node Tap Handler =====
function onNodeTap(e) {
  const node = e.target;
  const nodeId = node.data('id');
  const nodeType = node.data('nodeType');
  const nodeData = nodeMap[nodeId];

  // If clicking breadcrumb parent → go back up one level
  if (node.hasClass('breadcrumb')) {
    if (currentPath.length > 1) {
      currentPath.pop();
      enterView(currentPath[currentPath.length - 1], true);
    } else {
      enterRootView(true);
    }
    return;
  }

  // If clicking already focused node → do nothing
  if (node.hasClass('focused')) {
    return;
  }

  // If root node in root view → re-fit
  if (nodeId === 'life' && currentPath.length === 1) {
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
    return;
  }

  // Check if node has children
  const children = childrenMap[nodeId] || [];
  if (children.length > 0) {
    // Drill down to this node
    currentPath.push(nodeId);
    enterView(nodeId, true);
    return;
  }

  // If node is a topic (leaf node with words) → directly open group view
  if (nodeType === 'topic' || (nodeData && nodeData.words)) {
    openGroup(nodeData);
  }
}

// ===== View Switching (graph ↔ group view) =====
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

// ===== Open Group View (Displays the 6 Levels directly) =====
function openGroup(nodeData) {
  showGroupView();

  const container = document.getElementById('group-container');
  const domainId = getParentDomain(nodeData.id) || nodeData.id;
  const colorSet = DOMAIN_COLORS[domainId] || { main: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.4)' };
  const domainNode = nodeMap[domainId];
  const domainLabel = domainNode ? domainNode.label : '';

  const words = nodeData.words || [];

  // Group words into the 6 official levels
  const byLevel = { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
  for (const w of words) {
    const vd = vocabData[w];
    const lv = vd ? vd.lv : 1;
    if (byLevel[lv]) {
      byLevel[lv].push(w);
    } else {
      byLevel[1].push(w);
    }
  }

  let html = `
    <div class="group-header">
      ${domainLabel ? `<div class="group-domain-badge" style="color: ${colorSet.main}; background: ${colorSet.bg}; border-color: ${colorSet.border};">
        <span>●</span> ${domainLabel}
      </div>` : ''}
      <h1 class="group-name">${nodeData.label}</h1>
      <p class="group-word-count">${words.length} words · Group ${nodeData.group_id || ''}</p>
    </div>
  `;

  // Render all 6 level sections
  for (let lv = 1; lv <= 6; lv++) {
    const lvWords = byLevel[lv];
    if (!lvWords || lvWords.length === 0) continue;
    const cfg = LEVEL_CONFIG[lv];

    const chips = lvWords.map(w => {
      const vd = vocabData[w];
      const examBadge = vd && vd.cnt > 0 ? `<span class="exam-badge" title="Appeared in exams ${vd.cnt} time(s)">📝</span>` : '';
      return `<span class="word-chip ${cfg.cls}"
        onclick="showDefinition('${w}', 'en')"
        oncontextmenu="event.preventDefault(); showDefinition('${w}', 'zh')"
        ondblclick="showDefinition('${w}', 'zh')"
        title="Left Click: English | Right Click / Double Click: Chinese"
      >${w}${examBadge}</span>`;
    }).join('');

    html += `
      <div class="difficulty-section ${cfg.cls}">
        <div class="difficulty-header">
          <span class="difficulty-dot"></span>
          <span class="difficulty-label">${cfg.name}</span>
          <span class="difficulty-count">${lvWords.length} words</span>
        </div>
        <div class="word-grid">${chips}</div>
      </div>
    `;
  }

  container.innerHTML = html;
}

// ===== Word Definition Popup =====
function showDefinition(word, lang) {
  const vd = vocabData[word];
  if (!vd) return;

  const popup = document.getElementById('def-popup');
  const overlay = document.getElementById('def-overlay');

  document.getElementById('def-word').textContent = vd.w;

  const posStr = vd.pos && vd.pos.length ? vd.pos.join(', ') : '';
  const lvStr = `Level ${vd.lv}`;
  const examStr = vd.cnt > 0 ? `📝 Appeared in exams: ${vd.exam.join(', ')} (${vd.cnt} times)` : '';
  const formsStr = vd.forms && Object.keys(vd.forms).length > 0
    ? Object.entries(vd.forms).map(([k, v]) => `${k}: ${v}`).join(' | ')
    : '';
  const familyStr = vd.fam && vd.fam.length > 0 ? `Family: ${vd.fam.join(', ')}` : '';

  let metaHtml = `<span class="def-level">${lvStr}</span>`;
  if (posStr) metaHtml += `<span class="def-pos">${posStr}</span>`;
  if (examStr) metaHtml += `<div class="def-exam">${examStr}</div>`;
  if (formsStr) metaHtml += `<div class="def-forms">${formsStr}</div>`;
  if (familyStr) metaHtml += `<div class="def-family">${familyStr}</div>`;
  document.getElementById('def-meta').innerHTML = metaHtml;

  // Image support
  const imgContainer = document.getElementById('def-image-container');
  const imgEl = document.getElementById('def-image');
  const imgPath = `./data/images/${word}.png`;
  imgEl.src = imgPath;
  imgEl.onload = () => { imgContainer.style.display = 'block'; };
  imgEl.onerror = () => { imgContainer.style.display = 'none'; };

  // Definition content
  let contentHtml = '';
  if (lang === 'en') {
    const defs = vd.en || [];
    if (defs.length > 0) {
      contentHtml = '<div class="def-section"><h3>English Definition</h3><ul>' +
        defs.map(d => `<li>${d}</li>`).join('') +
        '</ul></div>';
    } else {
      contentHtml = '<p class="def-empty">No English definition available.</p>';
    }
  } else {
    const defs = vd.zh || [];
    if (defs.length > 0) {
      contentHtml = '<div class="def-section"><h3>中文釋義</h3><ul>' +
        defs.map(d => `<li>${d}</li>`).join('') +
        '</ul></div>';
    } else {
      contentHtml = '<p class="def-empty">無中文釋義。</p>';
    }
  }

  const otherLang = lang === 'en' ? 'zh' : 'en';
  const otherLabel = lang === 'en' ? '切換中文釋義' : 'Switch to English';
  contentHtml += `<button class="def-toggle" onclick="showDefinition('${word}', '${otherLang}')">${otherLabel}</button>`;

  document.getElementById('def-content').innerHTML = contentHtml;

  overlay.classList.add('visible');
  popup.classList.add('visible');
}

function closeDefinition() {
  document.getElementById('def-overlay').classList.remove('visible');
  document.getElementById('def-popup').classList.remove('visible');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDefinition();
});

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
  if (currentPath.length > 1) {
    enterRootView(true);
  } else {
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
  }
}

// ===== Run =====
initGraph();
