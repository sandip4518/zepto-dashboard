/* ============================================================
   ZEPTO DASHBOARD — dashboard.js
   All chart instances, filter logic, error handling
   ============================================================ */

// ── Constants ─────────────────────────────────────────────
const COLORS = {
    purple:  '#7c5cfc',
    purpleL: '#a48bfd',
    blue:    '#3d8ef8',
    blueL:   '#76b0fb',
    cyan:    '#06c8d4',
    cyanL:   '#5ae0e8',
    green:   '#0fd68a',
    greenL:  '#5ae6a8',
    amber:   '#f5a623',
    amberL:  '#f7be62',
    red:     '#f24b4b',
    redL:    '#f78080',
    pink:    '#e879f9',
    grid:    'rgba(255,255,255,0.05)',
    text:    '#8b9ab5',
    textP:   '#eef2f8',
};

const PALETTE = [
    COLORS.purple, COLORS.cyan, COLORS.amber, COLORS.green,
    COLORS.red,    COLORS.blue, COLORS.pink,  COLORS.amberL,
    COLORS.greenL, COLORS.redL, COLORS.purpleL, COLORS.cyanL,
];

// ── State ──────────────────────────────────────────────────
const charts = {};
let chart11Mode = 'best';
let chart11Data = { best: [], worst: [] };
let initRanges  = {};

// ── Chart.js Defaults ──────────────────────────────────────
Chart.defaults.color              = COLORS.text;
Chart.defaults.font.family        = "'Space Grotesk', sans-serif";
Chart.defaults.font.size          = 12;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyle    = 'rectRounded';
Chart.defaults.plugins.legend.labels.boxWidth      = 10;
Chart.defaults.plugins.legend.labels.boxHeight     = 10;
Chart.defaults.plugins.legend.labels.padding       = 16;

// Shared scale options
function scaleOpts(extra = {}) {
    return {
        grid:  { color: COLORS.grid, drawBorder: false },
        ticks: { color: COLORS.text, ...extra },
        border:{ display: false },
    };
}

// ── Helpers ────────────────────────────────────────────────
function fmtINR(val) {
    if (val >= 1e7) return '₹' + (val / 1e7).toFixed(1) + 'Cr';
    if (val >= 1e5) return '₹' + (val / 1e5).toFixed(1) + 'L';
    if (val >= 1e3) return '₹' + (val / 1e3).toFixed(1) + 'K';
    return '₹' + Math.round(val);
}

function fmtNum(val) {
    return Number(val).toLocaleString('en-IN');
}

function truncate(str, len = 22) {
    return str && str.length > len ? str.substring(0, len) + '…' : str;
}

function showLoading(on) {
    document.getElementById('loadingOverlay').classList.toggle('active', on);
}

function updateTimestamp() {
    const el = document.getElementById('lastUpdated');
    if (el) el.textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// Destroy + recreate chart safely
function makeChart(id, config) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
    charts[id] = new Chart(canvas.getContext('2d'), config);
}

// ── Init ───────────────────────────────────────────────────
async function initDashboard() {
    showLoading(true);
    try {
        const res  = await fetch('/api/init');
        if (!res.ok) throw new Error('Init fetch failed: ' + res.status);
        const data = await res.json();

        initRanges = data;

        // Category multi-select
        const catSel = document.getElementById('filterCategory');
        (data.categories || []).forEach(c => {
            const opt = document.createElement('option');
            opt.value = c; opt.textContent = c;
            catSel.appendChild(opt);
        });

        // MRP slider
        const mrpSlider = document.getElementById('filterMrpMax');
        mrpSlider.min   = Math.floor(data.mrpRange[0]);
        mrpSlider.max   = Math.ceil(data.mrpRange[1]);
        mrpSlider.value = mrpSlider.max;
        document.getElementById('mrpMaxVal').textContent = mrpSlider.max;

        // Discount slider
        const discSlider = document.getElementById('filterDiscMax');
        discSlider.min   = Math.floor(data.discountRange[0]);
        discSlider.max   = Math.ceil(data.discountRange[1]);
        discSlider.value = discSlider.max;
        document.getElementById('discMaxVal').textContent = discSlider.max;

        // Weight slider
        const wtSlider = document.getElementById('filterWtMax');
        wtSlider.min   = Math.floor(data.weightRange[0]);
        wtSlider.max   = Math.ceil(data.weightRange[1]);
        wtSlider.value = wtSlider.max;
        document.getElementById('wtMaxVal').textContent = wtSlider.max;

        // Live slider labels
        mrpSlider.oninput  = e => document.getElementById('mrpMaxVal').textContent  = e.target.value;
        discSlider.oninput = e => document.getElementById('discMaxVal').textContent = e.target.value;
        wtSlider.oninput   = e => document.getElementById('wtMaxVal').textContent   = e.target.value;

        // Buttons
        document.getElementById('applyFilters').addEventListener('click', applyFilters);
        document.getElementById('resetFilters').addEventListener('click', resetFilters);
        document.getElementById('toggleBestWorst').addEventListener('click', onToggleChart11);

        // Enter key in search
        document.getElementById('filterSearch').addEventListener('keydown', e => {
            if (e.key === 'Enter') applyFilters();
        });

        // Nav highlight on scroll
        setupScrollSpy();

        await applyFilters();
    } catch (err) {
        console.error('Init error:', err);
        showLoading(false);
    }
}

function resetFilters() {
    const r = initRanges;

    // Reset category
    const catSel = document.getElementById('filterCategory');
    Array.from(catSel.options).forEach(o => o.selected = false);

    // Reset stock
    document.getElementById('filterStock').value = 'All';

    // Reset sliders
    const mrpSlider  = document.getElementById('filterMrpMax');
    const discSlider = document.getElementById('filterDiscMax');
    const wtSlider   = document.getElementById('filterWtMax');

    mrpSlider.value  = mrpSlider.max;
    discSlider.value = discSlider.max;
    wtSlider.value   = wtSlider.max;

    document.getElementById('mrpMaxVal').textContent  = mrpSlider.max;
    document.getElementById('discMaxVal').textContent = discSlider.max;
    document.getElementById('wtMaxVal').textContent   = wtSlider.max;

    // Reset search
    document.getElementById('filterSearch').value = '';
    document.getElementById('lowStockThreshold').value = 20;

    applyFilters();
}

// ── Apply Filters ──────────────────────────────────────────
async function applyFilters() {
    showLoading(true);
    try {
        const catSel  = document.getElementById('filterCategory');
        const selCats = Array.from(catSel.selectedOptions).map(o => o.value);

        const mrpSlider  = document.getElementById('filterMrpMax');
        const discSlider = document.getElementById('filterDiscMax');
        const wtSlider   = document.getElementById('filterWtMax');

        const payload = {
            categories:         selCats,
            stockStatus:        document.getElementById('filterStock').value,
            mrpRange:           [parseFloat(mrpSlider.min), parseFloat(mrpSlider.value)],
            discountRange:      [parseFloat(discSlider.min), parseFloat(discSlider.value)],
            weightRange:        [parseFloat(wtSlider.min), parseFloat(wtSlider.value)],
            search:             document.getElementById('filterSearch').value.trim(),
            lowStockThreshold:  parseInt(document.getElementById('lowStockThreshold').value, 10) || 20,
        };

        const res = await fetch('/api/data', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });

        if (!res.ok) throw new Error('Data fetch failed: ' + res.status);
        const data = await res.json();
        updateDashboard(data);
        updateTimestamp();
    } catch (err) {
        console.error('Filter error:', err);
    } finally {
        showLoading(false);
    }
}

// ── Update Dashboard ───────────────────────────────────────
function updateDashboard(data) {
    const { kpis, charts: cd } = data;

    // KPIs
    document.getElementById('kpiSkus').textContent = fmtNum(kpis.total_skus);
    document.getElementById('kpiOos').textContent  = kpis.oos_pct + '%';
    document.getElementById('kpiDisc').textContent = kpis.avg_discount + '%';
    document.getElementById('kpiRev').textContent  = fmtINR(kpis.potential_revenue);

    renderChart1(cd.chart1);
    renderChart2(cd.chart2);
    renderChart3(cd.chart3);
    renderChart4(cd.chart4);
    renderChart5(cd.chart5);
    renderChart6(cd.chart6);
    renderChart7(cd.chart7);
    renderChart8(cd.chart8);
    renderChart9(cd.chart9);
    renderChart10(cd.chart10);

    // Store chart11 data and render
    chart11Data = { best: cd.chart11_best || [], worst: cd.chart11_worst || [] };
    renderChart11();
}

// ── Chart 1: Discount Histogram ────────────────────────────
function renderChart1(rows) {
    if (!rows || !rows.length) return;
    makeChart('chart1', {
        type: 'bar',
        data: {
            labels:   rows.map(r => r.bucket),
            datasets: [{
                label:           'SKU Count',
                data:            rows.map(r => r.count),
                backgroundColor: COLORS.purple + 'cc',
                borderColor:     COLORS.purple,
                borderWidth:     1,
                borderRadius:    4,
                borderSkipped:   false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: scaleOpts({ maxRotation: 45, minRotation: 0 }),
                y: { ...scaleOpts(), beginAtZero: true, ticks: { ...scaleOpts().ticks, callback: v => fmtNum(v) } },
            },
        },
    });
}

// ── Chart 2: Grouped Bar MRP vs SP ─────────────────────────
function renderChart2(rows) {
    if (!rows || !rows.length) return;
    makeChart('chart2', {
        type: 'bar',
        data: {
            labels:   rows.map(r => truncate(r.category, 14)),
            datasets: [
                {
                    label:           'Avg MRP',
                    data:            rows.map(r => r.avg_mrp),
                    backgroundColor: 'rgba(139,154,181,0.5)',
                    borderColor:     COLORS.text,
                    borderWidth:     1,
                    borderRadius:    3,
                    borderSkipped:   false,
                },
                {
                    label:           'Avg Selling Price',
                    data:            rows.map(r => r.avg_sp),
                    backgroundColor: COLORS.cyan + 'cc',
                    borderColor:     COLORS.cyan,
                    borderWidth:     1,
                    borderRadius:    3,
                    borderSkipped:   false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { color: COLORS.text } },
                tooltip: {
                    callbacks: { label: ctx => ctx.dataset.label + ': ₹' + ctx.parsed.y.toFixed(2) },
                },
            },
            scales: {
                x: scaleOpts({ maxRotation: 35, minRotation: 0 }),
                y: { ...scaleOpts(), beginAtZero: true, ticks: { ...scaleOpts().ticks, callback: v => '₹' + v } },
            },
        },
    });
}

// ── Chart 3: Scatter MRP vs Discount ──────────────────────
function renderChart3(rows) {
    if (!rows || !rows.length) return;

    // Group by category
    const grouped = {};
    rows.forEach(r => {
        if (!grouped[r.category]) grouped[r.category] = [];
        grouped[r.category].push({ x: r.mrp, y: r.discount, name: r.name });
    });

    const datasets = Object.entries(grouped).map(([cat, pts], i) => ({
        label:           cat,
        data:            pts,
        backgroundColor: PALETTE[i % PALETTE.length] + '99',
        borderColor:     PALETTE[i % PALETTE.length],
        pointRadius:     4,
        pointHoverRadius:6,
    }));

    makeChart('chart3', {
        type: 'scatter',
        data: { datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: COLORS.text, boxWidth: 10 } },
                tooltip: {
                    callbacks: {
                        label: ctx => `${truncate(ctx.raw.name, 28)} — ₹${ctx.raw.x} | ${ctx.raw.y}% off`,
                    },
                },
            },
            scales: {
                x: { ...scaleOpts(), title: { display: true, text: 'MRP (₹)', color: COLORS.text }, ticks: { ...scaleOpts().ticks, callback: v => '₹' + v } },
                y: { ...scaleOpts(), title: { display: true, text: 'Discount %', color: COLORS.text }, beginAtZero: true, ticks: { ...scaleOpts().ticks, callback: v => v + '%' } },
            },
        },
    });
}

// ── Chart 4: Donut In/Out Stock ────────────────────────────
function renderChart4(rows) {
    if (!rows || !rows.length) return;
    const total = rows.reduce((s, r) => s + r.count, 0);
    makeChart('chart4', {
        type: 'doughnut',
        data: {
            labels:   rows.map(r => r.status),
            datasets: [{
                data:            rows.map(r => r.count),
                backgroundColor: rows.map(r => r.status === 'Out of Stock' ? COLORS.red + 'dd' : COLORS.green + 'dd'),
                borderColor:     rows.map(r => r.status === 'Out of Stock' ? COLORS.red : COLORS.green),
                borderWidth:     2,
                hoverOffset:     6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'bottom', labels: { color: COLORS.text } },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.label}: ${fmtNum(ctx.parsed)} (${((ctx.parsed/total)*100).toFixed(1)}%)`,
                    },
                },
            },
            scales: { x: { display: false }, y: { display: false } },
        },
    });
}

// ── Chart 5: Stacked Bar Category Stock ───────────────────
function renderChart5(rows) {
    if (!rows || !rows.length) return;
    makeChart('chart5', {
        type: 'bar',
        data: {
            labels:   rows.map(r => truncate(r.category, 14)),
            datasets: [
                {
                    label:           'In Stock',
                    data:            rows.map(r => r.in_stock),
                    backgroundColor: COLORS.green + 'cc',
                    borderColor:     COLORS.green,
                    borderWidth:     1,
                    borderRadius:    3,
                    borderSkipped:   false,
                },
                {
                    label:           'Out of Stock',
                    data:            rows.map(r => r.out_of_stock),
                    backgroundColor: COLORS.red + 'cc',
                    borderColor:     COLORS.red,
                    borderWidth:     1,
                    borderRadius:    3,
                    borderSkipped:   false,
                },
            ],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { position: 'top', labels: { color: COLORS.text } } },
            scales: {
                x: { ...scaleOpts({ maxRotation: 35 }), stacked: true },
                y: { ...scaleOpts(), stacked: true, beginAtZero: true },
            },
        },
    });
}

// ── Chart 6: Low Stock Horizontal Bar ─────────────────────
function renderChart6(rows) {
    if (!rows || !rows.length) return;
    const bgColors = rows.map(r => {
        if (r.qty < 5)  return COLORS.red + 'dd';
        if (r.qty < 10) return COLORS.amber + 'dd';
        return COLORS.green + 'dd';
    });
    const bdColors = rows.map(r => {
        if (r.qty < 5)  return COLORS.red;
        if (r.qty < 10) return COLORS.amber;
        return COLORS.green;
    });

    // Dynamic height based on row count
    const wrapper = document.getElementById('chart6').parentElement;
    if (wrapper) wrapper.style.height = Math.max(300, rows.length * 28 + 60) + 'px';

    makeChart('chart6', {
        type: 'bar',
        data: {
            labels:   rows.map(r => truncate(r.name, 28)),
            datasets: [{
                label:           'Available Qty',
                data:            rows.map(r => r.qty),
                backgroundColor: bgColors,
                borderColor:     bdColors,
                borderWidth:     1,
                borderRadius:    3,
                borderSkipped:   false,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` Qty: ${ctx.parsed.x}  |  Category: ${rows[ctx.dataIndex]?.category || ''}`,
                    },
                },
            },
            scales: {
                x: { ...scaleOpts(), beginAtZero: true },
                y: { ...scaleOpts({ font: { size: 11 } }) },
            },
        },
    });
}

// ── Chart 7: Treemap Revenue Potential ────────────────────
function renderChart7(rows) {
    if (!rows || !rows.length) return;

    // Build color map per category
    const colorMap = {};
    rows.forEach((r, i) => { colorMap[r.category] = PALETTE[i % PALETTE.length]; });

    makeChart('chart7', {
        type: 'treemap',
        data: {
            datasets: [{
                label:  'Revenue Potential',
                tree:   rows,
                key:    'revenue',
                groups: ['category'],
                backgroundColor: ctx => {
                    if (ctx.type !== 'data') return 'transparent';
                    const cat = ctx.raw?._data?.category;
                    return (colorMap[cat] || COLORS.purple) + 'bb';
                },
                borderColor: ctx => {
                    if (ctx.type !== 'data') return 'transparent';
                    const cat = ctx.raw?._data?.category;
                    return colorMap[cat] || COLORS.purple;
                },
                borderWidth: 2,
                labels: {
                    display:   true,
                    color:     '#fff',
                    font:      { size: 12, weight: '600' },
                    formatter: ctx => {
                        if (!ctx.raw?._data) return '';
                        return [ctx.raw._data.category, fmtINR(ctx.raw.v)];
                    },
                },
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        title: () => '',
                        label: ctx => ` ${ctx.raw._data?.category}: ${fmtINR(ctx.raw.v)}`,
                    },
                },
            },
            scales: { x: { display: false }, y: { display: false } },
        },
    });
}

// ── Chart 8: SKU Count per Category ───────────────────────
function renderChart8(rows) {
    if (!rows || !rows.length) return;

    const wrapper = document.getElementById('chart8').parentElement;
    if (wrapper) wrapper.style.height = Math.max(280, rows.length * 30 + 60) + 'px';

    makeChart('chart8', {
        type: 'bar',
        data: {
            labels:   rows.map(r => truncate(r.category, 20)),
            datasets: [{
                label:           'SKU Count',
                data:            rows.map(r => r.count),
                backgroundColor: COLORS.cyan + 'bb',
                borderColor:     COLORS.cyan,
                borderWidth:     1,
                borderRadius:    3,
                borderSkipped:   false,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ...scaleOpts(), beginAtZero: true },
                y: scaleOpts({ font: { size: 12 } }),
            },
        },
    });
}

// ── Chart 9: Radar Avg Discount ────────────────────────────
function renderChart9(rows) {
    if (!rows || !rows.length) return;
    makeChart('chart9', {
        type: 'radar',
        data: {
            labels:   rows.map(r => truncate(r.category, 14)),
            datasets: [{
                label:           'Avg Discount %',
                data:            rows.map(r => r.avg_discount),
                backgroundColor: COLORS.purple + '30',
                borderColor:     COLORS.purple,
                borderWidth:     2,
                pointBackgroundColor: COLORS.purple,
                pointBorderColor:     '#fff',
                pointBorderWidth:     1,
                pointRadius:          4,
                pointHoverRadius:     6,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                r: {
                    grid:        { color: COLORS.grid },
                    angleLines:  { color: COLORS.grid },
                    pointLabels: { color: COLORS.text, font: { size: 11 } },
                    ticks:       { color: COLORS.text, backdropColor: 'transparent', callback: v => v + '%' },
                    suggestedMin: 0,
                },
                // Disable cartesian scales for radar
                x: { display: false },
                y: { display: false },
            },
        },
    });
}

// ── Chart 10: Boxplot Price per Gram ──────────────────────
function renderChart10(rows) {
    if (!rows || !rows.length) return;
    makeChart('chart10', {
        type: 'boxplot',
        data: {
            labels:   rows.map(r => truncate(r.category, 16)),
            datasets: [{
                label:                  'Price/Gram Distribution',
                backgroundColor:        COLORS.purple + '55',
                borderColor:            COLORS.purple,
                borderWidth:            1.5,
                outlierBackgroundColor: COLORS.red + 'aa',
                outlierRadius:          3,
                itemBackgroundColor:    COLORS.purple + '88',
                // Pass as array of arrays: [min, q1, median, q3, max]
                data: rows.map(r => [r.min, r.q1, r.median, r.q3, r.max]),
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: scaleOpts({ maxRotation: 35 }),
                y: { ...scaleOpts(), ticks: { ...scaleOpts().ticks, callback: v => '₹' + Number(v).toFixed(3) } },
            },
        },
    });
}

// ── Chart 11: Best / Worst Value Toggle ───────────────────
function renderChart11() {
    const rows  = chart11Data[chart11Mode] || [];
    const isBest = chart11Mode === 'best';
    const color  = isBest ? COLORS.green : COLORS.red;
    const label  = isBest ? 'Best Value (Lowest ₹/g)' : 'Worst Value (Highest ₹/g)';

    if (!rows.length) return;

    const wrapper = document.getElementById('chart11').parentElement;
    if (wrapper) wrapper.style.height = Math.max(280, rows.length * 30 + 60) + 'px';

    makeChart('chart11', {
        type: 'bar',
        data: {
            labels:   rows.map(r => `${truncate(r.category, 10)} · ${truncate(r.name, 14)}`),
            datasets: [{
                label:           label,
                data:            rows.map(r => parseFloat(r.price_per_gram)),
                backgroundColor: color + 'bb',
                borderColor:     color,
                borderWidth:     1,
                borderRadius:    3,
                borderSkipped:   false,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ₹${ctx.parsed.x.toFixed(4)}/g`,
                    },
                },
            },
            scales: {
                x: { ...scaleOpts(), beginAtZero: true, ticks: { ...scaleOpts().ticks, callback: v => '₹' + v.toFixed(3) } },
                y: scaleOpts({ font: { size: 11 } }),
            },
        },
    });
}

function onToggleChart11() {
    chart11Mode = chart11Mode === 'best' ? 'worst' : 'best';
    const btn   = document.getElementById('toggleBestWorst');
    const label = document.getElementById('toggleLabel');
    btn.dataset.mode     = chart11Mode;
    label.textContent    = chart11Mode === 'best' ? 'Best Value' : 'Worst Value';
    renderChart11();
}

// ── Scroll Spy for Sidebar ─────────────────────────────────
function setupScrollSpy() {
    const sections = document.querySelectorAll('.dash-section[id], .kpi-grid[id]');
    const navItems = document.querySelectorAll('.nav-item');

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                navItems.forEach(n => n.classList.remove('active'));
                const target = document.querySelector(`.nav-item[href="#${entry.target.id}"]`);
                if (target) target.classList.add('active');
            }
        });
    }, { threshold: 0.3 });

    sections.forEach(s => observer.observe(s));
}

// ── Boot ───────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initDashboard);