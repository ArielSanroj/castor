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

    if (!form) return;

    setupForecastTabs();

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorBox.style.display = "none";
        errorBox.textContent = "";

        const formData = new FormData(form);
        const payload = {
            location: formData.get("location"),
            candidate_name: formData.get("candidate_name") || null,
            days_back: parseInt(formData.get("days_back") || 30),
            forecast_days: parseInt(formData.get("forecast_days") || 14)
        };

        submitBtn.disabled = true;
        submitBtn.textContent = "Generando...";

        try {
            const url = (window.API_CONFIG?.apiUrl("/api/forecast/dashboard")) || "/api/forecast/dashboard";
            const res = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

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
    // Render human-readable summaries first
    renderHumanReadableSummaries(data);
    
    // Render detailed charts
    if (data.icce) {
        renderICCE(data.icce);
    }
    if (data.momentum) {
        renderMomentum(data.momentum);
    }
    if (data.forecast) {
        renderForecast(data.forecast, data.icce);
    }
    
    // Render opportunities and risks
    renderOpportunities(data);
    renderRisks(data);
    
    // Render detailed metrics
    if (data.metadata && data.metadata.narrative_metrics) {
        renderDetailedMetrics(data.metadata.narrative_metrics, data);
    }
}

function renderICCE(icceData) {
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
        const date = new Date(v.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });
    const values = icceData.historical_values.map(v => v.value);

    forecastCharts.icce = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "ICCE",
                data: values,
                borderColor: "rgb(255, 106, 61)",
                backgroundColor: "rgba(255, 106, 61, 0.1)",
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
                    text: "Evolución del ICCE"
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

function renderForecast(forecastData, icceData) {
    const ctx = document.getElementById("forecast-chart");
    if (!ctx) return;

    if (forecastCharts.forecast) {
        forecastCharts.forecast.destroy();
    }

    // Combine historical and forecast data
    const historicalLabels = icceData.historical_values.map(v => {
        const date = new Date(v.date);
        return date.toLocaleDateString('es-ES', { month: 'short', day: 'numeric' });
    });
    const historicalValues = icceData.historical_values.map(v => v.value);

    const forecastLabels = forecastData.forecast_points.map(p => {
        const date = new Date(p.date);
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
                    label: "ICCE Histórico",
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
                    text: "Proyección de ICCE"
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
    const candidateName = data.candidate_name || "El candidato";
    const location = data.location || "";
    const metrics = data.metadata?.narrative_metrics;
    
    console.log("Candidate:", candidateName, "Location:", location, "Metrics:", metrics);
    
    // Estado Actual
    const currentStatusEl = document.getElementById("current-status-text");
    console.log("current-status-text element:", currentStatusEl);
    if (currentStatusEl && data.icce) {
        try {
            const statusText = translateCurrentStatusToHumanLanguage(
                data.icce.current_icce,
                data.icce.sentiment_overview || null,
                location,
                data.topic || "el tema"
            );
            console.log("Status text:", statusText);
            currentStatusEl.textContent = statusText;
        } catch (error) {
            console.error("Error translating current status:", error);
            currentStatusEl.textContent = `ICCE actual: ${data.icce.current_icce.toFixed(1)}`;
        }
    } else {
        console.warn("currentStatusEl not found or data.icce missing");
    }
    
    // Momentum
    const momentumStatusEl = document.getElementById("momentum-status-text");
    console.log("momentum-status-text element:", momentumStatusEl);
    if (momentumStatusEl && data.momentum) {
        try {
            const momentumText = translateMomentumToHumanLanguage(
                data.momentum.current_momentum,
                data.momentum.trend,
                candidateName
            );
            console.log("Momentum text:", momentumText);
            momentumStatusEl.textContent = momentumText;
        } catch (error) {
            console.error("Error translating momentum:", error);
            momentumStatusEl.textContent = `Momentum: ${data.momentum.current_momentum > 0 ? '+' : ''}${data.momentum.current_momentum.toFixed(2)}`;
        }
    } else {
        console.warn("momentumStatusEl not found or data.momentum missing");
    }
    
    // Proyección
    const projectionStatusEl = document.getElementById("projection-status-text");
    console.log("projection-status-text element:", projectionStatusEl);
    if (projectionStatusEl && data.forecast && data.icce) {
        try {
            const projectionText = translateProjectionToHumanLanguage(
                data.forecast.forecast_points,
                data.icce.current_icce,
                candidateName
            );
            console.log("Projection text:", projectionText);
            projectionStatusEl.textContent = projectionText;
        } catch (error) {
            console.error("Error translating projection:", error);
            projectionStatusEl.textContent = `Proyección: ${data.forecast.forecast_points.length} días`;
        }
    } else {
        console.warn("projectionStatusEl not found or data missing");
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
    const opportunities = generateOpportunities(data);
    const container = document.getElementById("opportunities-list");
    
    if (!container) return;
    
    if (opportunities.length === 0) {
        container.innerHTML = '<p style="color: var(--muted); padding: 2rem; text-align: center;">No se identificaron oportunidades específicas en este momento.</p>';
        return;
    }
    
    container.innerHTML = opportunities.map(opp => `
        <div style="padding: 1.5rem; background: var(--panel-alt); border-radius: 12px; border-left: 4px solid var(--success);">
            <div style="display: flex; align-items: start; gap: 1rem;">
                <span style="font-size: 1.5rem;">${opp.icon}</span>
                <div style="flex: 1;">
                    <h4 style="font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text);">${opp.title}</h4>
                    <p style="color: var(--muted); line-height: 1.6;">${opp.description}</p>
                </div>
            </div>
        </div>
    `).join('');
}

function renderRisks(data) {
    const risks = generateRisks(data);
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
                    <span style="font-size: 1.5rem;">${risk.icon}</span>
                    <div style="flex: 1;">
                        <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                            <h4 style="font-size: 1.1rem; font-weight: 600; color: var(--text);">${risk.title}</h4>
                            <span style="font-size: 0.85rem; padding: 0.25rem 0.5rem; background: ${borderColor}20; color: ${borderColor}; border-radius: 4px; font-weight: 600;">${risk.severity}</span>
                        </div>
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
// MOCKUP DATA FOR TESTING
// ====================
function generateForecastMockupData() {
    const now = new Date();
    const historicalDates = [];
    const forecastDates = [];
    
    // Generate historical dates (last 30 days)
    for (let i = 29; i >= 0; i--) {
        const date = new Date(now);
        date.setDate(date.getDate() - i);
        historicalDates.push(date.toISOString());
    }
    
    // Generate forecast dates (next 14 days)
    for (let i = 1; i <= 14; i++) {
        const date = new Date(now);
        date.setDate(date.getDate() + i);
        forecastDates.push(date.toISOString());
    }
    
    // Generate historical ICCE values (trending upward)
    const historicalValues = historicalDates.map((date, i) => {
        const baseValue = 58 + (i * 0.25) + (Math.random() * 4 - 2);
        return {
            date: date,
            value: Math.max(0, Math.min(100, baseValue)),
            volume: 40 + Math.floor(Math.random() * 20),
            sentiment_score: 0.1 + (Math.random() * 0.2),
            conversation_share: 0.35 + (Math.random() * 0.1)
        };
    });
    
    // Generate historical momentum values
    const historicalMomentum = historicalDates.slice(7).map((date, i) => {
        const momentum = 0.5 + (Math.random() * 1.5 - 0.75);
        return {
            date: date,
            momentum: momentum,
            change: momentum - (i > 0 ? historicalMomentum[i - 1]?.momentum || 0.5 : 0.5),
            trend: momentum > 1.0 ? "up" : momentum < 0.0 ? "down" : "stable"
        };
    });
    
    // Generate forecast points
    const lastICCEValue = historicalValues[historicalValues.length - 1].value;
    const forecastPoints = forecastDates.map((date, i) => {
        const projectedValue = lastICCEValue + (i * 0.3) + (Math.random() * 2 - 1);
        return {
            date: date,
            projected_value: Math.max(0, Math.min(100, projectedValue)),
            lower_bound: Math.max(0, projectedValue - 5 - Math.random() * 3),
            upper_bound: Math.min(100, projectedValue + 5 + Math.random() * 3),
            confidence: 0.95 - (i * 0.01)
        };
    });
    
    return {
        success: true,
        candidate_name: "Juan Pérez",
        location: "Bogotá",
        icce: {
            success: true,
            candidate_name: "Juan Pérez",
            location: "Bogotá",
            current_icce: lastICCEValue,
            historical_values: historicalValues,
            sentiment_overview: {
                positive: 0.35,
                negative: 0.30,
                neutral: 0.35,
                total_tweets: 150
            },
            metadata: {
                days_back: 30,
                data_points: historicalValues.length
            }
        },
        momentum: {
            success: true,
            candidate_name: "Juan Pérez",
            location: "Bogotá",
            current_momentum: historicalMomentum[historicalMomentum.length - 1]?.momentum || 1.2,
            historical_momentum: historicalMomentum,
            trend: historicalMomentum[historicalMomentum.length - 1]?.trend || "stable",
            metadata: {
                days_back: 30,
                data_points: historicalMomentum.length
            }
        },
        forecast: {
            success: true,
            candidate_name: "Juan Pérez",
            location: "Bogotá",
            forecast_points: forecastPoints,
            model_type: "holt_winters",
            metadata: {
                forecast_days: 14,
                historical_points: historicalValues.length
            }
        },
        metadata: {
            calculated_at: now.toISOString(),
            narrative_metrics: {
                sve: 0.42,
                sna: 0.15,
                cp: 0.58,
                nmi: 0.22,
                ivn: {
                    ivn: 0.65,
                    interpretation: "Competitivo con sesgo positivo",
                    risk_level: "medio-bajo",
                    components: {
                        sve: 0.42,
                        sna: 0.575,
                        cp: 0.58,
                        nmi: 0.61
                    }
                }
            }
        }
    };
}

// Function to test forecast with mockup data
window.testForecastWithMockup = function() {
    try {
        const resultsSection = document.getElementById("forecast-results");
        if (!resultsSection) {
            console.error("Results section not found");
            alert("Error: No se encontró la sección de resultados");
            return;
        }
        
        // Fill form with example values
        const locationInput = document.getElementById("forecast-location");
        const candidateInput = document.getElementById("forecast-candidate");
        const daysBackInput = document.getElementById("forecast-days-back");
        const daysAheadInput = document.getElementById("forecast-days-ahead");
        
        if (locationInput) locationInput.value = "Bogotá";
        if (candidateInput) candidateInput.value = "Juan Pérez";
        if (daysBackInput) daysBackInput.value = "30";
        if (daysAheadInput) daysAheadInput.value = "14";
        
        // Show results section first
        resultsSection.style.display = "block";
        
        // Generate mockup data
        const mockupData = generateForecastMockupData();
        console.log("Mockup data generated:", mockupData);
        
        // Verify required functions exist
        if (typeof renderForecastDashboard !== 'function') {
            console.error("renderForecastDashboard function not found");
            alert("Error: Función de renderizado no encontrada");
            return;
        }
        
        // Check if translation functions are available
        const requiredFunctions = [
            'translateCurrentStatusToHumanLanguage',
            'translateMomentumToHumanLanguage',
            'translateProjectionToHumanLanguage',
            'translateIVNToHumanLanguage',
            'translateShareOfVoice',
            'translateSentiment',
            'generateOpportunities',
            'generateRisks'
        ];
        
        const missingFunctions = requiredFunctions.filter(fn => typeof window[fn] !== 'function');
        if (missingFunctions.length > 0) {
            console.error("Missing functions:", missingFunctions);
            console.log("Available functions:", Object.keys(window).filter(k => k.startsWith('translate') || k.startsWith('generate')));
            // Continue anyway, but log the issue
            console.warn("Some translation functions are missing, but continuing anyway...");
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
