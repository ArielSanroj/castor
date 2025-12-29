// Forecast Dashboard JavaScript
let forecastCharts = {
    icce: null,
    momentum: null,
    forecast: null
};

document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("forecast-form");
    const submitBtn = document.getElementById("forecast-submit-btn");
    const errorBox = document.getElementById("forecast-error");
    const resultsSection = document.getElementById("forecast-results");
    const loadingBox = document.getElementById("forecast-loading");

    if (!form) return;

    setupForecastTabs();

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorBox.style.display = "none";
        errorBox.textContent = "";
        if (loadingBox) {
            loadingBox.style.display = "flex";
        }

        const formData = new FormData(form);
        const payload = {
            location: (formData.get("location") || "").trim(),
            topic: formData.get("topic") || null,
            candidate_name: formData.get("candidate_name") || null,
            politician: formData.get("politician") || null,
            days_back: parseInt(formData.get("days_back") || 30),
            forecast_days: parseInt(formData.get("forecast_days") || 14)
        };

        // Client-side guardrails to avoid wasting requests
        if (!payload.location) {
            errorBox.textContent = "La ubicación es obligatoria.";
            errorBox.style.display = "block";
            if (loadingBox) loadingBox.style.display = "none";
            return;
        }
        if (payload.days_back < 7 || payload.days_back > 90) {
            errorBox.textContent = "Días hacia atrás debe estar entre 7 y 90.";
            errorBox.style.display = "block";
            if (loadingBox) loadingBox.style.display = "none";
            return;
        }
        if (payload.forecast_days < 7 || payload.forecast_days > 30) {
            errorBox.textContent = "Días a proyectar debe estar entre 7 y 30.";
            errorBox.style.display = "block";
            if (loadingBox) loadingBox.style.display = "none";
            return;
        }

        submitBtn.disabled = true;
        submitBtn.textContent = "Generando...";

        try {
            const url = (window.API_CONFIG?.apiUrl("/api/forecast/dashboard")) || "/api/forecast/dashboard";
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 25000);

            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
                signal: controller.signal
            });
            clearTimeout(timeout);

            if (!res.ok) {
                const text = await res.text();
                throw new Error(`Error HTTP ${res.status}: ${text}`);
            }

            const data = await res.json();
            if (!data.success) {
                throw new Error(data.error || "Error desconocido");
            }

            resultsSection.style.display = "block";
            renderForecastDashboard(data);
            resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

        } catch (err) {
            console.error(err);
            errorBox.textContent = err.message || "Error al generar forecast.";
            errorBox.style.display = "block";
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = "Generar Forecast";
            if (loadingBox) {
                loadingBox.style.display = "none";
            }
        }
    });
});

function setupForecastTabs() {
    const tabs = document.querySelectorAll("#forecast-results .tab");
    const contents = document.querySelectorAll("#forecast-results .tab-content");

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.dataset.tab;

            tabs.forEach((t) => {
                t.classList.remove("active");
                t.style.borderBottom = "2px solid transparent";
                t.style.color = "var(--muted)";
            });
            tab.classList.add("active");
            tab.style.borderBottom = "2px solid var(--accent)";
            tab.style.color = "var(--accent)";

            contents.forEach((c) => {
                const isActive = c.id === `tab-${target}`;
                c.style.display = isActive ? "block" : "none";
                c.classList.toggle("active", isActive);
            });
        });
    });
}

function renderForecastDashboard(data) {
    // Handle new API structure (series/forecast) or old structure (icce/momentum/forecast)
    let seriesData, forecastData, icceData, momentumData;
    
    if (data.series && data.forecast) {
        // New structure from API
        seriesData = data.series;
        forecastData = data.forecast;
        
        // Convert to old structure for compatibility
        icceData = {
            success: true,
            candidate_name: data.candidate_name || data.candidate,
            location: data.location,
            current_icce: (seriesData.icce[seriesData.icce.length - 1] || 0) * 100, // Convert to 0-100
            historical_values: seriesData.dates.map((date, i) => ({
                date: new Date(date),
                value: seriesData.icce[i] * 100, // Convert to 0-100
                volume: 0,
                sentiment_score: 0,
                conversation_share: 0
            })),
            metadata: data.metadata || {}
        };
        
        momentumData = {
            success: true,
            candidate_name: data.candidate_name || data.candidate,
            location: data.location,
            current_momentum: seriesData.momentum[seriesData.momentum.length - 1] || 0,
            historical_momentum: seriesData.dates.slice(1).map((date, i) => ({
                date: new Date(date),
                momentum: seriesData.momentum[i + 1] || 0,
                change: seriesData.momentum[i + 1] || 0,
                trend: (seriesData.momentum[i + 1] || 0) > 0.01 ? "up" : 
                       (seriesData.momentum[i + 1] || 0) < -0.01 ? "down" : "stable"
            })),
            trend: (seriesData.momentum[seriesData.momentum.length - 1] || 0) > 0.01 ? "up" : 
                   (seriesData.momentum[seriesData.momentum.length - 1] || 0) < -0.01 ? "down" : "stable",
            metadata: data.metadata || {}
        };
        
        // Convert forecast data
        const forecastPoints = forecastData.dates.map((date, i) => ({
            date: new Date(date),
            projected_value: forecastData.icce_pred[i] * 100, // Convert to 0-100
            lower_bound: forecastData.pred_low[i] * 100,
            upper_bound: forecastData.pred_high[i] * 100,
            confidence: 0.95
        }));
        
        data.forecast = {
            success: true,
            candidate_name: data.candidate_name || data.candidate,
            location: data.location,
            forecast_points: forecastPoints,
            model_type: data.metadata?.model_type || "holt_winters",
            metadata: data.metadata || {}
        };
        
        // Store smoothed values for chart rendering
        data.icce_smooth = seriesData.icce_smooth;
    } else {
        // Old structure (backward compatibility)
        icceData = data.icce;
        momentumData = data.momentum;
        forecastData = data.forecast;
    }
    
    // Render human-readable summaries first
    renderHumanReadableSummaries(data);
    
    // Render detailed charts
    if (icceData) {
        renderICCE(icceData, data.icce_smooth);
    }
    if (momentumData) {
        renderMomentum(momentumData);
    }
    if (data.forecast) {
        renderForecast(data.forecast, icceData, data.icce_smooth);
    }
    
    // Render opportunities and risks
    renderOpportunities(data);
    renderRisks(data);
    
    // Render detailed metrics
    if (data.metadata && data.metadata.narrative_metrics) {
        renderDetailedMetrics(data.metadata.narrative_metrics, data);
    }
}

function renderICCE(icceData, smoothedValues = null) {
    const currentEl = document.getElementById("icce-value");
    if (currentEl) {
        currentEl.textContent = icceData.current_icce.toFixed(1);
    }

    const ctx = document.getElementById("icce-chart");
    if (!ctx) return;

    if (forecastCharts.icce) {
        forecastCharts.icce.destroy();
    }

    const labels = icceData.historical_values.map(v => {
        const date = v.date instanceof Date ? v.date : new Date(v.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });
    const values = icceData.historical_values.map(v => v.value);
    
    // Convert smoothed values to 0-100 scale if provided
    const smoothed = smoothedValues ? smoothedValues.map(v => v * 100) : null;

    const datasets = [{
        label: "ICCE Raw",
        data: values,
        borderColor: "rgb(255, 106, 61)",
        backgroundColor: "rgba(255, 106, 61, 0.1)",
        tension: 0.4,
        fill: false,
        borderDash: [5, 5],
        pointRadius: 3
    }];
    
    // Add smoothed line if available
    if (smoothed && smoothed.length === values.length) {
        datasets.push({
            label: "ICCE Suavizado (EMA)",
            data: smoothed,
            borderColor: "rgb(66, 214, 151)",
            backgroundColor: "rgba(66, 214, 151, 0.1)",
            tension: 0.4,
            fill: false,
            pointRadius: 4
        });
    }

    forecastCharts.icce = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: "top"
                },
                title: {
                    display: true,
                    text: "Evolución del ICCE (Raw y Suavizado)"
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: "ICCE (0-100)"
                    }
                }
            }
        }
    });
}

function renderMomentum(momentumData) {
    const currentEl = document.getElementById("momentum-value");
    const trendEl = document.getElementById("momentum-trend");
    
    if (currentEl) {
        const momentum = momentumData.current_momentum;
        currentEl.textContent = momentum > 0 ? `+${momentum.toFixed(2)}` : momentum.toFixed(2);
        currentEl.style.color = momentum > 0 ? "var(--success)" : momentum < 0 ? "var(--error)" : "var(--muted)";
    }
    
    if (trendEl) {
        const trend = momentumData.trend;
        const trendText = {
            "up": "📈 Tendencia alcista",
            "down": "📉 Tendencia bajista",
            "stable": "➡️ Estable"
        };
        trendEl.textContent = trendText[trend] || trend;
    }

    const ctx = document.getElementById("momentum-chart");
    if (!ctx) return;

    if (forecastCharts.momentum) {
        forecastCharts.momentum.destroy();
    }

    const labels = momentumData.historical_momentum.map(v => {
        const date = new Date(v.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });
    const momentumValues = momentumData.historical_momentum.map(v => v.momentum);

    forecastCharts.momentum = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Momentum",
                data: momentumValues,
                borderColor: "rgb(66, 214, 151)",
                backgroundColor: "rgba(66, 214, 151, 0.1)",
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: "top"
                },
                title: {
                    display: true,
                    text: "Evolución del Momentum"
                }
            },
            scales: {
                y: {
                    title: {
                        display: true,
                        text: "Momentum"
                    }
                }
            }
        }
    });
}

function renderForecast(forecastData, icceData, smoothedValues = null) {
    const ctx = document.getElementById("forecast-chart");
    if (!ctx) return;

    if (forecastCharts.forecast) {
        forecastCharts.forecast.destroy();
    }

    // Use smoothed values if available, otherwise raw
    const historicalValues = smoothedValues ? 
        smoothedValues.map(v => v * 100) : 
        icceData.historical_values.map(v => v.value);

    const historicalLabels = icceData.historical_values.map(v => {
        const date = v.date instanceof Date ? v.date : new Date(v.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });

    const forecastLabels = forecastData.forecast_points.map(p => {
        const date = p.date instanceof Date ? p.date : new Date(p.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });
    const forecastValues = forecastData.forecast_points.map(p => p.projected_value);
    const lowerBounds = forecastData.forecast_points.map(p => p.lower_bound);
    const upperBounds = forecastData.forecast_points.map(p => p.upper_bound);

    const allLabels = [...historicalLabels, ...forecastLabels];
    const historicalData = [...historicalValues, ...Array(forecastLabels.length).fill(null)];
    const forecastDataArray = [...Array(historicalLabels.length).fill(null), ...forecastValues];
    const lowerData = [...Array(historicalLabels.length).fill(null), ...lowerBounds];
    const upperData = [...Array(historicalLabels.length).fill(null), ...upperBounds];

    forecastCharts.forecast = new Chart(ctx, {
        type: "line",
        data: {
            labels: allLabels,
            datasets: [
                {
                    label: smoothedValues ? "ICCE Suavizado (Histórico)" : "ICCE Histórico",
                    data: historicalData,
                    borderColor: "rgb(255, 106, 61)",
                    backgroundColor: "rgba(255, 106, 61, 0.1)",
                    tension: 0.4,
                    borderDash: []
                },
                {
                    label: "Proyección",
                    data: forecastDataArray,
                    borderColor: "rgb(66, 214, 151)",
                    backgroundColor: "rgba(66, 214, 151, 0.1)",
                    tension: 0.4,
                    borderDash: [5, 5]
                },
                {
                    label: "Límite inferior",
                    data: lowerData,
                    borderColor: "rgba(136, 146, 176, 0.3)",
                    backgroundColor: "rgba(136, 146, 176, 0.1)",
                    tension: 0.4,
                    borderDash: [2, 2],
                    fill: "+1"
                },
                {
                    label: "Límite superior",
                    data: upperData,
                    borderColor: "rgba(136, 146, 176, 0.3)",
                    backgroundColor: "rgba(136, 146, 176, 0.1)",
                    tension: 0.4,
                    borderDash: [2, 2],
                    fill: false
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: "top"
                },
                title: {
                    display: true,
                    text: "Proyección de ICCE (7-14 días)"
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: "ICCE (0-100)"
                    }
                }
            }
        }
    });
}


function renderNarrativeMetrics(metrics) {
    // Render individual metrics
    const sveEl = document.getElementById("sve-value");
    const snaEl = document.getElementById("sna-value");
    const cpEl = document.getElementById("cp-value");
    const nmiEl = document.getElementById("nmi-value");
    
    if (sveEl && metrics.sve !== undefined) {
        sveEl.textContent = (metrics.sve * 100).toFixed(1) + "%";
    }
    if (snaEl && metrics.sna !== undefined) {
        const sna = metrics.sna;
        snaEl.textContent = sna > 0 ? `+${sna.toFixed(2)}` : sna.toFixed(2);
        snaEl.style.color = sna > 0.2 ? "var(--success)" : sna < -0.2 ? "var(--error)" : "var(--muted)";
    }
    if (cpEl && metrics.cp !== undefined) {
        cpEl.textContent = (metrics.cp * 100).toFixed(1) + "%";
    }
    if (nmiEl && metrics.nmi !== undefined) {
        const nmi = metrics.nmi;
        nmiEl.textContent = nmi > 0 ? `+${nmi.toFixed(2)}` : nmi.toFixed(2);
        nmiEl.style.color = nmi > 0 ? "var(--success)" : nmi < 0 ? "var(--error)" : "var(--muted)";
    }
    
    // Render IVN
    if (metrics.ivn) {
        const ivnData = typeof metrics.ivn === 'object' ? metrics.ivn : { ivn: metrics.ivn };
        const ivnEl = document.getElementById("ivn-value");
        const interpretationEl = document.getElementById("ivn-interpretation");
        const riskEl = document.getElementById("ivn-risk");
        
        if (ivnEl && ivnData.ivn !== undefined) {
            const ivn = ivnData.ivn;
            ivnEl.textContent = (ivn * 100).toFixed(1) + "%";
            ivnEl.style.color = ivn >= 0.8 ? "var(--success)" : 
                                ivn >= 0.6 ? "var(--accent)" : 
                                ivn >= 0.4 ? "var(--warning)" : 
                                ivn >= 0.2 ? "var(--error)" : "var(--error)";
        }
        
        if (interpretationEl && ivnData.interpretation) {
            interpretationEl.textContent = ivnData.interpretation;
        }
        
        if (riskEl && ivnData.risk_level) {
            const riskLevel = ivnData.risk_level;
            const riskText = {
                "bajo": "🟢 Riesgo bajo",
                "medio-bajo": "🟡 Riesgo medio-bajo",
                "medio": "🟠 Riesgo medio",
                "medio-alto": "🟠 Riesgo medio-alto",
                "alto": "🔴 Riesgo alto"
            };
            riskEl.textContent = riskText[riskLevel] || `Riesgo: ${riskLevel}`;
        }
    }
}

// Human-readable rendering functions
function renderHumanReadableSummaries(data) {
    console.log("renderHumanReadableSummaries called with data:", data);
    const candidateName = data.candidate_name || data.candidate || "El candidato";
    const location = data.location || "";
    const metrics = data.metadata?.narrative_metrics;
    
    // Extract ICCE and momentum values (handle both old and new structure)
    let currentICCE, currentMomentum, momentumTrend, forecastPoints;
    
    if (data.series) {
        // New structure
        const lastICCE = Array.isArray(data.series.icce) && data.series.icce.length
            ? data.series.icce[data.series.icce.length - 1]
            : 0;
        currentICCE = lastICCE * 100; // Convert to 0-100 scale
        const momentumSeries = Array.isArray(data.series.momentum) ? data.series.momentum : [];
        currentMomentum = momentumSeries.length ? momentumSeries[momentumSeries.length - 1] : 0;
        momentumTrend = currentMomentum > 0.01 ? "up" : currentMomentum < -0.01 ? "down" : "stable";
        
        // Build forecast points only if structure is present and valid
        if (
            data.forecast &&
            Array.isArray(data.forecast.icce_pred) &&
            Array.isArray(data.forecast.dates)
        ) {
            forecastPoints = data.forecast.icce_pred.map((val, i) => ({
                date: new Date(data.forecast.dates[i]),
                projected_value: val * 100
            }));
        } else {
            forecastPoints = [];
        }
    } else {
        // Old structure
        currentICCE = data.icce?.current_icce || 0;
        currentMomentum = data.momentum?.current_momentum || 0;
        momentumTrend = data.momentum?.trend || "stable";
        forecastPoints = data.forecast?.forecast_points || [];
    }
    
    // Fuerza Narrativa (Estado Actual) - Usar traducción estratégica
    const currentStatusEl = document.getElementById("current-status-text");
    if (currentStatusEl) {
        try {
            if (typeof translateNarrativeStrength === 'function') {
                const narrativeStrength = translateNarrativeStrength(currentICCE, candidateName, location);
                // Actualizar también el título de la tarjeta si existe
                const cardTitle = document.querySelector("#current-status-card h3, #current-status-card p:first-child");
                if (cardTitle && cardTitle.textContent.includes("ESTADO ACTUAL")) {
                    cardTitle.innerHTML = `🔵 FUERZA NARRATIVA — ${narrativeStrength.score} puntos (${narrativeStrength.label})`;
                }
                currentStatusEl.textContent = narrativeStrength.interpretation;
            } else if (typeof translateCurrentStatusToHumanLanguage === 'function') {
                const statusText = translateCurrentStatusToHumanLanguage(
                    currentICCE,
                    null,
                    location,
                    "el tema"
                );
                currentStatusEl.textContent = statusText;
            } else {
                currentStatusEl.textContent = `Fuerza narrativa: ${currentICCE.toFixed(0)} puntos. La conversación sobre ${candidateName} en ${location} muestra una narrativa ${currentICCE >= 70 ? "dominante" : currentICCE >= 50 ? "competitiva" : currentICCE >= 30 ? "débil" : "en crisis"}.`;
            }
        } catch (error) {
            console.error("Error translating narrative strength:", error);
            currentStatusEl.textContent = `Fuerza narrativa: ${currentICCE.toFixed(0)} puntos`;
        }
    }
    
    // Tendencia Semanal (Momentum) - Usar traducción estratégica
    const momentumStatusEl = document.getElementById("momentum-status-text");
    if (momentumStatusEl) {
        try {
            const momentumHistory = data.series?.momentum || [];
            if (typeof translateWeeklyTrend === 'function') {
                const trendData = translateWeeklyTrend(currentMomentum, momentumTrend, candidateName, momentumHistory);
                // Actualizar título de tarjeta
                const cardTitle = document.querySelector("#momentum-status-card h3, #momentum-status-card p:first-child");
                if (cardTitle && cardTitle.textContent.includes("MOMENTUM")) {
                    cardTitle.innerHTML = `🟠 TENDENCIA SEMANAL — ${trendData.direction}`;
                }
                momentumStatusEl.textContent = trendData.explanation;
            } else if (typeof translateMomentumToHumanLanguage === 'function') {
                const momentumText = translateMomentumToHumanLanguage(
                    currentMomentum,
                    momentumTrend,
                    candidateName
                );
                momentumStatusEl.textContent = momentumText;
            } else {
                const momentumDesc = currentMomentum > 0.01 ? "ganando terreno" : 
                                    currentMomentum < -0.01 ? "perdiendo terreno" : "estable";
                momentumStatusEl.textContent = `Tendencia: ${momentumDesc}. ${candidateName} está ${momentumDesc} en la conversación.`;
            }
        } catch (error) {
            console.error("Error translating weekly trend:", error);
            momentumStatusEl.textContent = `Tendencia: ${momentumTrend}`;
        }
    }
    
    // Pronóstico de Conversación (Forecast) - Usar traducción estratégica
    const projectionStatusEl = document.getElementById("projection-status-text");
    if (projectionStatusEl && forecastPoints.length > 0) {
        try {
            if (typeof translateConversationForecast === 'function') {
                const forecastData = translateConversationForecast(forecastPoints, currentICCE, candidateName);
                // Actualizar título de tarjeta
                const cardTitle = document.querySelector("#projection-status-card h3, #projection-status-card p:first-child");
                if (cardTitle && cardTitle.textContent.includes("PROYECCIÓN")) {
                    cardTitle.innerHTML = `🟣 PRONÓSTICO A ${forecastPoints.length} DÍAS — ${forecastData.outlook}`;
                }
                projectionStatusEl.textContent = forecastData.explanation;
            } else if (typeof translateProjectionToHumanLanguage === 'function') {
                const projectionText = translateProjectionToHumanLanguage(
                    forecastPoints,
                    currentICCE,
                    candidateName
                );
                projectionStatusEl.textContent = projectionText;
            } else {
                const lastProjected = forecastPoints[forecastPoints.length - 1]?.projected_value || currentICCE;
                const change = lastProjected - currentICCE;
                const trendDesc = change > 2 ? "creciente" : change < -2 ? "decreciente" : "estable";
                projectionStatusEl.textContent = `Pronóstico a ${forecastPoints.length} días: tendencia ${trendDesc}. Se proyecta una conversación ${trendDesc}.`;
            }
        } catch (error) {
            console.error("Error translating forecast:", error);
            projectionStatusEl.textContent = `Pronóstico: ${forecastPoints.length} días`;
        }
    }
    
    // Mostrar Recomendación Estratégica si está disponible
    if (data.metadata?.strategic_recommendation) {
        const recommendationEl = document.getElementById("strategic-recommendation");
        const recommendationCard = document.getElementById("strategic-recommendation-card");
        if (recommendationEl) {
            recommendationEl.textContent = data.metadata.strategic_recommendation;
        }
        if (recommendationCard) {
            recommendationCard.style.display = "block";
        }
    }
    
    // Posición Narrativa
    if (metrics && metrics.ivn) {
        const positionData = translateIVNToHumanLanguage(
            metrics.ivn.ivn,
            metrics.ivn.interpretation,
            metrics.ivn.risk_level
        );
        
        const positionValueEl = document.getElementById("position-value");
        const positionLabelEl = document.getElementById("position-label");
        const positionInterpretationEl = document.getElementById("position-interpretation");
        const positionRiskEl = document.getElementById("position-risk");
        
        if (positionValueEl) {
            positionValueEl.textContent = (metrics.ivn.ivn * 100).toFixed(0) + "%";
            positionValueEl.style.color = metrics.ivn.ivn >= 0.8 ? "var(--success)" : 
                                         metrics.ivn.ivn >= 0.6 ? "var(--accent)" : 
                                         metrics.ivn.ivn >= 0.4 ? "var(--warning)" : 
                                         metrics.ivn.ivn >= 0.2 ? "var(--error)" : "var(--error)";
        }
        
        if (positionLabelEl) {
            positionLabelEl.textContent = positionData.label;
        }
        
        if (positionInterpretationEl) {
            positionInterpretationEl.textContent = positionData.interpretation;
        }
        
        if (positionRiskEl) {
            const riskText = {
                "bajo": "🟢 Riesgo bajo",
                "medio-bajo": "🟡 Riesgo medio-bajo",
                "medio": "🟠 Riesgo medio",
                "medio-alto": "🟠 Riesgo medio-alto",
                "alto": "🔴 Riesgo alto"
            };
            positionRiskEl.textContent = riskText[positionData.riskLevel] || `Riesgo: ${positionData.riskLevel}`;
        }
    }
    
    // Share of Voice
    const sveDisplayEl = document.getElementById("share-of-voice-display");
    if (sveDisplayEl && metrics) {
        const sveText = translateShareOfVoice(metrics.sve, candidateName);
        sveDisplayEl.innerHTML = `<p style="color: var(--text); font-size: 1rem; line-height: 1.6;">${sveText}</p>`;
    }
    
    // Sentiment
    const sentimentDisplayEl = document.getElementById("sentiment-display");
    if (sentimentDisplayEl && metrics) {
        const sentimentText = translateSentiment(metrics.sna, null);
        sentimentDisplayEl.innerHTML = `<p style="color: var(--text); font-size: 1rem; line-height: 1.6;">${sentimentText}</p>`;
    }
}

function renderOpportunities(data) {
    // Use metadata opportunities if available, otherwise generate
    let opportunities = [];
    
    if (data.metadata?.opportunities && Array.isArray(data.metadata.opportunities)) {
        // Use provided opportunities from metadata
        opportunities = data.metadata.opportunities.map(opp => ({
            title: typeof opp === 'string' ? "Oportunidad" : opp.title || "Oportunidad",
            description: typeof opp === 'string' ? opp : opp.description || opp,
            icon: "✅"
        }));
    } else {
        // Generate opportunities using function
        opportunities = generateOpportunities(data);
    }
    
    const container = document.getElementById("opportunities-list");
    
    if (!container) return;
    
    if (opportunities.length === 0) {
        container.innerHTML = '<p style="color: var(--muted); padding: 2rem; text-align: center;">No se identificaron oportunidades específicas en este momento.</p>';
        return;
    }
    
    container.innerHTML = opportunities.map(opp => `
        <div style="padding: 1.5rem; background: var(--panel-alt); border-radius: 12px; border-left: 4px solid var(--success);">
            <div style="display: flex; align-items: start; gap: 1rem;">
                <span style="font-size: 1.5rem;">${opp.icon || "✅"}</span>
                <div style="flex: 1;">
                    ${opp.title ? `<h4 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">${opp.title}</h4>` : ''}
                    <p style="color: var(--muted); line-height: 1.6;">${opp.description}</p>
                </div>
            </div>
        </div>
    `).join('');
}

function renderRisks(data) {
    // Use metadata risks if available, otherwise generate
    let risks = [];
    
    if (data.metadata?.risks && Array.isArray(data.metadata.risks)) {
        // Use provided risks from metadata
        risks = data.metadata.risks.map(risk => ({
            title: typeof risk === 'string' ? "Riesgo" : risk.title || "Riesgo",
            description: typeof risk === 'string' ? risk : risk.description || risk,
            severity: risk.severity || "medio",
            icon: "⚠️"
        }));
    } else {
        // Generate risks using function
        risks = generateRisks(data);
    }
    
    const container = document.getElementById("risks-list");
    
    if (!container) return;
    
    if (risks.length === 0) {
        container.innerHTML = '<p style="color: var(--muted); padding: 2rem; text-align: center;">No se identificaron riesgos significativos en este momento.</p>';
        return;
    }
    
    container.innerHTML = risks.map(risk => {
        const severityColors = {
            "bajo": "var(--success)",
            "medio-bajo": "var(--warning)",
            "medio": "var(--warning)",
            "medio-alto": "var(--error)",
            "alto": "var(--error)"
        };
        const borderColor = severityColors[risk.severity] || "var(--error)";
        
        return `
            <div style="padding: 1.5rem; background: var(--panel-alt); border-radius: 12px; border-left: 4px solid ${borderColor};">
                <div style="display: flex; align-items: start; gap: 1rem;">
                    <span style="font-size: 1.5rem;">${risk.icon || "⚠️"}</span>
                    <div style="flex: 1;">
                        ${risk.title ? `<div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <h4 style="font-size: 1.1rem; font-weight: 600; color: var(--text);">${risk.title}</h4>
                            ${risk.severity ? `<span style="font-size: 0.85rem; padding: 0.25rem 0.5rem; background: ${borderColor}20; color: ${borderColor}; border-radius: 4px; font-weight: 600;">${risk.severity}</span>` : ''}
                        </div>` : ''}
                        <p style="color: var(--muted); line-height: 1.6;">${risk.description}</p>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderDetailedMetrics(metrics, data) {
    // This function can be used to render detailed technical metrics if needed
    // For now, we focus on human-readable summaries
}

// ====================
// MOCKUP DATA FOR TESTING - Three scenarios: Good, Bad, Crisis
// ====================
function generateForecastMockupData(scenario = "bad") {
    const now = new Date();
    
    // Generate dates for last 7 days
    const historicalDates = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        historicalDates.push(date.toISOString().split('T')[0]);
    }
    
    // Generate forecast dates (next 7 days)
    const forecastDates = [];
    for (let i = 1; i <= 7; i++) {
        const date = new Date(now);
        date.setDate(date.getDate() + i);
        forecastDates.push(date.toISOString().split('T')[0]);
    }
    
    let icceRaw, icceSmooth, momentum, iccePred, predLow, predHigh;
    let candidateName, location, narrativeMetrics, risks, opportunities, strategicRecommendation;
    
    if (scenario === "good") {
        // 🟢 BUENO - Narrativa dominante
        candidateName = "María López";
        location = "Medellín";
        icceRaw = [0.65, 0.68, 0.71, 0.74, 0.76, 0.78, 0.79];
        icceSmooth = [0.65, 0.67, 0.69, 0.71, 0.73, 0.75, 0.77];
        momentum = [0.0, 0.02, 0.02, 0.02, 0.02, 0.02, 0.02];
        iccePred = [0.80, 0.81, 0.82, 0.83, 0.84, 0.85, 0.86];
        predLow = [0.75, 0.76, 0.77, 0.78, 0.79, 0.80, 0.81];
        predHigh = [0.85, 0.86, 0.87, 0.88, 0.89, 0.90, 0.91];
        narrativeMetrics = {
            sve: 0.65,
            sna: 0.35,
            cp: 0.72,
            nmi: 0.45,
            ivn: { ivn: 0.79, interpretation: "Narrativa dominante", risk_level: "bajo" }
        };
        risks = ["Críticas menores a ejecución de propuestas"];
        opportunities = ["Tema Empleo muy favorable", "Engagement alto con jóvenes"];
        strategicRecommendation = "Reforzar anuncios programáticos en Empleo y capitalizar el engagement con jóvenes para comunicar educación + trabajo.";
    } else if (scenario === "crisis") {
        // 🔴 CRISIS - Narrativa colapsada
        candidateName = "Ricardo Gómez";
        location = "Cali";
        icceRaw = [0.45, 0.35, 0.25, 0.20, 0.18, 0.19, 0.18];
        icceSmooth = [0.45, 0.41, 0.35, 0.29, 0.25, 0.22, 0.20];
        momentum = [0.0, -0.04, -0.06, -0.06, -0.04, -0.03, -0.02];
        iccePred = [0.17, 0.16, 0.15, 0.14, 0.13, 0.12, 0.11];
        predLow = [0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04];
        predHigh = [0.24, 0.23, 0.22, 0.21, 0.20, 0.19, 0.18];
        narrativeMetrics = {
            sve: 0.15,
            sna: -0.45,
            cp: 0.25,
            nmi: -0.30,
            ivn: { ivn: 0.18, interpretation: "Crisis severa", risk_level: "alto" }
        };
        risks = ["Crisis activa por escándalo", "Narrativa dominada por corrupción", "Pérdida de apoyo probable"];
        opportunities = ["Solo si hay respuesta clara y contundente"];
        strategicRecommendation = "Responder con evidencia contundente y vocería fuerte. Mitigar crisis con transparencia total.";
    } else {
        // 🟡 MALO - Narrativa débil pero recuperable (default)
        candidateName = "Juan Pérez";
        location = "Bogotá";
        icceRaw = [0.358, 0.370, 0.310, 0.298, 0.315, 0.360, 0.330];
        icceSmooth = [0.358, 0.364, 0.340, 0.324, 0.322, 0.335, 0.334];
        momentum = [0.0, 0.006, -0.024, -0.016, -0.002, 0.013, -0.001];
        iccePred = [0.336, 0.338, 0.340, 0.343, 0.345, 0.347, 0.348];
        predLow = [0.320, 0.322, 0.324, 0.326, 0.328, 0.329, 0.330];
        predHigh = [0.350, 0.354, 0.356, 0.358, 0.360, 0.364, 0.365];
        narrativeMetrics = {
            sve: 0.42,
            sna: 0.15,
            cp: 0.58,
            nmi: 0.22,
            ivn: { ivn: 0.45, interpretation: "Narrativa débil", risk_level: "medio-bajo" }
        };
        risks = ["Críticas sostenidas en Seguridad", "Caída fuerte a mitad de semana"];
        opportunities = ["Tema Empleo en tono positivo", "Buen rebote post-debate"];
        strategicRecommendation = "Posicionar mensajes en Empleo y mitigar críticas en Seguridad con propuestas claras y datos verificables.";
    }
    
    // Build response matching new API structure
    return {
        success: true,
        candidate: candidateName,
        candidate_name: candidateName,
        location: location,
        series: {
            dates: historicalDates,
            icce: icceRaw,
            icce_smooth: icceSmooth,
            momentum: momentum
        },
        forecast: {
            dates: forecastDates,
            icce_pred: iccePred,
            pred_low: predLow,
            pred_high: predHigh
        },
        metadata: {
            calculated_at: now.toISOString(),
            days_back: 7,
            forecast_days: 7,
            model_type: "holt_winters",
            narrative_metrics: narrativeMetrics,
            risks: risks,
            opportunities: opportunities,
            strategic_recommendation: strategicRecommendation
        }
    };
}

// Function to test forecast with mockup data
window.testForecastWithMockup = function(scenario = "bad") {
    try {
        const resultsSection = document.getElementById("forecast-results");
        if (!resultsSection) {
            console.error("Results section not found");
            alert("Error: No se encontró la sección de resultados");
            return;
        }
        
        // Generate mockup data for selected scenario
        const mockupData = generateForecastMockupData(scenario);
        
        // Fill form with example values from mockup
        const locationInput = document.getElementById("forecast-location");
        const topicInput = document.getElementById("forecast-topic");
        const candidateInput = document.getElementById("forecast-candidate");
        const politicianInput = document.getElementById("forecast-politician");
        const daysBackInput = document.getElementById("forecast-days-back");
        const daysAheadInput = document.getElementById("forecast-days-ahead");
        
        if (locationInput) locationInput.value = mockupData.location;
        if (topicInput) topicInput.value = "";
        if (candidateInput) candidateInput.value = mockupData.candidate_name;
        if (politicianInput) politicianInput.value = "";
        if (daysBackInput) daysBackInput.value = "30";
        if (daysAheadInput) daysAheadInput.value = "14";
        
        // Show results section first
        resultsSection.style.display = "block";
        
        console.log("Mockup data generated:", mockupData);
        
        // Verify required functions exist
        if (typeof renderForecastDashboard !== 'function') {
            console.error("renderForecastDashboard function not found");
            alert("Error: Función de renderizado no encontrada");
            return;
        }
        
        // Wait a bit for DOM to be ready, then render
        setTimeout(() => {
            try {
                renderForecastDashboard(mockupData);
                // Scroll to results
                resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
            } catch (error) {
                console.error("Error rendering dashboard:", error);
                alert("Error al renderizar el ejemplo: " + error.message);
            }
        }, 100);
    } catch (error) {
        console.error("Error in testForecastWithMockup:", error);
        alert("Error al generar ejemplo: " + error.message);
    }
};
