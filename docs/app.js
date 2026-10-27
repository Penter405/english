/**
 * Exam Vocabulary Graph — Interactive Multi-Level Explorer
 *
 * Features:
 *   - Infinite drill-down: root → domain → category → level_group → words
 *   - Breadcrumb navigation with parent-relative-position indicator
 *   - Left click / tap → English definition popup
 *   - Right click / double-tap → Chinese definition popup
 *   - Word images support
 */

// ===== State =====
let cy = null;
let graphData = null;
let vocabData = null;
let nodeMap = {};        // id → node data
let childrenMap = {};    // id → [child ids]
let parentMap = {};      // id → parent id

// Navigation stack: [{nodeId, label}]
let navStack = []; // e.g. [{id:'life', label:'Vocabulary'}, {id:'daily_life', label:'Daily Life'}, ...]
let currentView = 'graph'; // 'graph' | 'words'

// Layout constants
const CHILD_RADIUS = 220;
const PARENT_LINK_DIST = 450;

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
    if (!graphRes.ok) throw new Error(`Graph: HTTP ${graphRes.status}`);
    if (!vocabRes.ok) throw new Error(`Vocab: HTTP ${vocabRes.status}`);

    graphData = await graphRes.json();
    vocabData = await vocabRes.json();

    buildMaps();
    renderGraph();
    loadingEl.style.display = 'none';
  } catch (err) {
    console.error('Failed to load:', err);
    loadingEl.style.display = 'none';
    errorEl.style.display = 'flex';
    document.getElementById('error-text').textContent = `Failed to load: ${err.message}`;
  }
}

function buildMaps() {
  nodeMap = {};
  childrenMap = {};
  parentMap = {};

  for (const node of graphData.graph.nodes) {
    nodeMap[node.id] = node;
  }

  for (const edge of graphData.graph.edges) {
    if (edge.type === 'contains') {
      if (!childrenMap[edge.source]) childrenMap[edge.source] = [];
      childrenMap[edge.source].push(edge.target);
      parentMap[edge.target] = edge.source;
    }
  }
}

// Get the domain ancestor of a node (for coloring)
function getDomainAncestor(nodeId) {
  let current = nodeId;
  while (current) {
    const node = nodeMap[current];
    if (node && node.type === 'domain') return current;
    current = parentMap[current];
  }
  return null;
}

// Get color for a node
function getNodeColor(node) {
  if (node.color) return node.color;
  const domainId = getDomainAncestor(node.id);
  if (domainId && nodeMap[domainId]) return nodeMap[domainId].color || '#64748b';
  return '#64748b';
}

// ===== Render Graph (one-time setup) =====
function renderGraph() {
  const cyElements = [];

  for (const node of graphData.graph.nodes) {
    const color = getNodeColor(node);
    cyElements.push({
      group: 'nodes',
      data: {
        id: node.id,
        label: node.label + (node.word_count ? ` (${node.word_count})` : ''),
        rawLabel: node.label,
        nodeType: node.type,
        color: color,
        wordCount: node.word_count || 0,
        hasWords: !!node.words,
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
      // Root node
      {
        selector: 'node[nodeType="root"]',
        style: {
          'width': 75,
          'height': 75,
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
      // Root as breadcrumb
      {
        selector: 'node[nodeType="root"].breadcrumb',
        style: {
          'width': 40,
          'height': 40,
          'border-width': 2,
          'font-size': 10,
          'opacity': 0.6
        }
      },
      // Domain nodes
      {
        selector: 'node[nodeType="domain"]',
        style: {
          'width': 58,
          'height': 58,
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
          'text-max-width': 120,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2.5,
          'z-index': 8,
          'overlay-opacity': 0,
          'transition-property': 'width, height, border-width',
          'transition-duration': '0.3s'
        }
      },
      // Category nodes
      {
        selector: 'node[nodeType="category"]',
        style: {
          'width': 42,
          'height': 42,
          'background-color': 'data(color)',
          'background-opacity': 0.15,
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
          'text-max-width': 100,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2,
          'z-index': 5,
          'overlay-opacity': 0,
          'transition-property': 'background-opacity, width, height',
          'transition-duration': '0.2s'
        }
      },
      // Level group nodes
      {
        selector: 'node[nodeType="level_group"]',
        style: {
          'width': 36,
          'height': 36,
          'background-color': 'data(color)',
          'background-opacity': 0.12,
          'border-width': 1.8,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 10,
          'font-weight': 600,
          'font-family': 'Inter, sans-serif',
          'color': '#cbd5e1',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 7,
          'text-wrap': 'wrap',
          'text-max-width': 90,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2,
          'z-index': 4,
          'overlay-opacity': 0,
        }
      },
      // Focused node (currently drilled-into)
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
      // Breadcrumb parent (non-root)
      {
        selector: 'node.breadcrumb',
        style: {
          'width': 36,
          'height': 36,
          'border-width': 1.5,
          'font-size': 9,
          'opacity': 0.5,
        }
      },
      // Contains edges
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
      // Breadcrumb edge
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
      // Hover
      {
        selector: 'node:active',
        style: { 'overlay-opacity': 0.08 }
      }
    ]
  });

  // Event listeners
  cy.on('tap', 'node', onNodeClick);

  // Right-click for Chinese definition
  cy.on('cxttap', 'node', onNodeRightClick);

  // Cursor
  cy.on('mouseover', 'node', () => { document.getElementById('cy').style.cursor = 'pointer'; });
  cy.on('mouseout', 'node', () => { document.getElementById('cy').style.cursor = 'default'; });

  // Prevent context menu on graph
  document.getElementById('cy').addEventListener('contextmenu', e => e.preventDefault());

  // Start at root
  navStack = [{ id: 'life', label: 'Vocabulary' }];
  enterNodeView('life', false);
}

// ===== Core Navigation: Enter a node's view =====
function enterNodeView(nodeId, animate) {
  const node = nodeMap[nodeId];
  if (!node) return;

  // If this node has words (leaf), show word list
  if (node.words && node.words.length > 0 && !childrenMap[nodeId]) {
    showWordList(node);
    return;
  }

  // Show graph view
  if (currentView !== 'graph') {
    showGraphView();
  }

  const children = childrenMap[nodeId] || [];
  if (children.length === 0 && node.words) {
    showWordList(node);
    return;
  }

  const positions = {};

  // Position the focused node at center
  positions[nodeId] = { x: 0, y: 0 };

  // Position children around center
  const childAngleStep = 360 / Math.max(children.length, 1);
  for (let i = 0; i < children.length; i++) {
    const childNode = nodeMap[children[i]];
    const angleDeg = childNode && childNode.angle_degrees != null
      ? childNode.angle_degrees
      : i * childAngleStep;
    const angleRad = angleDeg * Math.PI / 180;
    positions[children[i]] = {
      x: Math.cos(angleRad) * CHILD_RADIUS,
      y: Math.sin(angleRad) * CHILD_RADIUS
    };
  }

  // Position parent as breadcrumb (opposite direction)
  const parentId = parentMap[nodeId];
  if (parentId) {
    // Use the node's position relative to parent to determine direction
    const focusedNode = nodeMap[nodeId];
    let dx = focusedNode.x || 0;
    let dy = focusedNode.y || 0;
    if (dx === 0 && dy === 0) {
      // Use angle_degrees if available
      const ang = (focusedNode.angle_degrees || 0) * Math.PI / 180;
      dx = Math.cos(ang);
      dy = Math.sin(ang);
    }
    const dist = Math.sqrt(dx * dx + dy * dy) || 1;
    positions[parentId] = {
      x: (-dx / dist) * PARENT_LINK_DIST,
      y: (-dy / dist) * PARENT_LINK_DIST
    };
  }

  // Show/hide elements
  cy.batch(() => {
    cy.nodes().style('display', 'none');
    cy.edges().style('display', 'none');
    cy.elements().removeClass('breadcrumb breadcrumb-edge focused');

    // Show focused node
    const focusedEle = cy.getElementById(nodeId);
    focusedEle.style('display', 'element');
    if (nodeId !== 'life') focusedEle.addClass('focused');

    // Show parent as breadcrumb
    if (parentId) {
      const parentEle = cy.getElementById(parentId);
      parentEle.style('display', 'element');
      parentEle.addClass('breadcrumb');

      const edgeId = `${parentId}-${nodeId}`;
      const edge = cy.getElementById(edgeId);
      if (edge.length) {
        edge.style('display', 'element');
        edge.addClass('breadcrumb-edge');
      }
    }

    // Show children + edges
    for (const childId of children) {
      cy.getElementById(childId).style('display', 'element');
      const edgeId = `${nodeId}-${childId}`;
      const edge = cy.getElementById(edgeId);
      if (edge.length) edge.style('display', 'element');
    }
  });

  // Apply positions
  for (const [id, pos] of Object.entries(positions)) {
    const ele = cy.getElementById(id);
    if (!ele.length) continue;
    if (animate) {
      ele.animate({ position: pos }, { duration: 400, easing: 'ease-in-out-cubic' });
    } else {
      ele.position(pos);
    }
  }

  // Fit
  const visible = cy.elements(':visible');
  if (animate) {
    setTimeout(() => {
      cy.animate({ fit: { eles: visible, padding: 60 } }, { duration: 350, easing: 'ease-in-out-cubic' });
    }, 420);
  } else {
    cy.fit(visible, 60);
  }

  updateBreadcrumb();
}

// ===== Node Click Handlers =====
function onNodeClick(e) {
  const node = e.target;
  const nodeId = node.data('id');
  const nodeData = nodeMap[nodeId];

  if (!nodeData) return;

  // If clicking the breadcrumb parent, go up
  if (node.hasClass('breadcrumb')) {
    goUp();
    return;
  }

  // If this is the focused node, do nothing
  if (node.hasClass('focused') && nodeId !== 'life') return;

  // If node has children, drill down
  const children = childrenMap[nodeId];
  if (children && children.length > 0) {
    navStack.push({ id: nodeId, label: nodeData.label });
    enterNodeView(nodeId, true);
    return;
  }

  // If node has words (leaf), show word list
  if (nodeData.words && nodeData.words.length > 0) {
    navStack.push({ id: nodeId, label: nodeData.label });
    showWordList(nodeData);
    return;
  }
}

function onNodeRightClick(e) {
  // Right-click on a word-bearing leaf → show Chinese defs
  // But on graph nodes, this doesn't make much sense
  // We'll handle right-click on word chips in the word list view
  e.originalEvent.preventDefault();
}

// ===== Word List View =====
function showWordList(nodeData) {
  currentView = 'words';
  document.getElementById('graph-view').classList.remove('active');
  document.getElementById('word-view').classList.add('active');
  document.getElementById('graph-controls').style.display = 'none';

  const container = document.getElementById('word-list-container');
  const color = getNodeColor(nodeData);
  const words = nodeData.words || [];

  // Group by level
  const byLevel = { 1: [], 2: [], 3: [], 4: [], 5: [], 6: [] };
  for (const w of words) {
    const vd = vocabData[w];
    const lv = vd ? vd.lv : 0;
    if (byLevel[lv]) byLevel[lv].push(w);
    else if (byLevel[1]) byLevel[1].push(w);
  }

  // Get domain label
  let domainLabel = '';
  let domainColor = color;
  const domainId = getDomainAncestor(nodeData.id);
  if (domainId && nodeMap[domainId]) {
    domainLabel = nodeMap[domainId].label;
    domainColor = nodeMap[domainId].color || color;
  }

  let html = `
    <div class="group-header">
      ${domainLabel ? `<div class="group-domain-badge" style="color: ${domainColor}; background: ${domainColor}20; border-color: ${domainColor}60;">
        <span>●</span> ${domainLabel}
      </div>` : ''}
      <h1 class="group-name">${nodeData.label}</h1>
      <p class="group-word-count">${words.length} words</p>
    </div>
  `;

  // Level sections
  const levelLabels = {
    1: { name: 'Level 1 — Basic', cls: 'lv1' },
    2: { name: 'Level 2 — Elementary', cls: 'lv2' },
    3: { name: 'Level 3 — Intermediate', cls: 'lv3' },
    4: { name: 'Level 4 — Upper-Intermediate', cls: 'lv4' },
    5: { name: 'Level 5 — Advanced', cls: 'lv5' },
    6: { name: 'Level 6 — Expert', cls: 'lv6' },
  };

  for (const [lv, lvWords] of Object.entries(byLevel)) {
    if (lvWords.length === 0) continue;
    const info = levelLabels[lv] || { name: `Level ${lv}`, cls: 'lv1' };
    const chips = lvWords.map(w => {
      const vd = vocabData[w];
      const examBadge = vd && vd.cnt > 0 ? `<span class="exam-badge" title="Appeared in ${vd.cnt} exam(s)">📝</span>` : '';
      return `<span class="word-chip ${info.cls}" 
        onclick="showDefinition('${w}', 'en')" 
        oncontextmenu="event.preventDefault(); showDefinition('${w}', 'zh')"
        ondblclick="showDefinition('${w}', 'zh')"
        title="Click: English | Right-click/Double-click: Chinese"
      >${w}${examBadge}</span>`;
    }).join('');

    html += `
      <div class="difficulty-section ${info.cls}">
        <div class="difficulty-header">
          <span class="difficulty-dot"></span>
          <span class="difficulty-label">${info.name}</span>
          <span class="difficulty-count">${lvWords.length} words</span>
        </div>
        <div class="word-grid">${chips}</div>
      </div>
    `;
  }

  container.innerHTML = html;
  updateBreadcrumb();
}

function showGraphView() {
  currentView = 'graph';
  document.getElementById('word-view').classList.remove('active');
  document.getElementById('graph-view').classList.add('active');
  document.getElementById('graph-controls').style.display = 'flex';
}

// ===== Definition Popup =====
function showDefinition(word, lang) {
  const vd = vocabData[word];
  if (!vd) return;

  const popup = document.getElementById('def-popup');
  const overlay = document.getElementById('def-overlay');

  // Word title
  document.getElementById('def-word').textContent = vd.w;

  // Meta info
  const posStr = vd.pos.join(', ') || '';
  const lvStr = `Level ${vd.lv}`;
  const examStr = vd.cnt > 0 ? `📝 Appeared in exams: ${vd.exam.join(', ')}` : '';
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

  // Image
  const imgContainer = document.getElementById('def-image-container');
  const imgEl = document.getElementById('def-image');
  const imgPath = `./data/images/${word}.png`;
  imgEl.src = imgPath;
  imgEl.onload = () => { imgContainer.style.display = 'block'; };
  imgEl.onerror = () => { imgContainer.style.display = 'none'; };

  // Definitions
  let contentHtml = '';
  if (lang === 'en') {
    const defs = vd.en || [];
    if (defs.length > 0) {
      contentHtml = '<div class="def-section"><h3>English Definitions</h3><ul>' +
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

  // Add toggle button
  const otherLang = lang === 'en' ? 'zh' : 'en';
  const otherLabel = lang === 'en' ? '切換中文' : 'Switch to English';
  contentHtml += `<button class="def-toggle" onclick="showDefinition('${word}', '${otherLang}')">${otherLabel}</button>`;

  document.getElementById('def-content').innerHTML = contentHtml;

  // Show
  overlay.classList.add('visible');
  popup.classList.add('visible');
}

function closeDefinition() {
  document.getElementById('def-overlay').classList.remove('visible');
  document.getElementById('def-popup').classList.remove('visible');
}

// Close on Escape
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeDefinition();
});

// ===== Breadcrumb =====
function updateBreadcrumb() {
  const bar = document.getElementById('breadcrumb-bar');
  let html = '';

  for (let i = 0; i < navStack.length; i++) {
    const item = navStack[i];
    if (i > 0) html += '<span class="breadcrumb-sep">›</span>';
    if (i === navStack.length - 1) {
      html += `<span class="breadcrumb-item current">${item.label}</span>`;
    } else {
      html += `<button class="breadcrumb-item" onclick="goToLevel(${i})">${item.label}</button>`;
    }
  }

  bar.innerHTML = html;
}

function goToRoot() {
  navStack = [{ id: 'life', label: 'Vocabulary' }];
  if (currentView !== 'graph') showGraphView();
  enterNodeView('life', true);
}

function goToLevel(level) {
  if (level < 0 || level >= navStack.length) return;
  navStack = navStack.slice(0, level + 1);
  if (currentView !== 'graph') showGraphView();
  enterNodeView(navStack[navStack.length - 1].id, true);
}

function goUp() {
  if (navStack.length <= 1) return;
  navStack.pop();
  if (currentView !== 'graph') showGraphView();
  enterNodeView(navStack[navStack.length - 1].id, true);
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
  if (navStack.length > 1) {
    goToRoot();
  } else {
    cy.animate({ fit: { eles: cy.elements(':visible'), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
  }
}

// ===== Init =====
initGraph();
