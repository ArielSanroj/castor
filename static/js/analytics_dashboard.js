/**
 * CASTOR Analytics Dashboard
 * Dashboard unificado de inteligencia electoral
 */

// Chart instances
let icceHistoryChart = null;
let momentumChart = null;
let forecastChart = null;
let sentimentPieChart = null;
let topicsBarChart = null;
let combinedChart = null;

// Data storage
let analyticsData = {
    media: null,
    campaign: null,
    forecast: null,
    trending: null
};

document.addEventListener('DOMContentLoaded', () => {
    initializeAnalytics();
});

function initializeAnalytics() {
    const form = document.getElementById('analytics-form');
    const btnDemo = document.getElementById('btn-demo');

    if (!form) return;

    // Setup module tabs
    setupModuleTabs();

    // Form submission
    form.addEventListener('submit', handleFormSubmit);

    // Demo button
    if (btnDemo) {
        btnDemo.addEventListener('click', loadDemoData);
    }

    // Copy speech button
    const btnCopy = document.getElementById('btn-copy-speech');
    if (btnCopy) {
        btnCopy.addEventListener('click', copySpeechToClipboard);
    }
}

function setupModuleTabs() {
    const tabs = document.querySelectorAll('.module-tab');
    const contents = document.querySelectorAll('.module-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const target = tab.dataset.module;

            // Update tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update content
            contents.forEach(c => {
                c.classList.remove('active');
                if (c.id === `module-${target}`) {
                    c.classList.add('active');
                }
            });

            // Render charts if needed
            if (target === 'charts' && analyticsData.media) {
                renderAllCharts();
            }
            if (target === 'forecast' && analyticsData.forecast) {
                renderForecastCharts();
            }
        });
    });
}

async function handleFormSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const errorBox = document.getElementById('form-error');
    const loadingBox = document.getElementById('form-loading');
    const submitBtn = document.getElementById('btn-analyze');
    const resultsSection = document.getElementById('analytics-results');

    // Get form values
    const formData = new FormData(form);
    const location = (formData.get('location') || '').trim();
    const topic = emptyToNull(formData.get('topic'));
    const candidateName = emptyToNull(formData.get('candidate_name'));
    const politician = emptyToNull(formData.get('politician'));
    const daysBack = Number(formData.get('days_back') || 30);
    const forecastDays = Number(formData.get('forecast_days') || 14);

    // Validation
    errorBox.style.display = 'none';
    errorBox.textContent = '';

    if (!location) {
        showError(errorBox, 'La ubicación es obligatoria.');
        return;
    }

    if (daysBack < 7 || daysBack > 90) {
        showError(errorBox, 'Los días hacia atrás deben estar entre 7 y 90.');
        return;
    }

    if (forecastDays < 7 || forecastDays > 30) {
        showError(errorBox, 'Los días a proyectar deben estar entre 7 y 30.');
        return;
    }

    // Start loading
    submitBtn.disabled = true;
    submitBtn.textContent = 'Analizando...';
    loadingBox.style.display = 'flex';

    const apiUrl = (path) => (window.API_CONFIG?.apiUrl(path)) || path;

    // Build payloads
    const mediaPayload = {
        location,
        topic,
        candidate_name: candidateName,
        politician: politician ? politician.replace('@', '') : null,
        max_tweets: 15,
        time_window_days: Math.min(daysBack, 30),
        language: 'es'
    };

    const forecastPayload = {
        location,
        topic,
        candidate_name: candidateName,
        politician: politician ? politician.replace('@', '') : null,
        days_back: daysBack,
        forecast_days: forecastDays
    };

    const campaignPayload = topic ? {
        location,
        theme: topic,
        candidate_name: candidateName,
        politician: politician ? politician.replace('@', '') : null,
        max_tweets: 120,
        language: 'es'
    } : null;

    try {
        // Make parallel requests
        const requests = [
            fetchWithTimeout(apiUrl('/api/media/analyze'), mediaPayload, 25000),
            fetchWithTimeout(apiUrl('/api/forecast/dashboard'), forecastPayload, 25000),
            fetchWithTimeout(apiUrl(`/api/campaign/trending?location=${encodeURIComponent(location)}&limit=6`), null, 15000, 'GET')
        ];

        if (campaignPayload) {
            requests.push(fetchWithTimeout(apiUrl('/api/campaign/analyze'), campaignPayload, 30000));
        }

        const results = await Promise.allSettled(requests);

        // Extract results
        analyticsData.media = getSuccessValue(results[0]);
        analyticsData.forecast = getSuccessValue(results[1]);
        analyticsData.trending = getSuccessValue(results[2]);
        analyticsData.campaign = getSuccessValue(results[3]);

        if (!analyticsData.media && !analyticsData.forecast) {
            throw new Error('No se pudieron obtener datos. Verifica la conexión o los parámetros.');
        }

        // Render results
        resultsSection.classList.add('active');
        renderAnalytics({
            location,
            topic,
            candidateName
        });

        // Scroll to results
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        console.error('Analytics error:', err);
        showError(errorBox, err.message || 'Error al procesar el análisis.');
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Analizar conversación';
        loadingBox.style.display = 'none';
    }
}

async function fetchWithTimeout(url, payload, timeoutMs, method = 'POST') {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);

    const options = {
        method,
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal
    };

    if (payload && method !== 'GET') {
        options.body = JSON.stringify(payload);
    }

    const response = await fetch(url, options);
    clearTimeout(timeout);

    if (!response.ok) {
        const text = await response.text();
        throw new Error(`HTTP ${response.status}: ${text}`);
    }

    const data = await response.json();
    if (data && data.success === false) {
        throw new Error(data.error || 'Respuesta sin éxito');
    }

    return data;
}

function getSuccessValue(result) {
    if (!result || result.status !== 'fulfilled') return null;
    return result.value;
}

function emptyToNull(value) {
    if (value == null) return null;
    const trimmed = String(value).trim();
    return trimmed === '' ? null : trimmed;
}

function showError(box, message) {
    box.textContent = message;
    box.style.display = 'block';
}

// =====================
// RENDER FUNCTIONS
// =====================

function renderAnalytics(input) {
    renderContextBar(input);
    renderKPIs();
    renderOverview(input);
    renderMediaModule();
    renderCampaignModule();
    renderForecastModule();
}

function renderContextBar(input) {
    const { media, forecast } = analyticsData;
    const now = new Date();

    // Window
    const daysBack = document.getElementById('analytics-days-back')?.value || 30;
    setText('ctx-window', `${daysBack} días`);

    // Sample
    const tweets = media?.metadata?.tweets_analyzed || '--';
    setText('ctx-sample', `${tweets} tweets`);

    // Location
    setText('ctx-location', input.location || '--');

    // Topic
    setText('ctx-topic', input.topic || 'General');

    // Updated
    const timeStr = now.toLocaleString('es-ES', {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
    setText('ctx-updated', timeStr);
}

function renderKPIs() {
    const { media, forecast } = analyticsData;
    const totalTweets = media?.metadata?.tweets_analyzed || 0;

    // ICCE
    const icceEl = document.getElementById('kpi-icce');
    const icceMeta = document.getElementById('kpi-icce-meta');
    const icceCard = document.getElementById('kpi-icce-card');

    let icceValue = null;
    if (forecast?.series?.icce?.length) {
        icceValue = forecast.series.icce[forecast.series.icce.length - 1] * 100;
    }

    if (icceEl) {
        icceEl.textContent = icceValue != null ? icceValue.toFixed(1) : '--';
    }
    if (icceMeta) {
        // Show zone label
        icceMeta.textContent = icceValue != null ? getICCELabel(icceValue) : 'Sin datos de forecast';
    }
    if (icceCard) {
        icceCard.classList.remove('positive', 'negative', 'neutral');
        if (icceValue != null) {
            if (icceValue >= 60) icceCard.classList.add('positive');
            else if (icceValue < 40) icceCard.classList.add('negative');
            else icceCard.classList.add('neutral');
        }
    }

    // Momentum
    const momentumEl = document.getElementById('kpi-momentum');
    const momentumMeta = document.getElementById('kpi-momentum-meta');
    const momentumCard = document.getElementById('kpi-momentum-card');

    let momentumValue = null;
    if (forecast?.series?.momentum?.length) {
        momentumValue = forecast.series.momentum[forecast.series.momentum.length - 1];
    }

    if (momentumEl) {
        momentumEl.textContent = momentumValue != null ? (momentumValue >= 0 ? '+' : '') + momentumValue.toFixed(3) : '--';
    }
    if (momentumMeta) {
        // Show direction indicator
        if (momentumValue != null) {
            const arrow = momentumValue > 0.005 ? '↑' : momentumValue < -0.005 ? '↓' : '→';
            momentumMeta.textContent = `${arrow} ${getMomentumLabel(momentumValue)}`;
        } else {
            momentumMeta.textContent = 'Sin datos de momentum';
        }
    }
    if (momentumCard) {
        momentumCard.classList.remove('positive', 'negative', 'neutral');
        if (momentumValue != null) {
            if (momentumValue > 0.01) momentumCard.classList.add('positive');
            else if (momentumValue < -0.01) momentumCard.classList.add('negative');
            else momentumCard.classList.add('neutral');
        }
    }

    // Sentiment
    const sentimentEl = document.getElementById('kpi-sentiment');
    const sentimentMeta = document.getElementById('kpi-sentiment-meta');
    const sentimentCard = document.getElementById('kpi-sentiment-card');

    let netSentiment = null;
    if (media?.sentiment_overview) {
        const s = media.sentiment_overview;
        netSentiment = (s.positive - s.negative) * 100;
    }

    if (sentimentEl) {
        sentimentEl.textContent = netSentiment != null ? (netSentiment >= 0 ? '+' : '') + netSentiment.toFixed(1) + '%' : '--';
    }
    if (sentimentMeta) {
        // Show breakdown
        if (media?.sentiment_overview) {
            const s = media.sentiment_overview;
            const posCount = Math.round(s.positive * totalTweets);
            const negCount = Math.round(s.negative * totalTweets);
            sentimentMeta.textContent = `${posCount} favorable vs ${negCount} crítica`;
        } else {
            sentimentMeta.textContent = 'Sin datos de sentimiento';
        }
    }
    if (sentimentCard) {
        sentimentCard.classList.remove('positive', 'negative', 'neutral');
        if (netSentiment != null) {
            if (netSentiment > 5) sentimentCard.classList.add('positive');
            else if (netSentiment < -5) sentimentCard.classList.add('negative');
            else sentimentCard.classList.add('neutral');
        }
    }

    // Volume
    const volumeEl = document.getElementById('kpi-volume');
    const volumeMeta = document.getElementById('kpi-volume-meta');

    if (volumeEl) {
        volumeEl.textContent = totalTweets || '--';
    }
    if (volumeMeta) {
        const days = media?.metadata?.time_window_days || 30;
        volumeMeta.textContent = `Ventana: ${days} días`;
    }
}

function renderOverview(input) {
    const { media, forecast } = analyticsData;
    const totalTweets = media?.metadata?.tweets_analyzed || 0;

    // TL;DR Narrative
    const tldr = extractTLDR(media, input);
    setText('narrative-tldr', tldr);

    // Drivers
    const driversEl = document.getElementById('narrative-drivers');
    if (driversEl) {
        driversEl.innerHTML = '';
        const drivers = extractDrivers(media, input);
        drivers.forEach(d => {
            const li = document.createElement('li');
            li.textContent = d;
            driversEl.appendChild(li);
        });
    }

    // Risks
    const risksEl = document.getElementById('narrative-risks');
    if (risksEl) {
        risksEl.innerHTML = '';
        const risks = extractRisks(media, forecast);
        risks.forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            risksEl.appendChild(li);
        });
    }

    // Watch
    const watchEl = document.getElementById('narrative-watch');
    if (watchEl) {
        watchEl.innerHTML = '';
        const watch = extractWatch(media, forecast);
        watch.forEach(w => {
            const li = document.createElement('li');
            li.textContent = w;
            watchEl.appendChild(li);
        });
    }

    // Sentiment bars with counts
    if (media?.sentiment_overview) {
        const s = media.sentiment_overview;
        const posCount = Math.round(s.positive * totalTweets);
        const neuCount = Math.round(s.neutral * totalTweets);
        const negCount = Math.round(s.negative * totalTweets);

        updateSentimentBar('positive', s.positive * 100);
        updateSentimentBar('neutral', s.neutral * 100);
        updateSentimentBar('negative', s.negative * 100);

        setText('sentiment-positive-count', `(${posCount})`);
        setText('sentiment-neutral-count', `(${neuCount})`);
        setText('sentiment-negative-count', `(${negCount})`);
    }

    // Forecast metrics with enhanced info
    const forecastDays = document.getElementById('analytics-forecast-days')?.value || 14;
    setText('forecast-horizon', `${forecastDays} días`);

    let forecastDirection = '-';
    let forecastConfidence = '-';
    let forecastRange = '-';
    let forecastRisk = '-';
    let forecastPosition = '-';

    if (forecast?.series && forecast?.forecast) {
        const lastICCE = forecast.series.icce[forecast.series.icce.length - 1] || 0;
        const projectedICCE = forecast.forecast.icce_pred?.length ?
            forecast.forecast.icce_pred[forecast.forecast.icce_pred.length - 1] : lastICCE;

        const delta = (projectedICCE - lastICCE) * 100;

        // Calculate confidence based on prediction band width
        const predHigh = forecast.forecast.pred_high;
        const predLow = forecast.forecast.pred_low;
        let confidenceLabel = 'Media';
        if (predHigh && predLow && predHigh.length > 0) {
            const bandWidth = (predHigh[predHigh.length - 1] - predLow[predLow.length - 1]) * 100;
            if (bandWidth < 8) confidenceLabel = 'Alta';
            else if (bandWidth > 15) confidenceLabel = 'Baja';
        }

        // Calculate range
        if (predHigh && predLow && predHigh.length > 0) {
            const lowVal = Math.round(predLow[predLow.length - 1] * 100);
            const highVal = Math.round(predHigh[predHigh.length - 1] * 100);
            forecastRange = `${lowVal} - ${highVal}`;
        }

        forecastDirection = delta >= 0 ?
            `+${delta.toFixed(1)} pts (${confidenceLabel.toLowerCase()})` :
            `${delta.toFixed(1)} pts (${confidenceLabel.toLowerCase()})`;
        forecastConfidence = confidenceLabel;

        const momentum = forecast.series.momentum?.length ?
            forecast.series.momentum[forecast.series.momentum.length - 1] : 0;

        const icce = lastICCE * 100;
        const sentiment = media?.sentiment_overview ?
            (media.sentiment_overview.positive - media.sentiment_overview.negative) * 100 : 0;

        forecastRisk = getRiskLevel(icce, momentum, sentiment);
        forecastPosition = getPositionLabel(icce, sentiment);
    }

    const dirEl = document.getElementById('forecast-direction');
    if (dirEl) {
        dirEl.className = `forecast-metric-value ${forecastDirection.includes('+') ? 'up' : 'down'}`;
    }
    setText('forecast-direction', forecastDirection);
    setText('forecast-confidence', forecastConfidence);
    setText('forecast-range', forecastRange);
    setText('forecast-risk', forecastRisk);
    setText('forecast-position', forecastPosition);

    // Action checklist
    const actions = buildActionChecklist(media, forecast, input);
    setText('action-monitor', actions.monitor);
    setText('action-validate', actions.validate);
    setText('action-prepare', actions.prepare);
}

function extractTLDR(media, input) {
    // Use structured tldr if available
    if (media?.summary?.tldr) {
        return media.summary.tldr;
    }
    if (media?.summary?.overview) {
        // Extract first sentence or create TL;DR
        const overview = media.summary.overview;
        const firstSentence = overview.split('.')[0] + '.';
        if (firstSentence.length < 150) return firstSentence;
    }
    return `Narrativa polarizada con tracción en ${input.topic || 'temas principales'}.`;
}

function extractDrivers(media, input) {
    // Use structured drivers if available
    if (media?.summary?.drivers?.length) {
        return media.summary.drivers.slice(0, 3);
    }

    // Fallback: generate from data
    const drivers = [];
    if (media?.topics?.length) {
        const top = media.topics[0];
        drivers.push(`Menciones concentradas en ${top.topic} (${top.tweet_count})`);
    }
    if (media?.summary?.key_findings?.length) {
        const finding = media.summary.key_findings[0];
        if (finding.length < 80) drivers.push(finding);
    }
    if (media?.sentiment_overview) {
        const s = media.sentiment_overview;
        if (s.positive > s.negative) {
            drivers.push('Tono general favorable en la conversación');
        } else if (s.negative > s.positive) {
            drivers.push('Predominio de menciones críticas');
        }
    }
    return drivers.slice(0, 3);
}

function extractRisks(media, forecast) {
    // Use structured risks if available
    if (media?.summary?.risks?.length) {
        return media.summary.risks.slice(0, 2);
    }

    // Fallback: generate from data
    const risks = [];
    if (media?.sentiment_overview?.negative > 0.35) {
        risks.push('Alta concentración de narrativa crítica (>35%)');
    }
    if (forecast?.series?.momentum?.length) {
        const m = forecast.series.momentum[forecast.series.momentum.length - 1];
        if (m < -0.02) {
            risks.push('Momentum negativo sostenido');
        }
    }
    if (risks.length === 0) {
        risks.push('Sin riesgos críticos identificados');
    }
    return risks.slice(0, 2);
}

function extractWatch(media, forecast) {
    // Use structured watch if available
    if (media?.summary?.watch?.length) {
        return media.summary.watch.slice(0, 2);
    }

    // Fallback: generate from data
    const watch = [];
    if (media?.sentiment_overview?.negative > 0.25) {
        watch.push('Cambios en "Crítica" si sube el volumen 2x');
    }
    if (forecast?.series?.icce?.length) {
        const icce = forecast.series.icce[forecast.series.icce.length - 1] * 100;
        if (icce < 50) {
            watch.push('ICCE por debajo de umbral neutral (50)');
        }
    }
    if (watch.length === 0) {
        watch.push('Picos de volumen inusuales');
    }
    return watch.slice(0, 2);
}

function buildActionChecklist(media, forecast, input) {
    const topic = input.topic || 'tema principal';
    const totalTweets = media?.metadata?.tweets_analyzed || 0;

    // Monitor
    let monitor = `${topic} (alertas por pico negativo)`;
    if (media?.topics?.length > 1) {
        const secondTopic = media.topics[1].topic;
        monitor = `${topic} y ${secondTopic} (alertas por pico negativo)`;
    }

    // Validate
    let validate = '3 claims críticos más repetidos en menciones negativas';
    if (media?.sentiment_overview?.negative < 0.2) {
        validate = 'Claims favorables para amplificación';
    }

    // Prepare
    let prepare = 'Q&A interno si riesgo sube a "medio"';
    if (forecast?.series?.momentum?.length) {
        const m = forecast.series.momentum[forecast.series.momentum.length - 1];
        if (m < -0.01) {
            prepare = 'Respuesta reactiva si momentum sigue negativo';
        }
    }

    return { monitor, validate, prepare };
}

function renderMediaModule() {
    const { media } = analyticsData;
    if (!media) return;

    // Overview
    setText('media-overview', media.summary?.overview || 'Sin resumen disponible.');

    // Stats
    const statsEl = document.getElementById('media-stats');
    if (statsEl && media.summary?.key_stats) {
        statsEl.innerHTML = '';
        media.summary.key_stats.forEach(stat => {
            const li = document.createElement('li');
            li.textContent = stat;
            statsEl.appendChild(li);
        });
    }

    // Findings
    const findingsEl = document.getElementById('media-findings');
    if (findingsEl && media.summary?.key_findings) {
        findingsEl.innerHTML = '';
        media.summary.key_findings.forEach(finding => {
            const li = document.createElement('li');
            li.textContent = finding;
            findingsEl.appendChild(li);
        });
    }

    // Topics
    const topicsEl = document.getElementById('media-topics');
    if (topicsEl && media.topics) {
        topicsEl.innerHTML = '';
        media.topics.forEach(topic => {
            const card = document.createElement('div');
            card.className = 'topic-card';

            const header = document.createElement('div');
            header.className = 'topic-header';
            header.innerHTML = `
                <span class="topic-name">${topic.topic}</span>
                <span class="topic-count">${topic.tweet_count} menciones</span>
            `;
            card.appendChild(header);

            const sentiment = topic.sentiment;
            const sentimentText = document.createElement('div');
            sentimentText.style.cssText = 'font-size: 0.85rem; color: var(--muted); margin-top: 0.5rem;';
            sentimentText.textContent = `Favorable ${(sentiment.positive * 100).toFixed(0)}% · Neutral ${(sentiment.neutral * 100).toFixed(0)}% · Crítica ${(sentiment.negative * 100).toFixed(0)}%`;
            card.appendChild(sentimentText);

            const bar = document.createElement('div');
            bar.className = 'sentiment-bar';
            bar.style.marginTop = '0.5rem';
            bar.innerHTML = `
                <div class="positive" style="width: ${sentiment.positive * 100}%"></div>
                <div class="neutral" style="width: ${sentiment.neutral * 100}%"></div>
                <div class="negative" style="width: ${sentiment.negative * 100}%"></div>
            `;
            card.appendChild(bar);

            topicsEl.appendChild(card);
        });
    }
}

function renderCampaignModule() {
    const { campaign, trending, media } = analyticsData;

    // Overview
    const overview = campaign?.executive_summary?.overview ||
        (media?.summary?.overview ? `Análisis estratégico: ${media.summary.overview}` : 'Ingresa un tema para obtener análisis de campaña.');
    setText('campaign-overview', overview);

    // Findings
    const findingsEl = document.getElementById('campaign-findings');
    if (findingsEl) {
        findingsEl.innerHTML = '';
        const findings = campaign?.executive_summary?.key_findings || media?.summary?.key_findings || [];
        findings.forEach(f => {
            const li = document.createElement('li');
            li.textContent = f;
            findingsEl.appendChild(li);
        });
        if (findings.length === 0) {
            const li = document.createElement('li');
            li.textContent = 'Sin hallazgos disponibles.';
            findingsEl.appendChild(li);
        }
    }

    // Recommendations
    const recsEl = document.getElementById('campaign-recommendations');
    if (recsEl) {
        recsEl.innerHTML = '';
        const recs = campaign?.executive_summary?.recommendations || [];

        // Add trending topics as recommendations
        if (trending?.trending_topics) {
            trending.trending_topics.slice(0, 3).forEach(t => {
                recs.push(`Tema tendencia: ${t}`);
            });
        }

        recs.forEach(r => {
            const li = document.createElement('li');
            li.textContent = r;
            recsEl.appendChild(li);
        });
        if (recs.length === 0) {
            const li = document.createElement('li');
            li.textContent = 'Sin recomendaciones disponibles.';
            recsEl.appendChild(li);
        }
    }

    // Strategic Plan
    const planEl = document.getElementById('campaign-plan');
    if (planEl) {
        planEl.innerHTML = '';
        if (campaign?.strategic_plan?.objectives) {
            campaign.strategic_plan.objectives.forEach(obj => {
                const card = document.createElement('div');
                card.className = 'topic-card';
                card.innerHTML = `
                    <div class="topic-header">
                        <span class="topic-name">${obj.name || obj.topic || 'Objetivo'}</span>
                    </div>
                    ${obj.need ? `<p style="margin: 0.5rem 0; color: var(--muted); font-size: 0.9rem;"><strong>Necesidad:</strong> ${obj.need}</p>` : ''}
                    ${obj.proposal ? `<p style="margin: 0.5rem 0; color: var(--muted); font-size: 0.9rem;"><strong>Propuesta:</strong> ${obj.proposal}</p>` : ''}
                    ${obj.impact ? `<p style="margin: 0.5rem 0; color: var(--success); font-size: 0.9rem;"><strong>Impacto:</strong> ${obj.impact}</p>` : ''}
                `;
                planEl.appendChild(card);
            });
        } else {
            planEl.innerHTML = '<p style="color: var(--muted);">Ingresa un tema para generar el plan estratégico.</p>';
        }
    }

    // Speech
    const speechEl = document.getElementById('speech-content');
    if (speechEl) {
        speechEl.value = campaign?.speech?.content || 'El discurso se generará cuando ingreses un tema específico.';
    }
}

function renderForecastModule() {
    const { forecast } = analyticsData;
    if (!forecast) return;

    // Alerts
    const alertsEl = document.getElementById('forecast-alerts');
    if (alertsEl) {
        alertsEl.innerHTML = '';
        const alerts = buildAlerts(forecast);
        alerts.forEach(alert => {
            const li = document.createElement('li');
            li.textContent = alert;
            alertsEl.appendChild(li);
        });
        if (alerts.length === 0) {
            const li = document.createElement('li');
            li.textContent = 'Sin alertas activas.';
            alertsEl.appendChild(li);
        }
    }

    // Render forecast charts
    renderForecastCharts();
}

function renderForecastCharts() {
    const { forecast } = analyticsData;
    if (!forecast?.series) return;

    const series = forecast.series;
    const forecastData = forecast.forecast;

    // ICCE History Chart
    const icceCtx = document.getElementById('icce-history-chart');
    if (icceCtx && series.dates && series.icce) {
        if (icceHistoryChart) icceHistoryChart.destroy();

        icceHistoryChart = new Chart(icceCtx, {
            type: 'line',
            data: {
                labels: series.dates.map(d => formatShortDate(d)),
                datasets: [{
                    label: 'ICCE',
                    data: series.icce.map(v => (v || 0) * 100),
                    borderColor: '#FF6A3D',
                    backgroundColor: 'rgba(255, 106, 61, 0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: getChartOptions('ICCE Histórico')
        });
    }

    // Momentum Chart
    const momentumCtx = document.getElementById('momentum-chart');
    if (momentumCtx && series.dates && series.momentum) {
        if (momentumChart) momentumChart.destroy();

        momentumChart = new Chart(momentumCtx, {
            type: 'bar',
            data: {
                labels: series.dates.map(d => formatShortDate(d)),
                datasets: [{
                    label: 'Momentum',
                    data: series.momentum,
                    backgroundColor: series.momentum.map(v => v >= 0 ? 'rgba(66, 214, 151, 0.7)' : 'rgba(255, 107, 129, 0.7)')
                }]
            },
            options: getChartOptions('Momentum')
        });
    }

    // Forecast Chart
    const forecastCtx = document.getElementById('forecast-chart');
    if (forecastCtx && forecastData?.dates && forecastData?.icce_pred) {
        if (forecastChart) forecastChart.destroy();

        forecastChart = new Chart(forecastCtx, {
            type: 'line',
            data: {
                labels: forecastData.dates.map(d => formatShortDate(d)),
                datasets: [
                    {
                        label: 'Proyección',
                        data: forecastData.icce_pred.map(v => (v || 0) * 100),
                        borderColor: '#42d697',
                        backgroundColor: 'rgba(66, 214, 151, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Límite superior',
                        data: forecastData.pred_high?.map(v => (v || 0) * 100) || [],
                        borderColor: 'rgba(66, 214, 151, 0.3)',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3
                    },
                    {
                        label: 'Límite inferior',
                        data: forecastData.pred_low?.map(v => (v || 0) * 100) || [],
                        borderColor: 'rgba(66, 214, 151, 0.3)',
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.3
                    }
                ]
            },
            options: getChartOptions('Proyección 14 días')
        });
    }
}

function renderAllCharts() {
    const { media, forecast } = analyticsData;

    // Sentiment Pie Chart
    const pieCtx = document.getElementById('sentiment-pie-chart');
    if (pieCtx && media?.sentiment_overview) {
        if (sentimentPieChart) sentimentPieChart.destroy();

        const s = media.sentiment_overview;
        sentimentPieChart = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Favorable', 'Neutral', 'Crítica'],
                datasets: [{
                    data: [s.positive * 100, s.neutral * 100, s.negative * 100],
                    backgroundColor: ['rgba(66, 214, 151, 0.8)', 'rgba(136, 146, 176, 0.6)', 'rgba(255, 107, 129, 0.8)']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#F5F7FA' }
                    }
                }
            }
        });
    }

    // Topics Bar Chart
    const barCtx = document.getElementById('topics-bar-chart');
    if (barCtx && media?.topics?.length) {
        if (topicsBarChart) topicsBarChart.destroy();

        const topics = media.topics;
        topicsBarChart = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: topics.map(t => t.topic),
                datasets: [
                    {
                        label: 'Favorable',
                        data: topics.map(t => Math.round(t.sentiment.positive * t.tweet_count)),
                        backgroundColor: 'rgba(66, 214, 151, 0.8)'
                    },
                    {
                        label: 'Neutral',
                        data: topics.map(t => Math.round(t.sentiment.neutral * t.tweet_count)),
                        backgroundColor: 'rgba(136, 146, 176, 0.6)'
                    },
                    {
                        label: 'Crítica',
                        data: topics.map(t => Math.round(t.sentiment.negative * t.tweet_count)),
                        backgroundColor: 'rgba(255, 107, 129, 0.8)'
                    }
                ]
            },
            options: {
                ...getChartOptions('Sentimiento por Tema'),
                scales: {
                    x: {
                        stacked: true,
                        ticks: { color: '#8892B0' },
                        grid: { color: 'rgba(136, 146, 176, 0.1)' }
                    },
                    y: {
                        stacked: true,
                        ticks: { color: '#8892B0' },
                        grid: { color: 'rgba(136, 146, 176, 0.1)' }
                    }
                }
            }
        });
    }

    // Combined ICCE + Forecast Chart
    const combinedCtx = document.getElementById('combined-chart');
    if (combinedCtx && forecast?.series) {
        if (combinedChart) combinedChart.destroy();

        const series = forecast.series;
        const forecastData = forecast.forecast;

        const historyLabels = series.dates.map(d => formatShortDate(d));
        const forecastLabels = forecastData?.dates?.map(d => formatShortDate(d)) || [];
        const allLabels = [...historyLabels, ...forecastLabels];

        const historyValues = series.icce.map(v => (v || 0) * 100);
        const forecastValues = new Array(historyLabels.length).fill(null);

        if (forecastData?.icce_pred) {
            forecastData.icce_pred.forEach((v, i) => {
                forecastValues.push((v || 0) * 100);
            });
        }

        combinedChart = new Chart(combinedCtx, {
            type: 'line',
            data: {
                labels: allLabels,
                datasets: [
                    {
                        label: 'ICCE Histórico',
                        data: [...historyValues, ...new Array(forecastLabels.length).fill(null)],
                        borderColor: '#FF6A3D',
                        backgroundColor: 'rgba(255, 106, 61, 0.1)',
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: 'Proyección',
                        data: forecastValues,
                        borderColor: '#42d697',
                        backgroundColor: 'rgba(66, 214, 151, 0.1)',
                        borderDash: [6, 6],
                        fill: true,
                        tension: 0.35
                    }
                ]
            },
            options: getChartOptions('Evolución ICCE + Forecast')
        });
    }
}

// =====================
// HELPER FUNCTIONS
// =====================

function getChartOptions(title) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: { color: '#F5F7FA' }
            },
            title: {
                display: false
            }
        },
        scales: {
            x: {
                ticks: { color: '#8892B0' },
                grid: { color: 'rgba(136, 146, 176, 0.1)' }
            },
            y: {
                ticks: { color: '#8892B0' },
                grid: { color: 'rgba(136, 146, 176, 0.1)' }
            }
        }
    };
}

function formatShortDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
}

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function updateSentimentBar(type, value) {
    const bar = document.getElementById(`sentiment-${type}-bar`);
    const pct = document.getElementById(`sentiment-${type}-pct`);

    if (bar) bar.style.width = `${value}%`;
    if (pct) pct.textContent = `${value.toFixed(1)}%`;
}

function getICCELabel(value) {
    if (value >= 70) return 'Posición fuerte';
    if (value >= 50) return 'Posición estable';
    if (value >= 30) return 'Posición débil';
    return 'Posición crítica';
}

function getMomentumLabel(value) {
    if (value > 0.03) return 'Fuerte al alza';
    if (value > 0.01) return 'Tendencia positiva';
    if (value < -0.03) return 'Fuerte a la baja';
    if (value < -0.01) return 'Tendencia negativa';
    return 'Estable';
}

function getSentimentLabel(value) {
    if (value > 15) return 'Muy favorable';
    if (value > 5) return 'Favorable';
    if (value < -15) return 'Muy crítico';
    if (value < -5) return 'Crítico';
    return 'Equilibrado';
}

function getRiskLevel(icce, momentum, sentiment) {
    if ((icce != null && icce < 35) || sentiment < -10 || (momentum != null && momentum < -0.03)) {
        return 'Alto';
    }
    if ((icce != null && icce < 50) || sentiment < -5 || (momentum != null && momentum < -0.01)) {
        return 'Medio';
    }
    return 'Bajo';
}

function getPositionLabel(icce, sentiment) {
    if (icce >= 60 && sentiment >= 0) return 'Territorio favorable';
    if (icce < 40 && sentiment < 0) return 'Territorio crítico';
    return 'Territorio neutral';
}

function buildRecommendation(forecast, media, topic) {
    if (!forecast?.series?.icce?.length) {
        return 'Genera un análisis para obtener recomendaciones estratégicas.';
    }

    const icce = forecast.series.icce[forecast.series.icce.length - 1] * 100;
    const sentiment = media?.sentiment_overview ?
        (media.sentiment_overview.positive - media.sentiment_overview.negative) * 100 : 0;

    if (icce < 40 || sentiment < -5) {
        return `Reforzar mensajes positivos${topic ? ` en ${topic}` : ''} y contener narrativa negativa. Priorizar comunicación directa y respuesta rápida a críticas.`;
    }
    if (icce > 65 && sentiment > 5) {
        return `Aprovechar ventana favorable con anuncios tácticos${topic ? ` en ${topic}` : ''}. Consolidar territorios ganados y expandir alcance.`;
    }
    return `Mantener consistencia narrativa y monitorear cambios${topic ? ` en ${topic}` : ''}. Preparar estrategias de contingencia.`;
}

function buildAlerts(forecast) {
    const alerts = [];

    if (forecast?.series?.momentum?.length) {
        const momentum = forecast.series.momentum[forecast.series.momentum.length - 1];
        if (momentum < -0.03) {
            alerts.push('Momentum negativo sostenido - riesgo de desgaste');
        }
    }

    if (forecast?.series?.icce?.length) {
        const icce = forecast.series.icce[forecast.series.icce.length - 1] * 100;
        if (icce < 35) {
            alerts.push('ICCE bajo - posición narrativa comprometida');
        }
    }

    if (forecast?.forecast?.icce_pred?.length) {
        const last = forecast.series.icce[forecast.series.icce.length - 1];
        const projected = forecast.forecast.icce_pred[forecast.forecast.icce_pred.length - 1];
        if (projected > last) {
            alerts.push('Proyección favorable a 14 días');
        } else if (projected < last * 0.9) {
            alerts.push('Proyección indica posible caída significativa');
        }
    }

    return alerts;
}

function copySpeechToClipboard() {
    const speechEl = document.getElementById('speech-content');
    const statusEl = document.getElementById('copy-status');

    if (!speechEl || !speechEl.value) return;

    navigator.clipboard.writeText(speechEl.value).then(() => {
        if (statusEl) {
            statusEl.textContent = 'Copiado';
            setTimeout(() => { statusEl.textContent = ''; }, 2000);
        }
    }).catch(() => {
        if (statusEl) {
            statusEl.textContent = 'Error al copiar';
            setTimeout(() => { statusEl.textContent = ''; }, 2000);
        }
    });
}

// =====================
// DEMO DATA
// =====================

function loadDemoData() {
    // Fill form with Paloma Valencia demo values
    document.getElementById('analytics-location').value = 'Colombia';
    document.getElementById('analytics-topic').value = 'Seguridad';
    document.getElementById('analytics-candidate').value = 'Paloma Valencia';
    document.getElementById('analytics-politician').value = '@PalomaValenciaL';
    document.getElementById('analytics-days-back').value = '30';
    document.getElementById('analytics-forecast-days').value = '14';

    // Generate mock data for Paloma Valencia
    analyticsData.media = generateMockMediaData();
    analyticsData.forecast = generateMockForecastData();
    analyticsData.campaign = generateMockCampaignData();
    analyticsData.trending = { trending_topics: ['#Seguridad', '#PalomaValencia', '#Elecciones2026', '#CentroDemocratico'] };

    // Show results
    const resultsSection = document.getElementById('analytics-results');
    resultsSection.classList.add('active');

    renderAnalytics({
        location: 'Colombia',
        topic: 'Seguridad',
        candidateName: 'Paloma Valencia'
    });

    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function generateMockMediaData() {
    // Datos basados en límite mensual de Twitter API (100 tweets/mes)
    // Simulamos análisis de ~85 tweets para Paloma Valencia
    return {
        success: true,
        summary: {
            // TL;DR - primera frase clara
            overview: 'Narrativa polarizada con fuerte tracción en seguridad y orden público. La senadora del Centro Democrático genera alta resonancia en discusiones sobre política de defensa y posiciones frente al proceso de paz. Se identifican comunidades de apoyo consolidadas y sectores críticos activos.',
            // Para TL;DR extraction
            tldr: 'Narrativa polarizada con fuerte tracción en seguridad y orden público.',
            // Drivers estructurados
            drivers: [
                'Menciones concentradas en Seguridad (38 tweets)',
                'Debate activo sobre proceso de paz genera engagement',
                'Alto engagement en posts propios (@PalomaValenciaL)'
            ],
            // Riesgos estructurados
            risks: [
                'Picos de crítica en tema Paz (45% negativo)',
                'Posible fatiga narrativa si no diversifica temas'
            ],
            // Vigilar
            watch: [
                'Cambios en "Crítica" si sube volumen 2x en tema Paz'
            ],
            key_stats: [
                '85 tweets analizados en los últimos 30 días',
                'Distribución: 42% favorable, 31% crítica, 27% neutral',
                'Pico de conversación: 22 de diciembre (debate seguridad)',
                'Alcance estimado: 2.3M impresiones',
                'Engagement rate: 4.2% (superior al promedio)'
            ],
            key_findings: [
                'Paloma Valencia lidera conversación en seguridad',
                'Alta resonancia en sectores que demandan firmeza',
                'Críticas de sectores pro-diálogo de paz',
                'Fuerte posicionamiento en redes Centro Democrático',
                'Narrativa coherente en orden público y defensa'
            ]
        },
        sentiment_overview: {
            positive: 0.42,
            neutral: 0.27,
            negative: 0.31,
            total_tweets: 85,
            // Conteos explícitos
            counts: {
                positive: 36,
                neutral: 23,
                negative: 26
            }
        },
        topics: [
            {
                topic: 'Seguridad',
                tweet_count: 38,
                sentiment: { positive: 0.47, negative: 0.28, neutral: 0.25 }
            },
            {
                topic: 'Paz',
                tweet_count: 22,
                sentiment: { positive: 0.32, negative: 0.45, neutral: 0.23 }
            },
            {
                topic: 'Gobernanza',
                tweet_count: 15,
                sentiment: { positive: 0.40, negative: 0.35, neutral: 0.25 }
            },
            {
                topic: 'Economía',
                tweet_count: 10,
                sentiment: { positive: 0.50, negative: 0.25, neutral: 0.25 }
            }
        ],
        metadata: {
            tweets_analyzed: 85,
            location: 'Colombia',
            topic: 'Seguridad',
            candidate_name: 'Paloma Valencia',
            time_window_days: 30,
            api_usage: '85/100 tweets mensuales utilizados'
        }
    };
}

function generateMockForecastData() {
    const dates = [];
    const icce = [];
    const momentum = [];
    const now = new Date();

    // Historical data (30 days) - Paloma Valencia muestra tendencia positiva
    // Inicia en ~52% y sube gradualmente a ~58% con variaciones
    for (let i = 29; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        dates.push(date.toISOString().split('T')[0]);

        // Tendencia alcista gradual para Paloma Valencia
        const dayProgress = (29 - i) / 29;
        const baseValue = 0.52 + (dayProgress * 0.06); // De 52% a 58%
        const variation = Math.sin(i / 4) * 0.03 + (Math.random() - 0.5) * 0.02;

        // Pico en día 22 (debate de seguridad)
        const debatePeak = (i === 7) ? 0.04 : 0;

        icce.push(Math.max(0.45, Math.min(0.65, baseValue + variation + debatePeak)));
    }

    // Calculate momentum
    for (let i = 0; i < icce.length; i++) {
        if (i === 0) {
            momentum.push(0);
        } else {
            momentum.push(icce[i] - icce[i - 1]);
        }
    }

    // Forecast data (14 days) - Proyección favorable
    const forecastDates = [];
    const forecastPred = [];
    const forecastHigh = [];
    const forecastLow = [];

    const lastICCE = icce[icce.length - 1];
    for (let i = 1; i <= 14; i++) {
        const date = new Date(now);
        date.setDate(date.getDate() + i);
        forecastDates.push(date.toISOString().split('T')[0]);

        // Proyección ligeramente positiva
        const trend = 0.004 * i;
        const seasonality = Math.sin(i / 3) * 0.015;
        const projected = lastICCE + trend + seasonality;
        forecastPred.push(Math.max(0.50, Math.min(0.70, projected)));
        forecastHigh.push(forecastPred[forecastPred.length - 1] + 0.04);
        forecastLow.push(forecastPred[forecastPred.length - 1] - 0.04);
    }

    return {
        candidate: 'Paloma Valencia',
        location: 'Colombia',
        series: {
            dates,
            icce,
            icce_smooth: icce.map((v, i) => {
                // Suavizado exponencial
                if (i === 0) return v;
                return icce[i-1] * 0.3 + v * 0.7;
            }),
            momentum
        },
        forecast: {
            dates: forecastDates,
            icce_pred: forecastPred,
            pred_high: forecastHigh,
            pred_low: forecastLow
        },
        metadata: {
            model_type: 'holt_winters',
            confidence: 0.85,
            calculated_at: now.toISOString(),
            narrative_position: 'Territorio favorable',
            risk_level: 'Bajo'
        }
    };
}

function generateMockCampaignData() {
    return {
        success: true,
        executive_summary: {
            overview: 'El análisis estratégico para Paloma Valencia revela una posición sólida en temas de seguridad y orden público. Su narrativa de mano firme contra el crimen y defensa de las instituciones resuena con sectores conservadores y ciudadanos preocupados por la inseguridad. Existe oportunidad de ampliar base hacia independientes moderados.',
            key_findings: [
                'Liderazgo claro en narrativa de seguridad nacional y defensa',
                'Base de apoyo consolidada en sectores uribistas y Centro Democrático',
                'Polarización moderada: 42% favorable vs 31% crítica',
                'Oportunidad de crecimiento en clase media urbana preocupada por seguridad',
                'Debilidad percibida en temas de reconciliación y diálogo social'
            ],
            recommendations: [
                'Mantener liderazgo en agenda de seguridad con propuestas específicas',
                'Suavizar tono en temas de paz sin abandonar posición de firmeza',
                'Ampliar presencia en ciudades intermedias y zonas rurales afectadas por violencia',
                'Desarrollar propuestas económicas que complementen agenda de seguridad',
                'Fortalecer comunicación directa en redes sociales con respuestas a críticos'
            ]
        },
        strategic_plan: {
            objectives: [
                {
                    name: 'Seguridad Nacional',
                    need: 'Los colombianos demandan mano firme contra grupos armados y crimen organizado. Paloma Valencia tiene credibilidad en este tema.',
                    proposal: 'Plan integral de seguridad: fortalecimiento de Fuerzas Armadas, persecución efectiva a cabecillas, y protección a líderes sociales con enfoque de resultados.',
                    impact: 'Consolidar liderazgo como referente en seguridad. Proyección: +5 puntos en intención de voto en segmento preocupado por orden público.'
                },
                {
                    name: 'Economía y Empleo',
                    need: 'Complementar agenda de seguridad con propuestas económicas concretas para ampliar base electoral.',
                    proposal: 'Programa de emprendimiento en zonas afectadas por violencia. Incentivos tributarios para empresas que generen empleo formal.',
                    impact: 'Ampliar narrativa más allá de seguridad. Atraer votantes de centro preocupados por economía.'
                },
                {
                    name: 'Gobernanza y Transparencia',
                    need: 'Diferenciarse de críticas de corrupción asociadas a clase política tradicional.',
                    proposal: 'Propuesta de reforma anticorrupción con penas más severas y extinción de dominio acelerada.',
                    impact: 'Fortalecer imagen de político honesto y comprometido con transparencia.'
                }
            ]
        },
        speech: {
            title: 'Discurso de Seguridad - Paloma Valencia',
            content: `Colombianas y colombianos,

Hoy les hablo con la misma convicción de siempre: Colombia necesita orden, Colombia necesita seguridad, Colombia necesita un gobierno que proteja a su gente.

Durante años, algunos han querido hacernos creer que la debilidad es tolerancia, que ceder ante los violentos es paz. Pero ustedes y yo sabemos la verdad: la paz verdadera se construye con justicia, con firmeza, con instituciones fuertes.

Les propongo un Colombia donde:

PRIMERO - Seguridad sin excusas. Fuerzas Armadas fortalecidas, persecución implacable a los cabecillas del narcotráfico y el terrorismo. No más zonas de despeje, no más santuarios para los criminales.

SEGUNDO - Justicia que funcione. Penas efectivas, no rebajas escandalosas. Que quien cometa un crimen pague las consecuencias. Protección real para nuestros jueces, fiscales y policías.

TERCERO - Prosperidad con trabajo. Empleo formal, apoyo al emprendedor, menos impuestos a quienes generan riqueza. Un país donde el esfuerzo se recompense.

CUARTO - Transparencia total. Cero tolerancia con la corrupción, venga de donde venga. Extinción de dominio acelerada para los ladrones del erario.

No les prometo lo fácil. Les prometo lo correcto.

Colombia merece un liderazgo que no tiemble, que no negocie sus principios, que ponga a los colombianos de bien primero.

¡Por una Colombia segura, próspera y libre!

¡Viva Colombia!`,
            key_points: [
                'Seguridad sin excusas - Fuerzas Armadas fortalecidas',
                'Justicia efectiva - Penas reales sin rebajas',
                'Prosperidad con trabajo - Apoyo al emprendimiento',
                'Transparencia total - Cero tolerancia a corrupción'
            ],
            duration_minutes: 5,
            target_audience: 'Clase media urbana, sectores conservadores, independientes preocupados por seguridad',
            emotional_tone: 'Firmeza con esperanza'
        }
    };
}
