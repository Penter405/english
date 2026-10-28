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

// ===== Group View State & Multi-Criteria Sorting =====
let currentGroupNodeData = null;
let globalSortMode = 'cnt_desc'; // 'cnt_desc', 'yrs_desc', 'latest_first', 'alpha'
let globalSpecificYear = '';
let sectionSortModes = {}; // { 1: 'cnt_desc', ... }

function sortWords(wordList, mode, specificYear) {
  return [...wordList].sort((a, b) => {
    const vdA = vocabData[a] || {};
    const vdB = vocabData[b] || {};

    // Specific Year filter/priority
    if (specificYear) {
      const y = Number(specificYear);
      const inA = (vdA.exam && vdA.exam.includes(y)) ? 1 : 0;
      const inB = (vdB.exam && vdB.exam.includes(y)) ? 1 : 0;
      if (inB !== inA) return inB - inA;
    }

    if (mode === 'cnt_desc') {
      const diff = (vdB.cnt || 0) - (vdA.cnt || 0);
      if (diff !== 0) return diff;
      return a.localeCompare(b);
    }
    if (mode === 'yrs_desc') {
      const diff = (vdB.yrs_cnt || 0) - (vdA.yrs_cnt || 0);
      if (diff !== 0) return diff;
      const cDiff = (vdB.cnt || 0) - (vdA.cnt || 0);
      if (cDiff !== 0) return cDiff;
      return a.localeCompare(b);
    }
    if (mode === 'latest_first') {
      const diff = (vdB.latest_yr || 0) - (vdA.latest_yr || 0);
      if (diff !== 0) return diff;
      const cDiff = (vdB.cnt || 0) - (vdA.cnt || 0);
      if (cDiff !== 0) return cDiff;
      return a.localeCompare(b);
    }
    // 'alpha'
    return a.localeCompare(b);
  });
}

function setGlobalSort(mode) {
  globalSortMode = mode;
  sectionSortModes = {}; // Reset section overrides to follow global
  renderGroupContent();
}

function setGlobalSpecificYear(year) {
  globalSpecificYear = year;
  renderGroupContent();
}

function setSectionSort(lv, mode) {
  if (mode === 'global') {
    delete sectionSortModes[lv];
  } else {
    sectionSortModes[lv] = mode;
  }
  renderGroupContent();
}

// ===== Open Group View (Directly displays the 6 Levels) =====
function openGroup(nodeData) {
  const domainId = getParentDomain(nodeData.id) || nodeData.id;
  currentPath = ['life', domainId, nodeData.id];
  updateBreadcrumb();

  showGroupView();
  currentGroupNodeData = nodeData;
  renderGroupContent();
}

function renderGroupContent() {
  if (!currentGroupNodeData) return;
  const nodeData = currentGroupNodeData;
  const domainId = getParentDomain(nodeData.id) || nodeData.id;
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
      
      <!-- Global Adjust Toolbar -->
      <div class="adjust-bar global-adjust-bar">
        <div class="adjust-label"><span class="adjust-icon">⚙️</span> 全域排序 (Global Sort):</div>
        <div class="adjust-controls">
          <button class="adjust-btn ${globalSortMode === 'cnt_desc' && !globalSpecificYear ? 'active' : ''}" onclick="setGlobalSort('cnt_desc')">📊 出現次數</button>
          <button class="adjust-btn ${globalSortMode === 'yrs_desc' && !globalSpecificYear ? 'active' : ''}" onclick="setGlobalSort('yrs_desc')">📅 出現年數</button>
          <button class="adjust-btn ${globalSortMode === 'latest_first' && !globalSpecificYear ? 'active' : ''}" onclick="setGlobalSort('latest_first')">🕒 最新考年</button>
          <button class="adjust-btn ${globalSortMode === 'alpha' && !globalSpecificYear ? 'active' : ''}" onclick="setGlobalSort('alpha')">🔤 字母 A–Z</button>
          
          <select class="adjust-select ${globalSpecificYear ? 'active' : ''}" onchange="setGlobalSpecificYear(this.value)">
            <option value="">🎯 特定考年篩選...</option>
            <option value="115" ${globalSpecificYear === '115' ? 'selected' : ''}>115 學年度</option>
            <option value="114" ${globalSpecificYear === '114' ? 'selected' : ''}>114 學年度</option>
            <option value="113" ${globalSpecificYear === '113' ? 'selected' : ''}>113 學年度</option>
            <option value="112" ${globalSpecificYear === '112' ? 'selected' : ''}>112 學年度</option>
            <option value="111" ${globalSpecificYear === '111' ? 'selected' : ''}>111 學年度</option>
            <option value="110" ${globalSpecificYear === '110' ? 'selected' : ''}>110 學年度</option>
            <option value="109" ${globalSpecificYear === '109' ? 'selected' : ''}>109 學年度</option>
            <option value="108" ${globalSpecificYear === '108' ? 'selected' : ''}>108 學年度</option>
            <option value="107" ${globalSpecificYear === '107' ? 'selected' : ''}>107 學年度</option>
            <option value="106" ${globalSpecificYear === '106' ? 'selected' : ''}>106 學年度</option>
            <option value="105" ${globalSpecificYear === '105' ? 'selected' : ''}>105 學年度</option>
            <option value="104" ${globalSpecificYear === '104' ? 'selected' : ''}>104 學年度</option>
          </select>
        </div>
      </div>
    </div>
  `;

  // Render each of the 6 level sections (only if it contains words)
  for (let lv = 1; lv <= 6; lv++) {
    const rawLvWords = byLevel[lv];
    if (!rawLvWords || rawLvWords.length === 0) continue;
    const cfg = LEVEL_CONFIG[lv];

    // Determine effective sorting for this section
    const secSort = sectionSortModes[lv] || 'global';
    const effectiveMode = secSort === 'global' ? globalSortMode : secSort;
    const sortedWords = sortWords(rawLvWords, effectiveMode, globalSpecificYear);

    const chips = sortedWords.map(w => {
      const vd = vocabData[w];
      let examBadge = '';
      if (vd && vd.cnt > 0) {
        if (effectiveMode === 'yrs_desc') {
          examBadge = `<span class="exam-badge yrs" title="出題橫跨 ${vd.yrs_cnt} 年，共 ${vd.cnt} 次">📅${vd.yrs_cnt}年</span>`;
        } else if (effectiveMode === 'latest_first' && vd.latest_yr > 0) {
          examBadge = `<span class="exam-badge rec" title="最近於 ${vd.latest_yr} 年出題，共 ${vd.cnt} 次">🕒${vd.latest_yr}</span>`;
        } else {
          examBadge = `<span class="exam-badge" title="Appeared in exams ${vd.cnt} time(s) across ${vd.yrs_cnt} year(s)">📝${vd.cnt}</span>`;
        }
      }
      return `<span class="word-chip ${cfg.cls}"
        onclick="showDefinition('${w}', 'simple')"
        oncontextmenu="event.preventDefault(); showDefinition('${w}', 'zh')"
        ondblclick="showDefinition('${w}', 'zh')"
        title="Left Click: Level 1-2 Simple English | Right Click / Double Click: Chinese"
      >${w}${examBadge}</span>`;
    }).join('');

    html += `
      <div class="difficulty-section ${cfg.cls}">
        <div class="difficulty-header">
          <div class="difficulty-title-wrap">
            <span class="difficulty-dot"></span>
            <span class="difficulty-label">${cfg.name}</span>
            <span class="difficulty-count">${rawLvWords.length} words</span>
          </div>
          <div class="section-adjust-wrap">
            <label class="section-adjust-label">分區排序:</label>
            <select class="section-adjust-select" onchange="setSectionSort(${lv}, this.value)">
              <option value="global" ${secSort === 'global' ? 'selected' : ''}>連動全域 (${getSortLabel(globalSortMode)})</option>
              <option value="cnt_desc" ${secSort === 'cnt_desc' ? 'selected' : ''}>出現次數 (多→少)</option>
              <option value="yrs_desc" ${secSort === 'yrs_desc' ? 'selected' : ''}>出現年數 (多→少)</option>
              <option value="latest_first" ${secSort === 'latest_first' ? 'selected' : ''}>最新考年優先</option>
              <option value="alpha" ${secSort === 'alpha' ? 'selected' : ''}>字母 (A–Z)</option>
            </select>
          </div>
        </div>
        <div class="word-grid">${chips}</div>
      </div>
    `;
  }

  container.innerHTML = html;
}

function getSortLabel(mode) {
  if (mode === 'cnt_desc') return '次數';
  if (mode === 'yrs_desc') return '年數';
  if (mode === 'latest_first') return '最新';
  return 'A–Z';
}

// ===== Word Definition Popup =====
function showDefinition(word, lang = 'simple') {
  const vd = vocabData[word];
  if (!vd) return;

  const popup = document.getElementById('def-popup');
  const overlay = document.getElementById('def-overlay');

  document.getElementById('def-word').textContent = vd.w;

  const posStr = vd.pos && vd.pos.length ? vd.pos.join(', ') : '';
  const lvStr = `Level ${vd.lv}`;
  const examStr = vd.cnt > 0 
    ? `📝 統測歷屆考題：出題 ${vd.cnt} 次，橫跨 ${vd.yrs_cnt} 個學年度 [${vd.exam.join(', ')}] (最新: ${vd.latest_yr} 年)`
    : '📝 統測歷屆考題：尚未直接出題 (Level 1–4 基礎單字)';
  const formsStr = vd.forms && Object.keys(vd.forms).length > 0
    ? Object.entries(vd.forms).map(([k, v]) => `${k}: ${v}`).join(' | ')
    : '';
  const familyStr = vd.fam && vd.fam.length > 0 ? `Family: ${vd.fam.join(', ')}` : '';

  let metaHtml = `<span class="def-level">Level ${vd.lv}</span>`;
  if (posStr) metaHtml += `<span class="def-pos">${posStr}</span>`;
  metaHtml += `<div class="def-exam">${examStr}</div>`;
  if (formsStr) metaHtml += `<div class="def-forms">${formsStr}</div>`;
  if (familyStr) metaHtml += `<div class="def-family">${familyStr}</div>`;
  document.getElementById('def-meta').innerHTML = metaHtml;

  // Image support
  const imgContainer = document.getElementById('def-image-container');
  const imgEl = document.getElementById('def-image');
  imgEl.src = `./data/images/${word}.png`;
  imgEl.onload = () => { imgContainer.style.display = 'block'; };
  imgEl.onerror = () => { imgContainer.style.display = 'none'; };

  // Definition content with 3-way Mode Switcher (Simple EN, Advanced EN, Chinese)
  let contentHtml = `
    <div class="def-tabs">
      <button class="def-tab-btn ${lang === 'simple' ? 'active' : ''}" onclick="showDefinition('${word}', 'simple')">🟢 基礎英釋 (Level 1-2)</button>
      <button class="def-tab-btn ${lang === 'en' ? 'active' : ''}" onclick="showDefinition('${word}', 'en')">📘 詳細英釋 (Advanced)</button>
      <button class="def-tab-btn ${lang === 'zh' ? 'active' : ''}" onclick="showDefinition('${word}', 'zh')">🇹🇼 繁體中文</button>
    </div>
  `;

  if (lang === 'simple') {
    const simpleDef = vd.simple_en || '';
    if (simpleDef) {
      contentHtml += `
        <div class="simple-def-box">
          <div class="simple-def-tag">🌱 100% 基礎單字解釋 (Level 1–2 Defining Words)</div>
          <div class="simple-def-text">${simpleDef}</div>
        </div>
      `;
    } else {
      contentHtml += '<p class="def-empty">No Level 1-2 simple definition available.</p>';
    }
  } else if (lang === 'en') {
    const defs = vd.en || [];
    if (defs.length > 0) {
      contentHtml += '<div class="def-section"><h3>English Definitions</h3><ul>' +
        defs.map(d => `<li>${d}</li>`).join('') +
        '</ul></div>';
    } else {
      contentHtml += '<p class="def-empty">No English definition available.</p>';
    }
  } else {
    const defs = vd.zh || [];
    if (defs.length > 0) {
      contentHtml += '<div class="def-section"><h3>繁體中文釋義</h3><ul>' +
        defs.map(d => `<li>${d}</li>`).join('') +
        '</ul></div>';
    } else {
      contentHtml += '<p class="def-empty">無中文釋義。</p>';
    }
  }

  // Deterministic Root & Affix Breakdown Box (Zero Guesswork)
  if (vd.roots) {
    const r = vd.roots;
    contentHtml += `
      <div class="root-breakdown-box">
        <div class="root-breakdown-header">
          <span class="root-title">🔤 確定性字根字綴拆解 (Root & Affix Breakdown)</span>
          <span class="root-verified-badge">✨ 資料庫確定對照</span>
        </div>
        <div class="root-pills">
    `;

    if (r.prefix) {
      contentHtml += `<div class="root-pill prefix"><span class="rp-label">字首 (Prefix)</span><span class="rp-text">${r.prefix.text}</span><span class="rp-meaning">${r.prefix.meaning_zh} (${r.prefix.meaning_en})</span></div>`;
    }
    if (r.root) {
      contentHtml += `<div class="root-pill root"><span class="rp-label">字根 (Root)</span><span class="rp-text">${r.root.text}</span><span class="rp-meaning">${r.root.meaning_zh} (${r.root.meaning_en})</span></div>`;
    }
    if (r.suffix) {
      contentHtml += `<div class="root-pill suffix"><span class="rp-label">字尾 (Suffix)</span><span class="rp-text">${r.suffix.text}</span><span class="rp-meaning">${r.suffix.meaning_zh} (${r.suffix.meaning_en})</span></div>`;
    }

    contentHtml += `
        </div>
        <div class="root-synthesis"><strong>構詞聯想：</strong> ${r.synthesis_zh || r.synthesis_en}</div>
        ${r.explanation ? `<div class="root-explanation"><strong>同源說明：</strong> ${r.explanation}</div>` : ''}
      </div>
    `;
  }

  // Sentence Examples Box
  if (vd.sentences && vd.sentences.length > 0) {
    contentHtml += `
      <div class="sentences-box">
        <div class="sentences-header">📖 實用與真題例句 (Examples)</div>
        <div class="sentences-list">
    `;

    for (const sent of vd.sentences) {
      const isExam = sent.type === 'exam' || sent.source.includes('統測');
      const badgeCls = isExam ? 'exam-badge' : 'standard-badge';
      
      // Highlight target word in sentence
      const regex = new RegExp(`\\b(${word}[a-z]*)\\b`, 'gi');
      const highlightedEn = sent.en.replace(regex, '<span class="sentence-highlight">$1</span>');

      contentHtml += `
        <div class="sentence-card">
          <div class="sentence-meta">
            <span class="sentence-badge ${badgeCls}">${sent.source}</span>
          </div>
          <div class="sentence-en">${highlightedEn}</div>
          ${sent.zh ? `<div class="sentence-zh">${sent.zh}</div>` : ''}
        </div>
      `;
    }

    contentHtml += `
        </div>
      </div>
    `;
  }

  document.getElementById('def-content').innerHTML = contentHtml;

  overlay.classList.add('visible');
  popup.classList.add('visible');
}

function closeDefinition() {
  document.getElementById('def-overlay').classList.remove('visible');
  document.getElementById('def-popup').classList.remove('visible');
}

// ===== Affix Compound Search Modal =====
function openAffixSearchModal() {
  document.getElementById('search-overlay').classList.add('visible');
  document.getElementById('search-modal').classList.add('visible');
  const pfxInput = document.getElementById('search-prefix');
  pfxInput.focus();
  triggerAffixSearch();
}

function closeAffixSearchModal() {
  document.getElementById('search-overlay').classList.remove('visible');
  document.getElementById('search-modal').classList.remove('visible');
}

function triggerAffixSearch() {
  const pfxInput = (document.getElementById('search-prefix').value || '').trim().toLowerCase().replace(/\*+$/, '');
  const sfxInput = (document.getElementById('search-postfix').value || '').trim().toLowerCase().replace(/^\*+/, '');
  const posInput = (document.getElementById('search-pos').value || '').trim().toLowerCase();

  const statusEl = document.getElementById('search-status');
  const gridEl = document.getElementById('search-results-grid');

  if (!pfxInput && !sfxInput && !posInput) {
    statusEl.textContent = '請輸入字首 (如 com*)、字尾 (如 *te) 或選擇詞性進行即時檢索...';
    gridEl.innerHTML = '';
    return;
  }

  const posMap = {
    'verb': ['v.', 'vi.', 'vt.', 'verb'],
    'noun': ['n.', 'noun'],
    'adj': ['adj.', 'a.', 'adjective'],
    'adv': ['adv.', 'r.', 'adverb']
  };

  const results = [];
  for (const [w, vd] of Object.entries(vocabData)) {
    if (pfxInput && !w.startsWith(pfxInput)) continue;
    if (sfxInput && !w.endsWith(sfxInput)) continue;
    if (pfxInput && sfxInput && w.length < pfxInput.length + sfxInput.length - 1) continue;

    if (posInput) {
      const allowed = posMap[posInput] || [posInput];
      const wordPos = (vd.pos || []).map(p => p.toLowerCase());
      const zhDefs = (vd.zh || []).join(' ').toLowerCase();
      const match = allowed.some(tag => wordPos.some(wp => wp.includes(tag)) || zhDefs.startsWith(tag) || zhDefs.includes(`[${tag}`));
      if (!match) continue;
    }

    results.push(vd);
  }

  // Sort by level ascending, then total appearances descending
  results.sort((a, b) => {
    if (a.lv !== b.lv) return a.lv - b.lv;
    if ((b.cnt || 0) !== (a.cnt || 0)) return (b.cnt || 0) - (a.cnt || 0);
    return a.w.localeCompare(b.w);
  });

  statusEl.innerHTML = `找到 <strong>${results.length}</strong> 個符合條件的單字 (依 Level 排序)：`;

  if (results.length === 0) {
    gridEl.innerHTML = '<div class="no-search-results">查無符合條件的單字，請嘗試放寬篩選條件。</div>';
    return;
  }

  const chips = results.slice(0, 100).map(vd => {
    const examBadge = vd.cnt > 0 ? `<span class="exam-badge" title="出題 ${vd.cnt} 次">📝${vd.cnt}</span>` : '';
    const zhDef = vd.zh && vd.zh.length ? vd.zh[0] : '';
    const cleanZh = zhDef.replace(/^[a-z]+\.\s*/, '').split(/[,;；]/)[0];
    const rootTag = vd.roots ? `<span class="search-root-tag" title="${vd.roots.synthesis_zh || ''}">🔤字根</span>` : '';
    
    return `
      <div class="search-result-card lv-${vd.lv}" onclick="showDefinition('${vd.w}', 'simple')">
        <div class="src-word-line">
          <span class="src-word">${vd.w}</span>
          <span class="src-level">L${vd.lv}</span>
          ${examBadge}
          ${rootTag}
        </div>
        <div class="src-meaning">${cleanZh}</div>
      </div>
    `;
  }).join('');

  gridEl.innerHTML = chips + (results.length > 100 ? `<div class="search-more-hint">... 僅顯示前 100 筆 (共 ${results.length} 筆)</div>` : '');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeDefinition();
    closeAffixSearchModal();
  }
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
