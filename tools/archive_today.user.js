// ==UserScript==
// @name         archive.today Extractor :: Lost and Found
// @namespace    https://github.com/UoEMainLibrary
// @description  Extract hosts and URLs from search results of archive.today
// @author       The University of Edinburgh
// @match        *://archive.ph/*
// @license      Apache 2.0

// ==/UserScript==

(() => {
  'use strict';

  const STORAGE_KEY = 'archivetoday_extractor_data';
  const RUN_KEY = 'archivetoday_extractor_running';

  let urls = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  let seen = new Set(urls);
  let mode = 'idle'; // idle | running | completed

  const save = () =>
    localStorage.setItem(STORAGE_KEY, JSON.stringify(urls));

  const el = (tag, props = {}, children = []) => {
    const node = document.createElement(tag);
    Object.assign(node, props);
    children.forEach(c => node.append(c));
    return node;
  };

  /* ------------------- CSS ------------------- */

  const style = document.createElement('style');
  style.textContent = `
#uc-root {
  --primary: #fff;
  --secondary: #000;
  --tertiary: #444;

  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 400px;
  height: 400px;
  background: var(--secondary);
  color: var(--primary);
  border: 1px solid var(--tertiary);
  font-family: Courier New, monospace;
  font-size: 12px;
  z-index: 999999;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

#uc-root * {
  box-sizing: border-box;
}

#uc-header {
  padding: 8px;
  border-bottom: 1px solid var(--tertiary);
  text-align: center;
  letter-spacing: 1px;
}

#uc-meta {
  padding: 8px;
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--tertiary);
}

#uc-actions {
  display: flex;
  gap: 8px;
  padding: 8px;
  border-bottom: 1px solid var(--tertiary);
}

.uc-btn {
  flex: 1;
  padding: 8px;
  font-size: 11px;
  border: 1px solid var(--tertiary);
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  font-family: Courier New, monospace;
}

.uc-btn:hover {
  border-color: var(--primary);
}

.uc-btn.running {
  background: var(--primary);
  color: var(--secondary);
}

.uc-btn:disabled {
  color: var(--tertiary);
  cursor: not-allowed;
}

#uc-list {
  flex: 1;
  overflow-y: auto;
  line-height: 1.4;
}

.uc-item {
  display: flex;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--tertiary);
}

.uc-index {
  width: 40px;
  text-align: right;
  opacity: 0.6;
  flex-shrink: 0;
}

.uc-value {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

#uc-root.running {
  cursor: progress;
}

#uc-root.running button {
  pointer-events: none;
  opacity: 0.6;
}

#uc-instructions {
  padding: 8px;
  line-height: 1.4;
}

#uc-instructions a {
  color: var(--primary);
  text-decoration: underline;
}
`;
  document.head.appendChild(style);

  /* ------------------- UI ------------------- */

  const root = el('div', { id: 'uc-root' });

  const countLabel = el('div');
  const stateLabel = el('div');

  const header = el('div', {
    id: 'uc-header',
    textContent: 'ARCHIVE.TODAY URL COLLECTOR'
  });

  const meta = el('div', { id: 'uc-meta' }, [countLabel, stateLabel]);

  const makeBtn = label => {
    const b = el('button', { textContent: label, className: 'uc-btn' });
    return b;
  };

  const startBtn = makeBtn('Start');
  const copyBtn = makeBtn('Copy');
  const exportBtn = makeBtn('Export');
  const resetBtn = makeBtn('Reset');

  const actions = el('div', { id: 'uc-actions' }, [
    startBtn,
    copyBtn,
    exportBtn,
    resetBtn
  ]);

  const list = el('div', { id: 'uc-list' });

  root.append(header, actions, list, meta);
  document.body.appendChild(root);

  /* ------------------- State ------------------- */

  function setMode(newMode) {
    mode = newMode;

    startBtn.textContent = mode === 'auto' ? 'Scraping...' : 'Start';
    startBtn.classList.toggle('running', mode === 'auto');
    root.classList.toggle('running', mode === 'auto');

    stateLabel.textContent =
      mode === 'idle' ? 'Idle' :
      mode === 'auto' ? 'Running' :
      'Completed';
  }

  function updateButtonStates() {
    const empty = urls.length === 0;
    const validSearch = location.pathname.startsWith('/*');

    startBtn.disabled = !validSearch || mode === 'auto';
    copyBtn.disabled = empty;
    resetBtn.disabled = empty;
    exportBtn.disabled = empty;
  }

  /* ------------------- Main ------------------- */

  function render() {
    countLabel.textContent = `Collected ${urls.length} URLs`;

    list.innerHTML = urls.length
      ? urls.map((u, i) => `
        <div class="uc-item" title="${u}">
          <div class="uc-index">${String(i + 1).padStart(4, ' ')}</div>
          <div class="uc-value">${u}</div>
        </div>
      `).join('')
      : `
        <div id="uc-instructions">
          <div>1. Open the archive.today 'wildcard' search page <a href="https://archive.ph/search/?q=*.">https://archive.ph/search/?q=*.</a></div>
          <div>2. Append your target domain after the existing *. in the search query (for example, *.ed.ac.uk) and click search</div>
          <div>3. Click 'Start' in the userscript interface and wait for it to process all available results pages.</div>
          <div>4. When complete, click 'Export' to download the results or 'Copy' to copy them to your clipboard.</div>
          <div>5. Click Reset to clear stored results before starting a new search</div>
        </div>
      `;
    updateButtonStates();
  }

  function extract() {
    document.querySelectorAll('.TEXT-BLOCK a[href]').forEach(a => {
      let url = a.href.trim();
      if (!url || seen.has(url)) return;

      url = url.replace(/^https?:\/\/archive\.ph\//, '');

      seen.add(url);
      urls.push(url);
    });

    save();
  }

  function nextPage() {
    const next = [...document.querySelectorAll('a')]
      .find(a => a.textContent.trim() === '→');

    if (!next) return false;
    next.click();
    return true;
  }

  function run() {
    extract();

    if (nextPage()) {
      localStorage.setItem(RUN_KEY, '1');
      setMode('auto');
    } else {
      localStorage.removeItem(RUN_KEY);
      setMode('finished');
    }

    render();
  }

  /* ------------------- CSV Export ------------------- */

  function exportCSV() {
    const csv =
      'url\n' +
      urls.map(u => `"${u.replace(/"/g, '""')}"`).join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);

    const a = el('a', { href: url, download: 'urls.csv' });
    document.body.appendChild(a);
    a.click();
    a.remove();

    URL.revokeObjectURL(url);
  }

  /* ------------------- Events ------------------- */

  startBtn.onclick = () => {
    localStorage.setItem(RUN_KEY, '1');
    setMode('auto');
    run();
  };

  copyBtn.onclick = async () => {
    await navigator.clipboard.writeText(urls.join('\n'));
    copyBtn.textContent = 'Copied';
    setTimeout(() => (copyBtn.textContent = 'Copy'), 900);
  };

  resetBtn.onclick = () => {
    if (!confirm('Reset all collected URLs?')) return;

    urls = [];
    seen = new Set();
    localStorage.removeItem(STORAGE_KEY);

    setMode('idle');
    render();
  };

  exportBtn.onclick = exportCSV;

  if (localStorage.getItem(RUN_KEY) === '1') {
    setMode('auto');
    setTimeout(run, 50);
  }

  render();
})();