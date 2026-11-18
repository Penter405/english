/* ============================================================
 * 下一個單字預測 (Next-Word Prediction)
 * 資料: data/next_word.json  (scripts/build_next_word_model.py 產生)
 *   ctx["<s>"]       句首 → [[word, prob], ...]
 *   ctx["<s> i"]     句首 + i
 *   ctx["i like"]    前 2 個字
 *   ctx["like"]      前 1 個字 (退回用)
 * 查詢順序: 前 2 字 → 前 1 字 → 句首
 * ============================================================ */
(function () {
  let model = null;
  let loading = null;
  const NAME = '<name>';

  function loadModel() {
    if (model) return Promise.resolve(model);
    if (!loading) {
      loading = fetch('./data/next_word.json')
        .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(d => (model = d));
    }
    return loading;
  }

  // 把輸入句子切成 token；句中大寫開頭的字 (不是 I / I'm) 視為專有名詞
  function tokenize(text) {
    const raw = text.replace(/’/g, "'").match(/[A-Za-z]+(?:'[A-Za-z]+)?/g) || [];
    return raw.map((t, i) => {
      const low = t.toLowerCase();
      if (i > 0 && /^[A-Z][a-z]/.test(t) && low !== 'i' && !low.startsWith("i'")) return NAME;
      return low;
    });
  }

  // 只看「最後一個句子」(遇到 . ? ! 就重新開始)
  function currentSentence(text) {
    const parts = text.split(/[.?!]+/);
    return parts[parts.length - 1];
  }

  function predict(text) {
    const toks = tokenize(currentSentence(text));
    const p1 = toks.length >= 1 ? toks[toks.length - 1] : '<s>';
    const p2 = toks.length >= 2 ? toks[toks.length - 2] : '<s>';
    const tries = [];
    if (toks.length >= 1) tries.push({ key: `${p2} ${p1}`, label: toks.length >= 2 ? `前 2 個字「${p2} ${p1}」` : `句首 +「${p1}」` });
    if (toks.length >= 1) tries.push({ key: p1, label: `前 1 個字「${p1}」` });
    tries.push({ key: '<s>', label: '句首 (還沒輸入任何字)' });
    for (let i = 0; i < tries.length; i++) {
      const t = tries[i];
      const list = model.ctx[t.key];
      if (list && list.length) {
        return { list, label: t.label, backoff: i > 0 && toks.length > 0, end: model.end[t.key] || 0 };
      }
    }
    return { list: [], label: '', backoff: false, end: 0 };
  }

  function display(w) {
    if (w === NAME) return '人名 / 地名';
    if (w === 'i') return 'I';
    if (w.startsWith("i'")) return 'I' + w.slice(1);
    return w;
  }

  function render() {
    const input = document.getElementById('predict-input');
    const box = document.getElementById('predict-results');
    const info = document.getElementById('predict-context');
    if (!model) return;
    const { list, label, backoff, end } = predict(input.value);
    info.innerHTML = label
      ? `依據：<strong>${label}</strong>${backoff ? '　<span class="predict-backoff">(前 2 字的例句太少，改看前 1 字)</span>' : ''}`
      : '找不到這個情境的資料';
    const max = list.length ? list[0][1] : 1;
    box.innerHTML = list.map(([w, p]) => {
      const lv = model.level[w];
      const pct = (p * 100).toFixed(p >= 0.1 ? 0 : 1);
      return `
        <button class="predict-row" data-word="${w}">
          <span class="predict-word">${display(w)}</span>
          ${lv ? `<span class="predict-lv lv${lv}">Lv${lv}</span>` : '<span class="predict-lv none"></span>'}
          <span class="predict-bar"><span style="width:${Math.max(4, (p / max) * 100)}%"></span></span>
          <span class="predict-pct">${pct}%</span>
        </button>`;
    }).join('') + (end >= 0.02
      ? `<div class="predict-end">句子在這裡結束的機率：${(end * 100).toFixed(0)}%</div>` : '');
    box.querySelectorAll('.predict-row').forEach(btn => {
      btn.addEventListener('click', () => {
        const w = btn.dataset.word;
        let add = w === NAME ? 'Tom' : display(w);
        const v = input.value;
        const atStart = !tokenize(currentSentence(v)).length;
        if (atStart && add.length) add = add[0].toUpperCase() + add.slice(1);
        input.value = v + (v && !/\s$/.test(v) ? ' ' : '') + add + ' ';
        input.focus();
        render();
      });
      btn.addEventListener('contextmenu', ev => {   // 右鍵 → 開單字解釋
        const w = btn.dataset.word;
        if (w !== NAME && typeof showDefinition === 'function' && typeof vocabData !== 'undefined'
            && vocabData && vocabData[w]) {
          ev.preventDefault();
          showDefinition(w);
        }
      });
    });
  }

  window.openPredictModal = function () {
    document.getElementById('predict-overlay').classList.add('visible');
    document.getElementById('predict-modal').classList.add('visible');
    const info = document.getElementById('predict-context');
    info.textContent = '載入預測模型中…';
    loadModel().then(() => {
      render();
      document.getElementById('predict-input').focus();
    }).catch(() => { info.textContent = '無法載入 data/next_word.json'; });
  };

  window.closePredictModal = function () {
    document.getElementById('predict-overlay').classList.remove('visible');
    document.getElementById('predict-modal').classList.remove('visible');
  };

  window.clearPredictInput = function () {
    const input = document.getElementById('predict-input');
    input.value = '';
    input.focus();
    render();
  };

  document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('predict-input');
    if (input) input.addEventListener('input', render);
  });
})();
