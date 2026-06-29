// Evidence Gap Atlas — Specialty drilldown architecture

let DB = null;
let activeSpecialty = null;
let activeGuideline = null;
let searchQuery = '';

// Colors: green (well-evidenced) to red (evidence gap)
// Use string keys to avoid JS float-to-int coercion (1.0 -> "1")
const TIER_KEYS   = ['t1', 't075', 't05', 't025', 't0125'];
const TIER_VALUES = [1.0, 0.75, 0.5, 0.25, 0.125];
const TIER_COLORS = { t1: '#4a8c6a', t075: '#5b8fb8', t05: '#c4a94d', t025: '#c4824a', t0125: '#b85b5b' };
const TIER_LETTERS = { t1: 'A', t075: 'B', t05: 'C', t025: 'D', t0125: 'E' };
const TIER_DESC = {
    t1:    'Multiple RCTs or meta-analyses',
    t075:  'Single RCT or moderate certainty',
    t05:   'Observational or low certainty',
    t025:  'Case series or very low certainty',
    t0125: 'Expert opinion or consensus only',
};
const TIER_LABELS = { t1: 'A', t075: 'B', t05: 'C', t025: 'D', t0125: 'E' };

function tierKeyOf(norm) {
    if (norm == null) return null;
    if (norm >= 1.0) return 't1';
    if (norm >= 0.75) return 't075';
    if (norm >= 0.5) return 't05';
    if (norm >= 0.25) return 't025';
    return 't0125';
}
function tierColor(key) { return TIER_COLORS[key] || '#ccc'; }
function normColor(norm) { return tierColor(tierKeyOf(norm)); }
function gapColor(gap) {
    if (gap < 0.3) return '#4a8c6a';
    if (gap < 0.5) return '#5b8fb8';
    if (gap < 0.65) return '#c4a94d';
    if (gap < 0.8) return '#c4824a';
    return '#b85b5b';
}

function primaryGlIds() {
    return new Set(DB.guidelines.filter(g => g.in_primary_analysis).map(g => g.id));
}

function primaryRecs() {
    const glIds = primaryGlIds();
    return DB.recommendations.filter(r => r.loe_normalized != null && glIds.has(r.guideline_id));
}

// ---- Data Loading ----
async function loadData() {
    try {
        const r = await fetch('evidence_atlas.json?v=' + Date.now());
        DB = await r.json();
    } catch(e) {
        document.getElementById('overall-distribution').innerHTML =
            '<p style="color:var(--text-dim)">Could not load data. Run: python pipeline/consolidate.py</p>';
        return;
    }
    renderAll();
}

// Shared primary analysis filter (matching manuscript exactly):
// specialties with >=5 guidelines AND the in_primary_analysis flag (excludes single-/two-rec
// stub guidelines such as rapid updates that the manuscript drops). Yields 522 GLs / 22,693 recs.
function primaryAnalysisData() {
    const specGlCount = {};
    DB.guidelines.forEach(g => { specGlCount[g.specialty] = (specGlCount[g.specialty] || 0) + 1; });
    const primarySpecs = new Set(Object.keys(specGlCount).filter(s => specGlCount[s] >= 5));
    const primaryGls = DB.guidelines.filter(g => primarySpecs.has(g.specialty) && g.in_primary_analysis);
    const primaryGlIdSet = new Set(primaryGls.map(g => g.id));
    const recs = DB.recommendations.filter(r => r.loe_normalized != null && primaryGlIdSet.has(r.guideline_id));
    const socs = new Set(primaryGls.map(g => g.society));
    return { recs, gls: primaryGls, specs: primarySpecs, socs, glIdSet: primaryGlIdSet, specGlCount };
}

function renderAll() {
    const pa = primaryAnalysisData();

    document.getElementById('total-recs').textContent = pa.recs.length.toLocaleString();
    document.getElementById('total-guidelines').textContent = pa.gls.length;
    document.getElementById('total-societies').textContent = pa.socs.size;
    document.getElementById('total-specialties').textContent = pa.specs.size;

    renderOverallDistribution(pa);
    renderSpecialtyGrid(pa);
}

// ---- Overall Evidence Distribution ----
function renderOverallDistribution(pa) {
    const el = document.getElementById('overall-distribution');
    const recs = pa.recs;
    if (!recs.length) { el.innerHTML = '<p style="color:var(--text-dim)">No data.</p>'; return; }
    el.innerHTML = buildDistribution(recs, true);
}

function buildDistribution(recs, showStats) {
    const total = recs.length;
    const norms = recs.map(r => r.loe_normalized).filter(n => n != null);

    // Count per tier
    const tierCounts = {};
    TIER_KEYS.forEach(k => tierCounts[k] = 0);
    norms.forEach(n => { const k = tierKeyOf(n); if (k) tierCounts[k]++; });

    const maxCount = Math.max(...Object.values(tierCounts), 1);

    // Stats
    const pctHighest = (tierCounts.t1 / total * 100).toFixed(1);
    const pctLowest = ((tierCounts.t025 + tierCounts.t0125) / total * 100).toFixed(1);

    let statsHtml = '';
    if (showStats) {
        statsHtml = `
        <div class="overview-stats" style="margin-bottom:1.5rem">
            <div class="overview-stat">
                <span class="overview-stat-value">${total.toLocaleString()}</span>
                <span class="overview-stat-label">Recommendations</span>
            </div>
            <div class="overview-stat">
                <span class="overview-stat-value">${pctHighest}%</span>
                <span class="overview-stat-label">Highest evidence (RCTs)</span>
            </div>
            <div class="overview-stat">
                <span class="overview-stat-value">${pctLowest}%</span>
                <span class="overview-stat-label">Low / expert opinion</span>
            </div>
        </div>`;
    }

    // Stacked bar
    const barSegments = TIER_KEYS.map(k => {
        const pct = tierCounts[k] / total * 100;
        if (pct < 0.5) return '';
        return `<div class="ev-segment" style="flex:${pct};background:${tierColor(k)}"
            title="${TIER_LABELS[k]}: ${tierCounts[k]} (${pct.toFixed(1)}%)">
            <span>${pct >= 8 ? pct.toFixed(0) + '%' : ''}</span></div>`;
    }).join('');

    // Histogram
    const histogram = TIER_KEYS.map(k => {
        const count = tierCounts[k];
        const h = count / maxCount * 100;
        return `<div class="hist-bar-container">
            <div class="hist-count">${count}</div>
            <div class="hist-bar" style="height:${h}px;background:${tierColor(k)}"></div>
            <div class="hist-label">${TIER_LABELS[k]}</div>
        </div>`;
    }).join('');

    return `${statsHtml}
        <div class="evidence-bar large">${barSegments}</div>
        <div class="bar-legend" style="margin-top:0.5rem;margin-bottom:1.5rem">
            ${TIER_KEYS.map(k => `<span><span class="legend-dot" style="background:${tierColor(k)}"></span> <strong>${TIER_LETTERS[k]}</strong> ${TIER_DESC[k]} (${tierCounts[k]})</span>`).join('')}
        </div>
        <div class="histogram" style="height:130px">${histogram}</div>`;
}

// ---- Specialty Grid ----
function renderSpecialtyGrid(pa) {
    const el = document.getElementById('specialty-grid');
    const allLoeRecs = pa.recs;

    // Build specialty list from primary analysis recs
    const specMap = {};
    allLoeRecs.forEach(r => {
        if (!specMap[r.specialty]) specMap[r.specialty] = [];
        specMap[r.specialty].push(r);
    });

    // Sort by evidence gap (descending) — already filtered to >=5 GLs
    const specialties = Object.keys(specMap)
        .map(spec => {
        const specRecs = specMap[spec];
        const meanNorm = specRecs.reduce((s, r) => s + r.loe_normalized, 0) / specRecs.length;
        const societies = [...new Set(specRecs.map(r => r.society))];
        const glCount = pa.specGlCount[spec] || 0;
        return { specialty: spec, evidence_gap: 1.0 - meanNorm, recs: specRecs, societies, glCount };
    }).sort((a, b) => b.evidence_gap - a.evidence_gap);

    if (!specialties.length) {
        el.innerHTML = '<p style="color:var(--text-dim)">Extract more guidelines to see specialty breakdowns.</p>';
        return;
    }

    el.innerHTML = specialties.map(sg => {
        const gap = sg.evidence_gap;
        const color = gapColor(gap);
        const isActive = activeSpecialty === sg.specialty;

        // Mini bar for the card
        const recs = sg.recs;
        const tierCounts = {};
        TIER_KEYS.forEach(k => tierCounts[k] = 0);
        recs.forEach(r => { const k = tierKeyOf(r.loe_normalized); if (k) tierCounts[k]++; });
        const total = recs.length;
        const miniBar = TIER_KEYS.map(k => {
            const pct = tierCounts[k] / total * 100;
            return pct < 1 ? '' : `<div class="ev-segment" style="flex:${pct};background:${tierColor(k)}"><span></span></div>`;
        }).join('');

        return `<div class="specialty-card${isActive ? ' active' : ''}" onclick="openSpecialty('${sg.specialty}')">
            <div class="card-header">
                <div class="card-title">${sg.specialty}</div>
            </div>
            <div class="card-stats">
                <div class="card-stat">
                    <span class="card-stat-value">${total}</span>
                    <span class="card-stat-label">recs</span>
                </div>
                <div class="card-stat">
                    <span class="card-stat-value">${new Set(recs.map(r => r.guideline_id)).size}</span>
                    <span class="card-stat-label">guidelines</span>
                </div>
                <div class="card-stat">
                    <span class="card-stat-value" style="color:${color}">${gap.toFixed(2)}</span>
                    <span class="card-stat-label">gap</span>
                </div>
            </div>
            <div class="evidence-bar small">${miniBar}</div>
            <div class="card-societies">${sg.societies.join(', ')}</div>
        </div>`;
    }).join('');
}

// ---- Specialty Drilldown ----
function openSpecialty(specialty) {
    if (activeSpecialty === specialty) {
        closeSpecialty();
        return;
    }
    activeSpecialty = specialty;
    activeGuideline = null;
    searchQuery = '';

    document.getElementById('drilldown').classList.remove('hidden');
    renderSpecialtyGrid(primaryAnalysisData());
    renderDrilldown();

    document.getElementById('drilldown').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function closeSpecialty() {
    activeSpecialty = null;
    activeGuideline = null;
    document.getElementById('drilldown').classList.add('hidden');
    renderSpecialtyGrid(primaryAnalysisData());
}

function renderDrilldown() {
    const pa = primaryAnalysisData();
    const recs = pa.recs.filter(r => r.specialty === activeSpecialty);
    const glIdsWithLoE = new Set(recs.map(r => r.guideline_id));
    const guidelines = DB.guidelines.filter(g => glIdsWithLoE.has(g.id));
    const societies = [...new Set(recs.map(r => r.society))];

    // Header
    document.getElementById('drilldown-header').innerHTML = `
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem">
            <div>
                <h2>${activeSpecialty}</h2>
                <p class="section-intro" style="margin-bottom:0">
                    ${recs.length} recommendations from ${guidelines.length} guidelines
                    (${societies.join(', ')})
                </p>
            </div>
            <button class="filter-btn" onclick="closeSpecialty()" style="font-size:0.85rem;padding:0.4rem 1rem">Back</button>
        </div>`;

    // Distribution for this specialty
    document.getElementById('drilldown-distribution').innerHTML = buildDistribution(recs, false);

    // Guidelines within this specialty
    document.getElementById('drilldown-guidelines').innerHTML = `
        <h3 style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-dim);margin:1.5rem 0 0.5rem">
            Guidelines
        </h3>
        <div class="guideline-grid">
            ${guidelines.map(g => {
                const gRecs = recs.filter(r => r.guideline_id === g.id);
                const isActive = activeGuideline === g.id;
                const tierCounts = {};
                TIER_KEYS.forEach(k => tierCounts[k] = 0);
                gRecs.forEach(r => { const k = tierKeyOf(r.loe_normalized); if (k) tierCounts[k]++; });
                const gt = gRecs.length;
                const miniBar = TIER_KEYS.map(k => {
                    const pct = tierCounts[k] / gt * 100;
                    return pct < 1 ? '' : `<div class="ev-segment" style="flex:${pct};background:${tierColor(k)}"><span>${pct >= 15 ? pct.toFixed(0)+'%' : ''}</span></div>`;
                }).join('');

                return `<div class="guideline-card${isActive ? ' active' : ''}" onclick="toggleGuideline('${g.id}')">
                    <div class="guideline-card-header">
                        <span class="guideline-year">${g.year}</span>
                        <span class="guideline-society">${g.society}</span>
                    </div>
                    <div class="guideline-card-title">${g.title}</div>
                    <div class="evidence-bar small" style="margin:0.5rem 0 0.3rem">${miniBar}</div>
                    <div class="guideline-card-meta">
                        ${gt} recommendations
                        ${g.doi ? ` · <a href="https://doi.org/${g.doi}" target="_blank" style="color:var(--accent)" onclick="event.stopPropagation()">DOI</a>` : ''}
                    </div>
                </div>`;
            }).join('')}
        </div>`;

    renderDrilldownFilters();
    renderDrilldownTable();
}

function toggleGuideline(id) {
    activeGuideline = activeGuideline === id ? null : id;
    renderDrilldown();
}

function renderDrilldownFilters() {
    const el = document.getElementById('drilldown-filters');
    const filtered = getDrilldownRecs();
    const total = DB.recommendations.filter(r => r.specialty === activeSpecialty && r.loe_normalized != null).length;
    const hasFilter = activeGuideline || searchQuery;

    let chips = '';
    if (activeGuideline) {
        const g = DB.guidelines.find(g => g.id === activeGuideline);
        chips += `<span class="filter-chip" onclick="toggleGuideline('${activeGuideline}')">${g?.title?.substring(0,40) || activeGuideline} &times;</span>`;
    }
    if (searchQuery) {
        chips += `<span class="filter-chip" onclick="searchQuery='';document.getElementById('drill-search').value='';renderDrilldownFilters();renderDrilldownTable()">"${searchQuery}" &times;</span>`;
    }

    el.innerHTML = `
        <div style="margin-top:1.5rem">
            <h3 style="font-size:0.75rem;text-transform:uppercase;letter-spacing:0.8px;color:var(--text-dim);margin-bottom:0.5rem">
                Recommendations
            </h3>
            <div class="filter-row">
                <input type="text" id="drill-search" placeholder="Search recommendations..."
                    value="${searchQuery}" class="search-input"
                    oninput="searchQuery=this.value;renderDrilldownFilters();renderDrilldownTable()">
                ${hasFilter ? `<button class="filter-btn clear" onclick="activeGuideline=null;searchQuery='';document.getElementById('drill-search').value='';renderDrilldown()">Clear</button>` : ''}
            </div>
            <div class="filter-info">
                ${chips}
                <span class="filter-count">${filtered.length} of ${total} recommendations</span>
                ${filtered.length > 0 ? `<button class="export-btn" onclick="exportCSV()">Export CSV</button>` : ''}
            </div>
        </div>`;
}

function getDrilldownRecs() {
    let recs = DB.recommendations.filter(r => r.specialty === activeSpecialty && r.loe && r.loe !== 'Not stated' && r.loe_normalized != null);
    if (activeGuideline) recs = recs.filter(r => r.guideline_id === activeGuideline);
    if (searchQuery) {
        const q = searchQuery.toLowerCase();
        recs = recs.filter(r => r.text.toLowerCase().includes(q));
    }
    return recs;
}

function renderDrilldownTable() {
    const el = document.getElementById('drilldown-table');
    const recs = getDrilldownRecs().slice(0, 300);
    const total = getDrilldownRecs().length;

    if (!recs.length) {
        el.innerHTML = '<p style="color:var(--text-dim);padding:0.5rem">No recommendations match.</p>';
        return;
    }

    el.innerHTML = `
        ${total > 300 ? `<p style="color:var(--text-dim);font-size:0.72rem;margin-bottom:0.4rem">Showing 300 of ${total}. Filter to narrow down.</p>` : ''}
        <table class="rec-table"><thead><tr>
            <th style="width:36%">Recommendation</th>
            <th style="width:9%" title="Source level of evidence as reported in the original guideline">Source LoE</th>
            <th style="width:7%">Norm.</th>
            <th style="width:5%">Gap</th>
            <!-- Strength of recommendation removed: varies too much across grading systems -->
            <th style="width:6%">Society</th>
            <th style="width:29%">Guideline</th>
        </tr></thead><tbody>
        ${recs.map(r => {
            const gap = r.evidence_gap;
            const gl = DB.guidelines.find(g => g.id === r.guideline_id);
            const glLabel = gl ? `${gl.title} (${gl.year})` : r.guideline_id;
            const normLabel = TIER_LETTERS[tierKeyOf(r.loe_normalized)] || '?';
            const displayText = r.text.length > 50 ? r.text.substring(0, 50) + '...' : r.text;
            return `<tr>
                <td class="rec-text">${highlightSearch(displayText)}</td>
                <td class="rec-source-loe">${r.loe}</td>
                <td><span class="loe-badge" style="background:${normColor(r.loe_normalized)}">${normLabel}</span></td>
                <td><span class="gap-badge" style="color:${gapColor(gap)}">${gap != null ? gap.toFixed(2) : '--'}</span></td>
                <!-- cor column removed -->
                <td class="rec-society">${r.society}</td>
                <td class="rec-guideline">${glLabel}</td>
            </tr>`;
        }).join('')}</tbody></table>`;
}

function highlightSearch(text) {
    if (!searchQuery) return text;
    const q = searchQuery.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    return text.replace(new RegExp(`(${q})`, 'gi'), '<mark>$1</mark>');
}

function exportCSV() {
    const recs = getDrilldownRecs();
    const CC_BY = new Set(['ESMO','ESCMID','ESHRE','EULAR','ERS','KDIGO','GINA','GOLD','ADA','EAU']);
    const headers = ['society','specialty','guideline','year','text_excerpt','loe','loe_normalized','evidence_gap','grading_system'];
    const rows = recs.map(r => {
        const copy = {...r};
        copy.text_excerpt = r.text.length > 50 ? r.text.substring(0, 50) + '...' : r.text;
        const gl = DB.guidelines.find(g => g.id === r.guideline_id);
        copy.guideline = gl ? `${gl.title} (${gl.year})` : r.guideline_id;
        return headers.map(h => `"${String(copy[h]||'').replace(/"/g,'""')}"`).join(',');
    });
    const csv = [headers.join(','), ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `evidence_gap_${activeSpecialty.replace(/\s/g,'_').toLowerCase()}.csv`;
    a.click();
}

document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSpecialty(); });
loadData();
