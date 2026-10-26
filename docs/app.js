/**
 * English Vocabulary Graph — Interactive Topic Explorer
 *
 * Main application: loads graph.json, renders with Cytoscape.js,
 * handles node click interactions, and displays vocabulary groups.
 */

// ===== State =====
let cy = null;            // Cytoscape instance
let graphData = null;     // Raw graph JSON
let nodeMap = {};         // id -> node data
let domainChildren = {};  // domain_id -> [topic_node_ids]
let currentView = 'graph';
let savedZoom = null;
let savedPan = null;

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
      const source = nodeMap[edge.source];
      const target = nodeMap[edge.target];
      if (source && target && source.type === 'domain' && target.type === 'topic') {
        if (!domainChildren[edge.source]) domainChildren[edge.source] = [];
        domainChildren[edge.source].push(edge.target);
      }
    }
  }
}

// ===== Find parent domain for a topic node =====
function getParentDomain(nodeId) {
  for (const edge of graphData.graph.edges) {
    if (edge.type === 'contains' && edge.target === nodeId) {
      const sourceNode = nodeMap[edge.source];
      if (sourceNode && sourceNode.type === 'domain') return edge.source;
    }
  }
  return null;
}

// ===== Get domain color for a topic =====
function getTopicColor(nodeId) {
  const domainId = getParentDomain(nodeId);
  return DOMAIN_COLORS[domainId] || { main: '#64748b', bg: 'rgba(100,116,139,0.12)', border: 'rgba(100,116,139,0.4)' };
}

// ===== Render Graph =====
function renderGraph() {
  const SCALE = 3.2;
  const nodes = graphData.graph.nodes;
  const edges = graphData.graph.edges;

  const cyElements = [];

  // Build nodes
  for (const node of nodes) {
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
      position: {
        x: node.x * SCALE,
        y: node.y * SCALE
      }
    });
  }

  // Build edges
  for (const edge of edges) {
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

  // Create Cytoscape instance
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
          'text-wrap': 'wrap',
          'text-max-width': 80,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 3,
          'z-index': 10,
          'overlay-opacity': 0,
          'transition-property': 'border-color, width, height',
          'transition-duration': '0.2s'
        }
      },
      // Domain nodes
      {
        selector: 'node[nodeType="domain"]',
        style: {
          'width': 56,
          'height': 56,
          'background-color': '#111827',
          'border-width': 2.5,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 12,
          'font-weight': 700,
          'font-family': 'Inter, sans-serif',
          'color': 'data(color)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 8,
          'text-wrap': 'wrap',
          'text-max-width': 100,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2.5,
          'z-index': 8,
          'overlay-opacity': 0,
          'transition-property': 'border-color, width, height, border-width',
          'transition-duration': '0.2s'
        }
      },
      // Topic nodes
      {
        selector: 'node[nodeType="topic"]',
        style: {
          'width': 30,
          'height': 30,
          'background-color': 'data(color)',
          'background-opacity': 0.15,
          'border-width': 1.5,
          'border-color': 'data(color)',
          'label': 'data(label)',
          'font-size': 9,
          'font-weight': 500,
          'font-family': 'Inter, sans-serif',
          'color': '#cbd5e1',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'text-margin-y': 6,
          'text-wrap': 'wrap',
          'text-max-width': 85,
          'text-outline-color': '#0a0e1a',
          'text-outline-width': 2,
          'z-index': 5,
          'overlay-opacity': 0,
          'transition-property': 'background-opacity, width, height, border-width',
          'transition-duration': '0.2s'
        }
      },
      // Edges — contains (hierarchical)
      {
        selector: 'edge[edgeType="contains"]',
        style: {
          'width': 1.2,
          'line-color': 'rgba(148, 163, 184, 0.15)',
          'curve-style': 'straight',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 1
        }
      },
      // Edges — related (cross-domain)
      {
        selector: 'edge[edgeType="related"]',
        style: {
          'width': 0.8,
          'line-color': 'rgba(99, 102, 241, 0.08)',
          'line-style': 'dashed',
          'line-dash-pattern': [6, 4],
          'curve-style': 'unbundled-bezier',
          'target-arrow-shape': 'none',
          'overlay-opacity': 0,
          'z-index': 0
        }
      },
      // Hover states
      {
        selector: 'node[nodeType="topic"]:active',
        style: {
          'background-opacity': 0.35,
          'width': 36,
          'height': 36,
          'border-width': 2.5
        }
      },
      {
        selector: 'node[nodeType="domain"]:active',
        style: {
          'width': 64,
          'height': 64,
          'border-width': 3.5
        }
      },
      {
        selector: 'node[nodeType="root"]:active',
        style: {
          'width': 80,
          'height': 80,
          'border-color': '#c4b5fd'
        }
      },
      // Highlighted domain
      {
        selector: '.domain-highlight',
        style: {
          'width': 64,
          'height': 64,
          'border-width': 3.5,
          'z-index': 20
        }
      },
      // Highlighted topic children
      {
        selector: '.topic-highlight',
        style: {
          'background-opacity': 0.4,
          'width': 36,
          'height': 36,
          'border-width': 2.5,
          'z-index': 15,
          'font-size': 11,
          'font-weight': 700,
          'color': '#f1f5f9'
        }
      },
      // Dimmed nodes
      {
        selector: '.dimmed',
        style: {
          'opacity': 0.2
        }
      },
      // Highlighted edges
      {
        selector: '.edge-highlight',
        style: {
          'width': 2,
          'line-color': 'rgba(148, 163, 184, 0.35)',
          'z-index': 10
        }
      }
    ]
  });

  // Event listeners
  cy.on('tap', 'node[nodeType="topic"]', onTopicClick);
  cy.on('tap', 'node[nodeType="domain"]', onDomainClick);
  cy.on('tap', 'node[nodeType="root"]', onRootClick);
  cy.on('tap', function(e) {
    if (e.target === cy) {
      clearHighlights();
    }
  });

  // Mouseover effects
  cy.on('mouseover', 'node', function(e) {
    e.target.style('cursor', 'pointer');
  });
  cy.on('mouseout', 'node', function() {
    // cursor resets automatically
  });

  // Fit view
  cy.fit(undefined, 60);
}

// ===== Node Click Handlers =====

function onTopicClick(e) {
  const node = e.target;
  const groupId = node.data('groupId');
  if (groupId) {
    openGroup(groupId, node.data('label'), node.data('domainId'));
  }
}

let highlightedDomain = null;

function onDomainClick(e) {
  const node = e.target;
  const domainId = node.data('id');

  // Toggle highlight
  if (highlightedDomain === domainId) {
    clearHighlights();
    return;
  }

  clearHighlights();
  highlightedDomain = domainId;

  // Dim all nodes and edges
  cy.elements().addClass('dimmed');

  // Highlight domain node
  node.removeClass('dimmed').addClass('domain-highlight');

  // Highlight its children and edges
  const children = domainChildren[domainId] || [];
  for (const childId of children) {
    cy.getElementById(childId).removeClass('dimmed').addClass('topic-highlight');
    cy.getElementById(`${domainId}-${childId}`).removeClass('dimmed').addClass('edge-highlight');
  }

  // Keep root and life->domain edge visible
  cy.getElementById('life').removeClass('dimmed');
  cy.getElementById(`life-${domainId}`).removeClass('dimmed').addClass('edge-highlight');

  // Animate to fit the domain cluster
  const domainNode = cy.getElementById(domainId);
  const childNodes = children.map(id => cy.getElementById(id));
  const collection = cy.collection([domainNode, ...childNodes]);
  cy.animate({
    fit: { eles: collection, padding: 80 }
  }, { duration: 400, easing: 'ease-in-out-cubic' });
}

function onRootClick() {
  clearHighlights();
  cy.animate({
    fit: { eles: cy.elements(), padding: 60 }
  }, { duration: 400, easing: 'ease-in-out-cubic' });
}

function clearHighlights() {
  highlightedDomain = null;
  cy.elements().removeClass('dimmed domain-highlight topic-highlight edge-highlight');
}

// ===== View Switching =====

function showGroup() {
  // Save current graph position
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

  // Restore graph position
  if (cy && savedZoom !== null && savedPan !== null) {
    cy.viewport({ zoom: savedZoom, pan: savedPan });
  }
}

// ===== Open Group =====

async function openGroup(groupId, label, domainId) {
  showGroup();

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
    ${renderDifficultySection('easy', 'Easy', data.levels.easy || [], '🟢')}
    ${renderDifficultySection('medium', 'Medium', data.levels.medium || [], '🟡')}
    ${renderDifficultySection('hard', 'Hard', data.levels.hard || [], '🔴')}
  `;
}

function renderDifficultySection(level, label, words, emoji) {
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
  clearHighlights();
  cy.animate({ fit: { eles: cy.elements(), padding: 60 } }, { duration: 400, easing: 'ease-in-out-cubic' });
}

// ===== Init =====
initGraph();
