// ==UserScript==
// @name         googleDork Extractor :: Lost and Found
// @namespace    https://github.com/UoEMainLibrary
// @description  Extract hosts from Google Search results using googleDorks ("dorking")
// @author       The University of Edinburgh, Heritage Collections
// @match        *://www.google.com/search*
// @license      Apache 2.0
// @downloadURL  https://raw.githubusercontent.com/UoEMainLibrary/lost-and-found/main/tools/googledork.user.js
// @updateURL    https://raw.githubusercontent.com/UoEMainLibrary/lost-and-found/main/tools/googledork.user.js
// ==/UserScript==

(() => {
  'use strict';

  const STORAGE_KEY = 'googledork_extractor_data';
  const RUN_KEY = 'googledork_extractor_running';

  const MIN_PAGE_DELAY = 1800;
  const MAX_PAGE_DELAY = 3500;

  // depth 0 = homepage (path is "/" or empty), depth 1 = one segment in
  // (e.g. /about) — still allowed. depth 2+ is a page buried in the site.
  const MAX_ROOT_DEPTH = 1;

  let items = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  let domainsSeen = new Set(items.map(i => i.domain));
  let mode = 'idle'; // idle | auto | finished | blocked

  const save = () =>
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));

  const el = (tag, props = {}, children = []) => {
    const node = document.createElement(tag);
    Object.assign(node, props);
    children.forEach(c => node.append(c));
    return node;
  };

  const randDelay = () =>
    MIN_PAGE_DELAY + Math.random() * (MAX_PAGE_DELAY - MIN_PAGE_DELAY);

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

#uc-query {
  padding: 8px;
  border-bottom: 1px solid var(--tertiary);
  opacity: 0.7;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

#uc-root-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px;
  border-bottom: 1px solid var(--tertiary);
  cursor: pointer;
}

#uc-root-toggle input {
  accent-color: var(--primary);
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
    textContent: 'GOOGLEDORK EXTRACTOR'
  });

  const queryLine = el('div', { id: 'uc-query' });
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

  const rootOnlyCheckbox = el('input', { type: 'checkbox', checked: true });
  const rootOnlyRow = el('label', { id: 'uc-root-toggle' }, [
    rootOnlyCheckbox,
    document.createTextNode('Top-level pages only (skip deep links)')
  ]);

  const list = el('div', { id: 'uc-list' });

  root.append(header, queryLine, rootOnlyRow, actions, list, meta);
  document.body.appendChild(root);

  /* ------------------- State ------------------- */

  function currentQuery() {
    const params = new URLSearchParams(location.search);
    return params.get('q') || '';
  }

  function setMode(newMode) {
    mode = newMode;

    startBtn.textContent = mode === 'auto' ? 'Scraping...' : 'Start';
    startBtn.classList.toggle('running', mode === 'auto');
    root.classList.toggle('running', mode === 'auto');

    stateLabel.textContent =
      mode === 'idle' ? 'Idle' :
      mode === 'auto' ? 'Running' :
      mode === 'blocked' ? 'Blocked — solve captcha, then Start again' :
      'Completed';
  }

  function updateButtonStates() {
    const empty = items.length === 0;
    startBtn.disabled = mode === 'auto';
    copyBtn.disabled = empty;
    resetBtn.disabled = empty;
    exportBtn.disabled = empty;
  }

  function render() {
    queryLine.textContent = `Query: ${currentQuery()}`;
    countLabel.textContent = `Collected ${items.length} domains`;

    list.innerHTML = items.length
      ? items.map((it, i) => `
        <div class="uc-item" title="${it.url}">
          <div class="uc-index">${String(i + 1).padStart(4, ' ')}</div>
          <div class="uc-value">${it.domain} — ${it.title || it.path}</div>
        </div>
      `).join('')
      : `
        <div id="uc-instructions">
          <div>1. Perform a Google search using one or more <a href="https://web.archive.org/web/20021208144443/http://johnny.ihackstuff.com/security/googleDorks.shtml" target="_blank">googleDorks ("dorking")</a> search operators. A collection of search operators can be found in this <a href="https://gist.github.com/sundowndev/283efaddbcf896ab405488330d1bbc06" target="_blank">googleDork (dorking) cheat sheet</a></div>
          <div>2. Click 'Start' in the userscript interface and wait for it to process all available results pages.</div>
          <div>3. When complete, click 'Export' to download the results or 'Copy' to copy them to your clipboard.</div>
          <div>4. Click Reset to clear stored results before starting a new search</div>
        </div>
      `;
    updateButtonStates();
  }

  /* ------------------- Main ------------------- */

  function looksBlocked() {
    return !!document.querySelector('form#captcha-form, iframe[src*="recaptcha"]')
      || /unusual traffic/i.test(document.body.innerText.slice(0, 2000));
  }

  function pathDepth(url) {
    try {
      const segments = new URL(url).pathname.split('/').filter(Boolean);
      return segments.length;
    } catch {
      return 99;
    }
  }

  function extract() {
    const rootOnly = rootOnlyCheckbox.checked;

    document.querySelectorAll('#search a:has(h3)').forEach(a => {
      let href = a.href;
      if (!href || !href.startsWith('http')) return;

      let parsed;
      try {
        parsed = new URL(href);
      } catch {
        return;
      }

      const domain = parsed.hostname.replace(/^www\./, '');

      if (rootOnly && pathDepth(href) > MAX_ROOT_DEPTH) return;

      if (domainsSeen.has(domain)) return;
      domainsSeen.add(domain);

      const h3 = a.querySelector('h3');
      const title = h3 ? h3.textContent.trim() : '';
      const path = parsed.pathname === '/' ? '(homepage)' : parsed.pathname;

      items.push({ domain, url: href, title, path, query: currentQuery() });
    });

    save();
  }

  function nextPage() {
    const next = document.querySelector('#pnnext, a[aria-label="Next page"]');
    if (!next) return false;
    next.click();
    return true;
  }

  function run() {
    if (looksBlocked()) {
      localStorage.removeItem(RUN_KEY);
      setMode('blocked');
      render();
      return;
    }

    extract();
    render();

    if (nextPage()) {
      localStorage.setItem(RUN_KEY, '1');
      setMode('auto');
    } else {
      localStorage.removeItem(RUN_KEY);
      setMode('finished');
    }
  }

  /* ------------------- CSV Export ------------------- */

  function exportCSV() {
    const csv =
      'domain,url,title,path,query\n' +
      items.map(it =>
        [it.domain, it.url, it.title, it.path, it.query]
          .map(v => `"${(v || '').replace(/"/g, '""')}"`)
          .join(',')
      ).join('\n');

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
    await navigator.clipboard.writeText(items.map(i => i.url).join('\n'));
    copyBtn.textContent = 'Copied';
    setTimeout(() => (copyBtn.textContent = 'Copy'), 900);
  };

  resetBtn.onclick = () => {
    if (!confirm('Reset all collected URLs?')) return;
    items = [];
    domainsSeen = new Set();
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(RUN_KEY);
    setMode('idle');
    render();
  };

  exportBtn.onclick = exportCSV;

  if (localStorage.getItem(RUN_KEY) === '1') {
    setMode('auto');
    setTimeout(run, randDelay());
  }

  render();
})();