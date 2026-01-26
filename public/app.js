// app.js - Institutional Dashboard Logic

const API_BASE = "/api"; // API prefix

async function fetchHome() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        const data = await response.json();

        document.getElementById('totalIndexed').textContent = data.db_status.split(' ')[0];
        document.getElementById('workerState').textContent = data.worker.is_running ? "SCANNING" : "IDLE";

        if (data.worker.is_running) {
            document.getElementById('scanProgressText').textContent = `Stock Analysis in Progress...`;
            document.getElementById('workerState').classList.add('scanning');
        } else {
            const lastRun = data.worker.last_run.includes('GMT') ? data.worker.last_run : data.worker.last_run;
            document.getElementById('scanProgressText').textContent = `Last run: ${lastRun}`;
            document.getElementById('workerState').classList.remove('scanning');
        }
    } catch (e) {
        console.error("Error fetching status:", e);
    }
}

async function fetchStocks(minScore = 0) {
    try {
        let url = `${API_BASE}/scan?limit=50&min_score=${minScore}`;

        if (minScore === "darwinex") {
            url = `${API_BASE}/scan-darwinex?limit=50&min_score=0`;
        } else {
            url = `${API_BASE}/scan?limit=50&min_score=${minScore}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        const grid = document.getElementById('stocksGrid');
        grid.innerHTML = "";

        document.getElementById('opportunityCount').textContent = data.results.filter(s => s.score >= 75).length;

        data.results.forEach(stock => {
            const card = document.createElement('div');
            card.className = 'stock-card';

            const details = stock.details || {};
            const technicals = details.technicals || {};
            const institutional = details.institutional || {};
            const financials = details.financials || {};

            const rvol = technicals.relative_volume || 1.0;
            const sector = financials.sector || 'Market';
            const finScore = financials.score || 0;

            card.innerHTML = `
                <div class="stock-card-header">
                    <div class="stock-symbol">${stock.symbol}</div>
                    <div class="stock-score">${stock.score} <span style="font-size: 10px; opacity: 0.7;">PTS</span></div>
                </div>
                <div class="stock-name">${sector}</div>
                <div class="stock-metrics">
                    <div class="metric-item">
                        <span class="metric-label">Financiero</span>
                        <span class="metric-value" style="color: ${finScore > 70 ? 'var(--success)' : 'inherit'}">${finScore}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">RVol</span>
                        <span class="metric-value">${rvol.toFixed(2)}</span>
                    </div>
                </div>
                <div class="stock-reasoning">
                    ${technicals.trend || 'Posicionamiento Institucional'} detectado.
                </div>
            `;

            card.onclick = () => showStockDetail(stock.symbol);
            grid.appendChild(card);
        });
    } catch (e) {
        console.error("Error fetching stocks:", e);
    }
}

async function showStockDetail(symbol) {
    const modal = document.getElementById('stockModal');
    const body = document.getElementById('modalBody');
    body.innerHTML = "<p>Cargando análisis profundo...</p>";
    modal.style.display = "block";

    try {
        const response = await fetch(`${API_BASE}/analyze/${symbol}`);
        const data = await response.json();

        const details = data.details || {};
        const technicals = details.technicals || {};
        const financials = details.financials || {};
        const institutional = details.institutional || {};

        body.innerHTML = `
            <div class="modal-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 20px;">
                <div>
                    <h2 style="font-size: 28px;">${data.symbol}</h2>
                    <p style="color: var(--text-muted)">${financials.sector || 'N/A'}</p>
                </div>
                <div style="font-size: 32px; font-weight: 800; color: var(--accent-primary);">${data.score} <span style="font-size: 14px;">PTS</span></div>
            </div>
            <div class="modal-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 30px;">
                <div class="analysis-section">
                    <h3 style="margin-bottom: 15px; font-size: 18px;">Análisis de Patrones</h3>
                    <div style="background: rgba(255,255,255,0.03); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
                        <p style="line-height: 1.6; color: var(--text-primary);">${institutional.outlook || 'Análisis en proceso...'}</p>
                    </div>
                    <ul style="margin-top: 20px; color: var(--text-muted); list-style: none; padding: 0;">
                        <li style="margin-bottom: 10px;"><i data-lucide="bar-chart-2" style="width: 14px; vertical-align: middle; margin-right: 8px;"></i> RVol: <strong>${technicals.relative_volume?.toFixed(2) || '1.00'}</strong></li>
                        <li style="margin-bottom: 10px;"><i data-lucide="trending-up" style="width: 14px; vertical-align: middle; margin-right: 8px;"></i> Tendencia: <strong>${technicals.trend || 'Neutral'}</strong></li>
                        <li style="margin-bottom: 10px;"><i data-lucide="activity" style="width: 14px; vertical-align: middle; margin-right: 8px;"></i> Estabilidad: <strong>${financials.stability || 'Media'}</strong></li>
                    </ul>
                </div>
                <div class="data-section">
                    <h3 style="margin-bottom: 15px; font-size: 18px;">Salud Financiera</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 12px 0; color: var(--text-muted);">P/E Ratio</td><td style="text-align: right; font-weight: 600;">${financials.pe?.toFixed(1) || 'N/A'}</td></tr>
                        <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 12px 0; color: var(--text-muted);">Debt to Equity</td><td style="text-align: right; font-weight: 600;">${financials.debt_equity?.toFixed(2) || 'N/A'}</td></tr>
                        <tr style="border-bottom: 1px solid var(--border);"><td style="padding: 12px 0; color: var(--text-muted);">ROE</td><td style="text-align: right; font-weight: 600;">${(financials.roe * 100)?.toFixed(1) || '0'}%</td></tr>
                        <tr><td style="padding: 12px 0; color: var(--text-muted);">Market Cap</td><td style="text-align: right; font-weight: 600;">${(financials.market_cap / 1e9).toFixed(1)}B</td></tr>
                    </table>
                    <div style="margin-top: 30px; padding: 15px; background: rgba(16, 185, 129, 0.1); border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.2); color: var(--success); font-weight: 600; text-align: center;">
                        ${data.passed_financials ? 'PASSED FUNDAMENTAL CHECK' : 'RISKY FUNDAMENTALS'}
                    </div>
                </div>
            </div>
        `;
        lucide.createIcons();
    } catch (e) {
        body.innerHTML = "<p>Error al cargar los datos detallados.</p>";
    }
}

// Event Listeners
document.getElementById('updateDbBtn').onclick = async () => {
    await fetch(`${API_BASE}/update-db`, { method: 'POST' });
    alert("Escaneo en segundo plano iniciado.");
    fetchHome();
};

document.getElementById('scoreFilter').onchange = (e) => {
    fetchStocks(e.target.value);
};

document.querySelector('.close-modal').onclick = () => {
    document.getElementById('stockModal').style.display = "none";
};

window.onclick = (event) => {
    const modal = document.getElementById('stockModal');
    if (event.target == modal) {
        modal.style.display = "none";
    }
};

// Initial Load
fetchHome();
fetchStocks();

// Refresh status every 10s
setInterval(fetchHome, 10000);
