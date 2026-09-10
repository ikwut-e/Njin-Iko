const PER_PAGE = 50;

let allWords = [];
let visibleWords = [];
let currentPage = 1;

const listEl = document.getElementById('entry-list');
const paginationEl = document.getElementById('pagination');
const searchInput = document.getElementById('search-input');
const resultCountEl = document.getElementById('result-count');

function normalize(s) {
  if (!s) return '';
  return s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function collectSearchText(word) {
  const parts = [word.ipa];
  for (const sense of word.senses) {
    for (const sd of sense.subdefinitions) {
      parts.push(sd.ipa, sd.pos, sd.eng, sd.cf, sd.var, sd.other, sd.notes);
      for (const ex of sd.examples || []) parts.push(ex.ipa, ex.eng);
      for (const d of [...(sd.derived || []), ...(sd.related || [])]) {
        parts.push(d.ipa, d.pos, d.eng, d.cf, d.var, d.other);
        for (const ex of d.examples || []) parts.push(ex.ipa, ex.eng);
      }
    }
  }
  return normalize(parts.filter(Boolean).join(' '));
}

function escapeHtml(s) {
  if (s === undefined || s === null) return '';
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function renderExample(ex) {
  const eng = ex.eng ? escapeHtml(ex.eng) : '';
  return `
    <div class="example">
      <div class="ex-ipa">${escapeHtml(ex.ipa)}</div>
      <div class="ex-gloss">${eng}</div>
    </div>`;
}

function renderChild(d, label) {
  const pos = d.pos ? `<span class="pos">${escapeHtml(d.pos)}</span>` : '';
  const eng = d.eng ? escapeHtml(d.eng) : '';
  const examples = (d.examples || []).map(renderExample).join('');
  return `
    <div class="child-entry">
      <span class="child-label">${label}</span>
      <span class="child-ipa">${escapeHtml(d.ipa)}</span> ${pos}${eng}
      ${examples ? `<div class="examples">${examples}</div>` : ''}
    </div>`;
}

function renderSubdef(subdef, letter) {
  const letterHtml = letter ? `<span class="subdef-letter">${letter}.</span>` : '';
  const pos = subdef.pos ? `<span class="pos">${escapeHtml(subdef.pos)}</span>` : '';
  const eng = subdef.eng ? escapeHtml(subdef.eng) : '';
  const cfVarOther = [
    subdef.cf ? `cf. ${escapeHtml(subdef.cf)}` : '',
    subdef.var ? `var. ${escapeHtml(subdef.var)}` : '',
    subdef.other ? escapeHtml(subdef.other) : '',
  ].filter(Boolean).join(' · ');
  const examples = (subdef.examples || []).map(renderExample).join('');
  const derived = (subdef.derived || []).map(d => renderChild(d, 'Derived')).join('');
  const related = (subdef.related || []).map(d => renderChild(d, 'Related')).join('');

  return `
    <div class="subdef">
      ${letterHtml}${pos}${eng}
      ${cfVarOther ? `<div class="cf-var-other">${cfVarOther}</div>` : ''}
    </div>
    ${examples ? `<div class="examples">${examples}</div>` : ''}
    ${derived ? `<div class="derived">${derived}</div>` : ''}
    ${related ? `<div class="related">${related}</div>` : ''}
  `;
}

function renderSense(sense, num) {
  const numHtml = num ? `<span class="sense-num">${num}.</span>` : '';
  const multi = sense.subdefinitions.length > 1;
  const subdefs = sense.subdefinitions
    .map((sd, i) => renderSubdef(sd, multi ? String.fromCharCode(97 + i) : null))
    .join('');
  return `
    <div class="sense">
      ${numHtml}${subdefs}
    </div>`;
}

function renderWord(word) {
  const multi = word.senses.length > 1;
  const senses = word.senses
    .map((s, i) => renderSense(s, multi ? String(i + 1) : null))
    .join('');
  return `
    <article class="entry">
      <div class="headword">${escapeHtml(word.ipa)}</div>
      ${senses}
    </article>`;
}

function renderPage() {
  const start = (currentPage - 1) * PER_PAGE;
  const pageItems = visibleWords.slice(start, start + PER_PAGE);

  if (pageItems.length === 0) {
    listEl.innerHTML = `<div class="empty-state">No matching entries.</div>`;
  } else {
    listEl.innerHTML = pageItems.map(renderWord).join('');
  }

  renderPagination();
  window.scrollTo({ top: 0, behavior: 'instant' });
}

function renderPagination() {
  const totalPages = Math.max(1, Math.ceil(visibleWords.length / PER_PAGE));
  if (totalPages <= 1) {
    paginationEl.innerHTML = '';
    return;
  }
  paginationEl.innerHTML = `
    <button id="prev-btn" ${currentPage === 1 ? 'disabled' : ''}>&larr; Prev</button>
    <span class="page-jump">
      Page <input type="number" id="page-input" min="1" max="${totalPages}" value="${currentPage}">
      of ${totalPages}
    </span>
    <button id="next-btn" ${currentPage === totalPages ? 'disabled' : ''}>Next &rarr;</button>
  `;
  document.getElementById('prev-btn').addEventListener('click', () => {
    currentPage--;
    renderPage();
  });
  document.getElementById('next-btn').addEventListener('click', () => {
    currentPage++;
    renderPage();
  });

  const pageInput = document.getElementById('page-input');
  const jumpToPage = () => {
    const n = Math.round(Number(pageInput.value));
    const clamped = Math.min(totalPages, Math.max(1, Number.isFinite(n) ? n : currentPage));
    if (clamped !== currentPage) {
      currentPage = clamped;
      renderPage();
    } else {
      pageInput.value = currentPage;
    }
  };
  pageInput.addEventListener('change', jumpToPage);
  pageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') pageInput.blur();
  });
}

function updateResultCount() {
  if (!searchInput.value.trim()) {
    resultCountEl.textContent = `${allWords.length} words`;
  } else {
    resultCountEl.textContent = `${visibleWords.length} match${visibleWords.length === 1 ? '' : 'es'}`;
  }
}

function applySearch() {
  const query = normalize(searchInput.value.trim());
  visibleWords = query
    ? allWords.filter(w => w._search.includes(query))
    : allWords;
  currentPage = 1;
  updateResultCount();
  renderPage();
}

let debounceTimer;
searchInput.addEventListener('input', () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(applySearch, 120);
});

fetch('updated_obolo_dictionary.json')
  .then(r => r.json())
  .then(data => {
    allWords = data.map(w => ({ ...w, _search: collectSearchText(w) }));
    visibleWords = allWords;
    updateResultCount();
    renderPage();
  })
  .catch(err => {
    listEl.innerHTML = `<div class="empty-state">Failed to load dictionary data: ${escapeHtml(err.message)}</div>`;
  });
