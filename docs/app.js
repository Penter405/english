/**
 * English Vocabulary Graph — Interactive Exam Topic Explorer (Option A)
 *
 * Architecture:
 *   - Level 1 (Root):   Life ── 9 Domains (radius 320, radial lines)
 *   - Level 2 (Domain): Life (opposite direction, 520px) ── Domain (0,0) ── Topics (outward fan 240px)
 *   - Clean geometry: Lines NEVER touch or cross other nodes (angular gap >= 110° from parent)
 *   - Click topic → vocabulary view directly showing 6 official levels
 */

// ===== State =====
let cy = null;
let graphData = null;
let vocabData = null;
let nodeMap = {};
let childrenMap = {};
let parentMap = {};

let currentPath = ['life'];
let currentView = 'graph'; // 'graph' | 'group'
let savedZoom = null;
let savedPan = null;

// Layout constants
const DOMAIN_RADIUS = 320;   // root → domain distance (root view)
const CHILD_RADIUS = 240;    // domain → topic distance (domain view, outward fan)
const ROOT_LINK_DIST = 520;  // domain → root distance (opposite direction, ample space)

// Domain color mapping (9 distinct, vibrant colors)
const DOMAIN_COLORS = {
  people_character:  { main: '#ec4899', bg: 'rgba(236,72,153,0.14)', border: 'rgba(236,72,153,0.45)' },
  mind_emotions:     { main: '#f472b6', bg: 'rgba(244,114,182,0.14)', border: 'rgba(244,114,182,0.45)' },
  body_actions:      { main: '#ef4444', bg: 'rgba(239,68,68,0.14)',   border: 'rgba(239,68,68,0.45)' },
  daily_life:        { main: '#f59e0b', bg: 'rgba(245,158,11,0.14)', border: 'rgba(245,158,11,0.45)' },
  school_education:  { main: '#8b5cf6', bg: 'rgba(139,92,246,0.14)', border: 'rgba(139,92,246,0.45)' },
  work_society:      { main: '#f97316', bg: 'rgba(249,115,22,0.14)',  border: 'rgba(249,115,22,0.45)' },
  tech_transport:    { main: '#06b6d4', bg: 'rgba(6,182,212,0.14)',   border: 'rgba(6,182,212,0.45)' },
  nature_science:    { main: '#10b981', bg: 'rgba(16,185,129,0.14)',  border: 'rgba(16,185,129,0.45)' },
  description_logic: { main: '#6366f1', bg: 'rgba(99,102,241,0.14)',  border: 'rgba(99,102,241,0.45)' }
};

// Level color mapping (Official Levels 1–6)
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

// ===== Render Cytoscape Graph =====
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
        labelZh: node.label_zh || '',
        nodeType: node.type,
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
      // ── Root Node ──
      {
        selector: 'node[nodeType="root"]',
        style: {
          'width': 75,
          'height': 75,
          'background-color': '#0a0e1a',
          'border-width': 3.5,
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
      // Root when displayed as breadcrumb in domain view
      {
        selector: 'node.breadcrumb',
        style: {
          'width': 48,
          'height': 48,
          'border-width': 2,
          'font-size': 11,
          'opacity': 0.75,
          'z-index': 12
        }
      },
      // ── Domain Nodes ──
      {
        selector: 'node[nodeType="domain"]',
        style: {
          'width': 62,
          'height': 62,
          'background-color': '#111827',
          'border-width': 2.8,
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
          'text-max-width': 120,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2.5,
          'z-index': 8,
          'overlay-opacity': 0,
          'transition-property': 'width, height, border-width',
          'transition-duration': '0.3s'
        }
      },
      // Focused domain in domain view
      {
        selector: 'node.focused',
        style: {
          'width': 74,
          'height': 74,
          'border-width': 3.8,
          'font-size': 15,
          'font-weight': 800,
          'z-index': 20
        }
      },
      // ── Topic (Subcategory) Nodes ──
      {
        selector: 'node[nodeType="topic"]',
        style: {
          'width': 44,
          'height': 44,
          'background-color': 'data(color)',
          'background-opacity': 0.18,
          'border-width': 2,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 11,
          'font-weight': 600,
          'font-family': 'Inter, sans-serif',
          'color': '#e2e8f0',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 8,
          'text-wrap': 'wrap',
          'text-max-width': 105,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2,
          'z-index': 5,
          'overlay-opacity': 0,
          'transition-property': 'background-opacity, width, height',
          'transition-duration': '0.2s'
        }
      },
      // ── Hierarchical Edges ──
      {
        selector: 'edge[edgeType="contains"]',
        style: {
          'width': 1.6,
          'line-color': 'rgba(148, 163, 184, 0.25)',
          'curve-style': 'straight',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 1
        }
      },
      // Breadcrumb edge (root/parent → current domain)
      {
        selector: 'edge.breadcrumb-edge',
        style: {
          'width': 1.4,
          'line-color': 'rgba(167, 139, 250, 0.35)',
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

  // Event handlers
  cy.on('tap', 'node', onNodeTap);
  cy.on('mouseover', 'node', () => { document.getElementById('cy').style.cursor = 'pointer'; });
  cy.on('mouseout', 'node', () => { document.getElementById('cy').style.cursor = 'default'; });

  // Initial Root View
  currentPath = ['life'];
  enterView('life', false);
}

// ===== View Switching & Positioning =====

function enterView(nodeId, animate) {
  if (nodeId === 'life') {
    enterRootView(animate);
  } else {
    enterDomainView(nodeId, animate);
  }
}

// 1. Root View (Life at center + 9 Domains radially placed)
function enterRootView(animate) {
  currentPath = ['life'];
  updateBreadcrumb();

  const positions = {};
  positions['life'] = { x: 0, y: 0 };

  const domains = childrenMap['life'] || [];
  for (const dId of domains) {
    const node = nodeMap[dId];
    if (node) {
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

    // Show Root
    cy.getElementById('life').style('display', 'element');

    // Show Domains + radial straight edges (zero overlap)
    for (const dId of domains) {
      cy.getElementById(dId).style('display', 'element');
      const edge = cy.getElementById(`life-${dId}`);
      if (edge.length) edge.style('display', 'element');
    }
  });

  applyPositions(positions, animate);
  fitVisible(animate);
}

// 2. Domain View (Focused domain at center, Root in opposite direction, children in outward fan)
function enterDomainView(domainId, animate) {
  currentPath = ['life', domainId];
  updateBreadcrumb();

  const domainNode = nodeMap[domainId];
  const parentId = parentMap[domainId] || 'life';
  const children = childrenMap[domainId] || [];

  // Vector (dx, dy) of domain from root
  const dx = domainNode.x || 0;
  const dy = domainNode.y || 0;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;

  // Parent is in EXACT OPPOSITE direction (-dx, -dy) at distance ROOT_LINK_DIST (520)
  const parentX = (-dx / dist) * ROOT_LINK_DIST;
  const parentY = (-dy / dist) * ROOT_LINK_DIST;

  const positions = {};
  positions[parentId] = { x: parentX, y: parentY };
  positions[domainId] = { x: 0, y: 0 };

  // Outward direction angle (facing away from parent/root)
  const outwardAngleRad = Math.atan2(dy, dx);
  const outwardAngleDeg = outwardAngleRad * 180 / Math.PI;

  // Position children in an outward fan/arc centered at outwardAngleDeg
  // Span is 130 deg for <= 4 children, 150 deg for 5 children
  // Guaranteed angular gap to parent >= 105 deg: lines NEVER touch any node!
  const numChildren = children.length;
  const spanDeg = numChildren <= 4 ? 130 : 150;
  const startAngleDeg = outwardAngleDeg - spanDeg / 2;
  const stepDeg = spanDeg / Math.max(numChildren - 1, 1);

  for (let j = 0; j < numChildren; j++) {
    const childId = children[j];
    const angleDeg = startAngleDeg + j * stepDeg;
    const angleRad = angleDeg * Math.PI / 180;
    positions[childId] = {
      x: Math.cos(angleRad) * CHILD_RADIUS,
      y: Math.sin(angleRad) * CHILD_RADIUS
    };
  }

  cy.batch(() => {
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show Root/Parent as breadcrumb
    const parentEle = cy.getElementById(parentId);
    parentEle.style('display', 'element');
    parentEle.addClass('breadcrumb');

    // Show Focused Domain
    const domainEle = cy.getElementById(domainId);
    domainEle.style('display', 'element');
    domainEle.addClass('focused');

    // Show breadcrumb edge (dashed)
    const breadcrumbEdge = cy.getElementById(`${parentId}-${domainId}`);
    if (breadcrumbEdge.length) {
      breadcrumbEdge.style('display', 'element');
      breadcrumbEdge.addClass('breadcrumb-edge');
    }

    // Show Subcategory children + outward lines
    for (const childId of children) {
      cy.getElementById(childId).style('display', 'element');
      const edge = cy.getElementById(`${domainId}-${childId}`);
      if (edge.length) edge.style('display', 'element');
    }
  });

  applyPositions(positions, animate);
  fitVisible(animate);
}

// ===== Animation & Camera Helpers =====
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

// ===== Node Tap Interaction =====
function onNodeTap(e) {
  const node = e.target;
  const nodeId = node.data('id');
  const nodeType = node.data('nodeType');
  const nodeData = nodeMap[nodeId];

  // If clicking breadcrumb parent (e.g. Life) → return to Root View
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

  // If root node clicked in root view → re-fit
  if (nodeId === 'life' && currentPath.length === 1) {
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
    return;
  }

  // If node has children (Domain) → drill down to domain view
  const children = childrenMap[nodeId] || [];
  if (children.length > 0) {
    currentPath.push(nodeId);
    enterView(nodeId, true);
    return;
  }

  // If node is a topic (Subcategory leaf node) → directly open Group View showing 6 levels
  if (nodeType === 'topic' || (nodeData && nodeData.words)) {
    openGroup(nodeData);
  }
}

// ===== View Switching (Graph ↔ Group) =====
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

  if (currentPath.length > 2) {
    currentPath.pop();
  }
  updateBreadcrumb();

  if (cy && savedZoom !== null && savedPan !== null) {
    cy.viewport({ zoom: savedZoom, pan: savedPan });
  }
}

// ===== Open Group View (Directly displays the 6 Levels) =====
function openGroup(nodeData) {
  const domainId = getParentDomain(nodeData.id) || nodeData.id;
  currentPath = ['life', domainId, nodeData.id];
  updateBreadcrumb();

  showGroupView();

  const container = document.getElementById('group-container');
  const colorSet = DOMAIN_COLORS[domainId] || { main: '#64748b', bg: 'rgba(100,116,139,0.14)', border: 'rgba(100,116,139,0.45)' };
  const domainNode = nodeMap[domainId];
  const domainLabel = domainNode ? (domainNode.label_zh ? `${domainNode.label} (${domainNode.label_zh})` : domainNode.label) : '';

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

  const topicLabelZh = nodeData.label_zh ? ` · ${nodeData.label_zh}` : '';

  let html = `
    <div class="group-header">
      ${domainLabel ? `<div class="group-domain-badge" style="color: ${colorSet.main}; background: ${colorSet.bg}; border-color: ${colorSet.border};">
        <span>●</span> ${domainLabel}
      </div>` : ''}
      <h1 class="group-name">${nodeData.label}<span style="font-size: 1.3rem; opacity: 0.8; font-weight: 500;">${topicLabelZh}</span></h1>
      <p class="group-word-count">${words.length} words in this category</p>
    </div>
  `;

  // Render each of the 6 level sections (only if it contains words)
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
  const examStr = vd.cnt > 0 ? `📝 Appeared in exams: ${vd.exam.join(', ')} (${vd.cnt} time(s))` : '';
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
      contentHtml = '<div class="def-section"><h3>繁體中文釋義</h3><ul>' +
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

// ===== Breadcrumb Path Navigation =====
function updateBreadcrumb() {
  const bar = document.getElementById('breadcrumb-bar');
  if (!bar) return;
  let html = '';

  for (let i = 0; i < currentPath.length; i++) {
    const id = currentPath[i];
    const node = nodeMap[id];
    let label = node ? node.label : id;
    if (node && node.label_zh) {
      label = `${node.label} (${node.label_zh})`;
    }
    if (i > 0) html += '<span class="breadcrumb-sep">›</span>';
    if (i === currentPath.length - 1) {
      html += `<span class="breadcrumb-item current">${label}</span>`;
    } else {
      html += `<button class="breadcrumb-item" onclick="goToLevel(${i})">${label}</button>`;
    }
  }

  bar.innerHTML = html;
}

function goToRoot() {
  currentPath = ['life'];
  if (currentView === 'group') showGraph();
  enterRootView(true);
}

function goToLevel(idx) {
  if (idx < 0 || idx >= currentPath.length) return;
  if (currentView === 'group') showGraph();
  if (idx === 0) {
    goToRoot();
  } else {
    currentPath = currentPath.slice(0, idx + 1);
    const targetId = currentPath[currentPath.length - 1];
    enterDomainView(targetId, true);
  }
}

// ===== Run =====
initGraph();
