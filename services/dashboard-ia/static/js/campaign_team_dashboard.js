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
    setupModalCloseOnOverlay();

    // Initial load
    loadDashboardData();

    // Start real-time refresh
    startRealTimeRefresh();
});

// Setup click-outside-to-close for all modals
function setupModalCloseOnOverlay() {
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            // Close only if clicking directly on overlay (not on modal content)
            if (e.target === overlay) {
                overlay.classList.remove('active');
            }
        });
    });
}

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

    // Helper to safely parse JSON response
    const safeJson = async (response, fallback = { success: false }) => {
        try {
            if (!response.ok) {
                console.warn(`API returned ${response.status}: ${response.statusText}`);
                return fallback;
            }
            return await response.json();
        } catch (e) {
            console.warn('Failed to parse JSON response:', e);
            return fallback;
        }
    };

    try {
        // Load data from API including E-14 live data
        const [statsResponse, votesResponse, alertsResponse, e14Response] = await Promise.all([
            fetch(`/api/campaign-team/war-room/stats?contest_id=${currentContestId}`).catch(() => null),
            fetch(`/api/campaign-team/reports/votes-by-candidate?contest_id=${currentContestId}`).catch(() => null),
            fetch(`/api/campaign-team/war-room/alerts?contest_id=${currentContestId}&limit=100`).catch(() => null),
            fetch(`/api/campaign-team/e14-live?limit=500`).catch(() => null)
        ]);

        const statsData = statsResponse ? await safeJson(statsResponse) : { success: false };
        const votesData = votesResponse ? await safeJson(votesResponse) : { success: false };
        const alertsData = alertsResponse ? await safeJson(alertsResponse) : { success: false };
        const e14Data = e14Response ? await safeJson(e14Response) : { success: false };

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
            // Store data globally for other functions
            window.e14LiveData = e14Data;

            renderE14LiveForm(e14Data);

            // Process votes data for the party chart
            if (typeof processE14VotesData === 'function') {
                processE14VotesData();
            }

            // Update KPIs from E-14 data
            if (typeof updateE14KPIs === 'function') {
                updateE14KPIs(e14Data);
            }
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
        // Still try to render with fallback data
        generateMockRiskData();
        populateFilters();
        renderContiendaTab();
    } finally {
        showLoading(false);
    }
}

function processStatsData(data) {
    // Store raw stats
    window.dashboardStats = data;
}

function processVotesData(data) {
    console.log('processVotesData received:', data);

    // Store candidates data from API
    const candidates = data.candidates || data.by_candidate || [];
    console.log('Found candidates:', candidates.length);

    // Update tracked candidates with API data
    candidates.forEach(apiCandidate => {
        const candidate = trackedCandidates.find(c => c.name === apiCandidate.name);
        if (candidate) {
            candidate.votes = apiCandidate.votes || 0;
            candidate.percentage = apiCandidate.percentage || 0;
            candidate.mesas = apiCandidate.mesas_processed || 0;
            candidate.trend = apiCandidate.trend || 'stable';
            candidate.trendValue = apiCandidate.trend_value || 0;
            candidate.color = apiCandidate.color || candidate.color;
            candidate.coverage = apiCandidate.coverage_pct || 0;
            console.log(`Updated ${candidate.name}: ${candidate.votes} votes`);
        } else {
            console.warn(`Candidate not found: ${apiCandidate.name}`);
        }
    });

    // Store votes with risk classification
    allVotes = candidates.map((vote, index) => ({
        ...vote,
        id: index + 1,
        party: vote.party || 'Sin partido',
        ocrConfidence: (vote.confidence || 0.85) * 100,
        dept: data.dept || 'Nacional',
        muni: data.muni || 'Nacional',
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

function processE14VotesData() {
    // Process E-14 partido data for the votes table
    // Priority: Use party_summary from API (pre-aggregated) if available
    const partySummary = window.e14LiveData?.party_summary || [];
    const totalVotesFromAPI = window.e14LiveData?.total_votes || 0;

    // If party_summary is available (Tesseract data), use it directly
    if (partySummary.length > 0) {
        console.log(`Using party_summary with ${partySummary.length} parties, ${totalVotesFromAPI} total votes`);

        allVotes = partySummary.map((partido, index) => ({
            id: index + 1,
            party_name: partido.party_name,
            party_code: partido.party_code || '',
            total_votes: partido.total_votes,
            percentage: totalVotesFromAPI > 0 ? (partido.total_votes / totalVotesFromAPI) * 100 : 0,
            ocrConfidence: (partido.avg_confidence || 0.85) * 100,
            mesas_count: partido.mesas_count || 0,
            riskLevel: 'low'
        }));

        // Add risk classification based on OCR confidence
        allVotes.forEach(vote => {
            if (vote.ocrConfidence < 70) {
                vote.riskLevel = 'high';
            } else if (vote.ocrConfidence < 85) {
                vote.riskLevel = 'medium';
            } else {
                vote.riskLevel = 'low';
            }
        });

        // Already sorted by API, but ensure sort
        allVotes.sort((a, b) => b.total_votes - a.total_votes);

        console.log(`Processed ${allVotes.length} partidos from party_summary (Congress 2022)`);

        // Render the votes table
        renderVotesTable(allVotes);

        // Render party chart
        renderPartyChart(allVotes);
        return;
    }

    // Fallback: aggregate from forms if no party_summary
    const forms = window.e14LiveData?.forms || [];

    // If no forms, use demo data from tracked candidates
    if (forms.length === 0) {
        console.log('No E-14 forms, using tracked candidates for party chart');
        useFallbackPartyData();
        return;
    }

    // Aggregate votes by partido across all E-14 forms
    const partidoVotes = {};
    let totalVotesAll = 0;

    forms.forEach(form => {
        const partidos = form.partidos || [];
        partidos.forEach(partido => {
            const key = partido.party_code || partido.party_name;
            if (!partidoVotes[key]) {
                partidoVotes[key] = {
                    party_code: partido.party_code,
                    party_name: partido.party_name,
                    total_votes: 0,
                    confidence_sum: 0,
                    count: 0
                };
            }
            // Support both formats: 'votes' (Tesseract) and 'total_votos' (Vision)
            const votes = partido.votes || partido.total_votos || 0;
            partidoVotes[key].total_votes += votes;
            partidoVotes[key].confidence_sum += (partido.confidence || 0.85) * 100;
            partidoVotes[key].count += 1;
            totalVotesAll += votes;
        });
    });

    // Convert to array and calculate percentages
    allVotes = Object.values(partidoVotes).map((partido, index) => ({
        id: index + 1,
        party_name: partido.party_name || `Partido ${partido.party_code}`,
        party_code: partido.party_code,
        total_votes: partido.total_votes,
        percentage: totalVotesAll > 0 ? (partido.total_votes / totalVotesAll) * 100 : 0,
        ocrConfidence: partido.count > 0 ? partido.confidence_sum / partido.count : 85,
        riskLevel: 'low'
    }));

    // Add risk classification based on OCR confidence
    allVotes.forEach(vote => {
        if (vote.ocrConfidence < 70) {
            vote.riskLevel = 'high';
        } else if (vote.ocrConfidence < 85) {
            vote.riskLevel = 'medium';
        } else {
            vote.riskLevel = 'low';
        }
    });

    // Sort by votes descending
    allVotes.sort((a, b) => b.total_votes - a.total_votes);

    console.log(`Processed ${allVotes.length} partidos from E-14 forms`);

    // Render the votes table
    renderVotesTable(allVotes);

    // Render party chart
    renderPartyChart(allVotes);
}

/**
 * Fallback function to populate party chart with tracked candidates data
 * Used when no E-14 forms are available from the API
 */
function useFallbackPartyData() {
    // Ensure candidates have demo data
    const hasData = trackedCandidates.some(c => c.votes > 0);
    if (!hasData && typeof simulateCandidateDataFallback === 'function') {
        simulateCandidateDataFallback();
    }

    // Use tracked candidates (9 presidential candidates) as party data
    const partyData = trackedCandidates.map((candidate, index) => ({
        id: index + 1,
        party_name: candidate.party || candidate.name,
        party_code: candidate.id,
        total_votes: candidate.votes || 0,
        percentage: candidate.percentage || 0,
        ocrConfidence: 85 + Math.random() * 10, // Simulate 85-95% confidence
        riskLevel: 'low',
        color: candidate.color
    }));

    // Sort by votes descending
    partyData.sort((a, b) => b.total_votes - a.total_votes);

    // Update global allVotes
    allVotes = partyData;

    console.log('Using fallback party data:', partyData.length, 'parties');

    // Render the votes table
    renderVotesTable(allVotes);

    // Render party chart
    renderPartyChart(allVotes);

    // Render OCR problems list (empty since this is fallback data)
    renderOCRProblemsList([]);
}

/**
 * Update KPI cards with real E-14 data
 * Updates: Sufragantes, Votos Urna, Votos Válidos, Votos Blanco, Votos Nulos, No Marcados
 * Also updates: Recuento section (Hubo Recuento, Solicitado por, Representación, Jurados Firmantes)
 */
function updateE14KPIs(data) {
    const forms = data?.forms || [];
    const summary = data?.summary || {};

    // Aggregate totals from all E-14 forms
    let totalSufragantes = 0;
    let totalVotosUrna = 0;
    let totalVotosValidos = 0;
    let totalVotosBlanco = 0;
    let totalVotosNulos = 0;
    let totalNoMarcados = 0;

    // Recuento aggregates
    let huboRecuento = false;
    let recuentoSolicitado = '-';
    let recuentoRepresentacion = '-';
    let totalJuradosFirmantes = 0;
    let totalJurados = 0;

    forms.forEach(form => {
        const nivelacion = form.nivelacion || {};
        const resumen = form.resumen || {};
        const constancias = form.constancias || {};

        // Nivelación data
        totalSufragantes += nivelacion.total_sufragantes || 0;
        totalVotosUrna += nivelacion.votos_en_urna || nivelacion.total_votos_urna || 0;
        totalVotosValidos += nivelacion.votos_validos || 0;
        totalVotosBlanco += nivelacion.votos_blanco || 0;
        totalVotosNulos += nivelacion.votos_nulos || 0;
        totalNoMarcados += nivelacion.votos_no_marcados || 0;

        // Resumen data
        if (resumen.hubo_recuento) {
            huboRecuento = true;
            recuentoSolicitado = resumen.solicitado_por || recuentoSolicitado;
            recuentoRepresentacion = resumen.representacion_de || recuentoRepresentacion;
        }

        // Constancias - jurados
        const jurados = constancias.jurados || [];
        totalJurados += jurados.length;
        totalJuradosFirmantes += jurados.filter(j => j.firma).length;
    });

    // Use summary data if no forms or as fallback
    if (forms.length === 0 && summary) {
        totalSufragantes = summary.total_sufragantes || 0;
        totalVotosUrna = summary.total_votos_urna || 0;
        totalVotosValidos = summary.votos_validos || 0;
        totalVotosBlanco = summary.votos_blanco || 0;
        totalVotosNulos = summary.votos_nulos || 0;
        totalNoMarcados = summary.votos_no_marcados || 0;
    }
    const stats = data?.stats || null;
    if (stats) {
        totalVotosValidos = stats.total_votes || totalVotosValidos || 0;
        totalVotosBlanco = stats.total_blancos || totalVotosBlanco || 0;
        totalVotosNulos = stats.total_nulos || totalVotosNulos || 0;
        totalVotosUrna = totalVotosValidos + totalVotosBlanco + totalVotosNulos;
        totalSufragantes = totalVotosUrna;
        totalNoMarcados = 0;
    }

    // Update KPI cards
    const kpiSufragantes = document.getElementById('kpi-sufragantes');
    if (kpiSufragantes) kpiSufragantes.textContent = formatNumber(totalSufragantes);

    const kpiVotosUrna = document.getElementById('kpi-votos-urna');
    if (kpiVotosUrna) kpiVotosUrna.textContent = formatNumber(totalVotosUrna);

    const kpiVotosValidos = document.getElementById('kpi-votos-validos');
    if (kpiVotosValidos) kpiVotosValidos.textContent = formatNumber(totalVotosValidos);

    const kpiVotosBlanco = document.getElementById('kpi-votos-blanco');
    if (kpiVotosBlanco) kpiVotosBlanco.textContent = formatNumber(totalVotosBlanco);

    const kpiVotosNulos = document.getElementById('kpi-votos-nulos');
    if (kpiVotosNulos) kpiVotosNulos.textContent = formatNumber(totalVotosNulos);

    const kpiNoMarcados = document.getElementById('kpi-no-marcados');
    if (kpiNoMarcados) kpiNoMarcados.textContent = formatNumber(totalNoMarcados);

    // Update Recuento section
    const recuentoHubo = document.getElementById('recuento-hubo');
    if (recuentoHubo) {
        recuentoHubo.textContent = huboRecuento ? 'Sí' : 'No';
        recuentoHubo.className = huboRecuento ? 'recuento-value si' : 'recuento-value no';
    }

    const recuentoSolicitadoEl = document.getElementById('recuento-solicitado');
    if (recuentoSolicitadoEl) recuentoSolicitadoEl.textContent = recuentoSolicitado;

    const recuentoRepresentacionEl = document.getElementById('recuento-representacion');
    if (recuentoRepresentacionEl) recuentoRepresentacionEl.textContent = recuentoRepresentacion;

    const recuentoJurados = document.getElementById('recuento-jurados');
    if (recuentoJurados) {
        recuentoJurados.textContent = totalJurados > 0 ? `${totalJuradosFirmantes}/${totalJurados}` : '-';
    }

    console.log('Updated E-14 KPIs:', {
        sufragantes: totalSufragantes,
        votosUrna: totalVotosUrna,
        votosValidos: totalVotosValidos,
        votosBlanco: totalVotosBlanco,
        votosNulos: totalVotosNulos,
        noMarcados: totalNoMarcados,
        huboRecuento,
        juradosFirmantes: `${totalJuradosFirmantes}/${totalJurados}`
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
        const deptsMunis = [
            { departamento: 'Antioquia', municipio: 'Medellín' },
            { departamento: 'Antioquia', municipio: 'Envigado' },
            { departamento: 'Antioquia', municipio: 'Itagüí' },
            { departamento: 'Valle del Cauca', municipio: 'Cali' },
            { departamento: 'Cundinamarca', municipio: 'Bogotá' },
            { departamento: 'Atlántico', municipio: 'Barranquilla' },
            { departamento: 'Santander', municipio: 'Bucaramanga' },
            { departamento: 'Nariño', municipio: 'Pasto' }
        ];

        for (let i = allMesas.length; i < 25; i++) {
            const confidence = Math.max(40, Math.min(98, 70 + Math.random() * 30 - Math.random() * 30));
            const loc = deptsMunis[i % deptsMunis.length];
            allMesas.push({
                id: i + 1,
                mesa: i + 1,
                departamento: loc.departamento,
                municipio: loc.municipio,
                puesto: puestos[i % puestos.length],
                ocrConfidence: confidence,
                reason: confidence < 70 ? 'Imagen borrosa o dañada' : (confidence < 85 ? 'Algunos campos ilegibles' : 'Validación exitosa'),
                totalVotes: Math.floor(Math.random() * 500) + 100,
                status: confidence < 70 ? 'NEEDS_REVIEW' : 'VALIDATED',
                riskLevel: confidence < 70 ? 'high' : (confidence < 85 ? 'medium' : 'low')
            });
        }
    }

    // Update OCR problems list with the generated data
    renderOCRProblemsList(allMesas);

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
    let filteredVotes = getFilteredVotes();

    // If no votes data, use fallback
    if (filteredVotes.length === 0) {
        useFallbackPartyData();
        filteredVotes = getFilteredVotes();
    }

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
    // Get E-14 data from API response
    const e14Data = window.e14LiveData || {};
    const forms = e14Data.forms || [];

    // Calculate totals from E-14 forms
    let totalSufragantes = 0;
    let totalVotosUrna = 0;
    let totalVotosValidos = 0;
    let totalVotosBlanco = 0;
    let totalVotosNulos = 0;
    let totalNoMarcados = 0;
    let huboRecuento = false;
    let recuentoSolicitado = '--';
    let recuentoRepresentacion = '--';
    let juradosFirmantes = 0;

    forms.forEach(form => {
        const niv = form.nivelacion || {};
        const res = form.resumen || {};
        const constancias = form.constancias || {};

        totalSufragantes += niv.total_sufragantes || 0;
        totalVotosUrna += niv.total_votos_urna || 0;
        totalVotosValidos += res.total_votos_validos || 0;
        totalVotosBlanco += res.votos_blanco || 0;
        totalVotosNulos += res.votos_nulos || 0;
        totalNoMarcados += res.votos_no_marcados || 0;

        if (constancias.hubo_recuento) huboRecuento = true;
        if (constancias.recuento_solicitado_por) recuentoSolicitado = constancias.recuento_solicitado_por;
        if (constancias.recuento_en_representacion_de) recuentoRepresentacion = constancias.recuento_en_representacion_de;
        juradosFirmantes = Math.max(juradosFirmantes, constancias.num_jurados_firmantes || 0);
    });

    // Update KPI elements (with null checks)
    const setKPI = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
    };

    // KPIs del E-14
    setKPI('kpi-sufragantes', formatNumber(totalSufragantes));
    setKPI('kpi-votos-urna', formatNumber(totalVotosUrna));
    setKPI('kpi-votos-validos', formatNumber(totalVotosValidos));
    setKPI('kpi-votos-blanco', formatNumber(totalVotosBlanco));
    setKPI('kpi-votos-nulos', formatNumber(totalVotosNulos));
    setKPI('kpi-no-marcados', formatNumber(totalNoMarcados));

    // Recuento info
    const recuentoHuboEl = document.getElementById('recuento-hubo');
    if (recuentoHuboEl) {
        recuentoHuboEl.textContent = huboRecuento ? 'SÍ' : 'NO';
        recuentoHuboEl.className = 'recuento-value ' + (huboRecuento ? 'si' : 'no');
    }
    setKPI('recuento-solicitado', recuentoSolicitado);
    setKPI('recuento-representacion', recuentoRepresentacion);
    setKPI('recuento-jurados', juradosFirmantes > 0 ? juradosFirmantes : '--');
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
        type: 'pie',
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
                        font: { size: 10 },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const value = context.raw;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${formatNumber(value)} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderOCRProblemsList(mesas) {
    const container = document.getElementById('ocr-problems-list');
    const countEl = document.getElementById('ocr-problems-count');
    if (!container) return;

    // Filter mesas with OCR confidence < 90%
    const problemMesas = mesas
        .filter(m => (m.ocrConfidence || m.confidence || 100) < 90)
        .sort((a, b) => (a.ocrConfidence || a.confidence || 0) - (b.ocrConfidence || b.confidence || 0))
        .slice(0, 20); // Show top 20 worst

    // Update count
    if (countEl) {
        countEl.textContent = `(${problemMesas.length} ubicaciones < 90%)`;
    }

    if (problemMesas.length === 0) {
        container.innerHTML = `
            <div class="ocr-problem-empty">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-bottom: 0.5rem; opacity: 0.5;">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <div>Todas las ubicaciones tienen confianza ≥ 90%</div>
            </div>
        `;
        return;
    }

    container.innerHTML = problemMesas.map(mesa => {
        const confidence = mesa.ocrConfidence || mesa.confidence || 0;
        const isCritical = confidence < 70;
        const severityClass = isCritical ? '' : 'medium';
        const valueClass = isCritical ? 'critical' : 'warning';

        // Get location info
        const dept = mesa.departamento || mesa.department || '';
        const muni = mesa.municipio || mesa.municipality || '';
        const puesto = mesa.puesto || mesa.location || mesa.ubicacion || '';
        const mesaNum = mesa.mesaId || mesa.mesa_id || mesa.mesa || mesa.id || '';

        // Build location string
        let locationParts = [];
        if (dept) locationParts.push(dept);
        if (muni) locationParts.push(muni);
        const locationStr = locationParts.join(', ') || 'Sin ubicación';

        return `
            <div class="ocr-problem-item ${severityClass}">
                <div class="ocr-problem-location">
                    <span class="ocr-problem-mesa">Mesa ${escapeHtml(String(mesaNum))}</span>
                    <span class="ocr-problem-geo">${escapeHtml(locationStr)}</span>
                    ${puesto ? `<span class="ocr-problem-place">${escapeHtml(puesto)}</span>` : ''}
                </div>
                <div class="ocr-problem-confidence">
                    <span class="ocr-problem-value ${valueClass}">${confidence.toFixed(0)}%</span>
                    <span class="ocr-problem-label">Confianza</span>
                </div>
            </div>
        `;
    }).join('');
}

// Keep old function name as alias for compatibility
function renderRiskDistributionChart(mesas) {
    renderOCRProblemsList(mesas);
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
// ZONAS DE RIESGO TAB - Sistema MOE + OCR
// ============================================================

let moeRiskData = null;
let selectedMunicipality = null;
let municipalityFilter = 'all';

// Load MOE risk data on init
async function loadMOERiskData() {
    try {
        const response = await fetch('/api/geography/moe/risk-municipalities');
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                moeRiskData = data;
            } else {
                moeRiskData = getMOEFallbackData();
            }
        } else {
            // Use embedded fallback data
            moeRiskData = getMOEFallbackData();
        }
        console.log('MOE data loaded:', moeRiskData?.municipalities?.length, 'municipalities');
    } catch (error) {
        console.log('Using MOE fallback data');
        moeRiskData = getMOEFallbackData();
    }
}

function getMOEFallbackData() {
    // Embedded subset of critical municipalities for fallback
    return {
        metadata: { total_risk_municipalities: 166, extreme_risk_count: 104, high_risk_count: 62 },
        risk_factors: {
            ARMED_GROUPS: "Presencia de grupos armados ilegales",
            ILLEGAL_ECONOMY: "Economías ilegales (coca, minería)",
            TRASHUMANTISMO: "Migración ficticia de votantes",
            LEADER_ATTACKS: "Ataques a líderes políticos",
            MOBILITY_RESTRICTIONS: "Restricciones a la movilidad",
            BORDER_VULNERABILITY: "Vulnerabilidad fronteriza"
        },
        municipalities: [
            { code: "52835", name: "Tumaco", department: "Nariño", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "TRASHUMANTISMO", "LEADER_ATTACKS"], armed_group: "Disidencias FARC" },
            { code: "54810", name: "Tibú", department: "Norte de Santander", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "LEADER_ATTACKS", "MOBILITY_RESTRICTIONS"], armed_group: "ELN" },
            { code: "05142", name: "Caucasia", department: "Antioquia", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "POLITICAL_DOMINANCE"], armed_group: "Clan del Golfo" },
            { code: "27001", name: "Quibdó", department: "Chocó", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "LEADER_ATTACKS"], armed_group: "ELN" },
            { code: "19698", name: "Santander de Quilichao", department: "Cauca", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "LEADER_ATTACKS"], armed_group: "Disidencias FARC" },
            { code: "54001", name: "Cúcuta", department: "Norte de Santander", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "BORDER_VULNERABILITY", "TRASHUMANTISMO"], armed_group: "ELN" },
            { code: "76109", name: "Buenaventura", department: "Valle del Cauca", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "LEADER_ATTACKS"], armed_group: "Clan del Golfo" },
            { code: "81001", name: "Arauca", department: "Arauca", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "BORDER_VULNERABILITY", "MOBILITY_RESTRICTIONS"], armed_group: "ELN" },
            { code: "18001", name: "Florencia", department: "Caquetá", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "LEADER_ATTACKS"], armed_group: "Disidencias FARC" },
            { code: "23417", name: "Montelíbano", department: "Córdoba", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "POLITICAL_DOMINANCE"], armed_group: "Clan del Golfo" },
            { code: "05736", name: "Segovia", department: "Antioquia", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "LEADER_ATTACKS"], armed_group: "ELN" },
            { code: "19212", name: "Corinto", department: "Cauca", risk_level: "EXTREME", factors: ["ARMED_GROUPS", "ILLEGAL_ECONOMY", "LEADER_ATTACKS"], armed_group: "Disidencias FARC" },
            { code: "05837", name: "Turbo", department: "Antioquia", risk_level: "HIGH", factors: ["ARMED_GROUPS", "TRASHUMANTISMO", "BORDER_VULNERABILITY"], armed_group: "Clan del Golfo" },
            { code: "52356", name: "Ipiales", department: "Nariño", risk_level: "HIGH", factors: ["BORDER_VULNERABILITY", "TRASHUMANTISMO"] },
            { code: "19001", name: "Popayán", department: "Cauca", risk_level: "HIGH", factors: ["LEADER_ATTACKS", "POLITICAL_DOMINANCE"] },
            { code: "76834", name: "Tuluá", department: "Valle del Cauca", risk_level: "HIGH", factors: ["ARMED_GROUPS", "LEADER_ATTACKS"] },
            { code: "68081", name: "Barrancabermeja", department: "Santander", risk_level: "HIGH", factors: ["ARMED_GROUPS", "LEADER_ATTACKS"], armed_group: "ELN" }
        ],
        department_summary: {
            "05": { name: "Antioquia", extreme: 11, high: 5, main_threat: "Clan del Golfo" },
            "19": { name: "Cauca", extreme: 10, high: 4, main_threat: "Disidencias FARC" },
            "27": { name: "Chocó", extreme: 8, high: 4, main_threat: "ELN" },
            "52": { name: "Nariño", extreme: 9, high: 4, main_threat: "Disidencias FARC" },
            "54": { name: "Norte de Santander", extreme: 6, high: 1, main_threat: "ELN" }
        }
    };
}

function renderRiskZonesTab() {
    if (!moeRiskData) {
        loadMOERiskData().then(() => renderRiskZonesTabContent());
    } else {
        renderRiskZonesTabContent();
    }
}

function renderRiskZonesTabContent() {
    // Update KPIs with MOE data only
    updateRiskKPIs();

    // Render municipalities list (grouped by department)
    renderMunicipalitiesList();

    // Render risk factors
    renderRiskFactors();

    // Render departments ranking
    renderDepartmentsRanking();

    // Setup filter pills
    setupMunicipalityFilters();
}

function calculateCompositeRisk() {
    const municipalities = moeRiskData?.municipalities || [];
    const ocrData = allMesas || [];

    // Create lookup for OCR confidence by municipality
    const ocrByMuni = {};
    ocrData.forEach(mesa => {
        const muniCode = mesa.muni_code || mesa.municipio_code;
        if (!ocrByMuni[muniCode]) {
            ocrByMuni[muniCode] = { total: 0, sum: 0, lowCount: 0 };
        }
        ocrByMuni[muniCode].total++;
        ocrByMuni[muniCode].sum += mesa.ocrConfidence || 85;
        if ((mesa.ocrConfidence || 85) < 70) ocrByMuni[muniCode].lowCount++;
    });

    // Calculate composite risk for each municipality
    const result = {
        critical: [],
        high: [],
        moderate: [],
        normal: [],
        matrix: {
            extreme_ok: 0, extreme_med: 0, extreme_low: 0,
            high_ok: 0, high_med: 0, high_low: 0,
            normal_ok: 0, normal_med: 0, normal_low: 0
        }
    };

    municipalities.forEach(muni => {
        const ocrInfo = ocrByMuni[muni.code] || { total: 0, sum: 0 };
        const avgOcr = ocrInfo.total > 0 ? ocrInfo.sum / ocrInfo.total : 90;

        // Determine OCR level
        let ocrLevel = 'ok';
        if (avgOcr < 70) ocrLevel = 'low';
        else if (avgOcr < 90) ocrLevel = 'med';

        // Determine MOE level
        const moeLevel = muni.risk_level === 'EXTREME' ? 'extreme' :
                        (muni.risk_level === 'HIGH' ? 'high' : 'normal');

        // Update matrix counts
        result.matrix[`${moeLevel}_${ocrLevel}`]++;

        // Calculate composite risk
        const muniWithComposite = {
            ...muni,
            avgOcr,
            ocrLevel,
            mesasCount: ocrInfo.total,
            lowOcrCount: ocrInfo.lowCount || 0
        };

        // Determine composite category
        if ((moeLevel === 'extreme' && ocrLevel !== 'ok') ||
            (moeLevel === 'high' && ocrLevel === 'low')) {
            muniWithComposite.compositeRisk = 'CRITICAL';
            result.critical.push(muniWithComposite);
        } else if (moeLevel === 'extreme' ||
                   (moeLevel === 'high' && ocrLevel === 'med') ||
                   (moeLevel === 'normal' && ocrLevel === 'low')) {
            muniWithComposite.compositeRisk = 'HIGH';
            result.high.push(muniWithComposite);
        } else if (moeLevel === 'high' || ocrLevel === 'med') {
            muniWithComposite.compositeRisk = 'MODERATE';
            result.moderate.push(muniWithComposite);
        } else {
            muniWithComposite.compositeRisk = 'NORMAL';
            result.normal.push(muniWithComposite);
        }
    });

    // Sort by risk (critical first by lowest OCR)
    result.critical.sort((a, b) => a.avgOcr - b.avgOcr);
    result.high.sort((a, b) => a.avgOcr - b.avgOcr);

    return result;
}

function updateRiskKPIs() {
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    // Count MOE levels directly from source data
    const municipalities = moeRiskData?.municipalities || [];
    const extremeCount = municipalities.filter(m => m.risk_level === 'EXTREME').length;
    const highCount = municipalities.filter(m => m.risk_level === 'HIGH').length;
    const totalCount = municipalities.length;

    setEl('risk-extreme-count', extremeCount);
    setEl('risk-high-count', highCount);
    setEl('risk-total-count', totalCount);

    // Update tab badge with extreme count
    const badge = document.getElementById('risk-badge');
    if (badge) {
        if (extremeCount > 0) {
            badge.textContent = extremeCount;
            badge.style.display = 'inline';
        } else {
            badge.style.display = 'none';
        }
    }
}

function updateRiskMatrix(compositeRisk) {
    const m = compositeRisk.matrix;
    const setCell = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    setCell('matrix-extreme-ok', m.extreme_ok);
    setCell('matrix-extreme-med', m.extreme_med);
    setCell('matrix-extreme-low', m.extreme_low);
    setCell('matrix-high-ok', m.high_ok);
    setCell('matrix-high-med', m.high_med);
    setCell('matrix-high-low', m.high_low);
    setCell('matrix-normal-ok', m.normal_ok);
    setCell('matrix-normal-med', m.normal_med);
    setCell('matrix-normal-low', m.normal_low);
}

function renderMunicipalitiesList() {
    const container = document.getElementById('critical-municipalities-list');
    if (!container) return;

    let municipalities = moeRiskData?.municipalities || [];

    // Apply MOE filter
    if (municipalityFilter === 'EXTREME') {
        municipalities = municipalities.filter(m => m.risk_level === 'EXTREME');
    } else if (municipalityFilter === 'HIGH') {
        municipalities = municipalities.filter(m => m.risk_level === 'HIGH');
    }

    if (municipalities.length === 0) {
        container.innerHTML = '<div class="loading-state">No hay municipios con este filtro</div>';
        return;
    }

    // Group by department
    const byDepartment = {};
    municipalities.forEach(muni => {
        const dept = muni.department || 'Sin departamento';
        if (!byDepartment[dept]) {
            byDepartment[dept] = [];
        }
        byDepartment[dept].push(muni);
    });

    // Sort departments alphabetically
    const sortedDepts = Object.keys(byDepartment).sort();

    // Sort municipalities within each department: by risk level (EXTREME first), then by name
    sortedDepts.forEach(dept => {
        byDepartment[dept].sort((a, b) => {
            if (a.risk_level === 'EXTREME' && b.risk_level !== 'EXTREME') return -1;
            if (a.risk_level !== 'EXTREME' && b.risk_level === 'EXTREME') return 1;
            return a.name.localeCompare(b.name);
        });
    });

    // Render grouped list
    let html = '';
    sortedDepts.forEach(dept => {
        const deptMunis = byDepartment[dept];
        const extremeCount = deptMunis.filter(m => m.risk_level === 'EXTREME').length;
        const highCount = deptMunis.filter(m => m.risk_level === 'HIGH').length;

        html += `
            <div class="dept-group">
                <div class="dept-group-header">
                    <span class="dept-group-name">${escapeHtml(dept)}</span>
                    <span class="dept-group-counts">
                        ${extremeCount > 0 ? `<span class="count-extreme">${extremeCount} extremo</span>` : ''}
                        ${highCount > 0 ? `<span class="count-high">${highCount} alto</span>` : ''}
                    </span>
                </div>
                <div class="dept-group-municipalities">
                    ${deptMunis.map(muni => `
                        <div class="municipality-item ${muni.risk_level?.toLowerCase() || ''} ${selectedMunicipality === muni.code ? 'selected' : ''}"
                             onclick="selectMunicipality('${muni.code}')">
                            <span class="muni-name">${escapeHtml(muni.name)}</span>
                            <span class="muni-risk-badge ${muni.risk_level?.toLowerCase() || ''}">
                                ${muni.risk_level === 'EXTREME' ? 'Extremo' : 'Alto'}
                            </span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

window.selectMunicipality = function(code) {
    selectedMunicipality = code;
    renderMunicipalitiesList();
    renderMunicipalityDetail(code);
};

function renderMunicipalityDetail(code) {
    const panel = document.getElementById('detail-panel-content');
    const titleEl = document.getElementById('detail-municipality-name');
    const deptEl = document.getElementById('detail-department');

    if (!panel) return;

    const muni = moeRiskData?.municipalities?.find(m => m.code === code);
    if (!muni) return;

    titleEl.textContent = muni.name;
    deptEl.textContent = muni.department;

    // Get factor descriptions
    const factorNames = {
        ARMED_GROUPS: 'Grupos Armados',
        ILLEGAL_ECONOMY: 'Economía Ilegal',
        TRASHUMANTISMO: 'Trashumantismo',
        POLITICAL_DOMINANCE: 'Dominancia Política',
        ATYPICAL_VOTES: 'Votos Atípicos',
        MOBILITY_RESTRICTIONS: 'Restricción Movilidad',
        LEADER_ATTACKS: 'Ataques a Líderes',
        INSTITUTIONAL_WEAKNESS: 'Debilidad Institucional',
        BORDER_VULNERABILITY: 'Vulnerabilidad Fronteriza',
        GEOGRAPHIC_ISOLATION: 'Aislamiento Geográfico'
    };

    const factorTags = (muni.factors || [])
        .map(f => `<span class="factor-tag">${factorNames[f] || f}</span>`)
        .join('');

    const armedGroupHtml = muni.armed_group ? `
        <div class="detail-armed-group">
            <div class="armed-group-label">Grupo Armado Principal</div>
            <div class="armed-group-name">${escapeHtml(muni.armed_group)}</div>
        </div>
    ` : '';

    panel.innerHTML = `
        <div class="detail-stats">
            <div class="detail-stat">
                <div class="detail-stat-value" style="color: ${muni.risk_level === 'EXTREME' ? '#DC3545' : '#E65100'}">
                    ${muni.risk_level === 'EXTREME' ? 'EXTREMO' : 'ALTO'}
                </div>
                <div class="detail-stat-label">Riesgo MOE</div>
            </div>
            <div class="detail-stat">
                <div class="detail-stat-value">${muni.factors?.length || 0}</div>
                <div class="detail-stat-label">Factores</div>
            </div>
        </div>

        <div class="detail-factors">
            <h4>Factores de Riesgo</h4>
            ${factorTags || '<span class="factor-tag">Sin factores identificados</span>'}
        </div>

        ${armedGroupHtml}

        <!-- Resultados E-14 del Municipio -->
        <div class="detail-e14-section" style="margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid var(--border);">
            <h4 style="margin: 0 0 1rem; color: var(--accent);">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align: middle; margin-right: 0.5rem;">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
                Resultados E-14
            </h4>
            <div id="muni-e14-results" style="font-size: 0.9rem;">
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin-bottom: 1rem;">
                    <div style="background: rgba(201, 162, 39, 0.1); padding: 0.5rem; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: 600;" id="muni-e14-mesas">--</div>
                        <div style="font-size: 0.75rem; color: var(--muted);">Mesas Procesadas</div>
                    </div>
                    <div style="background: rgba(201, 162, 39, 0.1); padding: 0.5rem; border-radius: 6px; text-align: center;">
                        <div style="font-size: 1.2rem; font-weight: 600;" id="muni-e14-confianza">--%</div>
                        <div style="font-size: 0.75rem; color: var(--muted);">Confianza OCR</div>
                    </div>
                </div>
                <div style="background: var(--panel); padding: 0.75rem; border-radius: 8px;">
                    <div style="font-weight: 600; margin-bottom: 0.5rem; font-size: 0.85rem;">Votos por Candidato</div>
                    <div id="muni-e14-candidates" style="font-size: 0.85rem;"></div>
                </div>
            </div>
        </div>

        <div style="margin-top: 1rem;">
            <button class="btn-action" onclick="escalateMunicipality('${code}')" style="width: 100%;">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                </svg>
                Escalar a Jurídico
            </button>
        </div>
    `;

    // Load E-14 results for this municipality
    loadMunicipalityE14Results(code, muni.name);
};

window.escalateMunicipality = function(code) {
    const muni = moeRiskData?.municipalities?.find(m => m.code === code);
    if (muni) {
        alert(`Escalando ${muni.name} (${muni.department}) al equipo jurídico.\n\nRiesgo: ${muni.risk_level}\nFactores: ${muni.factors?.join(', ')}`);
    }
};

// Load E-14 results for a specific municipality
function loadMunicipalityE14Results(muniCode, muniName) {
    const mesasEl = document.getElementById('muni-e14-mesas');
    const confianzaEl = document.getElementById('muni-e14-confianza');
    const candidatesEl = document.getElementById('muni-e14-candidates');

    if (!mesasEl || !confianzaEl || !candidatesEl) return;

    // Generate mock E-14 data for this municipality
    // In production, this would fetch from an API endpoint
    const seed = muniCode.split('').reduce((a, c) => a + c.charCodeAt(0), 0);
    const random = (min, max) => {
        const x = Math.sin(seed * 9999) * 10000;
        return Math.floor((x - Math.floor(x)) * (max - min + 1)) + min;
    };

    const mesasCount = random(5, 45);
    const confianza = random(65, 95);

    mesasEl.textContent = mesasCount;
    confianzaEl.textContent = `${confianza}%`;
    confianzaEl.style.color = confianza < 70 ? '#DC3545' : confianza < 85 ? '#E65100' : '#27AE60';

    // Generate votes for top candidates based on municipality
    const candidateVotes = trackedCandidates.map(c => {
        const baseVotes = random(50, 500);
        return {
            name: c.name,
            party: c.party,
            votes: baseVotes,
            color: c.color
        };
    }).sort((a, b) => b.votes - a.votes).slice(0, 5);

    const totalVotes = candidateVotes.reduce((sum, c) => sum + c.votes, 0);

    candidatesEl.innerHTML = candidateVotes.map((c, i) => {
        const pct = ((c.votes / totalVotes) * 100).toFixed(1);
        return `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.3rem 0; ${i < candidateVotes.length - 1 ? 'border-bottom: 1px solid var(--border);' : ''}">
                <span style="display: flex; align-items: center; gap: 0.4rem;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: ${c.color};"></span>
                    ${c.name.split(' ').slice(0, 2).join(' ')}
                </span>
                <span style="font-weight: 600;">${formatNumber(c.votes)} <span style="color: var(--muted); font-weight: normal;">(${pct}%)</span></span>
            </div>
        `;
    }).join('');
}

function setupMunicipalityFilters() {
    document.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            municipalityFilter = pill.dataset.filter;
            renderMunicipalitiesList();
        });
    });
}

// Store municipalities by factor for popups
let municipalitiesByFactor = {};

function renderRiskFactors() {
    const municipalities = moeRiskData?.municipalities || [];
    const factorCounts = {};
    municipalitiesByFactor = {};

    // Collect municipalities for each factor
    municipalities.forEach(muni => {
        (muni.factors || []).forEach(factor => {
            factorCounts[factor] = (factorCounts[factor] || 0) + 1;
            if (!municipalitiesByFactor[factor]) {
                municipalitiesByFactor[factor] = [];
            }
            municipalitiesByFactor[factor].push({
                name: muni.name,
                department: muni.department,
                risk_level: muni.risk_level
            });
        });
    });

    const maxCount = Math.max(...Object.values(factorCounts), 1);

    // Map factor codes to element IDs and labels
    const factorMap = {
        'ARMED_GROUPS': { bar: 'factor-armed', count: 'factor-armed-count', label: 'Grupos Armados' },
        'ILLEGAL_ECONOMY': { bar: 'factor-economy', count: 'factor-economy-count', label: 'Economía Ilegal' },
        'TRASHUMANTISMO': { bar: 'factor-trashumantismo', count: 'factor-trashumantismo-count', label: 'Trashumantismo' },
        'LEADER_ATTACKS': { bar: 'factor-leaders', count: 'factor-leaders-count', label: 'Ataques a Líderes' },
        'MOBILITY_RESTRICTIONS': { bar: 'factor-mobility', count: 'factor-mobility-count', label: 'Restricción Movilidad' },
        'BORDER_VULNERABILITY': { bar: 'factor-border', count: 'factor-border-count', label: 'Vulnerabilidad Fronteriza' }
    };

    Object.entries(factorMap).forEach(([factor, ids]) => {
        const count = factorCounts[factor] || 0;
        const percentage = (count / maxCount) * 100;

        const barEl = document.getElementById(ids.bar);
        const countEl = document.getElementById(ids.count);

        if (barEl) barEl.style.width = `${percentage}%`;
        if (countEl) countEl.textContent = count;

        // Add click handler to parent element
        const parentEl = barEl?.closest('.risk-factor-bar');
        if (parentEl) {
            parentEl.style.cursor = 'pointer';
            parentEl.dataset.factor = factor;
            parentEl.dataset.label = ids.label;
            parentEl.onclick = () => showFactorPopup(factor, ids.label);
        }
    });
}

function showFactorPopup(factor, label) {
    const munis = municipalitiesByFactor[factor] || [];

    // Group by department
    const byDept = {};
    munis.forEach(m => {
        if (!byDept[m.department]) byDept[m.department] = [];
        byDept[m.department].push(m);
    });

    // Sort departments
    const sortedDepts = Object.keys(byDept).sort();

    // Build popup content
    let content = `<div class="factor-popup-header">
        <h4>${label}</h4>
        <span class="factor-popup-count">${munis.length} municipios afectados</span>
        <button class="factor-popup-close" onclick="closeFactorPopup()">&times;</button>
    </div>
    <div class="factor-popup-body">`;

    sortedDepts.forEach(dept => {
        const deptMunis = byDept[dept].sort((a, b) => a.name.localeCompare(b.name));
        content += `<div class="factor-popup-dept">
            <div class="factor-popup-dept-name">${dept}</div>
            <div class="factor-popup-munis">
                ${deptMunis.map(m => `
                    <span class="factor-popup-muni ${m.risk_level?.toLowerCase()}">${m.name}</span>
                `).join('')}
            </div>
        </div>`;
    });

    content += '</div>';

    // Create or update popup
    let popup = document.getElementById('factor-popup');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'factor-popup';
        popup.className = 'factor-popup';
        document.body.appendChild(popup);
    }

    popup.innerHTML = content;
    popup.style.display = 'block';

    // Position popup
    popup.style.top = '50%';
    popup.style.left = '50%';
    popup.style.transform = 'translate(-50%, -50%)';
}

function closeFactorPopup() {
    const popup = document.getElementById('factor-popup');
    if (popup) popup.style.display = 'none';
}

// Close popup on escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFactorPopup();
});

function renderDepartmentsRanking() {
    const container = document.getElementById('departments-ranking');
    if (!container) return;

    const deptSummary = moeRiskData?.department_summary || {};

    // Convert to array and sort by total risk
    const departments = Object.entries(deptSummary)
        .map(([code, data]) => ({
            code,
            ...data,
            totalRisk: (data.extreme || 0) + (data.high || 0)
        }))
        .sort((a, b) => b.totalRisk - a.totalRisk)
        .slice(0, 8);

    if (departments.length === 0) {
        container.innerHTML = '<div class="loading-state">No hay datos de departamentos</div>';
        return;
    }

    container.innerHTML = departments.map((dept, index) => `
        <div class="dept-rank-card">
            <div class="dept-rank-position">#${index + 1}</div>
            <div class="dept-rank-info">
                <div class="dept-rank-name">${escapeHtml(dept.name)}</div>
                <div class="dept-rank-stats">
                    <span class="dept-rank-stat extreme">${dept.extreme || 0} extremo</span>
                    <span class="dept-rank-stat high">${dept.high || 0} alto</span>
                </div>
            </div>
        </div>
    `).join('');
}

// Legacy functions for backward compatibility
window.viewMesaDetails = function(mesaId) {
    const mesa = allMesas.find(m => m.id === mesaId);
    if (mesa) {
        alert(`Detalles de ${mesa.mesaId}:\n\nUbicación: ${mesa.puesto}, ${mesa.muni}\nDirección: ${mesa.location}\nConfianza OCR: ${mesa.ocrConfidence?.toFixed(1) || '--'}%\nTotal votos: ${mesa.totalVotes}\nEstado: ${mesa.status}`);
    }
};

window.selectMesaForWitness = function(mesaId) {
    const mesa = allMesas.find(m => m.id === mesaId);
    if (mesa) {
        document.querySelector('[data-tab="llamar-testigo"]')?.click();
        setTimeout(() => {
            const select = document.getElementById('critical-mesa-select');
            if (select) {
                select.value = mesaId;
                onCriticalMesaSelect();
            }
        }, 100);
    }
};

// Initialize MOE data on load
document.addEventListener('DOMContentLoaded', () => {
    loadMOERiskData();
});

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

    // Filter witnesses by coverage zone (same department/municipality or matching puesto)
    const nearbyWitnesses = allWitnesses.filter(w => {
        // Prioridad 1: Mismo departamento
        if (w.coverage_dept_name && mesa.dept && w.coverage_dept_name === mesa.dept) {
            // Si tiene municipio asignado, verificar que coincida
            if (w.coverage_muni_name && mesa.muni) {
                if (w.coverage_muni_name !== mesa.muni) return false;
            }
            // Si tiene puesto asignado, verificar que coincida
            if (w.coverage_station_name && mesa.puesto) {
                if (w.coverage_station_name !== mesa.puesto) return false;
            }
            return true;
        }
        // Fallback: mismo puesto o ubicacion actual
        return w.currentLocation === mesa.puesto;
    });

    if (countEl) {
        countEl.textContent = `${nearbyWitnesses.length} testigos en la zona`;
    }

    if (nearbyWitnesses.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No hay testigos disponibles para esta zona</p></div>';
        return;
    }

    container.innerHTML = nearbyWitnesses.map(witness => `
        <div class="witness-card">
            <div class="witness-card-header">
                <span class="witness-name">${escapeHtml(witness.name)}</span>
                <span class="witness-status ${witness.status}">${witness.status === 'available' ? 'Disponible' : 'Ocupado'}</span>
            </div>
            <div class="witness-coverage" style="font-size: 0.8rem; color: var(--muted); margin-bottom: 0.25rem;">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display: inline; vertical-align: middle;">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                    <circle cx="12" cy="10" r="3"/>
                </svg>
                Cubre: ${escapeHtml(witness.coverageDisplay || 'Sin zona')}
            </div>
            <div class="witness-phone" style="font-size: 0.85rem;">Tel: ${escapeHtml(witness.phone)}</div>
            ${witness.push_enabled ? '<div class="witness-push" style="font-size: 0.75rem; color: var(--success);">Push activo</div>' : ''}
            <div class="witness-actions">
                <button class="btn-action" onclick="callWitness(${witness.id})">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07"/>
                    </svg>
                    Llamar
                </button>
                <button class="btn-action primary" onclick="openCallModal(${witness.id})" ${witness.status === 'busy' ? 'disabled' : ''}>
                    ${witness.push_enabled ? 'Notificar' : 'Asignar'}
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

// 9 Candidatos Elecciones 2026
let trackedCandidates = [
    {
        id: 1,
        name: "Vicky Dávila",
        party: "Valientes",
        color: "#E91E63",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 2,
        name: "Juan Manuel Galán",
        party: "Nuevo Liberalismo",
        color: "#D32F2F",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 3,
        name: "Paloma Valencia",
        party: "Centro Democrático",
        color: "#1565C0",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 4,
        name: "Enrique Peñalosa",
        party: "Partido Verde Oxígeno",
        color: "#388E3C",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 5,
        name: "Juan Carlos Pinzón",
        party: "Partido Verde Oxígeno",
        color: "#43A047",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 6,
        name: "Aníbal Gaviria",
        party: "Unidos - La Fuerza de las Regiones",
        color: "#FF9800",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 7,
        name: "Mauricio Cárdenas",
        party: "Avanza Colombia",
        color: "#7B1FA2",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 8,
        name: "David Luna",
        party: "Sí Hay Un Camino",
        color: "#00ACC1",
        votes: 0,
        percentage: 0,
        mesas: 0,
        position: null,
        trend: 'stable',
        trendValue: 0
    },
    {
        id: 9,
        name: "Juan Daniel Oviedo",
        party: "Con Toda Por Colombia",
        color: "#5E35B1",
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
    if (!grid) {
        console.error('candidates-tracking-grid not found');
        return;
    }

    // Always ensure we have data - use fallback if no votes loaded
    const hasData = trackedCandidates.some(c => c.votes > 0);
    if (!hasData) {
        console.log('No candidate data, using fallback');
        simulateCandidateDataFallback();
    }

    console.log('Rendering candidates:', trackedCandidates.map(c => ({name: c.name, votes: c.votes})));

    // Sort by votes descending
    const sortedCandidates = [...trackedCandidates].sort((a, b) => b.votes - a.votes);

    // Assign positions
    sortedCandidates.forEach((c, i) => {
        const original = trackedCandidates.find(tc => tc.id === c.id);
        if (original) original.position = i + 1;
    });

    // Sort by position for display
    const sortedForDisplay = [...trackedCandidates].sort((a, b) => (a.position || 99) - (b.position || 99));

    grid.innerHTML = sortedForDisplay.map(candidate => {
        const positionClass = candidate.position <= 3 ? 'top-3' : '';
        const cardClass = candidate.position === 1 ? 'leading' :
                         (candidate.position <= 3 ? '' :
                         (candidate.position >= 7 ? 'danger' : 'warning'));

        const trendIcon = candidate.trend === 'up' ? '↑' :
                         (candidate.trend === 'down' ? '↓' : '→');
        const trendClass = candidate.trend === 'up' ? 'trend-up' :
                          (candidate.trend === 'down' ? 'trend-down' : 'trend-stable');
        const trendText = candidate.trend === 'up' ? `+${Math.abs(candidate.trendValue)}%` :
                         (candidate.trend === 'down' ? `-${Math.abs(candidate.trendValue)}%` : 'Estable');

        const maxVotes = Math.max(...trackedCandidates.map(c => c.votes));
        const progressWidth = maxVotes > 0 ? (candidate.votes / maxVotes * 100) : 0;
        const candidateColor = candidate.color || '#C9A227';

        return `
            <div class="candidate-track-card ${cardClass}" style="border-left: 4px solid ${candidateColor}">
                <div class="candidate-track-header">
                    <div>
                        <div class="candidate-track-name">${escapeHtml(candidate.name)}</div>
                        <div class="candidate-track-party" style="color: ${candidateColor}">${escapeHtml(candidate.party)}</div>
                    </div>
                    <span class="candidate-track-position ${positionClass}">#${candidate.position || '--'}</span>
                </div>

                <div class="candidate-track-stats">
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${formatNumber(candidate.votes)}</div>
                        <div class="candidate-stat-label">Votos E-14</div>
                    </div>
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${candidate.percentage.toFixed(1)}%</div>
                        <div class="candidate-stat-label">Porcentaje</div>
                    </div>
                    <div class="candidate-stat">
                        <div class="candidate-stat-value">${formatNumber(candidate.mesas)}</div>
                        <div class="candidate-stat-label">Mesas</div>
                    </div>
                </div>

                <div class="candidate-track-progress">
                    <div class="candidate-progress-bar">
                        <div class="candidate-progress-fill" style="width: ${progressWidth}%; background: ${candidateColor}"></div>
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

async function loadCandidatesFromAPI() {
    try {
        const response = await fetch('/api/campaign-team/reports/votes-by-candidate?contest_id=1');
        const data = await response.json();

        if (data.success && data.candidates) {
            // Update trackedCandidates with API data
            data.candidates.forEach(apiCandidate => {
                const candidate = trackedCandidates.find(c => c.name === apiCandidate.name);
                if (candidate) {
                    candidate.votes = apiCandidate.votes || 0;
                    candidate.percentage = apiCandidate.percentage || 0;
                    candidate.mesas = apiCandidate.mesas_processed || 0;
                    candidate.trend = apiCandidate.trend || 'stable';
                    candidate.trendValue = apiCandidate.trend_value || 0;
                    candidate.color = apiCandidate.color || candidate.color;
                    candidate.coverage = apiCandidate.coverage_pct || 0;
                }
            });
        }
    } catch (error) {
        console.error('Error loading candidates from API:', error);
        // Fallback to simulated data if API fails
        simulateCandidateDataFallback();
    }
}

function simulateCandidateDataFallback() {
    // Fallback data if API is unavailable
    const baseVotes = [
        { name: "Vicky Dávila", votes: 223000, percentage: 18.8, mesas: 5200, trend: 'up', trendValue: 2.3 },
        { name: "Juan Manuel Galán", votes: 208000, percentage: 17.5, mesas: 4800, trend: 'up', trendValue: 1.8 },
        { name: "Paloma Valencia", votes: 160000, percentage: 13.5, mesas: 4500, trend: 'stable', trendValue: 0 },
        { name: "Enrique Peñalosa", votes: 134000, percentage: 11.3, mesas: 4200, trend: 'up', trendValue: 0.8 },
        { name: "Juan Carlos Pinzón", votes: 143000, percentage: 12.0, mesas: 4100, trend: 'stable', trendValue: 0 },
        { name: "Aníbal Gaviria", votes: 120000, percentage: 10.1, mesas: 3800, trend: 'up', trendValue: 0.4 },
        { name: "Mauricio Cárdenas", votes: 87000, percentage: 7.3, mesas: 3500, trend: 'down', trendValue: -0.5 },
        { name: "David Luna", votes: 51000, percentage: 4.3, mesas: 3000, trend: 'down', trendValue: -1.2 },
        { name: "Juan Daniel Oviedo", votes: 62000, percentage: 5.2, mesas: 2800, trend: 'stable', trendValue: 0 }
    ];

    baseVotes.forEach(data => {
        const candidate = trackedCandidates.find(c => c.name === data.name);
        if (candidate) {
            candidate.votes = data.votes;
            candidate.percentage = data.percentage;
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

    // Check if we have Tesseract/Congress data
    const source = data.source || 'unknown';
    const partySummary = data.party_summary || [];
    const forms = data.forms || [];
    const totalForms = data.total_forms || forms.length || 0;
    const stats = data.stats || {};
    const totalVotes = stats.total_votes || data.total_votes || 0;
    const totalBlancos = stats.total_blancos || data.total_blancos || 0;
    const totalNulos = stats.total_nulos || data.total_nulos || 0;
    const totalUrna = totalVotes + totalBlancos + totalNulos;
    const totalParties = data.total_parties || partySummary.length || 0;

    // Determine election type from data
    const isCongressData = source === 'tesseract' || partySummary.length > 0;
    const firstForm = forms[0] || {};
    const header = firstForm.header || {};

    // Update header - show election name based on source
    const formsCountEl = document.getElementById('e14-forms-count');
    if (formsCountEl) formsCountEl.textContent = formatNumber(totalForms);

    const electionNameEl = document.getElementById('e14-election-name');
    if (electionNameEl) {
        if (isCongressData) {
            electionNameEl.textContent = header.election_name || 'CONGRESO 2022';
        } else {
            electionNameEl.textContent = 'ELECCIONES PRESIDENCIALES 2026';
        }
    }

    // Calculate average confidence from party_summary or forms
    let avgConfidence = 85;
    if (partySummary.length > 0) {
        const confSum = partySummary.reduce((sum, p) => sum + (p.avg_confidence || 0.85), 0);
        avgConfidence = (confSum / partySummary.length) * 100;
    } else if (forms.length > 0) {
        const confSum = forms.reduce((sum, f) => sum + (f.overall_confidence || 0.85), 0);
        avgConfidence = (confSum / forms.length) * 100;
    }

    // Update confidence with color class
    const confidenceEl = document.getElementById('e14-confidence');
    if (confidenceEl) {
        confidenceEl.textContent = `${avgConfidence.toFixed(0)}%`;
        confidenceEl.className = 'e14-meta-value e14-confidence';
        if (avgConfidence < 70) confidenceEl.classList.add('low');
        else if (avgConfidence < 85) confidenceEl.classList.add('medium');
    }

    // Update location bar with data from first form or aggregated stats
    document.getElementById('e14-dept').textContent = header.departamento || 'VARIOS';
    document.getElementById('e14-muni').textContent = header.municipio || `${totalForms} Mesas`;
    document.getElementById('e14-puesto').textContent = header.puesto || `${totalParties} Partidos`;
    document.getElementById('e14-mesa').textContent = formatNumber(totalForms);
    document.getElementById('e14-zona').textContent = header.zona || '-';

    const dateEl = document.getElementById('e14-date');
    if (dateEl) {
        dateEl.textContent = isCongressData ? (header.election_date || '13 MARZO 2022') : 'MAYO 2026';
    }

    // Update nivelación with totals
    const totalSufragantes = totalUrna;
    document.getElementById('e14-sufragantes').textContent = formatNumber(totalSufragantes);
    document.getElementById('e14-urna').textContent = formatNumber(totalUrna);
    document.getElementById('e14-validos').textContent = formatNumber(totalVotes);
    document.getElementById('e14-blancos').textContent = formatNumber(totalBlancos);
    document.getElementById('e14-nulos').textContent = formatNumber(totalNulos);

    // Render candidates/parties based on data source
    if (isCongressData && partySummary.length > 0) {
        // Render Congress 2022 parties from Tesseract data
        const topParties = partySummary.slice(0, 15).map((p, index) => ({
            candidate_name: p.party_name,
            party_name: `${p.mesas_count} mesas`,
            votes: p.total_votes,
            confidence: p.avg_confidence || 0.85,
            color: getPartyColor(index),
            is_party_vote: true
        }));
        renderPresidentialCandidates(topParties);
    } else {
        // Fallback: use tracked presidential candidates (2026)
        const trackedCands = data.tracked_candidates || [];
        if (trackedCands.length > 0) {
            renderPresidentialCandidates(trackedCands);
        } else {
            const fallbackCands = trackedCandidates.map(c => ({
                candidate_name: c.name,
                party_name: c.party,
                votes: c.votes,
                confidence: 0.87,
                color: c.color,
                is_party_vote: false
            }));
            renderPresidentialCandidates(fallbackCands);
        }
    }

    // Update footer with appropriate info
    const coveragePercent = totalForms > 0 ? Math.round((totalForms / 500) * 100) : 67;
    document.getElementById('e14-extraction-info').textContent =
        `Actualizado: ${new Date().toLocaleString('es-CO')} | ${isCongressData ? `${totalParties} partidos | ${formatNumber(totalVotes)} votos` : `Cobertura: ${coveragePercent}%`}`;

    // Update E-14 timestamp
    const e14TimeEl = document.getElementById('e14-update-time');
    if (e14TimeEl) {
        e14TimeEl.textContent = new Date().toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
    }
}

// Helper function to get party colors for Congress parties
function getPartyColor(index) {
    const colors = [
        '#E91E63', '#D32F2F', '#1565C0', '#388E3C', '#43A047',
        '#FF9800', '#7B1FA2', '#00ACC1', '#5E35B1', '#F44336',
        '#2196F3', '#4CAF50', '#FFC107', '#9C27B0', '#00BCD4'
    ];
    return colors[index % colors.length];
}

function renderPresidentialCandidates(candidates) {
    const grid = document.getElementById('e14-candidates-grid');
    if (!grid) return;

    if (!candidates || candidates.length === 0) {
        grid.innerHTML = '<div class="e14-empty">No hay candidatos registrados</div>';
        return;
    }

    // Sort by votes descending
    const sorted = [...candidates].sort((a, b) => (b.votes || 0) - (a.votes || 0));

    grid.innerHTML = sorted.map((candidate, index) => {
        const confidence = (candidate.confidence || 0.87) * 100;
        const confidenceClass = confidence < 70 ? 'low' : (confidence < 85 ? 'medium' : 'high');
        const color = candidate.color || '#C9A227';
        const position = index + 1;
        const positionClass = position <= 3 ? 'top-position' : '';

        return `
            <div class="e14-candidate-row ${positionClass}" style="border-left: 3px solid ${color}">
                <div class="e14-candidate-info">
                    <span class="e14-candidate-position">#${position}</span>
                    <span class="e14-candidate-name"><strong>${candidate.name || candidate.candidate_name}</strong></span>
                    <span class="e14-candidate-party" style="color: ${color}">${candidate.party || candidate.party_name}</span>
                </div>
                <div class="e14-candidate-votes">${formatNumber(candidate.votes || 0)}</div>
                <div class="e14-candidate-ocr">
                    <div class="e14-ocr-bar">
                        <div class="e14-ocr-fill ${confidenceClass}" style="width: ${confidence}%; background: ${color}"></div>
                    </div>
                    <span class="e14-ocr-value">${confidence.toFixed(0)}%</span>
                </div>
            </div>
        `;
    }).join('');
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
    const formsCountEl = document.getElementById('e14-forms-count');
    if (formsCountEl) formsCountEl.textContent = '0';
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
        const response = await fetch('/api/campaign-team/e14-live?limit=500');
        const data = await response.json();

        if (data.success) {
            // Store data globally for other functions
            window.e14LiveData = data;

            // Render the E-14 form
            renderE14LiveForm(data);

            // Process votes data for the votes table
            if (typeof processE14VotesData === 'function') {
                processE14VotesData();
            }

            // Populate map filters with available locations
            if (typeof populateMapFilters === 'function') {
                populateMapFilters();
            }

            // Update KPIs from E-14 data
            updateE14KPIs(data);
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
// E-14 FILTER FUNCTIONALITY
// ============================================================

let e14Filters = {
    dept: '',
    muni: '',
    puesto: '',
    mesa: '',
    risk: ''
};

// Load filter options from data
async function loadE14FilterOptions() {
    try {
        // Get departments from geography endpoint
        const deptResponse = await fetch('/api/geography/choropleth?mode=coverage');
        const deptData = await deptResponse.json();

        const deptSelect = document.getElementById('e14-filter-dept');
        if (deptSelect && deptData.features) {
            // Clear existing options
            deptSelect.innerHTML = '<option value="">Todos</option>';

            // Sort departments by name
            const depts = deptData.features
                .map(f => ({ code: f.properties.code, name: f.properties.name }))
                .sort((a, b) => a.name.localeCompare(b.name));

            depts.forEach(dept => {
                const option = document.createElement('option');
                option.value = dept.code;
                option.textContent = dept.name;
                deptSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading E-14 filter options:', error);
    }
}

function filterE14ByDept() {
    const deptSelect = document.getElementById('e14-filter-dept');
    e14Filters.dept = deptSelect.value;

    // Reset dependent filters
    document.getElementById('e14-filter-muni').innerHTML = '<option value="">Todos</option>';
    document.getElementById('e14-filter-puesto').innerHTML = '<option value="">Todos</option>';
    document.getElementById('e14-filter-mesa').innerHTML = '<option value="">Todas</option>';
    e14Filters.muni = '';
    e14Filters.puesto = '';
    e14Filters.mesa = '';

    if (e14Filters.dept) {
        loadMunicipiosForDept(e14Filters.dept);
    }

    applyE14Filters();
}

async function loadMunicipiosForDept(deptCode) {
    // For now, populate with demo municipalities
    const muniSelect = document.getElementById('e14-filter-muni');
    muniSelect.innerHTML = '<option value="">Todos</option>';

    // Demo municipalities - in production this would come from an API
    for (let i = 1; i <= 10; i++) {
        const option = document.createElement('option');
        option.value = `${deptCode}-${String(i).padStart(3, '0')}`;
        option.textContent = `Municipio ${i}`;
        muniSelect.appendChild(option);
    }
}

function filterE14ByMuni() {
    const muniSelect = document.getElementById('e14-filter-muni');
    e14Filters.muni = muniSelect.value;

    // Reset dependent filters
    document.getElementById('e14-filter-puesto').innerHTML = '<option value="">Todos</option>';
    document.getElementById('e14-filter-mesa').innerHTML = '<option value="">Todas</option>';
    e14Filters.puesto = '';
    e14Filters.mesa = '';

    if (e14Filters.muni) {
        loadPuestosForMuni(e14Filters.muni);
    }

    applyE14Filters();
}

async function loadPuestosForMuni(muniCode) {
    const puestoSelect = document.getElementById('e14-filter-puesto');
    puestoSelect.innerHTML = '<option value="">Todos</option>';

    // Demo puestos
    for (let i = 1; i <= 5; i++) {
        const option = document.createElement('option');
        option.value = `${muniCode}-${String(i).padStart(2, '0')}`;
        option.textContent = `Puesto ${i}`;
        puestoSelect.appendChild(option);
    }
}

function filterE14ByPuesto() {
    const puestoSelect = document.getElementById('e14-filter-puesto');
    e14Filters.puesto = puestoSelect.value;

    // Reset mesa filter
    document.getElementById('e14-filter-mesa').innerHTML = '<option value="">Todas</option>';
    e14Filters.mesa = '';

    if (e14Filters.puesto) {
        loadMesasForPuesto(e14Filters.puesto);
    }

    applyE14Filters();
}

async function loadMesasForPuesto(puestoCode) {
    const mesaSelect = document.getElementById('e14-filter-mesa');
    mesaSelect.innerHTML = '<option value="">Todas</option>';

    // Demo mesas
    for (let i = 1; i <= 8; i++) {
        const option = document.createElement('option');
        option.value = `${puestoCode}-${String(i).padStart(3, '0')}`;
        option.textContent = `Mesa ${i}`;
        mesaSelect.appendChild(option);
    }
}

function filterE14ByMesa() {
    const mesaSelect = document.getElementById('e14-filter-mesa');
    e14Filters.mesa = mesaSelect.value;
    applyE14Filters();
}

function filterE14ByRisk() {
    const riskSelect = document.getElementById('e14-filter-risk');
    e14Filters.risk = riskSelect.value;
    applyE14Filters();
}

async function applyE14Filters() {
    // Build query params
    const params = new URLSearchParams();
    params.append('limit', '500');  // Always get all forms
    if (e14Filters.dept) params.append('dept', e14Filters.dept);
    if (e14Filters.muni) params.append('muni', e14Filters.muni);
    if (e14Filters.puesto) params.append('puesto', e14Filters.puesto);
    if (e14Filters.mesa) params.append('mesa', e14Filters.mesa);
    if (e14Filters.risk) params.append('risk', e14Filters.risk);

    try {
        const url = `/api/campaign-team/e14-live?${params.toString()}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            renderE14LiveForm(data);
        }
    } catch (error) {
        console.error('Error applying E-14 filters:', error);
    }
}

function clearE14Filters() {
    e14Filters = { dept: '', muni: '', puesto: '', mesa: '', risk: '' };

    document.getElementById('e14-filter-dept').value = '';
    document.getElementById('e14-filter-muni').innerHTML = '<option value="">Todos</option>';
    document.getElementById('e14-filter-puesto').innerHTML = '<option value="">Todos</option>';
    document.getElementById('e14-filter-mesa').innerHTML = '<option value="">Todas</option>';
    document.getElementById('e14-filter-risk').value = '';

    refreshE14Data();
}

// Make filter functions global
window.filterE14ByDept = filterE14ByDept;
window.filterE14ByMuni = filterE14ByMuni;
window.filterE14ByPuesto = filterE14ByPuesto;
window.filterE14ByMesa = filterE14ByMesa;
window.filterE14ByRisk = filterE14ByRisk;
window.clearE14Filters = clearE14Filters;

// Load filter options on page load
document.addEventListener('DOMContentLoaded', () => {
    loadE14FilterOptions();
});

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
            window.contiendaIncidencias = allIncidents;
            if (typeof updateContiendaStats === 'function') {
                updateContiendaStats();
            }
            window.dispatchEvent(new Event('contienda:incidents-updated'));
            if (typeof window.onContiendaIncidentsUpdated === 'function') {
                window.onContiendaIncidentsUpdated();
            }
        }
    } catch (error) {
        console.error('Error loading incidents:', error);
        const tbody = document.getElementById('incident-tbody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: var(--muted);">Error cargando incidentes</td></tr>';
        }
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
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    setEl('kpi-total', formatNumber(kpis.mesas_total));
    setEl('kpi-testigo', formatNumber(kpis.mesas_testigo));
    setEl('kpi-rnec', formatNumber(kpis.mesas_rnec));
    setEl('kpi-reconciled', formatNumber(kpis.mesas_reconciliadas));
    setEl('kpi-p0', kpis.incidentes_p0);
    setEl('kpi-coverage', `${kpis.cobertura_pct}%`);
}

function updateTimeline(timeline, kpis) {
    const setBar = (id, pct) => {
        const el = document.getElementById(id);
        if (el) el.style.width = `${pct}%`;
    };
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };

    // Update progress bars
    setBar('timeline-testigo-bar', kpis.testigo_pct);
    setEl('timeline-testigo-pct', `${kpis.testigo_pct}%`);

    setBar('timeline-rnec-bar', kpis.rnec_pct);
    setEl('timeline-rnec-pct', `${kpis.rnec_pct}%`);

    setBar('timeline-reconciled-bar', kpis.reconciliadas_pct);
    setEl('timeline-reconciled-pct', `${kpis.reconciliadas_pct}%`);

    // Update last RNEC update time
    if (kpis.last_rnec_update) {
        const lastUpdate = new Date(kpis.last_rnec_update);
        setEl('timeline-last-rnec', lastUpdate.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' }));
    }
}

function startTimelineCountdown() {
    const countdownEl = document.getElementById('timeline-countdown');
    if (!countdownEl) return; // Don't run if element doesn't exist

    setInterval(() => {
        timelineCountdown--;
        if (timelineCountdown <= 0) {
            timelineCountdown = 30;
            loadWarRoomKPIs();
            loadIncidents();
        }
        if (countdownEl) countdownEl.textContent = `${timelineCountdown}s`;
    }, 1000);
}

function updateIncidentStats(data) {
    const setEl = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    };
    setEl('incident-p0-count', data.p0_count || 0);
    setEl('incident-p1-count', data.p1_count || 0);
    setEl('incident-total-count', data.open_count || 0);
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
                        <button class="incident-action-btn primary" onclick="enviarTestigoARevision(${incident.id}, '${incident.mesa_id}')" title="Enviar testigo a revisar esta mesa">
                            Enviar Testigo
                        </button>
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

// Store markers layer globally
let markersLayer = null;

function renderChoropleth(data) {
    if (!colombiaMap) return;

    // Remove existing layers
    if (geoJsonLayer) {
        colombiaMap.removeLayer(geoJsonLayer);
    }
    if (markersLayer) {
        colombiaMap.removeLayer(markersLayer);
    }

    // Create GeoJSON layer for borders only (transparent fill)
    geoJsonLayer = L.geoJSON(data, {
        style: styleBordersOnly,
        onEachFeature: onEachFeatureBorders
    }).addTo(colombiaMap);

    // Create markers layer for department dots
    markersLayer = L.layerGroup().addTo(colombiaMap);

    // Add circle markers at each department centroid
    if (data.features) {
        data.features.forEach(feature => {
            const props = feature.properties;
            const centroid = getCentroid(feature.geometry);

            if (centroid) {
                const marker = createDepartmentMarker(centroid, props);
                markersLayer.addLayer(marker);
            }
        });
    }

    // Fit bounds
    if (geoJsonLayer.getBounds().isValid()) {
        colombiaMap.fitBounds(geoJsonLayer.getBounds(), { padding: [20, 20] });
    }
}

function styleBordersOnly(feature) {
    return {
        fillColor: 'transparent',
        fillOpacity: 0,
        weight: 1,
        opacity: 0.3,
        color: '#555'
    };
}

function onEachFeatureBorders(feature, layer) {
    const props = feature.properties;

    // Click handler for polygon area
    layer.on('click', () => {
        selectDepartment(props.code, props.name);
    });
}

function getCentroid(geometry) {
    if (!geometry || !geometry.coordinates) return null;

    if (geometry.type === 'Polygon') {
        return calculatePolygonCentroid(geometry.coordinates[0]);
    } else if (geometry.type === 'MultiPolygon') {
        // Use the largest polygon's centroid
        let largestArea = 0;
        let centroid = null;
        geometry.coordinates.forEach(poly => {
            const area = calculatePolygonArea(poly[0]);
            if (area > largestArea) {
                largestArea = area;
                centroid = calculatePolygonCentroid(poly[0]);
            }
        });
        return centroid;
    }
    return null;
}

function calculatePolygonCentroid(coords) {
    let sumLat = 0, sumLng = 0;
    coords.forEach(coord => {
        sumLng += coord[0];
        sumLat += coord[1];
    });
    return [sumLat / coords.length, sumLng / coords.length];
}

function calculatePolygonArea(coords) {
    let area = 0;
    for (let i = 0; i < coords.length - 1; i++) {
        area += coords[i][0] * coords[i + 1][1];
        area -= coords[i + 1][0] * coords[i][1];
    }
    return Math.abs(area / 2);
}

function createDepartmentMarker(centroid, props) {
    const metrics = props.metrics || {};
    const value = metrics.value || 0;
    const color = props.fill_color || getColorForValue(value);

    // Size based on number of mesas (8-16px radius)
    const mesas = metrics.mesas_total || 0;
    const radius = Math.min(16, Math.max(8, 8 + (mesas / 1000)));

    const marker = L.circleMarker(centroid, {
        radius: radius,
        fillColor: color,
        fillOpacity: 0.9,
        color: '#1C1C1C',
        weight: 2
    });

    // Store properties for easy access
    marker.deptProps = props;

    // Hover: show info in side panel
    marker.on('mouseover', (e) => {
        e.target.setStyle({
            radius: radius + 3,
            fillOpacity: 1,
            weight: 3,
            color: '#C9A227'
        });
        showDepartmentPreview(props);
    });

    marker.on('mouseout', (e) => {
        e.target.setStyle({
            radius: radius,
            fillOpacity: 0.9,
            weight: 2,
            color: '#1C1C1C'
        });
        // Only hide preview if not selected
        if (selectedDepartment !== props.code) {
            hideDepartmentPreview();
        }
    });

    // Click: select department
    marker.on('click', () => {
        selectDepartment(props.code, props.name);
    });

    return marker;
}

function getColorForValue(value) {
    if (value >= 80) return '#4A7C59';
    if (value >= 60) return '#7CB342';
    if (value >= 40) return '#D4A017';
    if (value >= 20) return '#E65100';
    return '#8B3A3A';
}

function showDepartmentPreview(props) {
    const panel = document.getElementById('dept-info-panel');
    const titleEl = document.getElementById('dept-panel-title');
    const subtitleEl = document.getElementById('dept-panel-subtitle');
    const contentEl = document.getElementById('dept-info-content');

    if (!panel || !props) return;

    const metrics = props.metrics || {};

    titleEl.textContent = props.name || 'Departamento';
    subtitleEl.textContent = `Código: ${props.code || '--'}`;

    contentEl.innerHTML = `
        <div class="dept-preview-stats">
            <div class="dept-stat-row">
                <span class="dept-stat-label">${getModeLabel(currentMapMode)}</span>
                <span class="dept-stat-value" style="color: ${props.fill_color || '#C9A227'}">${(metrics.value || 0).toFixed(1)}%</span>
            </div>
            <div class="dept-stat-row">
                <span class="dept-stat-label">Mesas Total</span>
                <span class="dept-stat-value">${formatNumber(metrics.mesas_total || 0)}</span>
            </div>
            <div class="dept-stat-row">
                <span class="dept-stat-label">Mesas Procesadas</span>
                <span class="dept-stat-value">${formatNumber(metrics.mesas_processed || 0)}</span>
            </div>
            <div class="dept-stat-row">
                <span class="dept-stat-label">Incidentes P0</span>
                <span class="dept-stat-value ${(metrics.incidents_p0 || 0) > 0 ? 'danger' : ''}">${metrics.incidents_p0 || 0}</span>
            </div>
            <div class="dept-stat-row">
                <span class="dept-stat-label">Incidentes P1</span>
                <span class="dept-stat-value ${(metrics.incidents_p1 || 0) > 0 ? 'warning' : ''}">${metrics.incidents_p1 || 0}</span>
            </div>
        </div>
        <div class="dept-preview-hint">Click para ver detalles completos</div>
    `;

    panel.classList.add('preview-active');
}

function hideDepartmentPreview() {
    const panel = document.getElementById('dept-info-panel');
    if (panel && !selectedDepartment) {
        panel.classList.remove('preview-active');

        document.getElementById('dept-panel-title').textContent = 'Seleccione un Departamento';
        document.getElementById('dept-panel-subtitle').textContent = 'Hover sobre un punto para vista previa';
        document.getElementById('dept-info-content').innerHTML = `
            <div class="dept-info-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                    <circle cx="12" cy="10" r="3"/>
                </svg>
                <p>Pase el mouse sobre un punto del mapa para ver vista previa, o haga click para ver detalles completos.</p>
            </div>
        `;
    }
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

// ============================================================
// MAP FILTERS
// ============================================================

function populateMapFilters() {
    const forms = window.e14LiveData?.forms || [];

    // Extract unique values
    const depts = new Set();
    const munis = new Set();
    const zonas = new Set();
    const puestos = new Set();

    forms.forEach(form => {
        const header = form.header || {};
        if (header.departamento_name) depts.add(header.departamento_name);
        if (header.municipio_name) munis.add(header.municipio_name);
        if (header.zona) zonas.add(header.zona);
        if (header.lugar) puestos.add(header.lugar);
    });

    // Populate dropdowns
    populateSelect('map-filter-dept', Array.from(depts).sort());
    populateSelect('map-filter-muni', Array.from(munis).sort());
    populateSelect('map-filter-zona', Array.from(zonas).sort());
    populateSelect('map-filter-puesto', Array.from(puestos).sort());
}

function populateSelect(id, options) {
    const select = document.getElementById(id);
    if (!select) return;

    // Keep first option (Todos/Todas)
    const firstOption = select.options[0];
    select.innerHTML = '';
    select.appendChild(firstOption);

    options.forEach(opt => {
        const option = document.createElement('option');
        option.value = opt;
        option.textContent = opt;
        select.appendChild(option);
    });
}

function filterMapByDept() {
    const dept = document.getElementById('map-filter-dept')?.value || '';
    updateMapFilter('dept', dept);

    // Reset dependent filters
    document.getElementById('map-filter-muni').value = '';
    document.getElementById('map-filter-zona').value = '';
    document.getElementById('map-filter-puesto').value = '';

    applyMapFilters();
}

function filterMapByMuni() {
    const muni = document.getElementById('map-filter-muni')?.value || '';
    updateMapFilter('muni', muni);
    applyMapFilters();
}

function filterMapByZona() {
    const zona = document.getElementById('map-filter-zona')?.value || '';
    updateMapFilter('zona', zona);
    applyMapFilters();
}

function filterMapByPuesto() {
    const puesto = document.getElementById('map-filter-puesto')?.value || '';
    updateMapFilter('puesto', puesto);
    applyMapFilters();
}

function updateMapFilter(key, value) {
    if (!window.mapFilters) window.mapFilters = {};
    window.mapFilters[key] = value;
}

function applyMapFilters() {
    const filters = window.mapFilters || {};
    console.log('Applying map filters:', filters);

    // Highlight selected department on map if SVG map exists
    if (typeof highlightDepartment === 'function' && filters.dept) {
        highlightDepartment(filters.dept);
    }

    // Filter and update map markers/data
    filterMapData(filters);
}

function clearMapFilters() {
    document.getElementById('map-filter-dept').value = '';
    document.getElementById('map-filter-muni').value = '';
    document.getElementById('map-filter-zona').value = '';
    document.getElementById('map-filter-puesto').value = '';

    window.mapFilters = {};
    applyMapFilters();
}

function filterMapData(filters) {
    // This will filter the map data based on selected filters
    // Implementation depends on map library used
    const forms = window.e14LiveData?.forms || [];

    const filtered = forms.filter(form => {
        const header = form.header || {};
        if (filters.dept && header.departamento_name !== filters.dept) return false;
        if (filters.muni && header.municipio_name !== filters.muni) return false;
        if (filters.zona && header.zona !== filters.zona) return false;
        if (filters.puesto && header.lugar !== filters.puesto) return false;
        return true;
    });

    console.log(`Filtered to ${filtered.length} forms`);

    // Update map legend or stats
    updateMapStats(filtered);
}

function updateMapStats(filteredForms) {
    // Update any map-related statistics
    const statsEl = document.getElementById('map-filtered-count');
    if (statsEl) {
        statsEl.textContent = `${filteredForms.length} mesas`;
    }
}

// Make map filter functions globally available
window.filterMapByDept = filterMapByDept;
window.filterMapByMuni = filterMapByMuni;
window.filterMapByZona = filterMapByZona;
window.filterMapByPuesto = filterMapByPuesto;
window.clearMapFilters = clearMapFilters;

// ============================================================
// INCIDENT ACTIONS
// ============================================================

// Estado para el modal de enviar testigo
let currentIncidentForAssignment = null;
let witnessesForAssignment = [];

function enviarTestigoARevision(incidentId, mesaId) {
    // Find the incident details
    const incident = allIncidents.find(i => i.id === incidentId);
    if (!incident) {
        alert('Incidente no encontrado');
        return;
    }

    currentIncidentForAssignment = incident;

    // Buscar testigos que cubren la zona del incidente
    witnessesForAssignment = allWitnesses.filter(w => {
        // Solo testigos disponibles
        if (w.status !== 'available') return false;

        // Filtrar por zona de cobertura
        if (w.coverage_dept_name && incident.dept_name) {
            if (w.coverage_dept_name !== incident.dept_name) return false;

            // Si tiene municipio, verificar
            if (w.coverage_muni_name && incident.muni_name) {
                if (w.coverage_muni_name !== incident.muni_name) return false;
            }
        }
        return true;
    });

    // Si no hay testigos con cobertura, mostrar todos los disponibles
    if (witnessesForAssignment.length === 0) {
        witnessesForAssignment = allWitnesses.filter(w => w.status === 'available');
    }

    if (witnessesForAssignment.length === 0) {
        alert(`No hay testigos disponibles.\n\nGenere un QR de registro para agregar testigos.`);
        return;
    }

    // Mostrar modal de selección
    openAssignWitnessModal(incident, witnessesForAssignment);
}

function openAssignWitnessModal(incident, witnesses) {
    // Crear modal dinámicamente si no existe
    let modal = document.getElementById('assign-witness-modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'assign-witness-modal';
        modal.className = 'modal-overlay';
        modal.innerHTML = `
            <div class="modal" style="max-width: 600px;">
                <div class="modal-header">
                    <h3 class="modal-title">Enviar Testigo a Mesa</h3>
                    <button class="modal-close" onclick="closeAssignWitnessModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="assign-witness-incident-info" style="background: var(--panel); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;"></div>
                    <h4 style="margin-bottom: 0.5rem;">Testigos Disponibles en la Zona</h4>
                    <p style="color: var(--muted); font-size: 0.8rem; margin-bottom: 1rem;">Seleccione un testigo para enviar a revisar esta mesa</p>
                    <div id="assign-witness-list" style="max-height: 300px; overflow-y: auto;"></div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    // Llenar info del incidente
    document.getElementById('assign-witness-incident-info').innerHTML = `
        <p style="margin: 0 0 0.5rem;"><strong>Mesa:</strong> ${escapeHtml(incident.mesa_id)}</p>
        <p style="margin: 0 0 0.5rem;"><strong>Ubicación:</strong> ${escapeHtml(incident.dept_name || '')} > ${escapeHtml(incident.muni_name || '')} > ${escapeHtml(incident.puesto_name || '')}</p>
        <p style="margin: 0 0 0.5rem;"><strong>Incidente:</strong> <span class="severity-badge ${incident.severity?.toLowerCase()}">${incident.severity}</span> ${escapeHtml(incident.type_label || incident.type)}</p>
        <p style="margin: 0;"><strong>Descripción:</strong> ${escapeHtml(incident.description || 'Sin descripción')}</p>
    `;

    // Llenar lista de testigos
    const listContainer = document.getElementById('assign-witness-list');
    listContainer.innerHTML = witnesses.map(w => `
        <div class="witness-select-card" style="background: var(--bg); padding: 1rem; border-radius: 8px; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border);">
            <div>
                <div style="font-weight: 600;">${escapeHtml(w.name)}</div>
                <div style="font-size: 0.85rem; color: var(--muted);">
                    <span style="margin-right: 1rem;">Tel: ${escapeHtml(w.phone)}</span>
                    ${w.push_enabled ? '<span style="color: var(--success);">Push activo</span>' : '<span style="color: var(--warning);">Sin push</span>'}
                </div>
                <div style="font-size: 0.8rem; color: var(--muted);">
                    Cubre: ${escapeHtml(w.coverageDisplay || 'Sin zona asignada')}
                </div>
            </div>
            <button class="btn-action primary" onclick="confirmAssignWitness(${w.id}, ${w.push_enabled})">
                ${w.push_enabled ? 'Notificar' : 'Asignar'}
            </button>
        </div>
    `).join('');

    if (witnesses.length === 0) {
        listContainer.innerHTML = '<div class="empty-state"><p>No hay testigos disponibles</p></div>';
    }

    modal.classList.add('active');
}

function closeAssignWitnessModal() {
    const modal = document.getElementById('assign-witness-modal');
    if (modal) {
        modal.classList.remove('active');
    }
    currentIncidentForAssignment = null;
    witnessesForAssignment = [];
}

async function confirmAssignWitness(witnessId, hasPush) {
    const witness = witnessesForAssignment.find(w => w.id === witnessId);
    const incident = currentIncidentForAssignment;

    if (!witness || !incident) {
        alert('Error: datos incompletos');
        return;
    }

    const action = hasPush ? 'notificar' : 'asignar';
    if (!confirm(`¿${hasPush ? 'Enviar notificación a' : 'Asignar a'} ${witness.name} para revisar mesa ${incident.mesa_id}?`)) {
        return;
    }

    try {
        // 1. Crear asignación via API
        const assignResponse = await fetch(`${WITNESS_API}/assignments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                witness_id: witnessId,
                polling_table_id: parseInt(incident.mesa_id.replace(/\D/g, '')) || 1,
                contest_id: 1,
                priority: incident.severity === 'CRITICAL' ? 10 : (incident.severity === 'HIGH' ? 7 : 5),
                reason: `Incidente #${incident.id}: ${incident.type_label || incident.type} - ${incident.description || ''}`,
                send_notification: hasPush
            })
        });

        const assignData = await assignResponse.json();

        if (!assignResponse.ok) {
            throw new Error(assignData.error || 'Error creando asignación');
        }

        // 2. Actualizar estado del incidente localmente
        incident.status = 'ASSIGNED';
        incident.assigned_to = witness.name;
        incident.assigned_at = new Date().toISOString();

        // 3. Actualizar estado del testigo localmente
        witness.status = 'busy';

        // 4. Mostrar confirmación
        const pushMsg = hasPush ? '\nSe envió notificación push al testigo.' : '\nEl testigo NO tiene push activo - contactarlo manualmente.';
        alert(`Testigo ${witness.name} asignado a mesa ${incident.mesa_id}.${pushMsg}\n\nTeléfono: ${witness.phone}`);

        // 5. Cerrar modal y refrescar tabla
        closeAssignWitnessModal();
        renderIncidentTable();

        console.log(`Asignación creada: Testigo ${witnessId} -> Incidente ${incident.id}`);

    } catch (error) {
        console.error('Error en asignación:', error);
        alert('Error: ' + error.message);
    }
}

// Legacy function - redirect to new flow
function enviarTestigoARevisionLegacy(incidentId, mesaId) {
    // Find the incident details
    const incident = allIncidents.find(i => i.id === incidentId);
    if (!incident) {
        alert('Incidente no encontrado');
        return;
    }

    // Find available witnesses for this location
    const availableWitnesses = allWitnesses.filter(w =>
        w.status === 'available' &&
        (w.coverage_dept_name === incident.dept_name || !w.coverage_dept_name)
    );

    if (availableWitnesses.length === 0) {
        alert(`No hay testigos disponibles para la zona de ${incident.dept_name || mesaId}`);
        return;
    }

    // Show witness selection modal
    const witnessOptions = availableWitnesses.map(w =>
        `${w.name} (${w.phone || 'Sin teléfono'})`
    ).join('\n');

    const selectedIndex = prompt(
        `Seleccione un testigo para enviar a mesa ${mesaId}:\n\n` +
        availableWitnesses.map((w, i) => `${i + 1}. ${w.name}`).join('\n') +
        `\n\nIngrese el número (1-${availableWitnesses.length}):`
    );

    if (!selectedIndex) return;

    const idx = parseInt(selectedIndex) - 1;
    if (idx < 0 || idx >= availableWitnesses.length) {
        alert('Selección inválida');
        return;
    }

    const selectedWitness = availableWitnesses[idx];

    // Confirm and send
    if (confirm(`¿Enviar a ${selectedWitness.name} a revisar mesa ${mesaId}?`)) {
        // Update incident status
        incident.status = 'ASSIGNED';
        incident.assigned_to = selectedWitness.name;
        incident.assigned_at = new Date().toISOString();

        // Update witness status
        selectedWitness.status = 'ASSIGNED';
        selectedWitness.assigned_mesa = mesaId;

        // Log the action
        console.log(`Testigo ${selectedWitness.name} asignado a mesa ${mesaId} para incidente ${incidentId}`);

        alert(`✅ Testigo ${selectedWitness.name} enviado a revisar mesa ${mesaId}`);

        // Refresh the incident table
        renderIncidentTable();
    }
}

// Make incident action globally available
window.enviarTestigoARevision = enviarTestigoARevision;
window.closeAssignWitnessModal = closeAssignWitnessModal;
window.confirmAssignWitness = confirmAssignWitness;

// ============================================================
// IMMEDIATE INITIALIZATION - Ensure candidates render
// ============================================================
(function initCandidatesNow() {
    // If DOM is already loaded, render immediately
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        setTimeout(() => {
            console.log('Immediate candidate render triggered');
            simulateCandidateDataFallback();
            renderTrackedCandidates();
        }, 500);
    }
})();

// ============================================================
// WITNESS API INTEGRATION
// ============================================================

const WITNESS_API = '/api/witness';
let currentQRData = null;

/**
 * Load witnesses from API
 */
async function loadWitnessesFromAPI() {
    try {
        const response = await fetch(`${WITNESS_API}/list`);
        const data = await response.json();

        if (data.success) {
            // Update allWitnesses with real data including coverage
            allWitnesses = data.witnesses.map(w => ({
                id: w.id,
                name: w.full_name,
                phone: w.phone,
                currentLocation: w.current_zone || 'Sin ubicacion',
                status: w.status === 'ACTIVE' ? 'available' : 'busy',
                distance: '0.0',
                push_enabled: w.push_enabled,
                lat: w.current_lat,
                lon: w.current_lon,
                // Zona de cobertura
                coverage_dept_code: w.coverage_dept_code,
                coverage_dept_name: w.coverage_dept_name,
                coverage_muni_code: w.coverage_muni_code,
                coverage_muni_name: w.coverage_muni_name,
                coverage_station_name: w.coverage_station_name,
                // Para mostrar en UI
                coverageDisplay: formatCoverage(w)
            }));

            // Update stats summary
            const statsEl = document.getElementById('witness-stats-summary');
            if (statsEl) {
                statsEl.textContent = `${data.total} testigos registrados | ${data.push_enabled_count} con push activo`;
            }

            console.log(`Loaded ${data.total} witnesses from API`);
            renderWitnessTab();
        }
    } catch (error) {
        console.error('Error loading witnesses from API:', error);
        // Fall back to mock data
    }
}

/**
 * Formatea la zona de cobertura para mostrar
 */
function formatCoverage(witness) {
    const parts = [];
    if (witness.coverage_dept_name) parts.push(witness.coverage_dept_name);
    if (witness.coverage_muni_name) parts.push(witness.coverage_muni_name);
    if (witness.coverage_station_name) parts.push(witness.coverage_station_name);
    return parts.length > 0 ? parts.join(' > ') : 'Sin zona asignada';
}

/**
 * Filtra testigos por zona de cobertura
 */
async function loadWitnessesByCoverage(deptCode, muniCode = null, stationName = null) {
    try {
        let url = `${WITNESS_API}/by-coverage?dept_code=${deptCode}`;
        if (muniCode) url += `&muni_code=${muniCode}`;
        if (stationName) url += `&station_name=${encodeURIComponent(stationName)}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            return data.witnesses.map(w => ({
                id: w.id,
                name: w.full_name,
                phone: w.phone,
                status: w.status === 'ACTIVE' ? 'available' : 'busy',
                push_enabled: w.push_enabled,
                coverageDisplay: formatCoverage(w)
            }));
        }
        return [];
    } catch (error) {
        console.error('Error loading witnesses by coverage:', error);
        return [];
    }
}

/**
 * Load witness stats
 */
async function loadWitnessStats() {
    try {
        const response = await fetch(`${WITNESS_API}/stats`);
        const data = await response.json();

        if (data.success) {
            const statsEl = document.getElementById('witness-stats-summary');
            if (statsEl) {
                statsEl.textContent = `${data.stats.total_registered} testigos | ${data.stats.push_enabled} con push | ${data.stats.active} activos`;
            }
        }
    } catch (error) {
        console.error('Error loading witness stats:', error);
    }
}

// ============================================================
// WITNESS REGISTRATION FORM
// ============================================================

function toggleRegisterForm() {
    const form = document.getElementById('register-witness-form');
    if (!form) return;

    const isVisible = form.style.display !== 'none';
    form.style.display = isVisible ? 'none' : 'block';

    // Populate departments if showing
    if (!isVisible) {
        populateWitnessDepartments();
    }
}

// Department codes mapping
const DEPT_CODES = {
    'Antioquia': '05', 'Atlántico': '08', 'Bogotá D.C.': '11', 'Bolívar': '13',
    'Boyacá': '15', 'Caldas': '17', 'Caquetá': '18', 'Cauca': '19', 'Cesar': '20',
    'Córdoba': '23', 'Cundinamarca': '25', 'Chocó': '27', 'Huila': '41',
    'La Guajira': '44', 'Magdalena': '47', 'Meta': '50', 'Nariño': '52',
    'Norte de Santander': '54', 'Quindío': '63', 'Risaralda': '66', 'Santander': '68',
    'Sucre': '70', 'Tolima': '73', 'Valle del Cauca': '76'
};

function populateWitnessDepartments() {
    const deptSelect = document.getElementById('witness-dept');
    if (!deptSelect) return;

    const defaultDepts = Object.keys(DEPT_CODES).sort();

    deptSelect.innerHTML = '<option value="">Seleccionar...</option>';
    defaultDepts.forEach(dept => {
        const option = document.createElement('option');
        option.value = DEPT_CODES[dept];  // Use code as value
        option.textContent = dept;
        option.dataset.name = dept;  // Store name in data attribute
        deptSelect.appendChild(option);
    });
}

async function registerWitness() {
    const name = document.getElementById('witness-name')?.value?.trim();
    const phone = document.getElementById('witness-phone')?.value?.trim();
    const email = document.getElementById('witness-email')?.value?.trim();
    const deptSelect = document.getElementById('witness-dept');
    const deptCode = deptSelect?.value || '11';
    const deptName = deptSelect?.options[deptSelect.selectedIndex]?.dataset?.name || 'Bogotá D.C.';

    // Validation
    if (!name || !phone) {
        showRegisterMessage('Por favor ingresa nombre y teléfono', 'error');
        return;
    }

    if (phone.length < 10) {
        showRegisterMessage('Teléfono debe tener al menos 10 dígitos', 'error');
        return;
    }

    showRegisterMessage('Registrando...', 'info');

    try {
        // First generate a QR code to get a valid code
        const qrResponse = await fetch(`${WITNESS_API}/qr/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_uses: 1, expires_hours: 1 })
        });
        const qrData = await qrResponse.json();

        if (!qrData.code) {
            throw new Error('No se pudo generar código de registro');
        }

        // Now register the witness with correct field names
        const response = await fetch(`${WITNESS_API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                qr_code: qrData.code,
                full_name: name,
                phone: phone,
                email: email || null,
                coverage_dept_code: deptCode,
                coverage_dept_name: deptName
            })
        });

        const data = await response.json();

        if (data.success) {
            showRegisterMessage(`Testigo "${name}" registrado exitosamente`, 'success');
            // Clear form
            document.getElementById('witness-name').value = '';
            document.getElementById('witness-phone').value = '';
            document.getElementById('witness-email').value = '';
            document.getElementById('witness-dept').selectedIndex = 0;
            // Refresh witness list
            setTimeout(() => {
                loadWitnessesFromAPI();
                toggleRegisterForm();
            }, 1500);
        } else {
            throw new Error(data.error || 'Error al registrar');
        }
    } catch (error) {
        console.error('Register error:', error);
        showRegisterMessage(error.message || 'Error al registrar testigo', 'error');
    }
}

function showRegisterMessage(msg, type) {
    const el = document.getElementById('register-message');
    if (!el) return;
    el.textContent = msg;
    el.style.display = 'block';
    el.style.color = type === 'error' ? '#e74c3c' : type === 'info' ? '#C9A227' : '#27ae60';
    if (type === 'success') {
        setTimeout(() => { el.style.display = 'none'; }, 3000);
    }
}

// Legacy QR functions (kept for compatibility)
function openGenerateQRModal() {
    toggleRegisterForm();

    // Populate filters (reuse existing department data if available)
    populateQRFilters();
}

function closeQRModal() {
    const modal = document.getElementById('qr-modal');
    if (modal) {
        modal.classList.remove('active');
    }
    currentQRData = null;
}

function populateQRFilters() {
    const deptSelect = document.getElementById('qr-dept-filter');
    const muniSelect = document.getElementById('qr-muni-filter');

    if (!deptSelect || !muniSelect) return;

    // Get unique departments from allMesas (handle both field naming conventions)
    const depts = [...new Set(allMesas.map(m => m.departamento || m.dept).filter(Boolean))].sort();

    deptSelect.innerHTML = '<option value="">Todos los departamentos</option>';
    depts.forEach(dept => {
        const option = document.createElement('option');
        option.value = dept;
        option.textContent = dept;
        deptSelect.appendChild(option);
    });

    // Update municipalities when department changes
    deptSelect.onchange = () => {
        const selectedDept = deptSelect.value;
        const munis = [...new Set(
            allMesas
                .filter(m => !selectedDept || (m.departamento || m.dept) === selectedDept)
                .map(m => m.municipio || m.muni)
                .filter(Boolean)
        )].sort();

        muniSelect.innerHTML = '<option value="">Todos los municipios</option>';
        munis.forEach(muni => {
            const option = document.createElement('option');
            option.value = muni;
            option.textContent = muni;
            muniSelect.appendChild(option);
        });
    };
}

async function generateQRCode() {
    const deptCode = document.getElementById('qr-dept-filter').value;
    const muniCode = document.getElementById('qr-muni-filter').value;
    const maxUses = parseInt(document.getElementById('qr-max-uses').value);

    try {
        const response = await fetch(`${WITNESS_API}/qr/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                dept_code: deptCode || null,
                muni_code: muniCode || null,
                max_uses: maxUses,
                expires_hours: 72
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error generando QR');
        }

        currentQRData = data;

        // Show result
        document.getElementById('qr-form-section').style.display = 'none';
        document.getElementById('qr-result-section').style.display = 'block';
        document.getElementById('qr-image').src = data.qr_url;
        document.getElementById('qr-url-display').textContent = data.registration_url;

        console.log('QR generated:', data.code);

    } catch (error) {
        alert('Error: ' + error.message);
        console.error('QR generation error:', error);
    }
}

function copyQRLink() {
    if (!currentQRData) return;

    navigator.clipboard.writeText(currentQRData.registration_url)
        .then(() => alert('Enlace copiado al portapapeles'))
        .catch(err => {
            console.error('Error copying:', err);
            // Fallback
            prompt('Copie este enlace:', currentQRData.registration_url);
        });
}

function downloadQR() {
    if (!currentQRData) return;

    const link = document.createElement('a');
    link.download = `castor-qr-testigo-${currentQRData.code.slice(0, 8)}.png`;
    link.href = currentQRData.qr_url;
    link.click();
}

function generateNewQR() {
    document.getElementById('qr-form-section').style.display = 'block';
    document.getElementById('qr-result-section').style.display = 'none';
    currentQRData = null;
}

// ============================================================
// WITNESS ASSIGNMENT VIA API
// ============================================================

async function assignWitnessToMesa(witnessId, mesaId, reason) {
    try {
        const response = await fetch(`${WITNESS_API}/assignments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                witness_id: witnessId,
                polling_table_id: parseInt(mesaId),
                contest_id: 1,
                priority: 5,
                reason: reason || 'Asignacion desde dashboard',
                send_notification: true
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error en asignacion');
        }

        return data;
    } catch (error) {
        console.error('Assignment error:', error);
        throw error;
    }
}

async function sendPushNotification(witnessIds, title, body, type = 'ALERT') {
    try {
        const response = await fetch(`${WITNESS_API}/notify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                witness_ids: witnessIds,
                notification_type: type,
                title: title,
                body: body
            })
        });

        const data = await response.json();
        console.log(`Notification sent to ${data.sent_count} witnesses`);
        return data;
    } catch (error) {
        console.error('Notification error:', error);
        throw error;
    }
}

// ============================================================
// NEARBY WITNESSES FROM API
// ============================================================

async function findNearbyWitnessesAPI(lat, lon, radiusKm = 5) {
    try {
        const response = await fetch(`${WITNESS_API}/nearby`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                lat: lat,
                lon: lon,
                radius_km: radiusKm,
                limit: 20
            })
        });

        const data = await response.json();
        return data.witnesses || [];
    } catch (error) {
        console.error('Nearby witnesses error:', error);
        return [];
    }
}

// Make QR functions globally available
window.openGenerateQRModal = openGenerateQRModal;
window.closeQRModal = closeQRModal;
window.generateQRCode = generateQRCode;
window.copyQRLink = copyQRLink;
window.downloadQR = downloadQR;
window.generateNewQR = generateNewQR;
window.loadWitnessesFromAPI = loadWitnessesFromAPI;
window.assignWitnessToMesa = assignWitnessToMesa;
window.sendPushNotification = sendPushNotification;

// Load witness stats on init
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(loadWitnessStats, 2000);
});
