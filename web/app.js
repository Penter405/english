/**
 * Root Word Explorer — Frontend Application
 * 
 * Handles search, API calls, and interactive result rendering.
 */

// API base URL configuration:
// - When frontend is on Vercel (same domain as API): leave as ''
// - When frontend is on GitHub Pages: set to your Vercel deployment URL
//   e.g. 'https://your-project.vercel.app'
const API_BASE = window.location.hostname === 'localhost'
  ? ''  // Local dev
  : (window.location.hostname.includes('github.io')
    ? 'https://english-api.vercel.app'  // TODO: replace with your Vercel URL
    : '');  // Same-origin (Vercel)

// ===== Search =====

function quickSearch(word) {
  document.getElementById('search-input').value = word;
  analyzeWord();
}

// Enter key handler
document.getElementById('search-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') analyzeWord();
});

async function analyzeWord() {
  const input = document.getElementById('search-input');
  const word = input.value.trim();
  if (!word) return;

  const container = document.getElementById('results-container');
  container.innerHTML = `
    <div class="loading">
      <div class="loading-spinner"></div>
      <span class="loading-text">Analyzing "${word}"...</span>
    </div>
  `;

  try {
    const res = await fetch(`${API_BASE}/api/analyze?word=${encodeURIComponent(word)}`);
    const data = await res.json();
    renderResults(data);
  } catch (err) {
    container.innerHTML = `
      <div class="error-message">
        <span class="emoji">⚠️</span>
        <p>Could not connect to the server. Make sure the API is running.</p>
      </div>
    `;
  }
}

// ===== Render Results =====

function renderResults(data) {
  const container = document.getElementById('results-container');

  if (!data.found) {
    container.innerHTML = `
      <div class="error-message">
        <span class="emoji">🤔</span>
        <p>${data.message || `No root word decomposition found for "${data.word}". Try another word!`}</p>
      </div>
    `;
    return;
  }

  let html = '';

  // Simple word info banner
  if (data.is_simple_word) {
    html += `
      <div class="simple-word-info">
        <p>💡 <strong>"${data.word}"</strong> is a simple root word. It evolved into the following roots through sound changes:</p>
      </div>
    `;
  }

  // Word breakdown
  if (data.components && data.components.length > 0) {
    html += renderWordBreakdown(data);
  }

  // Origin trace
  if (data.origin_trace && data.origin_trace.length > 0) {
    html += renderOriginTrace(data);
  }

  // Word families
  if (data.word_family && Object.keys(data.word_family).length > 0) {
    html += renderWordFamily(data);
  }

  container.innerHTML = html;
}

function renderWordBreakdown(data) {
  const segments = data.components.map((comp, i) => {
    const plus = i > 0 ? '<span class="segment-plus">+</span>' : '';
    return `${plus}<span class="word-segment ${comp.type}" title="${comp.meaning}">${comp.text}</span>`;
  }).join('');

  const meanings = data.components.map(comp => {
    const zhText = comp.meaning_zh ? ` (${comp.meaning_zh})` : '';
    return `<span class="meaning-chip ${comp.type}">${comp.text} = ${comp.meaning}${zhText}</span>`;
  }).join('');

  return `
    <div class="word-breakdown">
      <div class="word-breakdown-title">Word Decomposition</div>
      <div class="word-segments">${segments}</div>
      <div class="word-meaning-row">${meanings}</div>
      <div class="legend">
        <span class="legend-item"><span class="legend-dot prefix"></span> Prefix</span>
        <span class="legend-item"><span class="legend-dot root"></span> Root</span>
        <span class="legend-item"><span class="legend-dot suffix"></span> Suffix</span>
        <span class="legend-item"><span class="legend-dot origin"></span> Simple Word</span>
      </div>
    </div>
  `;
}

function renderOriginTrace(data) {
  const cards = data.origin_trace.map((trace, i) => `
    <div class="trace-card stagger-${i + 1}">
      <div class="trace-card-header">
        <div class="trace-arrow">
          <span class="trace-origin">${trace.origin_word}</span>
          <span class="trace-arrow-icon">→</span>
          <span class="trace-root">${trace.root}</span>
        </div>
        <span class="trace-rule-badge">Rule ${trace.rule}: ${trace.rule_name}</span>
      </div>
      <div class="trace-explanation">${trace.explanation}</div>
    </div>
  `).join('');

  const title = data.is_simple_word
    ? '🔗 Roots Evolved From This Word'
    : '🔍 Root Origins — Where Each Root Came From';

  return `
    <div class="origin-trace">
      <div class="section-title">
        ${title}
      </div>
      <div class="trace-cards">${cards}</div>
    </div>
  `;
}

function renderWordFamily(data) {
  const groups = Object.entries(data.word_family).map(([rootKey, family], i) => {
    const words = family.derived_words.map(w =>
      `<span class="family-word" onclick="quickSearch('${w}')">${w}</span>`
    ).join('');

    return `
      <div class="family-group stagger-${i + 1}">
        <div class="family-root-label">
          📚 Words from root <span class="root-text">${rootKey}</span> (${family.meaning})
        </div>
        <div class="family-words">${words}</div>
      </div>
    `;
  }).join('');

  return `
    <div class="word-family">
      <div class="section-title">
        <span class="icon">🌳</span>
        Word Family — All Dictionary Words Sharing These Roots
      </div>
      ${groups}
    </div>
  `;
}

// ===== Rules Panel =====

async function loadRules() {
  try {
    const res = await fetch(`${API_BASE}/api/rules`);
    const data = await res.json();
    renderRules(data.rules);
  } catch (err) {
    // Silently fail — rules panel is not critical
    console.log('Could not load rules:', err);
  }
}

function renderRules(rules) {
  const grid = document.getElementById('rules-grid');
  
  grid.innerHTML = rules.map(rule => {
    const groupStr = rule.group.join(' ↔ ');
    const examples = rule.examples.map(ex =>
      `<span class="rule-example">${ex}</span>`
    ).join('');

    return `
      <div class="rule-card">
        <div class="rule-number">${rule.id}</div>
        <div class="rule-name">${rule.name}</div>
        <div class="rule-name-zh">${rule.name_zh}</div>
        <div class="rule-group">${groupStr}</div>
        <div class="rule-description">${rule.description}</div>
        <div class="rule-examples">${examples}</div>
      </div>
    `;
  }).join('');
}

// ===== Init =====
loadRules();
