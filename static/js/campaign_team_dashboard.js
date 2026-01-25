/**
 * Campaign Team Dashboard V2 - JavaScript
 * Dashboard integrado para el equipo de campaña electoral.
 * Control electoral, zonas de riesgo y coordinación de testigos.
 */

// ============================================================
// GLOBAL STATE
// ============================================================

let currentContestId = 1;
let refreshInterval = null;
const REFRESH_INTERVAL_MS = 30000; // 30 seconds

// Data stores
let allMesas = [];
let allVotes = [];
let allWitnesses = [];
let callLog = [];

// Filter state
let filters = {
    dept: '',
    muni: '',
    puesto: '',
    mesa: '',
    risk: ''
};

// Current selection for witness calling
let selectedMesa = null;
let selectedWitness = null;

// Chart instances
let partyChart = null;
let riskChart = null;

// Chart.js default config
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: '#E0DED8',
                font: { family: "'Source Sans 3', sans-serif" }
            }
        }
    },
    scales: {
        x: {
            ticks: { color: '#9A8F7C' },
            grid: { color: 'rgba(42, 42, 42, 0.5)' }
        },
        y: {
            ticks: { color: '#9A8F7C' },
            grid: { color: 'rgba(42, 42, 42, 0.5)' }
        }
    }
};

// ============================================================
// INITIALIZATION
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    setupTabs();
    setupFilters();
    setupTableSorting();
    setupCriticalMesaSelect();

    // Initial load
    loadDashboardData();

    // Start real-time refresh
    startRealTimeRefresh();
});

// ============================================================
// TAB NAVIGATION
// ============================================================

function setupTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Update buttons
            tabButtons.forEach(b => {
                b.classList.remove('active');
                b.setAttribute('aria-selected', 'false');
            });
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');

            // Update content
            tabContents.forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');

            // Load tab-specific data
            loadTabData(tabId);
        });
    });
}

function loadTabData(tabId) {
    switch (tabId) {
        case 'contienda':
            renderContiendaTab();
            break;
        case 'zonas-riesgo':
            renderRiskZonesTab();
            break;
        case 'llamar-testigo':
            renderWitnessTab();
            break;
    }
}

// ============================================================
// DATA LOADING
// ============================================================

async function loadDashboardData() {
    showLoading(true);

    try {
        // Load data from API including E-14 live data
        const [statsResponse, votesResponse, alertsResponse, e14Response] = await Promise.all([
            fetch(`/api/campaign-team/war-room/stats?contest_id=${currentContestId}`),
            fetch(`/api/campaign-team/reports/votes-by-candidate?contest_id=${currentContestId}`),
            fetch(`/api/campaign-team/war-room/alerts?contest_id=${currentContestId}&limit=100`),
            fetch(`/api/campaign-team/e14-live`)
        ]);

        const statsData = await statsResponse.json();
        const votesData = await votesResponse.json();
        const alertsData = await alertsResponse.json();
        const e14Data = await e14Response.json();

        // Process and store data
        if (statsData.success) {
            processStatsData(statsData);
        }

        if (votesData.success) {
            processVotesData(votesData);
        }

        if (alertsData.success) {
            processAlertsData(alertsData);
        }

        // Render E-14 live form
        if (e14Data.success) {
            renderE14LiveForm(e14Data);
        }

        // Generate mock risk data based on actual data
        generateMockRiskData();

        // Populate filters
        populateFilters();

        // Render initial tab (contienda)
        renderContiendaTab();

        updateTimestamp();

    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showError('Error cargando datos del dashboard');
    } finally {
        showLoading(false);
    }
}

function processStatsData(data) {
    // Store raw stats
    window.dashboardStats = data;
}

function processVotesData(data) {
    // Store votes with risk classification
    allVotes = (data.by_candidate || []).map((vote, index) => ({
        ...vote,
        id: index + 1,
        // Simulate OCR confidence based on vote count variance
        ocrConfidence: Math.max(50, Math.min(99, 85 + Math.random() * 15 - Math.random() * 20)),
        dept: data.dept || 'Antioquia',
        muni: data.muni || 'Medellín',
        puesto: `Puesto ${Math.floor(index / 5) + 1}`,
        mesaNum: (index % 10) + 1
    }));

    // Add risk classification
    allVotes.forEach(vote => {
        if (vote.ocrConfidence < 70) {
            vote.riskLevel = 'high';
        } else if (vote.ocrConfidence < 85) {
            vote.riskLevel = 'medium';
        } else {
            vote.riskLevel = 'low';
        }
    });
}

function processAlertsData(data) {
    // Convert alerts to mesa risk data
    const alerts = data.alerts || [];

    allMesas = alerts.map((alert, index) => ({
        id: alert.id || index + 1,
        mesaId: alert.mesa_id || `Mesa ${index + 1}`,
        dept: 'Antioquia',
        muni: 'Medellín',
        puesto: `Puesto de Votación ${Math.floor(index / 3) + 1}`,
        location: `Calle ${index + 10} # ${index + 5}-${index + 20}`,
        ocrConfidence: Math.max(40, Math.min(95, 75 + Math.random() * 30 - Math.random() * 35)),
        reason: alert.message || 'OCR con baja confianza',
        totalVotes: Math.floor(Math.random() * 500) + 100,
        status: alert.status || 'OPEN',
        severity: alert.severity || 'MEDIUM'
    }));

    // Add risk classification
    allMesas.forEach(mesa => {
        if (mesa.ocrConfidence < 70) {
            mesa.riskLevel = 'high';
        } else if (mesa.ocrConfidence < 85) {
            mesa.riskLevel = 'medium';
        } else {
            mesa.riskLevel = 'low';
        }
    });
}

function generateMockRiskData() {
    // Generate additional mesa data if not enough
    if (allMesas.length < 10) {
        const puestos = ['I.E. San José', 'Coliseo Municipal', 'Casa de la Cultura', 'Centro Comunitario', 'Escuela Rural'];
        const locations = ['Cra 50 # 45-20', 'Calle 30 # 52-15', 'Av. Principal 80-45', 'Calle 10 Sur # 25-30', 'Vereda El Alto'];

        for (let i = allMesas.length; i < 25; i++) {
            const confidence = Math.max(40, Math.min(98, 70 + Math.random() * 30 - Math.random() * 30));
            allMesas.push({
                id: i + 1,
                mesaId: `Mesa ${i + 1}`,
                dept: 'Antioquia',
                muni: i % 3 === 0 ? 'Medellín' : (i % 3 === 1 ? 'Envigado' : 'Itagüí'),
                puesto: puestos[i % puestos.length],
                location: locations[i % locations.length],
                ocrConfidence: confidence,
                reason: confidence < 70 ? 'Imagen borrosa o dañada' : (confidence < 85 ? 'Algunos campos ilegibles' : 'Validación exitosa'),
                totalVotes: Math.floor(Math.random() * 500) + 100,
                status: confidence < 70 ? 'NEEDS_REVIEW' : 'VALIDATED',
                riskLevel: confidence < 70 ? 'high' : (confidence < 85 ? 'medium' : 'low')
            });
        }
    }

    // Generate mock witnesses
    const witnessNames = ['Carlos Rodríguez', 'María García', 'Juan López', 'Ana Martínez', 'Pedro Sánchez', 'Laura Torres', 'Diego Hernández', 'Carmen Gómez'];
    allWitnesses = witnessNames.map((name, i) => ({
        id: i + 1,
        name: name,
        phone: `300${Math.floor(Math.random() * 9000000) + 1000000}`,
        currentLocation: allMesas[i % allMesas.length]?.puesto || 'Sin ubicación',
        status: i % 4 === 0 ? 'busy' : 'available',
        distance: (Math.random() * 2).toFixed(1)
    }));
}

// ============================================================
// FILTERS
// ============================================================

function setupFilters() {
    ['filter-dept', 'filter-muni', 'filter-puesto', 'filter-mesa', 'filter-risk'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', () => {
                updateFilterState();
            });
        }
    });
}

function populateFilters() {
    // Get unique values from mesas
    const depts = [...new Set(allMesas.map(m => m.dept).filter(Boolean))];
    const munis = [...new Set(allMesas.map(m => m.muni).filter(Boolean))];
    const puestos = [...new Set(allMesas.map(m => m.puesto).filter(Boolean))];
    const mesaIds = [...new Set(allMesas.map(m => m.mesaId).filter(Boolean))];

    populateSelect('filter-dept', depts, 'Todos');
    populateSelect('filter-muni', munis, 'Todos');
    populateSelect('filter-puesto', puestos, 'Todos');
    populateSelect('filter-mesa', mesaIds, 'Todas');
}

function populateSelect(id, options, defaultLabel) {
    const select = document.getElementById(id);
    if (!select) return;

    const currentValue = select.value;
    select.innerHTML = `<option value="">${defaultLabel}</option>`;

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });

    select.value = currentValue;
}

function updateFilterState() {
    filters.dept = document.getElementById('filter-dept')?.value || '';
    filters.muni = document.getElementById('filter-muni')?.value || '';
    filters.puesto = document.getElementById('filter-puesto')?.value || '';
    filters.mesa = document.getElementById('filter-mesa')?.value || '';
    filters.risk = document.getElementById('filter-risk')?.value || '';
}

function applyFilters() {
    updateFilterState();
    renderContiendaTab();
}

function clearFilters() {
    ['filter-dept', 'filter-muni', 'filter-puesto', 'filter-mesa', 'filter-risk'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    filters = { dept: '', muni: '', puesto: '', mesa: '', risk: '' };
    renderContiendaTab();
}

function getFilteredMesas() {
    return allMesas.filter(mesa => {
        if (filters.dept && mesa.dept !== filters.dept) return false;
        if (filters.muni && mesa.muni !== filters.muni) return false;
        if (filters.puesto && mesa.puesto !== filters.puesto) return false;
        if (filters.mesa && mesa.mesaId !== filters.mesa) return false;
        if (filters.risk && mesa.riskLevel !== filters.risk) return false;
        return true;
    });
}

function getFilteredVotes() {
    return allVotes.filter(vote => {
        if (filters.dept && vote.dept !== filters.dept) return false;
        if (filters.muni && vote.muni !== filters.muni) return false;
        if (filters.risk && vote.riskLevel !== filters.risk) return false;
        return true;
    });
}

// Make functions global for onclick handlers
window.applyFilters = applyFilters;
window.clearFilters = clearFilters;

// ============================================================
// CONTIENDA ELECTORAL TAB
// ============================================================

function renderContiendaTab() {
    const filteredMesas = getFilteredMesas();
    const filteredVotes = getFilteredVotes();

    // Update KPIs
    updateContiendaKPIs(filteredMesas, filteredVotes);

    // Render tracked candidates
    renderTrackedCandidates();

    // Render charts
    renderPartyChart(filteredVotes);
    renderRiskDistributionChart(filteredMesas);

    // Render votes table
    renderVotesTable(filteredVotes);
}

function updateContiendaKPIs(mesas, votes) {
    const stats = window.dashboardStats || {};

    const totalMesas = mesas.length || stats.total_mesas || 0;
    const validated = mesas.filter(m => m.status === 'VALIDATED').length || stats.validated || 0;
    const needsReview = mesas.filter(m => m.status === 'NEEDS_REVIEW').length || stats.needs_review || 0;
    const highRisk = mesas.filter(m => m.riskLevel === 'high').length;
    const totalVotes = votes.reduce((sum, v) => sum + (v.total_votes || 0), 0) || stats.total_votes || 0;
    const coverage = totalMesas > 0 ? Math.round((validated / totalMesas) * 100) : 0;

    document.getElementById('kpi-total').textContent = formatNumber(totalMesas);
    document.getElementById('kpi-validated').textContent = formatNumber(validated);
    document.getElementById('kpi-review').textContent = formatNumber(needsReview);
    document.getElementById('kpi-high-risk').textContent = formatNumber(highRisk);
    document.getElementById('kpi-votes').textContent = formatNumber(totalVotes);
    document.getElementById('kpi-coverage').textContent = `${coverage}%`;
}

function renderPartyChart(votes) {
    const ctx = document.getElementById('party-chart')?.getContext('2d');
    if (!ctx) return;

    if (partyChart) partyChart.destroy();

    // Aggregate votes by party
    const partyVotes = {};
    votes.forEach(v => {
        const party = v.party_name || 'Independiente';
        partyVotes[party] = (partyVotes[party] || 0) + (v.total_votes || 0);
    });

    const labels = Object.keys(partyVotes).slice(0, 8);
    const data = labels.map(l => partyVotes[l]);
    const colors = generateGoldPalette(labels.length);

    partyChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels.map(l => truncateText(l, 20)),
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderColor: '#1C1C1C',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: '#E0DED8',
                        padding: 10,
                        font: { size: 10 }
                    }
                }
            }
        }
    });
}

function renderRiskDistributionChart(mesas) {
    const ctx = document.getElementById('risk-chart')?.getContext('2d');
    if (!ctx) return;

    if (riskChart) riskChart.destroy();

    const riskCounts = {
        high: mesas.filter(m => m.riskLevel === 'high').length,
        medium: mesas.filter(m => m.riskLevel === 'medium').length,
        low: mesas.filter(m => m.riskLevel === 'low').length
    };

    riskChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Alto (<70%)', 'Medio (70-85%)', 'Bajo (>85%)'],
            datasets: [{
                label: 'Mesas',
                data: [riskCounts.high, riskCounts.medium, riskCounts.low],
                backgroundColor: [
                    'rgba(139, 58, 58, 0.8)',
                    'rgba(212, 160, 23, 0.8)',
                    'rgba(74, 124, 89, 0.8)'
                ],
                borderColor: [
                    'rgba(139, 58, 58, 1)',
                    'rgba(212, 160, 23, 1)',
                    'rgba(74, 124, 89, 1)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            ...chartDefaults,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#9A8F7C' },
                    grid: { color: 'rgba(42, 42, 42, 0.5)' }
                },
                x: {
                    ticks: { color: '#9A8F7C' },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderVotesTable(votes) {
    const tbody = document.getElementById('votes-tbody');
    const countEl = document.getElementById('table-count');

    if (!tbody) return;

    if (votes.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--muted);">No hay datos disponibles</td></tr>';
        if (countEl) countEl.textContent = '0 registros';
        return;
    }

    const maxVotes = Math.max(...votes.map(v => v.total_votes || 0));

    tbody.innerHTML = votes.map(vote => {
        const confidence = vote.ocrConfidence || 85;
        const riskClass = vote.riskLevel || 'low';
        const riskLabel = riskClass === 'high' ? 'Alto' : (riskClass === 'medium' ? 'Medio' : 'Bajo');
        const percentage = vote.percentage || 0;
        const barWidth = maxVotes > 0 ? ((vote.total_votes || 0) / maxVotes * 100) : 0;

        return `
            <tr>
                <td class="party-name">${escapeHtml(vote.party_name || vote.candidate_name || '-')}</td>
                <td>${formatNumber(vote.total_votes || 0)}</td>
                <td>${percentage.toFixed(1)}%</td>
                <td class="vote-bar-cell">
                    <div class="vote-bar">
                        <div class="vote-bar-fill" style="width: ${barWidth}%"></div>
                    </div>
                </td>
                <td>${confidence.toFixed(0)}%</td>
                <td><span class="risk-badge ${riskClass}">${riskLabel}</span></td>
            </tr>
        `;
    }).join('');

    if (countEl) countEl.textContent = `${votes.length} registros`;
}

// ============================================================
// ZONAS DE RIESGO TAB
// ============================================================

function renderRiskZonesTab() {
    const highRisk = allMesas.filter(m => m.riskLevel === 'high');
    const mediumRisk = allMesas.filter(m => m.riskLevel === 'medium');
    const lowRisk = allMesas.filter(m => m.riskLevel === 'low');
    const pending = allMesas.filter(m => !m.riskLevel);

    // Update counts
    document.getElementById('risk-high-count').textContent = highRisk.length;
    document.getElementById('risk-medium-count').textContent = mediumRisk.length;
    document.getElementById('risk-low-count').textContent = lowRisk.length;
    document.getElementById('risk-pending-count').textContent = pending.length;

    // Update badge
    const badge = document.getElementById('risk-badge');
    if (badge && highRisk.length > 0) {
        badge.textContent = highRisk.length;
        badge.style.display = 'inline';
    }

    // Render high risk cards
    renderRiskCards('high-risk-grid', highRisk, 'high');

    // Render medium risk cards
    renderRiskCards('medium-risk-grid', mediumRisk, 'medium');
}

function renderRiskCards(containerId, mesas, riskLevel) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (mesas.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No hay mesas con este nivel de riesgo</p>
            </div>
        `;
        return;
    }

    container.innerHTML = mesas.slice(0, 12).map(mesa => `
        <div class="risk-card ${riskLevel}-risk">
            <div class="risk-card-header">
                <span class="risk-card-mesa">${escapeHtml(mesa.mesaId)}</span>
                <span class="risk-badge ${riskLevel}">${mesa.ocrConfidence.toFixed(0)}% OCR</span>
            </div>
            <div class="risk-card-location">${escapeHtml(mesa.puesto)} - ${escapeHtml(mesa.muni)}</div>
            <div class="risk-card-reason">${escapeHtml(mesa.reason)}</div>
            <div class="risk-card-stats">
                <span class="risk-card-stat">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                        <circle cx="12" cy="7" r="4"/>
                    </svg>
                    ${formatNumber(mesa.totalVotes)} votos
                </span>
                <span class="risk-card-stat">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                        <circle cx="12" cy="10" r="3"/>
                    </svg>
                    ${escapeHtml(mesa.location || 'Sin ubicación')}
                </span>
            </div>
            <div class="risk-card-actions">
                <button class="btn-action" onclick="viewMesaDetails(${mesa.id})">Ver Detalles</button>
                <button class="btn-action danger" onclick="selectMesaForWitness(${mesa.id})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07"/>
                    </svg>
                    Llamar Testigo
                </button>
            </div>
        </div>
    `).join('');
}

window.viewMesaDetails = function(mesaId) {
    const mesa = allMesas.find(m => m.id === mesaId);
    if (mesa) {
        alert(`Detalles de ${mesa.mesaId}:\n\nUbicación: ${mesa.puesto}, ${mesa.muni}\nDirección: ${mesa.location}\nConfianza OCR: ${mesa.ocrConfidence.toFixed(1)}%\nTotal votos: ${mesa.totalVotes}\nEstado: ${mesa.status}`);
    }
};

window.selectMesaForWitness = function(mesaId) {
    const mesa = allMesas.find(m => m.id === mesaId);
    if (mesa) {
        // Switch to witness tab
        document.querySelector('[data-tab="llamar-testigo"]').click();

        // Select the mesa
        setTimeout(() => {
            const select = document.getElementById('critical-mesa-select');
            if (select) {
                select.value = mesaId;
                onCriticalMesaSelect();
            }
        }, 100);
    }
};

// ============================================================
// LLAMAR TESTIGO TAB
// ============================================================

function setupCriticalMesaSelect() {
    const select = document.getElementById('critical-mesa-select');
    if (select) {
        select.addEventListener('change', onCriticalMesaSelect);
    }
}

function renderWitnessTab() {
    // Populate critical mesa dropdown with high-risk mesas
    const criticalMesas = allMesas.filter(m => m.riskLevel === 'high' || m.riskLevel === 'medium');
    const select = document.getElementById('critical-mesa-select');

    if (select) {
        select.innerHTML = '<option value="">-- Seleccione una mesa --</option>';
        criticalMesas.forEach(mesa => {
            const option = document.createElement('option');
            option.value = mesa.id;
            option.textContent = `${mesa.mesaId} - ${mesa.puesto} (${mesa.ocrConfidence.toFixed(0)}% OCR)`;
            select.appendChild(option);
        });
    }

    // Render call log
    renderCallLog();
}

function onCriticalMesaSelect() {
    const select = document.getElementById('critical-mesa-select');
    const mesaId = parseInt(select?.value);

    if (!mesaId) {
        document.getElementById('mesa-location').value = '';
        document.getElementById('witnesses-grid').innerHTML = '<div class="empty-state"><p>Seleccione una mesa crítica para ver testigos disponibles en la zona</p></div>';
        document.getElementById('witnesses-count').textContent = '-- testigos en la zona';
        selectedMesa = null;
        return;
    }

    selectedMesa = allMesas.find(m => m.id === mesaId);

    if (selectedMesa) {
        document.getElementById('mesa-location').value = `${selectedMesa.puesto}, ${selectedMesa.muni} - ${selectedMesa.location}`;
        renderNearbyWitnesses(selectedMesa);
    }
}

function renderNearbyWitnesses(mesa) {
    const container = document.getElementById('witnesses-grid');
    const countEl = document.getElementById('witnesses-count');

    // Filter witnesses by location (same puesto/municipality)
    const nearbyWitnesses = allWitnesses.filter(w =>
        w.currentLocation === mesa.puesto || Math.random() > 0.5
    );

    if (countEl) {
        countEl.textContent = `${nearbyWitnesses.length} testigos en la zona`;
    }

    if (nearbyWitnesses.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No hay testigos disponibles en esta zona</p></div>';
        return;
    }

    container.innerHTML = nearbyWitnesses.map(witness => `
        <div class="witness-card">
            <div class="witness-card-header">
                <span class="witness-name">${escapeHtml(witness.name)}</span>
                <span class="witness-status ${witness.status}">${witness.status === 'available' ? 'Disponible' : 'Ocupado'}</span>
            </div>
            <div class="witness-location">Ubicación actual: ${escapeHtml(witness.currentLocation)}</div>
            <div class="witness-distance">Distancia: ${witness.distance} km</div>
            <div class="witness-actions">
                <button class="btn-action" onclick="callWitness(${witness.id})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07"/>
                    </svg>
                    Llamar
                </button>
                <button class="btn-action primary" onclick="openCallModal(${witness.id})" ${witness.status === 'busy' ? 'disabled' : ''}>
                    Enviar a Mesa
                </button>
            </div>
        </div>
    `).join('');
}

window.callWitness = function(witnessId) {
    const witness = allWitnesses.find(w => w.id === witnessId);
    if (witness) {
        alert(`Llamando a ${witness.name}...\nTeléfono: ${witness.phone}`);
    }
};

window.openCallModal = function(witnessId) {
    selectedWitness = allWitnesses.find(w => w.id === witnessId);

    if (!selectedWitness || !selectedMesa) {
        alert('Seleccione una mesa y un testigo primero');
        return;
    }

    document.getElementById('modal-witness-name').textContent = selectedWitness.name;
    document.getElementById('modal-mesa-id').textContent = selectedMesa.mesaId;
    document.getElementById('modal-location').textContent = `${selectedMesa.puesto}, ${selectedMesa.muni}`;
    document.getElementById('call-message').value = '';

    document.getElementById('call-modal').classList.add('active');
};

window.closeCallModal = function() {
    document.getElementById('call-modal').classList.remove('active');
    selectedWitness = null;
};

window.confirmCall = function() {
    if (!selectedWitness || !selectedMesa) return;

    const message = document.getElementById('call-message').value;

    // Add to call log
    callLog.unshift({
        id: callLog.length + 1,
        timestamp: new Date(),
        mesa: selectedMesa.mesaId,
        witness: selectedWitness.name,
        status: 'enviado',
        message: message
    });

    // Update witness status
    selectedWitness.status = 'busy';

    // Close modal
    closeCallModal();

    // Refresh displays
    renderCallLog();
    if (selectedMesa) {
        renderNearbyWitnesses(selectedMesa);
    }

    alert(`Llamado enviado a ${selectedWitness.name} para ${selectedMesa.mesaId}`);
};

function renderCallLog() {
    const tbody = document.getElementById('call-log-tbody');
    if (!tbody) return;

    if (callLog.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--muted);">No hay llamados registrados</td></tr>';
        return;
    }

    tbody.innerHTML = callLog.map(call => `
        <tr>
            <td>${formatTime(call.timestamp)}</td>
            <td>${escapeHtml(call.mesa)}</td>
            <td>${escapeHtml(call.witness)}</td>
            <td><span class="risk-badge ${call.status === 'enviado' ? 'medium' : 'low'}">${call.status}</span></td>
            <td>
                <button class="btn-action" onclick="markCallComplete(${call.id})">Completar</button>
            </td>
        </tr>
    `).join('');
}

window.markCallComplete = function(callId) {
    const call = callLog.find(c => c.id === callId);
    if (call) {
        call.status = 'completado';
        renderCallLog();
    }
};

// ============================================================
// TABLE SORTING
// ============================================================

function setupTableSorting() {
    document.querySelectorAll('.votes-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            sortVotesTable(sortKey, th);
        });
    });
}

let currentSort = { key: null, asc: true };

function sortVotesTable(key, th) {
    // Toggle sort direction
    if (currentSort.key === key) {
        currentSort.asc = !currentSort.asc;
    } else {
        currentSort.key = key;
        currentSort.asc = true;
    }

    // Update visual indicators
    document.querySelectorAll('.votes-table th.sortable').forEach(t => {
        t.classList.remove('sorted');
    });
    th.classList.add('sorted');
    th.querySelector('.sort-icon').textContent = currentSort.asc ? '↑' : '↓';

    // Sort the data
    const sortedVotes = [...getFilteredVotes()].sort((a, b) => {
        let valA, valB;

        switch (key) {
            case 'party':
                valA = (a.party_name || a.candidate_name || '').toLowerCase();
                valB = (b.party_name || b.candidate_name || '').toLowerCase();
                break;
            case 'votes':
                valA = a.total_votes || 0;
                valB = b.total_votes || 0;
                break;
            case 'percentage':
                valA = a.percentage || 0;
                valB = b.percentage || 0;
                break;
            case 'confidence':
                valA = a.ocrConfidence || 0;
                valB = b.ocrConfidence || 0;
                break;
            default:
                return 0;
        }

        if (valA < valB) return currentSort.asc ? -1 : 1;
        if (valA > valB) return currentSort.asc ? 1 : -1;
        return 0;
    });

    renderVotesTable(sortedVotes);
}

// ============================================================
// REAL-TIME REFRESH
// ============================================================

function startRealTimeRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);

    refreshInterval = setInterval(() => {
        const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab || 'contienda';

        // Auto-refresh contienda tab
        if (activeTab === 'contienda') {
            loadDashboardData();
        }
    }, REFRESH_INTERVAL_MS);
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function showLoading(show) {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.classList.toggle('active', show);
    }
}

function showError(message) {
    console.error(message);
    // Could show a toast notification here
}

function updateTimestamp() {
    const el = document.getElementById('last-update-time');
    if (el) {
        const now = new Date();
        el.textContent = now.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    }
}

function formatNumber(num) {
    if (num === null || num === undefined) return '--';
    return new Intl.NumberFormat('es-CO').format(num);
}

function formatTime(date) {
    if (!date) return '--';
    return new Date(date).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function generateGoldPalette(count) {
    const baseColors = [
        'rgba(201, 162, 39, 0.8)',
        'rgba(212, 175, 55, 0.8)',
        'rgba(232, 212, 138, 0.8)',
        'rgba(139, 115, 85, 0.8)',
        'rgba(74, 124, 89, 0.8)',
        'rgba(91, 142, 255, 0.8)',
        'rgba(139, 58, 58, 0.7)',
        'rgba(212, 160, 23, 0.8)'
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// ============================================================
// CANDIDATOS EN SEGUIMIENTO
// ============================================================

const trackedCandidates = [
    {
        id: 1,
        name: "Paloma Valencia",
        party: "Centro Democrático",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 2,
        name: "Vicky Dávila",
        party: "Independiente",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 3,
        name: "Juan Carlos Pinzón",
        party: "Coalición",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 4,
        name: "David Luna",
        party: "Cambio Radical",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 5,
        name: "Mauricio Cárdenas",
        party: "Partido Liberal",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 6,
        name: "Juan Manuel Galán",
        party: "Nuevo Liberalismo",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 7,
        name: "Juan Daniel Oviedo",
        party: "Independiente",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 8,
        name: "Aníbal Gaviria",
        party: "Partido Liberal",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    }
];

function renderTrackedCandidates() {
    const grid = document.getElementById('candidates-tracking-grid');
    if (!grid) return;

    // Simulate some initial data (this would come from real E-14 processing)
    simulateCandidateData();

    // Sort by votes descending
    const sortedCandidates = [...trackedCandidates].sort((a, b) => b.votes - a.votes);

    // Assign positions
    sortedCandidates.forEach((c, i) => {
        const original = trackedCandidates.find(tc => tc.id === c.id);
        if (original) original.position = i + 1;
    });

    grid.innerHTML = trackedCandidates.map(candidate => {
        const positionClass = candidate.position <= 3 ? 'top-3' : '';
        const cardClass = candidate.position === 1 ? 'leading' :
                         (candidate.position <= 3 ? '' :
                         (candidate.position >= 7 ? 'danger' : 'warning'));

        const trendIcon = candidate.trend === 'up' ? '↑' :
                         (candidate.trend === 'down' ? '↓' : '→');
        const trendText = candidate.trend === 'up' ? `+${candidate.trendValue}%` :
                         (candidate.trend === 'down' ? `${candidate.trendValue}%` : 'Estable');

        const maxVotes = Math.max(...trackedCandidates.map(c => c.votes));
        const progressWidth = maxVotes > 0 ? (candidate.votes / maxVotes * 100) : 0;

        return `
            <div class="candidate-track-card ${cardClass}">
                <div class="candidate-track-header">
                    <div>
                        <div class="candidate-track-name">${escapeHtml(candidate.name)}</div>
                        <div class="candidate-track-party">${escapeHtml(candidate.party)}</div>
                    </div>
                    <span class="candidate-track-position ${positionClass}">#${candidate.position || '--'}</span>
                </div>

                <div class="candidate-track-stats">
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${formatNumber(candidate.votes)}</div>
                        <div class="candidate-stat-label">Votos</div>
                    </div>
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${candidate.percentage.toFixed(1)}%</div>
                        <div class="candidate-stat-label">Porcentaje</div>
                    </div>
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${candidate.mesas}</div>
                        <div class="candidate-stat-label">Mesas</div>
                    </div>
                </div>

                <div class="candidate-track-progress">
                    <div class="candidate-progress-bar">
                        <div class="candidate-progress-fill" style="width: ${progressWidth}%"></div>
                    </div>
                    <div class="candidate-progress-labels">
                        <span>0</span>
                        <span>${formatNumber(maxVotes)}</span>
                    </div>
                </div>

                <div class="candidate-trend ${candidate.trend}">
                    <span>${trendIcon}</span>
                    <span>${trendText}</span>
                </div>
            </div>
        `;
    }).join('');
}

function simulateCandidateData() {
    // Simulate realistic vote data for tracked candidates
    // In production, this would match against E-14 extractions
    const baseVotes = [
        { name: "Paloma Valencia", votes: 15420, percentage: 18.5, mesas: 42, trend: 'up', trendValue: 2.3 },
        { name: "Vicky Dávila", votes: 12890, percentage: 15.4, mesas: 38, trend: 'up', trendValue: 1.8 },
        { name: "Juan Carlos Pinzón", votes: 11250, percentage: 13.5, mesas: 35, trend: 'stable', trendValue: 0 },
        { name: "David Luna", votes: 9870, percentage: 11.8, mesas: 32, trend: 'down', trendValue: -0.5 },
        { name: "Mauricio Cárdenas", votes: 8540, percentage: 10.2, mesas: 28, trend: 'up', trendValue: 0.8 },
        { name: "Juan Manuel Galán", votes: 7920, percentage: 9.5, mesas: 26, trend: 'stable', trendValue: 0 },
        { name: "Juan Daniel Oviedo", votes: 6350, percentage: 7.6, mesas: 22, trend: 'down', trendValue: -1.2 },
        { name: "Aníbal Gaviria", votes: 5890, percentage: 7.1, mesas: 20, trend: 'up', trendValue: 0.4 }
    ];

    baseVotes.forEach(data => {
        const candidate = trackedCandidates.find(c => c.name === data.name);
        if (candidate) {
            // Add some randomness to simulate live updates
            const variance = Math.random() * 0.1 - 0.05; // ±5%
            candidate.votes = Math.round(data.votes * (1 + variance));
            candidate.percentage = data.percentage * (1 + variance);
            candidate.mesas = data.mesas;
            candidate.trend = data.trend;
            candidate.trendValue = data.trendValue;
        }
    });
}

function updateTrackedCandidatesFromE14(e14Candidates) {
    // Match E-14 candidates with tracked candidates
    if (!e14Candidates) return;

    // In a real implementation, we would match by candidate name/number
    // For now, just trigger a re-render
    renderTrackedCandidates();
}

// ============================================================
// E-14 LIVE FORM RENDERING
// ============================================================

let currentE14Data = null;
let previousCandidates = {};

function renderE14LiveForm(data) {
    const container = document.getElementById('e14-form-container');
    if (!container) return;

    if (!data.forms || data.forms.length === 0) {
        renderE14Empty();
        return;
    }

    // Use the first form (most recent)
    const form = data.forms[0];
    currentE14Data = form;

    // Update header
    document.getElementById('e14-election-name').textContent =
        `${form.header.corporacion || 'CÁMARA'} - ${form.header.election_name || 'Elecciones'}`;
    document.getElementById('e14-mesa').textContent = form.header.mesa || '--';
    document.getElementById('e14-zona').textContent = form.header.zona || '--';

    // Update confidence with color class
    const confidenceEl = document.getElementById('e14-confidence');
    const confidence = (form.overall_confidence || 0.85) * 100;
    confidenceEl.textContent = `${confidence.toFixed(0)}%`;
    confidenceEl.className = 'e14-meta-value e14-confidence';
    if (confidence < 70) confidenceEl.classList.add('low');
    else if (confidence < 85) confidenceEl.classList.add('medium');

    // Update location
    document.getElementById('e14-dept').textContent = form.header.departamento || '--';
    document.getElementById('e14-muni').textContent = form.header.municipio || '--';
    document.getElementById('e14-puesto').textContent = form.header.puesto || '--';
    document.getElementById('e14-date').textContent = form.header.election_date || '--';

    // Update nivelación
    document.getElementById('e14-sufragantes').textContent =
        formatNumber(form.nivelacion.total_sufragantes);
    document.getElementById('e14-urna').textContent =
        formatNumber(form.nivelacion.total_votos_urna);
    document.getElementById('e14-validos').textContent =
        formatNumber(form.resumen.total_votos_validos);
    document.getElementById('e14-blancos').textContent =
        formatNumber(form.resumen.votos_blanco);
    document.getElementById('e14-nulos').textContent =
        formatNumber(form.resumen.votos_nulos);

    // Render candidates
    renderE14Candidates(form.candidates);

    // Update footer
    const extractedAt = form.extracted_at ? new Date(form.extracted_at).toLocaleString('es-CO') : '--';
    const processingTime = form.processing_time_ms ? `${(form.processing_time_ms / 1000).toFixed(1)}s` : '--';
    document.getElementById('e14-extraction-info').textContent =
        `Extraído: ${extractedAt} | Procesamiento: ${processingTime}`;

    // Update E-14 timestamp
    const e14TimeEl = document.getElementById('e14-update-time');
    if (e14TimeEl) {
        e14TimeEl.textContent = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    }
}

function renderE14Candidates(candidates) {
    const grid = document.getElementById('e14-candidates-grid');
    if (!grid) return;

    if (!candidates || candidates.length === 0) {
        grid.innerHTML = '<div class="e14-empty">No hay candidatos registrados</div>';
        return;
    }

    grid.innerHTML = candidates.map((candidate, index) => {
        const confidence = (candidate.confidence || 0.85) * 100;
        const confidenceClass = confidence < 70 ? 'low' : (confidence < 85 ? 'medium' : 'high');
        const needsReview = candidate.needs_review ? 'needs-review' : '';

        // Check if this candidate was updated (vote count changed)
        const prevVotes = previousCandidates[candidate.candidate_number];
        const wasUpdated = prevVotes !== undefined && prevVotes !== candidate.votes;
        const updatedClass = wasUpdated ? 'updated' : '';

        // Store current votes for next comparison
        previousCandidates[candidate.candidate_number] = candidate.votes;

        const displayName = candidate.is_party_vote
            ? `<strong>${truncateText(candidate.party_name, 40)}</strong> (Lista)`
            : `#${candidate.candidate_number}`;

        return `
            <div class="e14-candidate-row ${needsReview} ${updatedClass}">
                <div class="e14-candidate-info">
                    <span class="e14-candidate-name">${displayName}</span>
                    ${!candidate.is_party_vote ? `<span class="e14-candidate-party">${truncateText(candidate.party_name, 35)}</span>` : ''}
                </div>
                <div class="e14-candidate-votes">${formatNumber(candidate.votes)}</div>
                <div class="e14-candidate-ocr">
                    <div class="e14-ocr-bar">
                        <div class="e14-ocr-fill ${confidenceClass}" style="width: ${confidence}%"></div>
                    </div>
                    <span class="e14-ocr-value">${confidence.toFixed(0)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function renderE14Empty() {
    const grid = document.getElementById('e14-candidates-grid');
    if (grid) {
        grid.innerHTML = `
            <div class="e14-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 1rem; opacity: 0.5;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                </svg>
                <p>No hay extracciones E-14 disponibles</p>
                <p style="font-size: 0.8rem; margin-top: 0.5rem;">Procese un formulario E-14 para ver los datos aquí</p>
            </div>
        `;
    }

    // Clear header values
    document.getElementById('e14-election-name').textContent = 'Sin datos';
    document.getElementById('e14-mesa').textContent = '--';
    document.getElementById('e14-zona').textContent = '--';
    document.getElementById('e14-confidence').textContent = '--%';
}

async function refreshE14Data() {
    const container = document.getElementById('e14-form-container');
    if (container) {
        container.classList.add('updating');
    }

    try {
        const response = await fetch('/api/campaign-team/e14-live');
        const data = await response.json();

        if (data.success) {
            renderE14LiveForm(data);
        }
    } catch (error) {
        console.error('Error refreshing E-14 data:', error);
    } finally {
        if (container) {
            setTimeout(() => {
                container.classList.remove('updating');
            }, 500);
        }
    }
}

// Make refresh function global
window.refreshE14Data = refreshE14Data;

// Auto-refresh E-14 data every 15 seconds
setInterval(() => {
    const activeTab = document.querySelector('.tab-btn.active')?.dataset.tab;
    if (activeTab === 'contienda') {
        refreshE14Data();
    }
}, 15000);

// ============================================================
// INCIDENT QUEUE FUNCTIONALITY
// ============================================================

let allIncidents = [];
let incidentFilter = 'all';
let selectedIncidentId = null;
let timelineCountdown = 30;

// Initialize incident queue on page load
document.addEventListener('DOMContentLoaded', () => {
    setupIncidentFilters();
    loadIncidents();
    loadWarRoomKPIs();
    startTimelineCountdown();
});

function setupIncidentFilters() {
    document.querySelectorAll('.incident-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            document.querySelectorAll('.incident-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update filter and re-render
            incidentFilter = btn.dataset.filter;
            renderIncidentTable();
        });
    });
}

async function loadIncidents() {
    try {
        const response = await fetch('/api/incidents?status=OPEN,ASSIGNED&limit=50');
        const data = await response.json();

        if (data.success) {
            allIncidents = data.incidents || [];
            updateIncidentStats(data);
            renderIncidentTable();
        }
    } catch (error) {
        console.error('Error loading incidents:', error);
        document.getElementById('incident-tbody').innerHTML =
            '<tr><td colspan="7" style="text-align: center; color: var(--muted);">Error cargando incidentes</td></tr>';
    }
}

async function loadWarRoomKPIs() {
    try {
        const response = await fetch('/api/incidents/war-room/kpis');
        const data = await response.json();

        if (data.success) {
            updateWarRoomKPIs(data.kpis);
            updateTimeline(data.timeline, data.kpis);
        }
    } catch (error) {
        console.error('Error loading War Room KPIs:', error);
    }
}

function updateWarRoomKPIs(kpis) {
    document.getElementById('kpi-total').textContent = formatNumber(kpis.mesas_total);
    document.getElementById('kpi-testigo').textContent = formatNumber(kpis.mesas_testigo);
    document.getElementById('kpi-rnec').textContent = formatNumber(kpis.mesas_rnec);
    document.getElementById('kpi-reconciled').textContent = formatNumber(kpis.mesas_reconciliadas);
    document.getElementById('kpi-p0').textContent = kpis.incidentes_p0;
    document.getElementById('kpi-coverage').textContent = `${kpis.cobertura_pct}%`;
}

function updateTimeline(timeline, kpis) {
    // Update progress bars
    document.getElementById('timeline-testigo-bar').style.width = `${kpis.testigo_pct}%`;
    document.getElementById('timeline-testigo-pct').textContent = `${kpis.testigo_pct}%`;

    document.getElementById('timeline-rnec-bar').style.width = `${kpis.rnec_pct}%`;
    document.getElementById('timeline-rnec-pct').textContent = `${kpis.rnec_pct}%`;

    document.getElementById('timeline-reconciled-bar').style.width = `${kpis.reconciliadas_pct}%`;
    document.getElementById('timeline-reconciled-pct').textContent = `${kpis.reconciliadas_pct}%`;

    // Update last RNEC update time
    if (kpis.last_rnec_update) {
        const lastUpdate = new Date(kpis.last_rnec_update);
        document.getElementById('timeline-last-rnec').textContent =
            lastUpdate.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    }
}

function startTimelineCountdown() {
    setInterval(() => {
        timelineCountdown--;
        if (timelineCountdown <= 0) {
            timelineCountdown = 30;
            loadWarRoomKPIs();
            loadIncidents();
        }
        document.getElementById('timeline-countdown').textContent = `${timelineCountdown}s`;
    }, 1000);
}

function updateIncidentStats(data) {
    document.getElementById('incident-p0-count').textContent = data.p0_count || 0;
    document.getElementById('incident-p1-count').textContent = data.p1_count || 0;
    document.getElementById('incident-total-count').textContent = data.open_count || 0;
}

function renderIncidentTable() {
    const tbody = document.getElementById('incident-tbody');
    if (!tbody) return;

    // Filter incidents
    let filtered = [...allIncidents];
    if (incidentFilter !== 'all') {
        if (['P0', 'P1', 'P2', 'P3'].includes(incidentFilter)) {
            filtered = filtered.filter(i => i.severity === incidentFilter);
        } else if (['OPEN', 'ASSIGNED', 'INVESTIGATING'].includes(incidentFilter)) {
            filtered = filtered.filter(i => i.status === incidentFilter);
        }
    }

    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">No hay incidentes con este filtro</td></tr>';
        return;
    }

    tbody.innerHTML = filtered.map(incident => {
        const slaClass = getSlaClass(incident.sla_remaining_minutes);
        const slaText = formatSlaTime(incident.sla_remaining_minutes);
        const confidenceText = incident.ocr_confidence
            ? `${(incident.ocr_confidence * 100).toFixed(0)}%`
            : '--';

        return `
            <tr onclick="openIncidentDetail(${incident.id})" style="cursor: pointer;">
                <td>
                    <span class="severity-badge ${incident.severity.toLowerCase()}">${incident.severity}</span>
                </td>
                <td class="incident-mesa">${escapeHtml(incident.mesa_id)}</td>
                <td>
                    <span class="incident-type">${formatIncidentType(incident.incident_type)}</span>
                </td>
                <td>${escapeHtml(incident.dept_name || incident.dept_code)}</td>
                <td>${confidenceText}</td>
                <td>
                    <span class="incident-sla ${slaClass}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"/>
                            <polyline points="12 6 12 12 16 14"/>
                        </svg>
                        ${slaText}
                    </span>
                </td>
                <td>
                    <div class="incident-actions" onclick="event.stopPropagation();">
                        <button class="incident-action-btn" onclick="openMesaDetail('${incident.mesa_id}')" title="Ver detalle de mesa">Mesa</button>
                        <button class="incident-action-btn primary" onclick="openIncidentDetail(${incident.id})">Ver</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function getSlaClass(minutes) {
    if (minutes === null || minutes === undefined) return 'ok';
    if (minutes <= 5) return 'urgent';
    if (minutes <= 10) return 'warning';
    return 'ok';
}

function formatSlaTime(minutes) {
    if (minutes === null || minutes === undefined) return '--';
    if (minutes <= 0) return 'VENCIDO';
    if (minutes < 60) return `${minutes}m`;
    return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

function formatIncidentType(type) {
    const typeMap = {
        'OCR_LOW_CONF': 'OCR Bajo',
        'ARITHMETIC_FAIL': 'Error Suma',
        'E11_VS_URNA': 'E11≠Urna',
        'RECOUNT_MARKED': 'Recuento',
        'SIGNATURE_MISSING': 'Sin Firma',
        'RNEC_DELAY': 'RNEC Delay',
        'DISCREPANCY_RNEC': 'Δ RNEC',
        'SOURCE_MISMATCH': 'T≠Oficial'
    };
    return typeMap[type] || type;
}

// Incident Modal Functions
window.openIncidentDetail = async function(incidentId) {
    selectedIncidentId = incidentId;
    const incident = allIncidents.find(i => i.id === incidentId);

    if (!incident) {
        console.error('Incident not found:', incidentId);
        return;
    }

    // Populate modal
    document.getElementById('incident-modal-id').textContent = `#${incident.id}`;
    document.getElementById('incident-modal-severity').textContent = incident.severity;
    document.getElementById('incident-modal-severity').className = `severity-badge ${incident.severity.toLowerCase()}`;
    document.getElementById('incident-modal-type').textContent = incident.incident_type;
    document.getElementById('incident-modal-mesa').textContent = incident.mesa_id;
    document.getElementById('incident-modal-location').textContent =
        `${incident.dept_name || incident.dept_code} > ${incident.muni_name || incident.muni_code || '--'} > ${incident.puesto || '--'}`;
    document.getElementById('incident-modal-description').textContent = incident.description;
    document.getElementById('incident-modal-confidence').textContent =
        incident.ocr_confidence ? `${(incident.ocr_confidence * 100).toFixed(0)}%` : 'N/A';
    document.getElementById('incident-modal-sla').textContent = formatSlaTime(incident.sla_remaining_minutes);
    document.getElementById('incident-modal-status').textContent = incident.status;
    document.getElementById('incident-notes').value = incident.resolution_notes || '';

    // Show modal
    document.getElementById('incident-modal').classList.add('active');
};

window.closeIncidentModal = function() {
    document.getElementById('incident-modal').classList.remove('active');
    selectedIncidentId = null;
};

window.assignIncident = async function() {
    if (!selectedIncidentId) return;

    const notes = document.getElementById('incident-notes').value;
    const userId = 'current_user'; // In production, get from session

    try {
        const response = await fetch(`/api/incidents/${selectedIncidentId}/assign`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, notes: notes })
        });

        const data = await response.json();
        if (data.success) {
            closeIncidentModal();
            loadIncidents();
            alert('Incidente asignado correctamente');
        } else {
            alert('Error asignando incidente: ' + data.error);
        }
    } catch (error) {
        console.error('Error assigning incident:', error);
        alert('Error de conexión');
    }
};

window.resolveIncident = async function() {
    if (!selectedIncidentId) return;

    const notes = document.getElementById('incident-notes').value;
    if (!notes.trim()) {
        alert('Por favor agregue notas de resolución');
        return;
    }

    try {
        const response = await fetch(`/api/incidents/${selectedIncidentId}/resolve`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ resolution: 'RESOLVED', notes: notes })
        });

        const data = await response.json();
        if (data.success) {
            closeIncidentModal();
            loadIncidents();
            alert('Incidente resuelto correctamente');
        } else {
            alert('Error resolviendo incidente: ' + data.error);
        }
    } catch (error) {
        console.error('Error resolving incident:', error);
        alert('Error de conexión');
    }
};

window.escalateIncident = async function() {
    if (!selectedIncidentId) return;

    const reason = prompt('Razón para escalar el incidente:');
    if (!reason) return;

    const toLegal = confirm('¿Escalar a equipo legal?');

    try {
        const response = await fetch(`/api/incidents/${selectedIncidentId}/escalate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ reason: reason, to_legal: toLegal })
        });

        const data = await response.json();
        if (data.success) {
            closeIncidentModal();
            loadIncidents();
            alert('Incidente escalado correctamente');
        } else {
            alert('Error escalando incidente: ' + data.error);
        }
    } catch (error) {
        console.error('Error escalating incident:', error);
        alert('Error de conexión');
    }
};

window.refreshIncidents = function() {
    loadIncidents();
    loadWarRoomKPIs();
    timelineCountdown = 30;
};

// ============================================================
// CHOROPLETH MAP FUNCTIONALITY
// ============================================================

let colombiaMap = null;
let geoJsonLayer = null;
let currentMapMode = 'coverage';
let selectedDepartment = null;

// Initialize map when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initColombiaMap();
    setupMapModeSelector();
});

function initColombiaMap() {
    const mapContainer = document.getElementById('colombia-map');
    if (!mapContainer) return;

    // Initialize Leaflet map centered on Colombia
    colombiaMap = L.map('colombia-map', {
        center: [4.5, -74.0],
        zoom: 5,
        zoomControl: true,
        attributionControl: false,
        scrollWheelZoom: true
    });

    // Add dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        opacity: 0.7
    }).addTo(colombiaMap);

    // Load choropleth data
    loadChoroplethData('coverage');
}

function setupMapModeSelector() {
    document.querySelectorAll('.map-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            document.querySelectorAll('.map-mode-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update mode and reload data
            currentMapMode = btn.dataset.mode;
            loadChoroplethData(currentMapMode);
            updateMapLegend(currentMapMode);
        });
    });
}

async function loadChoroplethData(mode) {
    try {
        const response = await fetch(`/api/geography/choropleth?mode=${mode}`);
        const data = await response.json();

        if (data.success) {
            renderChoropleth(data);
        } else {
            console.error('Error loading choropleth:', data.error);
        }
    } catch (error) {
        console.error('Error fetching choropleth data:', error);
    }
}

function renderChoropleth(data) {
    if (!colombiaMap) return;

    // Remove existing layer
    if (geoJsonLayer) {
        colombiaMap.removeLayer(geoJsonLayer);
    }

    // Create new GeoJSON layer
    geoJsonLayer = L.geoJSON(data, {
        style: styleFeature,
        onEachFeature: onEachFeature
    }).addTo(colombiaMap);

    // Fit bounds
    if (geoJsonLayer.getBounds().isValid()) {
        colombiaMap.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    }
}

function styleFeature(feature) {
    return {
        fillColor: feature.properties.fill_color || '#555',
        weight: 1,
        opacity: 1,
        color: '#333',
        fillOpacity: 0.75
    };
}

function onEachFeature(feature, layer) {
    const props = feature.properties;
    const metrics = props.metrics || {};

    // Tooltip
    const tooltipContent = `
        <strong>${props.name}</strong><br>
        ${getModeLabel(currentMapMode)}: ${metrics.value?.toFixed(1) || '--'}%<br>
        Mesas: ${metrics.mesas_total || 0}
    `;
    layer.bindTooltip(tooltipContent, {
        permanent: false,
        direction: 'top',
        className: 'map-tooltip'
    });

    // Click handler
    layer.on('click', () => {
        selectDepartment(props.code, props.name);
    });

    // Hover effects
    layer.on('mouseover', (e) => {
        e.target.setStyle({
            weight: 3,
            color: '#C9A227',
            fillOpacity: 0.9
        });
    });

    layer.on('mouseout', (e) => {
        geoJsonLayer.resetStyle(e.target);
        if (selectedDepartment === props.code) {
            e.target.setStyle({
                weight: 3,
                color: '#C9A227'
            });
        }
    });
}

function getModeLabel(mode) {
    const labels = {
        'coverage': 'Cobertura',
        'risk': 'Riesgo',
        'discrepancy': 'Discrepancia',
        'votes': 'Votos'
    };
    return labels[mode] || mode;
}

function updateMapLegend(mode) {
    const legend = document.getElementById('map-legend');
    if (!legend) return;

    if (mode === 'coverage') {
        legend.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background: #4A7C59;"></span> Alto (>80%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #7CB342;"></span> Medio-Alto (60-80%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #D4A017;"></span> Medio (40-60%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #E65100;"></span> Bajo (20-40%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #8B3A3A;"></span> Crítico (<20%)</div>
        `;
    } else if (mode === 'risk') {
        legend.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background: #4A7C59;"></span> Bajo (<2%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #7CB342;"></span> Moderado (2-5%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #D4A017;"></span> Medio (5-10%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #E65100;"></span> Alto (10-15%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #8B3A3A;"></span> Crítico (>15%)</div>
        `;
    } else if (mode === 'discrepancy') {
        legend.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background: #4A7C59;"></span> Sin Δ (<2%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #7CB342;"></span> Bajo (2-5%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #D4A017;"></span> Medio (5-10%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #E65100;"></span> Alto (>10%)</div>
        `;
    } else if (mode === 'votes') {
        legend.innerHTML = `
            <div class="legend-item"><span class="legend-color" style="background: #7B1FA2;"></span> Líder (>30%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #9C27B0;"></span> Fuerte (20-30%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #BA68C8;"></span> Competitivo (15-20%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #CE93D8;"></span> Moderado (10-15%)</div>
            <div class="legend-item"><span class="legend-color" style="background: #E1BEE7;"></span> Bajo (<10%)</div>
        `;
    }
}

async function selectDepartment(deptCode, deptName) {
    selectedDepartment = deptCode;

    // Update panel header
    document.getElementById('dept-panel-title').textContent = deptName;
    document.getElementById('dept-panel-subtitle').textContent = `Código: ${deptCode}`;

    // Show loading
    const content = document.getElementById('dept-info-content');
    content.innerHTML = '<div class="dept-info-empty"><div class="loading-spinner" style="width: 32px; height: 32px;"></div><p>Cargando datos...</p></div>';

    try {
        // Fetch stats and incidents in parallel
        const [statsResponse, incidentsResponse] = await Promise.all([
            fetch(`/api/geography/department/${deptCode}/stats`),
            fetch(`/api/geography/department/${deptCode}/incidents?limit=5`)
        ]);

        const statsData = await statsResponse.json();
        const incidentsData = await incidentsResponse.json();

        if (statsData.success && incidentsData.success) {
            renderDepartmentInfo(statsData.stats, incidentsData.incidents);
        } else {
            content.innerHTML = '<div class="dept-info-empty"><p>Error cargando datos del departamento</p></div>';
        }
    } catch (error) {
        console.error('Error loading department data:', error);
        content.innerHTML = '<div class="dept-info-empty"><p>Error de conexión</p></div>';
    }
}

function renderDepartmentInfo(stats, incidents) {
    const content = document.getElementById('dept-info-content');

    const p0Class = stats.incidents_p0 > 0 ? 'danger' : '';
    const coverageClass = stats.coverage_pct >= 70 ? 'success' : (stats.coverage_pct >= 40 ? 'warning' : 'danger');
    const riskClass = stats.high_risk_count > 5 ? 'danger' : (stats.high_risk_count > 2 ? 'warning' : 'success');

    content.innerHTML = `
        <div class="dept-kpis">
            <div class="dept-kpi">
                <div class="dept-kpi-value">${formatNumber(stats.mesas_total)}</div>
                <div class="dept-kpi-label">Mesas Total</div>
            </div>
            <div class="dept-kpi">
                <div class="dept-kpi-value ${coverageClass}">${stats.coverage_pct}%</div>
                <div class="dept-kpi-label">Cobertura</div>
            </div>
            <div class="dept-kpi">
                <div class="dept-kpi-value">${formatNumber(stats.mesas_testigo)}</div>
                <div class="dept-kpi-label">Testigo</div>
            </div>
            <div class="dept-kpi">
                <div class="dept-kpi-value">${formatNumber(stats.mesas_rnec)}</div>
                <div class="dept-kpi-label">RNEC</div>
            </div>
            <div class="dept-kpi">
                <div class="dept-kpi-value ${riskClass}">${stats.high_risk_count}</div>
                <div class="dept-kpi-label">Alto Riesgo</div>
            </div>
            <div class="dept-kpi">
                <div class="dept-kpi-value ${p0Class}">${stats.incidents_p0}</div>
                <div class="dept-kpi-label">P0 Abiertos</div>
            </div>
        </div>

        <div class="dept-section-title">Incidentes Activos</div>
        <div class="dept-incidents-list">
            ${incidents.length > 0 ? incidents.map(inc => `
                <div class="dept-incident-item" style="cursor: pointer;" onclick="openMesaDetailFromIncident('${inc.mesa_id}')">
                    <span class="severity-badge ${inc.severity.toLowerCase()}">${inc.severity}</span>
                    <span class="dept-incident-mesa">${inc.mesa_id}</span>
                    <span class="dept-incident-type">${formatIncidentType(inc.incident_type)}</span>
                </div>
            `).join('') : '<div style="color: var(--muted); font-size: 0.75rem; padding: 0.5rem;">Sin incidentes activos</div>'}
        </div>

        <div class="dept-section-title">Top Candidatos</div>
        <div class="dept-incidents-list">
            ${stats.top_candidates ? stats.top_candidates.map((c, i) => `
                <div class="dept-incident-item">
                    <span style="font-weight: 700; color: var(--accent); width: 20px;">#${i + 1}</span>
                    <span class="dept-incident-mesa">${c.name}</span>
                    <span class="dept-incident-type">${c.percentage}%</span>
                </div>
            `).join('') : ''}
        </div>
    `;
}

// ============================================================
// MESA DETAIL MODAL FUNCTIONALITY
// ============================================================

let currentMesaDetail = null;

window.openMesaDetailFromIncident = function(mesaId) {
    openMesaDetail(mesaId);
};

async function openMesaDetail(mesaId) {
    currentMesaDetail = null;

    // Show modal with loading state
    document.getElementById('mesa-detail-modal').classList.add('active');
    document.getElementById('mesa-detail-id').textContent = mesaId;
    document.getElementById('mesa-detail-location').textContent = 'Cargando...';
    document.getElementById('mesa-detail-status').textContent = '...';
    document.getElementById('mesa-detail-confidence').textContent = '--%';
    document.getElementById('mesa-ocr-fields').innerHTML = '<div style="color: var(--muted); text-align: center; padding: 1rem;">Cargando...</div>';
    document.getElementById('mesa-validations').innerHTML = '<div style="color: var(--muted); text-align: center; padding: 1rem;">Cargando...</div>';
    document.getElementById('mesa-comparison-body').innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--muted);">Cargando...</td></tr>';
    document.getElementById('mesa-incidents-list').innerHTML = '<div style="color: var(--muted); font-size: 0.8rem;">Cargando...</div>';

    try {
        const response = await fetch(`/api/campaign-team/mesa/${mesaId}/detail`);
        const data = await response.json();

        if (data.success) {
            currentMesaDetail = data.detail;
            renderMesaDetail(data.detail);
        } else {
            alert('Error cargando detalles de la mesa: ' + data.error);
            closeMesaDetailModal();
        }
    } catch (error) {
        console.error('Error loading mesa detail:', error);
        alert('Error de conexión');
        closeMesaDetailModal();
    }
}

window.closeMesaDetailModal = function() {
    document.getElementById('mesa-detail-modal').classList.remove('active');
    currentMesaDetail = null;
};

function renderMesaDetail(detail) {
    // Header
    document.getElementById('mesa-detail-id').textContent = detail.mesa_id;
    document.getElementById('mesa-detail-location').textContent =
        `${detail.header.dept_name} > ${detail.header.muni_name} > ${detail.header.puesto} > Mesa ${detail.header.mesa_number}`;

    // Status badge
    const statusEl = document.getElementById('mesa-detail-status');
    statusEl.textContent = detail.status.replace('_', ' ');
    statusEl.className = 'mesa-status-badge';
    if (detail.status === 'VALIDATED') statusEl.classList.add('validated');
    else if (detail.status === 'NEEDS_REVIEW') statusEl.classList.add('needs-review');
    else statusEl.classList.add('high-risk');

    // Confidence
    const confEl = document.getElementById('mesa-detail-confidence');
    const confPct = (detail.overall_confidence * 100).toFixed(0);
    confEl.textContent = `${confPct}%`;
    confEl.className = 'mesa-confidence-value';
    if (detail.overall_confidence >= 0.85) confEl.classList.add('high');
    else if (detail.overall_confidence >= 0.70) confEl.classList.add('medium');
    else confEl.classList.add('low');

    // OCR Fields
    renderOcrFields(detail.ocr_fields);

    // Validations
    renderValidations(detail.validations);

    // Comparison table
    renderComparison(detail.comparison);

    // Incidents
    renderMesaIncidents(detail.incidents);
}

function renderOcrFields(fields) {
    const container = document.getElementById('mesa-ocr-fields');

    container.innerHTML = fields.map(field => {
        const confPct = (field.confidence * 100).toFixed(0);
        const confClass = field.confidence >= 0.85 ? 'high' : (field.confidence >= 0.70 ? 'medium' : 'low');
        const reviewClass = field.needs_review ? 'needs-review' : '';

        return `
            <div class="ocr-field-row ${reviewClass}">
                <span class="ocr-field-label">${field.label}</span>
                <div class="ocr-field-value">
                    <span class="ocr-field-number">${formatNumber(field.value)}</span>
                    <span class="ocr-field-confidence ${confClass}">${confPct}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function renderValidations(validations) {
    const container = document.getElementById('mesa-validations');

    container.innerHTML = validations.map(v => {
        const passedClass = v.passed ? 'passed' : 'failed';
        const icon = v.passed ? '✓' : '✗';

        return `
            <div class="validation-row ${passedClass}">
                <span class="validation-icon">${icon}</span>
                <span class="validation-name">${v.rule}: ${v.name}</span>
                <span class="validation-message">${v.message}</span>
            </div>
        `;
    }).join('');
}

function renderComparison(comparison) {
    const tbody = document.getElementById('mesa-comparison-body');

    if (!comparison || comparison.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--muted);">Sin datos de comparación</td></tr>';
        return;
    }

    tbody.innerHTML = comparison.map(row => {
        let deltaClass = 'delta-zero';
        let deltaText = '0';

        if (row.delta > 0) {
            deltaClass = 'delta-positive';
            deltaText = `+${row.delta}`;
        } else if (row.delta < 0) {
            deltaClass = 'delta-negative';
            deltaText = `${row.delta}`;
        }

        return `
            <tr>
                <td class="candidate-col">
                    <div style="font-weight: 500;">${row.candidate_name}</div>
                    <div style="font-size: 0.7rem; color: var(--muted);">${row.party}</div>
                </td>
                <td class="number-col">${row.testigo}</td>
                <td class="number-col">${row.rnec !== null ? row.rnec : '--'}</td>
                <td class="delta-col ${deltaClass}">
                    ${deltaText}
                    ${row.delta_pct > 0 ? `<span style="font-size: 0.7rem; opacity: 0.7;"> (${row.delta_pct}%)</span>` : ''}
                </td>
            </tr>
        `;
    }).join('');
}

function renderMesaIncidents(incidents) {
    const container = document.getElementById('mesa-incidents-list');

    if (!incidents || incidents.length === 0) {
        container.innerHTML = '<div style="color: var(--success); font-size: 0.8rem;">✓ Sin incidentes activos</div>';
        return;
    }

    container.innerHTML = incidents.map(inc => `
        <div class="mesa-incident-item">
            <span class="severity-badge ${inc.severity.toLowerCase()}">${inc.severity}</span>
            <span class="incident-type">${inc.type}</span>
            <span class="mesa-incident-desc">${inc.description}</span>
        </div>
    `).join('');
}

// Mesa Detail Actions
window.createMesaIncident = function() {
    if (!currentMesaDetail) return;

    const incidentType = prompt('Tipo de incidente:\n1. OCR_LOW_CONF\n2. ARITHMETIC_FAIL\n3. DISCREPANCY_RNEC\n4. SOURCE_MISMATCH\n\nIngrese número o nombre:');
    if (!incidentType) return;

    const typeMap = { '1': 'OCR_LOW_CONF', '2': 'ARITHMETIC_FAIL', '3': 'DISCREPANCY_RNEC', '4': 'SOURCE_MISMATCH' };
    const finalType = typeMap[incidentType] || incidentType.toUpperCase();

    const description = prompt('Descripción del incidente:');
    if (!description) return;

    // Create incident via API
    fetch('/api/incidents', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            incident_type: finalType,
            mesa_id: currentMesaDetail.mesa_id,
            dept_code: currentMesaDetail.header.dept_code,
            dept_name: currentMesaDetail.header.dept_name,
            muni_name: currentMesaDetail.header.muni_name,
            puesto: currentMesaDetail.header.puesto,
            description: description,
            ocr_confidence: currentMesaDetail.overall_confidence
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert('Incidente creado exitosamente');
            loadIncidents(); // Refresh incident queue
            openMesaDetail(currentMesaDetail.mesa_id); // Refresh mesa detail
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error creating incident:', err);
        alert('Error de conexión');
    });
};

window.callWitnessForMesa = function() {
    if (!currentMesaDetail) return;

    // Close mesa modal and switch to witness tab
    closeMesaDetailModal();

    // Switch to witness tab
    document.querySelector('[data-tab="llamar-testigo"]').click();

    alert(`Seleccione un testigo para enviar a:\n${currentMesaDetail.header.puesto}\nMesa ${currentMesaDetail.mesa_id}`);
};

window.escalateMesaToLegal = function() {
    if (!currentMesaDetail) return;

    const reason = prompt('Razón para escalar a equipo legal:');
    if (!reason) return;

    alert(`Mesa ${currentMesaDetail.mesa_id} escalada al equipo legal.\n\nRazón: ${reason}`);
    closeMesaDetailModal();
};

window.markMesaResolved = function() {
    if (!currentMesaDetail) return;

    if (confirm(`¿Marcar mesa ${currentMesaDetail.mesa_id} como resuelta?`)) {
        alert('Mesa marcada como resuelta');
        closeMesaDetailModal();
        loadIncidents(); // Refresh
    }
};

// Make openMesaDetail available globally
window.openMesaDetail = openMesaDetail;
