let unifiedChart = null;
let sentimentChart = null;
let gameRadarChart = null;
let gameGapChart = null;
let lastGameContext = null;

const RIVAL_PROFILES = {
  "Vicky Dávila": { seguridad: 76, economia: 52, salud: 38, paz: 50, sov: 70, sna: 32, momentum: 0.006 },
  "Mauricio Cárdenas": { seguridad: 55, economia: 72, salud: 48, paz: 50, sov: 58, sna: 44, momentum: 0.004 },
  "David Luna": { seguridad: 50, economia: 58, salud: 52, paz: 46, sov: 52, sna: 40, momentum: 0.003 },
  "Juan Manuel Galán": { seguridad: 48, economia: 62, salud: 64, paz: 58, sov: 55, sna: 46, momentum: 0.004 },
  "Aníbal Gaviria": { seguridad: 52, economia: 56, salud: 60, paz: 62, sov: 54, sna: 45, momentum: 0.003 },
  "Juan Daniel Oviedo": { seguridad: 44, economia: 66, salud: 58, paz: 54, sov: 50, sna: 42, momentum: 0.005 },
  "Juan Carlos Pinzón": { seguridad: 70, economia: 55, salud: 40, paz: 48, sov: 66, sna: 34, momentum: 0.007 },
  "Daniel Palacios": { seguridad: 68, economia: 50, salud: 40, paz: 46, sov: 64, sna: 36, momentum: 0.006 },
  "Abelardo de la Espriella": { seguridad: 72, economia: 46, salud: 36, paz: 40, sov: 62, sna: 30, momentum: 0.005 }
};

const COLOMBIA_POINTS = [
  { name: "Bogota", lat: 4.711, lon: -74.072 },
  { name: "Medellin", lat: 6.244, lon: -75.581 },
  { name: "Cali", lat: 3.451, lon: -76.532 },
  { name: "Barranquilla", lat: 10.968, lon: -74.781 },
  { name: "Cartagena", lat: 10.391, lon: -75.479 },
  { name: "Bucaramanga", lat: 7.119, lon: -73.119 },
  { name: "Pereira", lat: 4.815, lon: -75.694 },
  { name: "Manizales", lat: 5.07, lon: -75.513 },
  { name: "Santa Marta", lat: 11.241, lon: -74.205 },
  { name: "Villavicencio", lat: 4.142, lon: -73.627 }
];

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("unified-form");
  const submitBtn = document.getElementById("unified-submit-btn");
  const errorBox = document.getElementById("unified-error");
  const resultsSection = document.getElementById("unified-results");
  const loadingBox = document.getElementById("unified-loading");
  const mockBtn = document.getElementById("unified-mock-btn");

  if (!form) return;

  setupUnifiedTabs();
  setupAccordion();
  setupGameRivalSelector();

  mockBtn?.addEventListener("click", () => {
    // Llenar formulario con datos de Paloma Valencia
    document.getElementById("unified-location").value = "Colombia";
    document.getElementById("unified-topic").value = "Seguridad";
    document.getElementById("unified-candidate").value = "Paloma Valencia";
    document.getElementById("unified-politician").value = "@PalomaValenciaL";
    document.getElementById("unified-days-back").value = "30";
    document.getElementById("unified-forecast-days").value = "14";

    // Generar datos de ejemplo completos
    const mockData = generatePalomaValenciaMockData();
    
    // Mostrar dashboard con datos mock
    resultsSection.style.display = "block";
    renderUnifiedDashboard({
      mediaData: mockData.mediaData,
      forecastData: mockData.forecastData,
      trendingData: mockData.trendingData,
      campaignData: mockData.campaignData,
      input: { 
        location: "Colombia", 
        topic: "Seguridad", 
        candidateName: "Paloma Valencia" 
      }
    });
    resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.style.display = "none";
    errorBox.textContent = "";

    const formData = new FormData(form);
    const location = (formData.get("location") || "").trim();
    const topic = emptyToNull(formData.get("topic"));
    const candidateName = emptyToNull(formData.get("candidate_name"));
    const politician = emptyToNull(formData.get("politician"));
    const daysBack = Number(formData.get("days_back") || 30);
    const forecastDays = Number(formData.get("forecast_days") || 14);

    if (!location) {
      errorBox.textContent = "La ubicacion es obligatoria.";
      errorBox.style.display = "block";
      return;
    }

    if (daysBack < 7 || daysBack > 90) {
      errorBox.textContent = "Dias hacia atras debe estar entre 7 y 90.";
      errorBox.style.display = "block";
      return;
    }

    if (forecastDays < 7 || forecastDays > 30) {
      errorBox.textContent = "Dias a proyectar debe estar entre 7 y 30.";
      errorBox.style.display = "block";
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Sincronizando...";
    if (loadingBox) loadingBox.style.display = "flex";

    const apiUrl = (path) => (window.API_CONFIG?.apiUrl(path)) || path;
    const mediaPayload = {
      location,
      topic,
      candidate_name: candidateName,
      politician: politician ? politician.replace("@", "") : null,
      max_tweets: 15,
      time_window_days: Math.min(daysBack, 30),
      language: "es"
    };

    const forecastPayload = {
      location,
      topic,
      candidate_name: candidateName,
      politician: politician ? politician.replace("@", "") : null,
      days_back: daysBack,
      forecast_days: forecastDays
    };

    const campaignPayload = topic
      ? {
          location,
          theme: topic,
          candidate_name: candidateName,
          politician: politician ? politician.replace("@", "") : null,
          max_tweets: 120,
          language: "es"
        }
      : null;

    try {
      const requests = [
        fetchJsonWithTimeout(apiUrl("/api/media/analyze"), mediaPayload, 25000),
        fetchJsonWithTimeout(apiUrl("/api/forecast/dashboard"), forecastPayload, 25000),
        fetchJsonWithTimeout(
          apiUrl(`/api/campaign/trending?location=${encodeURIComponent(location)}&limit=6`),
          null,
          15000,
          "GET"
        )
      ];
      if (campaignPayload) {
        requests.push(fetchJsonWithTimeout(apiUrl("/api/campaign/analyze"), campaignPayload, 30000));
      }

      const results = await Promise.allSettled(requests);
      const mediaResult = results[0];
      const forecastResult = results[1];
      const trendingResult = results[2];
      const campaignResult = results[3];

      const mediaData = pickSuccessful(mediaResult);
      const forecastData = pickSuccessful(forecastResult);
      const trendingData = pickSuccessful(trendingResult);
      const campaignData = pickSuccessful(campaignResult);

      if (!mediaData && !forecastData && !trendingData && !campaignData) {
        throw new Error("No se pudo obtener datos de los streams. Revisa la conexion o los servicios.");
      }

      resultsSection.style.display = "block";
      renderUnifiedDashboard({
        mediaData,
        forecastData,
        trendingData,
        campaignData,
        input: { location, topic, candidateName }
      });
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error(err);
      errorBox.textContent = err.message || "Error al generar el dashboard.";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Generar dashboard";
      if (loadingBox) loadingBox.style.display = "none";
    }
  });
});

function emptyToNull(value) {
  if (value == null) return null;
  const trimmed = String(value).trim();
  return trimmed === "" ? null : trimmed;
}

async function fetchJsonWithTimeout(url, payload, timeoutMs, method = "POST") {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
    signal: controller.signal
  };

  if (payload && method !== "GET") {
    options.body = JSON.stringify(payload);
  }

  const response = await fetch(url, options);
  clearTimeout(timeout);

  if (!response.ok) {
    const text = await response.text();
    let errorMsg = `HTTP ${response.status}: ${text}`;
    try {
      const errorData = JSON.parse(text);
      errorMsg = errorData.error || errorData.message || errorMsg;
    } catch (e) {
      // Si no es JSON, usar el texto tal cual
    }
    throw new Error(errorMsg);
  }

  const data = await response.json();
  if (data && data.success === false) {
    throw new Error(data.error || data.message || "Respuesta sin exito");
  }
  return data;
}

function pickSuccessful(result) {
  if (!result || result.status !== "fulfilled") return null;
  return result.value;
}

function renderUnifiedDashboard({ mediaData, forecastData, trendingData, campaignData, input }) {
  lastGameContext = { mediaData, forecastData, trendingData, campaignData, input };
  // Tab: Resumen (Summary)
  renderContextBar(mediaData, forecastData, input);
  renderKPIs(mediaData, forecastData);
  renderDiagnosis(mediaData, forecastData, trendingData, input);
  renderNarrativeMetrics(mediaData, forecastData, input);
  renderStreamLists(mediaData, forecastData, trendingData, input);
  renderGameTheoryBlock(mediaData, forecastData, trendingData, campaignData, input);
  renderGeoPanel(mediaData, input?.location || "Colombia");

  // Tab: Resultados (Results) - Análisis detallados
  renderAnalysisOutputs(mediaData, campaignData, forecastData);

  // Tab: Temas (Topics)
  renderTopics(mediaData);

  // Tab: Gráficos (Charts)
  renderUnifiedChart(forecastData, input);
  renderSentimentChart(mediaData, input);

  // Tab: Tendencias (Forecast)
  renderForecastPanels(forecastData, mediaData);

  // Legacy tabs (si existen las funciones)
  if (typeof renderActionBlock === "function") renderActionBlock(mediaData, forecastData, campaignData, input);
  if (typeof renderTopFindings === "function") renderTopFindings(mediaData, forecastData, input);
  if (typeof renderProjection === "function") renderProjection(forecastData, input);
  if (typeof renderEvidenceTab === "function") renderEvidenceTab(mediaData, input);
  if (typeof renderActionsTab === "function") renderActionsTab(mediaData, campaignData, forecastData, input);
  if (typeof renderVigilanceTab === "function") renderVigilanceTab(forecastData, mediaData, input);
  if (typeof renderGeoTab === "function") renderGeoTab(mediaData, input);
  if (typeof renderExplorationTab === "function") renderExplorationTab(mediaData, forecastData);
}

function renderContextBar(mediaData, forecastData, input) {
  const paramsEl = document.getElementById("context-params");
  const timestampEl = document.getElementById("context-timestamp");

  const daysBack = document.getElementById("unified-days-back")?.value || 30;
  const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || "-";
  const location = input?.location || "-";
  const topic = input?.topic || "General";
  const candidate = input?.candidateName || "";

  if (paramsEl) {
    let contextText = `Ventana: ${daysBack} dias | Muestra: ${tweetsAnalyzed} tweets | Ubicacion: ${location} | Tema: ${topic}`;
    if (candidate) {
      contextText += ` | Candidato: ${candidate}`;
    }
    paramsEl.textContent = contextText;
  }

  if (timestampEl) {
    timestampEl.textContent = `Ultima actualizacion: ${new Date().toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" })}`;
  }
}

function renderKPIs(mediaData, forecastData) {
  const icceEl = document.getElementById("kpi-icce");
  const icceNoteEl = document.getElementById("kpi-icce-note");
  const momentumEl = document.getElementById("kpi-momentum");
  const momentumNoteEl = document.getElementById("kpi-momentum-note");
  const sentimentEl = document.getElementById("kpi-sentiment");
  const sentimentNoteEl = document.getElementById("kpi-sentiment-note");
  const volumeEl = document.getElementById("kpi-volume");
  const volumeNoteEl = document.getElementById("kpi-volume-note");

  const { icce, momentum, forecastDirection } = extractForecastSignals(forecastData);
  if (icceEl) icceEl.textContent = icce != null ? icce.toFixed(1) : "-";
  if (icceNoteEl) icceNoteEl.textContent = forecastDirection || "Sin forecast disponible";

  if (momentumEl) momentumEl.textContent = momentum != null ? formatSigned(momentum, 3) : "-";
  if (momentumNoteEl) momentumNoteEl.textContent = momentum != null ? momentumLabel(momentum) : "Sin momentum";

  const sentiment = extractSentiment(mediaData);
  if (sentimentEl) {
    sentimentEl.textContent = sentiment.netValue != null
      ? `${sentiment.netValue >= 0 ? "+" : ""}${(sentiment.netValue * 100).toFixed(0)}%`
      : "-";
  }
  if (sentimentNoteEl) sentimentNoteEl.textContent = sentiment.detail || "Sin sentimiento";

  if (volumeEl) volumeEl.textContent = mediaData?.metadata?.tweets_analyzed != null
    ? `${mediaData.metadata.tweets_analyzed}`
    : "-";
  if (volumeNoteEl) volumeNoteEl.textContent = mediaData?.metadata?.time_window_to
    ? `Ventana ${formatDate(mediaData.metadata.time_window_from)} - ${formatDate(mediaData.metadata.time_window_to)}`
    : "Ventana no disponible";
}

// ============================================
// NUEVAS FUNCIONES PARA ESTRUCTURA UNIFICADA
// ============================================

function renderDiagnosis(mediaData, forecastData, trendingData, input) {
  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "General";
  const candidate = input?.candidateName || "";

  // Que domina
  const dominaEl = document.getElementById("diagnosis-domina");
  const dominaContextEl = document.getElementById("diagnosis-domina-context");
  if (dominaEl) {
    const topTopic = mediaData?.topics?.[0]?.topic || topic;
    dominaEl.textContent = topTopic;
  }
  if (dominaContextEl) {
    const topicCount = mediaData?.topics?.[0]?.tweet_count || 0;
    dominaContextEl.textContent = `${topicCount} menciones en la muestra.`;
  }

  // Como se percibe
  const percibeEl = document.getElementById("diagnosis-percibe");
  const percibeContextEl = document.getElementById("diagnosis-percibe-context");
  if (percibeEl) {
    const posPct = (mediaData?.sentiment_overview?.positive || 0) * 100;
    const negPct = (mediaData?.sentiment_overview?.negative || 0) * 100;
    const perception = posPct > negPct + 15 ? "Favorable" : negPct > posPct + 15 ? "Critico" : "Polarizado";
    percibeEl.textContent = perception;
  }
  if (percibeContextEl) {
    const posPct = ((mediaData?.sentiment_overview?.positive || 0) * 100).toFixed(0);
    const negPct = ((mediaData?.sentiment_overview?.negative || 0) * 100).toFixed(0);
    const volume = mediaData?.metadata?.tweets_analyzed || 0;
    percibeContextEl.textContent = `${posPct}% fav / ${negPct}% crit (n=${volume})`;
  }

  // Que implica
  const implicaEl = document.getElementById("diagnosis-implica");
  const implicaContextEl = document.getElementById("diagnosis-implica-context");
  if (implicaEl) {
    const icce = signals.icce;
    const riskLevel = narrativeRiskLabel(icce, signals.momentum, sentiment.netLabel);
    const territory = narrativePositionLabel(icce, sentiment.netLabel);
    implicaEl.textContent = `Riesgo ${riskLevel}`;
  }
  if (implicaContextEl) {
    const territory = narrativePositionLabel(signals.icce, sentiment.netLabel);
    implicaContextEl.textContent = territory;
  }
}

function renderActionBlock(mediaData, forecastData, campaignData, input) {
  const recEl = document.getElementById("action-recommendation");
  const urgencyEl = document.getElementById("action-urgency");
  const confidenceEl = document.getElementById("action-confidence");
  const alertsEl = document.getElementById("active-alerts");

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "el tema";
  const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;

  // Recomendacion
  if (recEl) {
    recEl.textContent = buildRecommendationText(signals.icce, sentiment.netLabel, topic);
  }

  // Urgencia
  if (urgencyEl) {
    const riskLevel = narrativeRiskLabel(signals.icce, signals.momentum, sentiment.netLabel);
    urgencyEl.textContent = riskLevel.toUpperCase();
    urgencyEl.style.background = riskLevel === "alto" ? "#FF6A3D" : riskLevel === "medio" ? "#F5B800" : "#42d697";
    urgencyEl.style.color = riskLevel === "medio" ? "#1a1a1a" : "#fff";
  }

  // Confianza
  if (confidenceEl) {
    const confidence = calculateConfidenceLevel(tweetsAnalyzed, signals);
    confidenceEl.textContent = confidence.level;
    confidenceEl.style.color = confidence.level === "Alta" ? "#42d697" : confidence.level === "Media" ? "#F5B800" : "#FF6A3D";
  }

  // Alertas
  if (alertsEl) {
    alertsEl.innerHTML = "";
    const alerts = buildForecastAlerts(signals);
    if (alerts.length === 0) {
      alertsEl.innerHTML = '<li class="alert-item" style="color: #42d697;">Sin alertas criticas</li>';
    } else {
      alerts.forEach(alert => {
        const li = document.createElement("li");
        li.className = "alert-item";
        li.style.cssText = "padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: #FF6A3D;";
        li.textContent = alert;
        alertsEl.appendChild(li);
      });
    }
  }
}

function renderTopFindings(mediaData, forecastData, input) {
  const findingsEl = document.getElementById("top-findings");
  if (!findingsEl) return;

  findingsEl.innerHTML = "";
  const findings = mediaData?.summary?.key_findings?.slice(0, 3) || [];

  if (findings.length === 0) {
    findingsEl.innerHTML = '<p style="color: #8892B0;">Sin patrones significativos detectados.</p>';
    return;
  }

  findings.forEach((finding, index) => {
    const card = document.createElement("div");
    card.className = "finding-card";
    card.style.cssText = "background: rgba(255,255,255,0.02); padding: 0.75rem 1rem; border-radius: 0.5rem; border-left: 3px solid var(--accent);";
    card.innerHTML = `
      <p style="font-size: 0.9rem; color: var(--text); margin: 0;">${finding}</p>
    `;
    findingsEl.appendChild(card);
  });
}

function renderProjection(forecastData, input) {
  const arrowEl = document.getElementById("projection-arrow");
  const deltaEl = document.getElementById("projection-delta");
  const labelEl = document.getElementById("projection-label");
  const contextEl = document.getElementById("projection-context");
  const daysLabelEl = document.getElementById("forecast-days-label");

  const forecastDays = document.getElementById("unified-forecast-days")?.value || 14;
  if (daysLabelEl) daysLabelEl.textContent = forecastDays;

  const signals = extractForecastSignals(forecastData);
  const forecast = forecastData?.forecast;

  if (!forecast || !forecast.icce_pred?.length) {
    if (arrowEl) arrowEl.textContent = "—";
    if (deltaEl) deltaEl.textContent = "Sin proyeccion";
    if (labelEl) labelEl.textContent = "";
    if (contextEl) contextEl.textContent = "No hay datos suficientes para proyectar.";
    return;
  }

  const currentIcce = (forecastData?.series?.icce?.[forecastData.series.icce.length - 1] || 0) * 100;
  const projectedIcce = (forecast.icce_pred[forecast.icce_pred.length - 1] || 0) * 100;
  const delta = projectedIcce - currentIcce;

  if (arrowEl) {
    arrowEl.textContent = delta > 2 ? "↗" : delta < -2 ? "↘" : "→";
    arrowEl.style.color = delta > 2 ? "#42d697" : delta < -2 ? "#FF6A3D" : "#8892B0";
  }

  if (deltaEl) {
    deltaEl.textContent = `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`;
    deltaEl.style.color = delta > 2 ? "#42d697" : delta < -2 ? "#FF6A3D" : "#8892B0";
  }

  if (labelEl) {
    labelEl.textContent = delta > 2 ? "Tendencia al alza" : delta < -2 ? "Tendencia a la baja" : "Estable";
  }

  if (contextEl) {
    const topic = input?.topic || "el tema";
    if (delta > 5) {
      contextEl.textContent = `Ventana favorable. Considerar acciones tacticas en ${topic}.`;
    } else if (delta < -5) {
      contextEl.textContent = `Atencion: caida proyectada. Reforzar narrativa en ${topic}.`;
    } else {
      contextEl.textContent = `Proyeccion estable. Mantener monitoreo activo.`;
    }
  }
}

function renderEvidenceTab(mediaData, input) {
  // Datos de muestra
  const tweetsEl = document.getElementById("evidence-tweets");
  const windowEl = document.getElementById("evidence-window");
  const locationEl = document.getElementById("evidence-location");

  if (tweetsEl) tweetsEl.textContent = mediaData?.metadata?.tweets_analyzed || "-";
  if (windowEl) {
    const daysBack = document.getElementById("unified-days-back")?.value || 30;
    windowEl.textContent = `${daysBack} dias`;
  }
  if (locationEl) locationEl.textContent = input?.location || "-";

  // Barra de sentiment
  const sentiment = mediaData?.sentiment_overview || {};
  const posPct = (sentiment.positive || 0) * 100;
  const neuPct = (sentiment.neutral || 0) * 100;
  const negPct = (sentiment.negative || 0) * 100;

  const barPos = document.getElementById("sent-bar-pos");
  const barNeu = document.getElementById("sent-bar-neu");
  const barNeg = document.getElementById("sent-bar-neg");
  const pctPos = document.getElementById("sent-pct-pos");
  const pctNeu = document.getElementById("sent-pct-neu");
  const pctNeg = document.getElementById("sent-pct-neg");

  if (barPos) barPos.style.width = `${posPct}%`;
  if (barNeu) barNeu.style.width = `${neuPct}%`;
  if (barNeg) barNeg.style.width = `${negPct}%`;
  if (pctPos) pctPos.textContent = posPct.toFixed(0);
  if (pctNeu) pctNeu.textContent = neuPct.toFixed(0);
  if (pctNeg) pctNeg.textContent = negPct.toFixed(0);

  // Temas
  const topicsEl = document.getElementById("topics-evidence");
  if (topicsEl) {
    topicsEl.innerHTML = "";
    const topics = mediaData?.topics || [];
    if (topics.length === 0) {
      topicsEl.innerHTML = '<p style="color: #8892B0;">Sin temas detectados.</p>';
    } else {
      topics.forEach(topic => {
        const row = document.createElement("div");
        row.className = "topics-row";
        row.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);";
        const sentLabel = topic.sentiment?.positive > topic.sentiment?.negative ? "Favorable" : "Mixto";
        row.innerHTML = `
          <span style="font-weight: 500;">${topic.topic}</span>
          <span style="color: #8892B0;">${topic.tweet_count} menciones · ${sentLabel}</span>
        `;
        topicsEl.appendChild(row);
      });
    }
  }

  // Hallazgos completos
  const findingsEl = document.getElementById("evidence-findings");
  if (findingsEl) {
    findingsEl.innerHTML = "";
    const findings = mediaData?.summary?.key_findings || [];
    if (findings.length === 0) {
      findingsEl.innerHTML = '<li style="color: #8892B0;">Sin hallazgos.</li>';
    } else {
      findings.forEach(finding => {
        const li = document.createElement("li");
        li.textContent = finding;
        findingsEl.appendChild(li);
      });
    }
  }
}

function renderActionsTab(mediaData, campaignData, forecastData, input) {
  const briefEl = document.getElementById("action-brief");
  const oppsEl = document.getElementById("action-opportunities");
  const frictionsEl = document.getElementById("action-frictions");
  const itemsEl = document.getElementById("action-items");
  const planEl = document.getElementById("action-plan-by-topic");
  const speechEl = document.getElementById("action-speech");

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "General";
  const candidate = input?.candidateName || "el candidato";

  // Brief ejecutivo
  if (briefEl) {
    const icceLabel = signals.icce ? `ICCE en ${signals.icce.toFixed(0)}` : "sin datos suficientes";
    const sentLabel = sentiment.netLabel ? `balance de tono ${sentiment.netLabel}` : "tono mixto";
    briefEl.textContent = `Conversacion en ${topic} con ${icceLabel} y ${sentLabel}. ${buildRecommendationText(signals.icce, sentiment.netLabel, topic)}`;
  }

  // Oportunidades
  if (oppsEl) {
    oppsEl.innerHTML = "";
    const drivers = buildDrivers(mediaData, forecastData, null, input);
    drivers.forEach(d => {
      const li = document.createElement("li");
      li.textContent = d;
      oppsEl.appendChild(li);
    });
  }

  // Fricciones
  if (frictionsEl) {
    frictionsEl.innerHTML = "";
    const risks = buildRisks(mediaData, forecastData, input);
    risks.forEach(r => {
      const li = document.createElement("li");
      li.textContent = r;
      frictionsEl.appendChild(li);
    });
  }

  // Acciones internas
  if (itemsEl) {
    itemsEl.innerHTML = "";
    const actions = [
      { label: "Monitorear", text: `Vigilar picos en ${topic}. Alertas si volumen sube 50%.` },
      { label: "Validar", text: "Verificar claims en data antes de amplificar." },
      { label: "Preparar", text: "Contingencias listas si riesgo sube a alto." }
    ];
    actions.forEach(action => {
      const item = document.createElement("div");
      item.style.cssText = "background: rgba(255,255,255,0.02); padding: 0.75rem 1rem; border-radius: 0.5rem; margin-bottom: 0.5rem;";
      item.innerHTML = `<strong style="color: var(--accent);">${action.label}:</strong> <span style="color: #8892B0;">${action.text}</span>`;
      itemsEl.appendChild(item);
    });
  }

  // Plan por tema
  if (planEl) {
    planEl.innerHTML = "";
    const plan = campaignData?.strategic_plan || {};
    const objectives = plan.objectives || [`Mejorar percepcion en ${topic}`];
    objectives.slice(0, 2).forEach(obj => {
      const item = document.createElement("div");
      item.style.cssText = "background: rgba(255,255,255,0.02); padding: 1rem; border-radius: 0.5rem; margin-bottom: 0.75rem;";
      item.innerHTML = `
        <p style="font-weight: 500; margin-bottom: 0.5rem;">${obj}</p>
        <p style="font-size: 0.85rem; color: #8892B0;">Senal esperada: Mejora del balance de tono en ${topic}.</p>
      `;
      planEl.appendChild(item);
    });
  }

  // Discurso
  if (speechEl) {
    speechEl.textContent = campaignData?.speech?.content || "Discurso no disponible.";
  }
}

function renderVigilanceTab(forecastData, mediaData, input) {
  const daysEl = document.getElementById("vigilance-forecast-days");
  const scenarioUpEl = document.getElementById("scenario-up");
  const scenarioDownEl = document.getElementById("scenario-down");
  const momentumEl = document.getElementById("risk-momentum");
  const volatilityEl = document.getElementById("risk-volatility");
  const criticsEl = document.getElementById("risk-critics");
  const confEl = document.getElementById("risk-confidence");

  const forecastDays = document.getElementById("unified-forecast-days")?.value || 14;
  if (daysEl) daysEl.textContent = forecastDays;

  const signals = extractForecastSignals(forecastData);
  const topic = input?.topic || "el tema";

  // Escenarios
  if (scenarioUpEl) {
    scenarioUpEl.textContent = `Ventana para acciones tacticas en ${topic}. Aprovechar momentum favorable.`;
  }
  if (scenarioDownEl) {
    scenarioDownEl.textContent = `Reforzar narrativa en ${topic}. Activar plan de contencion.`;
  }

  // Senales de riesgo
  if (momentumEl) {
    const mom = signals.momentum;
    const label = mom == null ? "-" : mom > 0.02 ? "Positivo" : mom < -0.02 ? "Negativo" : "Estable";
    const color = mom == null ? "#8892B0" : mom > 0.02 ? "#42d697" : mom < -0.02 ? "#FF6A3D" : "#8892B0";
    momentumEl.textContent = label;
    momentumEl.style.color = color;
  }

  if (volatilityEl) {
    volatilityEl.textContent = "Baja";
    volatilityEl.style.color = "#42d697";
  }

  if (criticsEl) {
    const negPct = ((mediaData?.sentiment_overview?.negative || 0) * 100).toFixed(0);
    criticsEl.textContent = `${negPct}%`;
    criticsEl.style.color = negPct > 30 ? "#FF6A3D" : negPct > 20 ? "#F5B800" : "#42d697";
  }

  if (confEl) {
    const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;
    const confidence = calculateConfidenceLevel(tweetsAnalyzed, signals);
    confEl.textContent = confidence.level;
    confEl.style.color = confidence.level === "Alta" ? "#42d697" : confidence.level === "Media" ? "#F5B800" : "#FF6A3D";
  }

  // Render chart and alerts
  renderUnifiedChart(forecastData, input);
  renderForecastPanels(forecastData);
}

function renderGeoTab(mediaData, input) {
  renderGeoPanel(mediaData, input?.location);

  // Contexto geografico adicional
  const concEl = document.getElementById("geo-concentration");
  const domEl = document.getElementById("geo-dominant");
  const oppEl = document.getElementById("geo-opportunity");
  const sentGridEl = document.getElementById("geo-sentiment-grid");

  const distribution = buildGeoDistribution(mediaData, input?.location);

  if (distribution.length >= 2) {
    const top = distribution[0];
    const second = distribution[1];
    const concentration = (top.weight * 100).toFixed(0);

    if (concEl) {
      concEl.textContent = concentration > 40 ? `Alta (${concentration}% en ${top.name})` : `Distribuida`;
    }
    if (domEl) {
      domEl.textContent = top.name;
    }
    if (oppEl) {
      oppEl.textContent = concentration > 40 ? `Expandir hacia ${second.name}` : `Balance adecuado entre regiones`;
    }
  }

  // Grid de sentiment por region
  if (sentGridEl) {
    sentGridEl.innerHTML = "";
    distribution.slice(0, 4).forEach(point => {
      const item = document.createElement("div");
      item.style.cssText = "background: rgba(255,255,255,0.02); padding: 0.75rem; border-radius: 0.5rem; text-align: center;";
      item.innerHTML = `
        <p style="font-weight: 500; margin-bottom: 0.25rem;">${point.name}</p>
        <p style="font-size: 0.85rem; color: #8892B0;">${(point.weight * 100).toFixed(1)}%</p>
      `;
      sentGridEl.appendChild(item);
    });
  }
}

function renderExplorationTab(mediaData, forecastData) {
  renderSentimentChart(mediaData, {});
  renderTopics(mediaData);
}

function renderNarrativeSummary(mediaData, forecastData, trendingData, input) {
  const summaryEl = document.getElementById("narrative-summary");
  const tagsEl = document.getElementById("summary-tags");
  const titleEl = document.getElementById("narrative-title");
  const driversEl = document.getElementById("narrative-drivers");
  const risksEl = document.getElementById("narrative-risks");
  const watchEl = document.getElementById("narrative-watch");

  const location = input?.location || "la region";
  const candidate = input?.candidateName || "";
  const topic = input?.topic || "General";
  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);

  // Dynamic title
  if (titleEl) {
    let title = "Estado de la Narrativa";
    if (candidate) title += ` para ${candidate}`;
    if (topic && topic !== "General") title += ` en ${topic}`;
    titleEl.textContent = title;
  }

  // Summary text
  const overview = mediaData?.summary?.overview;
  const daysBack = document.getElementById("unified-days-back")?.value || 30;
  const fallback = `La conversacion en ${location}${candidate ? ` para ${candidate}` : ""} muestra una dinamica ${signals.icce > 55 ? "favorable" : signals.icce < 45 ? "critica" : "mixta"}. ${signals.forecastDirection || ""}`.trim();
  if (summaryEl) summaryEl.textContent = overview || fallback;

  // Generate drivers based on data
  const drivers = buildDrivers(mediaData, forecastData, trendingData, input);
  if (driversEl) {
    driversEl.innerHTML = "";
    drivers.forEach(driver => {
      const li = document.createElement("li");
      li.textContent = driver;
      driversEl.appendChild(li);
    });
  }

  // Generate risks based on data
  const risks = buildRisks(mediaData, forecastData, input);
  if (risksEl) {
    risksEl.innerHTML = "";
    risks.forEach(risk => {
      const li = document.createElement("li");
      li.textContent = risk;
      risksEl.appendChild(li);
    });
  }

  // Generate watch items
  const watchItems = buildWatchItems(mediaData, forecastData, input);
  if (watchEl) {
    watchEl.innerHTML = "";
    watchItems.forEach(item => {
      const li = document.createElement("li");
      li.textContent = item;
      watchEl.appendChild(li);
    });
  }

  // Tags
  if (tagsEl) {
    tagsEl.innerHTML = "";
    const tags = [];
    if (mediaData?.summary?.key_stats) tags.push(...mediaData.summary.key_stats.slice(0, 3));
    if (trendingData?.trending_topics) {
      tags.push(...trendingData.trending_topics.slice(0, 3).map((t) => `#${t}`));
    }
    if (tags.length === 0) {
      tags.push("Sin tags destacados");
    }
    tags.forEach((tag) => {
      const chip = document.createElement("span");
      chip.className = "summary-tag";
      chip.textContent = tag;
      tagsEl.appendChild(chip);
    });
  }
}

function buildDrivers(mediaData, forecastData, trendingData, input) {
  const drivers = [];
  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "el tema";

  if (signals.icce && signals.icce > 55) {
    drivers.push(`Alta traccion en ${topic} (ICCE ${signals.icce.toFixed(1)})`);
  }
  if (signals.momentum && signals.momentum > 0.01) {
    drivers.push(`Momentum positivo sostenido`);
  }
  if (sentiment.netLabel && parseFloat(sentiment.netLabel) > 10) {
    drivers.push(`Sentiment favorable en la muestra`);
  }
  if (trendingData?.trending_topics?.length > 0) {
    drivers.push(`Temas trending alineados: ${trendingData.trending_topics.slice(0, 2).join(", ")}`);
  }
  if (mediaData?.topics?.length > 0) {
    const topTopic = mediaData.topics[0];
    if (topTopic.sentiment?.positive > 0.4) {
      drivers.push(`Engagement alto en ${topTopic.topic}`);
    }
  }

  return drivers.length > 0 ? drivers.slice(0, 3) : ["Sin drivers significativos detectados"];
}

function buildRisks(mediaData, forecastData, input) {
  const risks = [];
  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "el tema";

  if (signals.icce && signals.icce < 45) {
    risks.push(`ICCE bajo (${signals.icce.toFixed(1)}) - riesgo de desgaste`);
  }
  if (signals.momentum && signals.momentum < -0.01) {
    risks.push(`Momentum negativo - tendencia a la baja`);
  }
  if (sentiment.netLabel && parseFloat(sentiment.netLabel) < -5) {
    risks.push(`Predominio de criticas en la conversacion`);
  }
  if (mediaData?.sentiment_overview?.negative > 0.3) {
    risks.push(`Mas de 30% de menciones negativas`);
  }
  if (mediaData?.metadata?.tweets_analyzed < 50) {
    risks.push(`Bajo volumen de datos - confianza reducida`);
  }

  return risks.length > 0 ? risks.slice(0, 3) : ["Sin riesgos criticos detectados"];
}

function buildWatchItems(mediaData, forecastData, input) {
  const watchItems = [];
  const signals = extractForecastSignals(forecastData);
  const topic = input?.topic || "el tema";
  const location = input?.location || "la region";

  if (signals.forecastDirection) {
    watchItems.push(`Proyeccion: ${signals.forecastDirection} - actuar si cambia direccion`);
  }
  if (signals.momentum) {
    if (Math.abs(signals.momentum) < 0.01) {
      watchItems.push(`Momentum estable - vigilar cambios subitos`);
    }
  }
  watchItems.push(`Picos en ${topic} en ${location} - activar alertas si volumen sube 50%+`);

  if (mediaData?.topics?.length > 1) {
    const secondTopic = mediaData.topics[1];
    if (secondTopic) {
      watchItems.push(`Tema secundario "${secondTopic.topic}" puede ganar relevancia`);
    }
  }

  return watchItems.slice(0, 3);
}

function renderNarrativeMetrics(mediaData, forecastData, input) {
  // Elementos del resumen narrativo
  const summaryEl = document.getElementById("narrative-summary");
  const tagsEl = document.getElementById("summary-tags");
  
  // Elementos de fuerza narrativa
  const strengthEl = document.getElementById("narrative-strength");
  const trendEl = document.getElementById("narrative-trend");
  const projectionEl = document.getElementById("narrative-projection");
  const positionEl = document.getElementById("narrative-position");
  const riskEl = document.getElementById("narrative-risk");
  const recommendationEl = document.getElementById("narrative-recommendation");
  const dominanceEl = document.getElementById("narrative-dominance");
  const toneEl = document.getElementById("narrative-tone");

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const icceValue = signals.icce ?? null;
  const topic = input?.topic || "General";
  const candidate = input?.candidateName || "el candidato";
  const location = input?.location || "la región";
  const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;

  // Resumen narrativo - texto principal
  if (summaryEl) {
    const execSummary = mediaData?.summary?.executive_summary;
    if (execSummary) {
      summaryEl.textContent = execSummary;
    } else {
      const posPct = ((mediaData?.sentiment_overview?.positive || 0) * 100).toFixed(0);
      const negPct = ((mediaData?.sentiment_overview?.negative || 0) * 100).toFixed(0);
      const icceText = icceValue ? `con un ICCE de ${icceValue.toFixed(1)}` : "";
      const sentimentText = posPct > negPct ? "predominantemente favorable" : posPct < negPct ? "con tono crítico" : "con tono mixto";
      summaryEl.textContent = `La conversación sobre ${topic} en ${location} ${icceText} muestra un clima ${sentimentText}. ${posPct}% de las menciones son positivas frente a ${negPct}% negativas. ${buildRecommendationText(icceValue, sentiment.netLabel, topic)}`;
    }
  }

  // Tags del resumen
  if (tagsEl) {
    tagsEl.innerHTML = "";
    const tags = [];
    if (icceValue) tags.push(`ICCE ${icceValue.toFixed(1)}`);
    if (signals.momentum != null) tags.push(`Momentum ${formatSigned(signals.momentum, 3)}`);
    if (sentiment.netValue != null) tags.push(`Sentimiento ${sentiment.netValue >= 0 ? "+" : ""}${(sentiment.netValue * 100).toFixed(0)}%`);
    if (tweetsAnalyzed) tags.push(`${tweetsAnalyzed} tweets`);
    
    tags.forEach(tag => {
      const span = document.createElement("span");
      span.className = "summary-tag";
      span.textContent = tag;
      tagsEl.appendChild(span);
    });
  }

  // Fuerza narrativa
  const strengthLabel = icceValue == null ? "Sin datos" : narrativeStrengthLabel(icceValue);
  if (strengthEl) {
    if (icceValue != null) {
      const comparison = icceValue > 60 ? "por encima del promedio" : icceValue < 40 ? "por debajo" : "en rango neutral";
      strengthEl.textContent = `${icceValue.toFixed(1)} · ${strengthLabel.charAt(0).toUpperCase() + strengthLabel.slice(1)} (${comparison})`;
    } else {
      strengthEl.textContent = "-";
    }
  }

  // Tendencia semanal
  if (trendEl) {
    const momentumText = signals.momentumLabel || "Sin tendencia";
    const arrow = signals.momentum > 0.01 ? "↑" : signals.momentum < -0.01 ? "↓" : "→";
    trendEl.textContent = `${arrow} ${momentumText}`;
  }

  // Proyección
  if (projectionEl) projectionEl.textContent = signals.forecastDirection || "Sin proyección disponible";

  // Posición narrativa
  if (positionEl) positionEl.textContent = narrativePositionLabel(icceValue, sentiment.netLabel);

  // Riesgo
  if (riskEl) {
    const riskLevel = narrativeRiskLabel(icceValue, signals.momentum, sentiment.netLabel);
    const riskColor = riskLevel === "alto" ? "#FF6A3D" : riskLevel === "medio" ? "#F5B800" : "#42d697";
    const riskIcon = riskLevel === "alto" ? "⚠️" : riskLevel === "medio" ? "⚡" : "✓";
    const riskHint = riskLevel === "alto" ? "alerta" : riskLevel === "medio" ? "vigilancia" : "estable";
    riskEl.innerHTML = `<span style="color: ${riskColor}; font-weight: 600;">${riskIcon} ${riskLevel.toUpperCase()} · ${riskHint}</span>`;
  }

  // Recomendación
  if (recommendationEl) {
    recommendationEl.textContent = buildRecommendationText(icceValue, sentiment.netLabel, topic);
  }

  // Dominio narrativo
  if (dominanceEl) {
    const topTopic = mediaData?.topics?.[0];
    if (topTopic) {
      const topSentiment = topTopic.sentiment?.positive > topTopic.sentiment?.negative ? "favorable" : "mixto";
      dominanceEl.textContent = `${topTopic.topic} (${topTopic.tweet_count} menciones, tono ${topSentiment})`;
    } else {
      dominanceEl.textContent = topic || "Sin datos de temas";
    }
  }

  // Tono de conversación
  if (toneEl) {
    const posPct = ((mediaData?.sentiment_overview?.positive || 0) * 100).toFixed(0);
    const negPct = ((mediaData?.sentiment_overview?.negative || 0) * 100).toFixed(0);
    const neuPct = ((mediaData?.sentiment_overview?.neutral || 0) * 100).toFixed(0);
    toneEl.textContent = `${posPct}% positivo · ${neuPct}% neutral · ${negPct}% crítico`;
  }
}

function calculateConfidenceLevel(tweetsAnalyzed, signals) {
  let score = 0;
  let reasons = [];

  if (tweetsAnalyzed >= 100) {
    score += 2;
    reasons.push("volumen alto");
  } else if (tweetsAnalyzed >= 50) {
    score += 1;
    reasons.push("volumen medio");
  } else {
    reasons.push("volumen bajo");
  }

  if (signals.icce != null) {
    score += 1;
  }
  if (signals.momentum != null) {
    score += 1;
  }

  if (score >= 3) {
    return { level: "Alta", reason: reasons[0] || "datos consistentes" };
  } else if (score >= 2) {
    return { level: "Media", reason: reasons[0] || "datos parciales" };
  } else {
    return { level: "Baja", reason: "datos insuficientes" };
  }
}

function renderStreamLists(mediaData, forecastData, trendingData, input) {
  const mediaList = document.getElementById("media-stream-list");
  const campaignList = document.getElementById("campaign-stream-list");
  const forecastList = document.getElementById("forecast-stream-list");
  const mediaContext = document.getElementById("media-stream-context");
  const campaignContext = document.getElementById("campaign-stream-context");
  const forecastContext = document.getElementById("forecast-stream-context");

  const topic = input?.topic || "el tema";
  const location = input?.location || "la region";

  // Media stream with importance context
  const mediaFindings = mediaData?.summary?.key_findings?.map((finding, i) => {
    if (i === 0) return `${finding} – Indica tono ciudadano predominante`;
    return finding;
  }) || [];
  const topicMentions = mediaData?.topics?.map((t) => {
    const sentLabel = t.sentiment?.positive > t.sentiment?.negative ? "favorable" : "mixto";
    return `${t.topic}: ${t.tweet_count} menciones (tono ${sentLabel})`;
  }) || [];

  fillList(mediaList, mediaFindings, topicMentions, "Sin hallazgos de medios.");
  if (mediaContext) {
    const negPct = mediaData?.sentiment_overview?.negative ? (mediaData.sentiment_overview.negative * 100).toFixed(0) : 0;
    mediaContext.textContent = negPct > 25
      ? `Alerta: ${negPct}% de menciones negativas detectadas.`
      : `Tono general controlado (${negPct}% negativos).`;
  }

  // Campaign stream with importance context
  const trendingItems = trendingData?.trending_topics?.map((topic, i) => {
    return `Tema caliente: ${topic}${i === 0 ? " – Mayor traccion actual" : ""}`;
  }) || [];

  fillList(campaignList, trendingItems, [], "Sin tendencias disponibles.");
  if (campaignContext) {
    campaignContext.textContent = trendingData?.trending_topics?.length > 0
      ? `${trendingData.trending_topics.length} temas activos en ${location}. Vigilar picos subitos.`
      : "Sin temas trending detectados en esta ventana.";
  }

  // Forecast stream with importance context
  const forecastSignals = extractForecastSignals(forecastData);
  const forecastItems = [
    forecastSignals.forecastDirection ? `${forecastSignals.forecastDirection} – Proyeccion principal` : null,
    forecastSignals.momentumLabel ? `${forecastSignals.momentumLabel} – Velocidad de cambio` : null,
    forecastSignals.icceLabel ? `${forecastSignals.icceLabel} – Indice actual` : null
  ].filter(Boolean);

  fillList(forecastList, forecastItems, [], "Sin forecast disponible.");
  if (forecastContext) {
    if (forecastSignals.momentum && forecastSignals.momentum < -0.02) {
      forecastContext.textContent = "Atencion: Momentum negativo. Considerar accion preventiva.";
    } else if (forecastSignals.momentum && forecastSignals.momentum > 0.02) {
      forecastContext.textContent = "Momentum positivo. Ventana favorable para acciones tacticas.";
    } else {
      forecastContext.textContent = "Tendencia estable. Mantener monitoreo activo.";
    }
  }
}

function renderGameTheoryBlock(mediaData, forecastData, trendingData, campaignData, input) {
  const mainEl = document.getElementById("game-main");
  const altEl = document.getElementById("game-alternatives");
  const signalEl = document.getElementById("game-rival-signal");
  const triggerEl = document.getElementById("game-trigger");
  const payoffEl = document.getElementById("game-payoff");
  const confidenceEl = document.getElementById("game-confidence");
  const radarCtx = document.getElementById("game-radar-chart");
  const gapCtx = document.getElementById("game-gap-chart");
  const radarContextEl = document.getElementById("game-radar-context");
  const gapContextEl = document.getElementById("game-gap-context");
  const rivalNameEl = document.getElementById("game-rival-name");
  const candidateNameEl = document.getElementById("game-candidate-name");

  if (!mainEl && !altEl && !signalEl && !triggerEl) return;

  const selectedRival = getSelectedRivalName();
  if (rivalNameEl) rivalNameEl.textContent = selectedRival;
  if (candidateNameEl) candidateNameEl.textContent = input?.candidateName || "Paloma Valencia";

  const gameData = buildGameTheoryFromSelection(
    mediaData,
    forecastData,
    trendingData,
    campaignData,
    input,
    selectedRival
  );

  if (mainEl) mainEl.textContent = gameData.main_move || "-";
  if (altEl) {
    altEl.innerHTML = "";
    (gameData.alternatives || []).forEach((alt) => {
      const li = document.createElement("li");
      li.textContent = alt;
      altEl.appendChild(li);
    });
  }
  if (signalEl) signalEl.textContent = gameData.rival_signal || "";
  if (triggerEl) triggerEl.textContent = gameData.trigger || "";
  if (payoffEl) payoffEl.textContent = gameData.payoff || "Payoff estimado";
  if (confidenceEl) confidenceEl.textContent = gameData.confidence ? `Confianza ${gameData.confidence}` : "Confianza media";

  renderGameTheoryCharts(gameData, radarCtx, gapCtx, radarContextEl, gapContextEl);
}

function buildGameTheoryFromSelection(mediaData, forecastData, trendingData, campaignData, input, selectedRival) {
  const baseGame = campaignData?.analysis?.game_theory || campaignData?.game_theory;
  const rivals = baseGame?.rivals || {};
  if (rivals[selectedRival]) {
    return { ...baseGame, ...rivals[selectedRival] };
  }

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topTopic = mediaData?.topics?.[0]?.topic || input?.topic || "Seguridad";
  const secondTopic = mediaData?.topics?.[1]?.topic || "Economia";
  const rivalProfile = RIVAL_PROFILES[selectedRival] || { seguridad: 58, economia: 58, salud: 58, paz: 58, sov: 58, sna: 40, momentum: 0.003 };

  const campaignScore = buildCampaignScores(signals, sentiment);
  const rivalScore = {
    seguridad: rivalProfile.seguridad,
    economia: rivalProfile.economia,
    salud: rivalProfile.salud,
    paz: rivalProfile.paz,
    sov: rivalProfile.sov,
    sna: rivalProfile.sna
  };
  const rivalIcce = (rivalScore.sov + rivalScore.sna) / 2;
  const rivalMomentum = (rivalProfile.momentum || 0) * 100;

  let mainMove = `Contrastar en ${topTopic}: comunicado + video corto + 3 posts con hashtags`;
  if (signals.icce != null && signals.icce >= 60 && signals.momentum > 0) {
    mainMove = `Proponer en ${topTopic}: anuncio táctico + entrevista regional + hilo explicativo`;
  } else if (sentiment.netValue != null && sentiment.netValue < 0) {
    mainMove = `Contener en ${topTopic}: mensajes de precisión + vocería técnica`;
  }

  const alternatives = [
    "Proponer economía: costo de vida + propuestas de empleo",
    "Desviar a salud: financiación hospitalaria + visita a clínica"
  ];

  const payoff = signals.icce != null && signals.icce >= 60
    ? "Payoff estimado: +12 ICCE · +8 SNA · costo medio"
    : "Payoff estimado: +6 ICCE · +4 SNA · costo bajo";

  const trigger = `Trigger: si ICCE cae >8 pts o SNA baja -10 en ${topTopic}, activar respuesta en 48h.`;
  const confidence = calculateConfidenceLevel(mediaData?.metadata?.tweets_analyzed || 0, signals).level;
  const rivalSignal = `Señal rival: ${selectedRival} domina ${topTopic} (+12% conversación)`;
  const fallback = baseGame || {};

  return {
    main_move: fallback.main_move || mainMove,
    alternatives: fallback.alternatives || alternatives,
    rival_signal: fallback.rival_signal || rivalSignal,
    trigger: fallback.trigger || trigger,
    payoff: fallback.payoff || payoff,
    confidence: fallback.confidence || confidence,
    compare: {
      labels: ["Seguridad", "Economía", "Salud", "Paz", "SOV General", "SNA Neto"],
      campaign: [campaignScore.seguridad, campaignScore.economia, campaignScore.salud, campaignScore.paz, campaignScore.sov, campaignScore.sna],
      rival: [rivalScore.seguridad, rivalScore.economia, rivalScore.salud, rivalScore.paz, rivalScore.sov, rivalScore.sna]
    },
    gap: {
      labels: ["SOV", "SNA", "ICCE", "Momentum"],
      values: [
        campaignScore.sov - rivalScore.sov,
        campaignScore.sna - rivalScore.sna,
        (signals.icce || 55) - rivalIcce,
        (signals.momentum || 0) * 100 - rivalMomentum
      ]
    },
    context: {
      radar: `Comparación vs ${selectedRival}. Brecha principal en ${topTopic}.`,
      gap: `Ventaja relativa en ${secondTopic}. Refuerza mensajes con mejor tono.`
    }
  };
}

function buildCampaignScores(signals, sentiment) {
  return {
    seguridad: Math.min(80, Math.max(35, (signals.icce || 55) + 5)),
    economia: 60,
    salud: 58,
    paz: 55,
    sov: Math.min(75, Math.max(40, 50 + (signals.momentum || 0) * 400)),
    sna: Math.min(80, Math.max(30, 50 + (sentiment.netValue || 0) * 100))
  };
}

function renderGameTheoryCharts(gameData, radarCtx, gapCtx, radarContextEl, gapContextEl) {
  if (!radarCtx || !gapCtx) return;

  const compare = gameData.compare || {};
  const gap = gameData.gap || {};

  if (gameRadarChart) gameRadarChart.destroy();
  gameRadarChart = new Chart(radarCtx, {
    type: "radar",
    data: {
      labels: compare.labels || [],
      datasets: [
        {
          label: "Tu campaña",
          data: compare.campaign || [],
          backgroundColor: "rgba(66, 214, 151, 0.2)",
          borderColor: "#42d697",
          pointBackgroundColor: "#42d697"
        },
        {
          label: "Rival principal",
          data: compare.rival || [],
          backgroundColor: "rgba(255, 106, 61, 0.18)",
          borderColor: "#FF6A3D",
          pointBackgroundColor: "#FF6A3D"
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: "rgba(255,255,255,0.08)" },
          grid: { color: "rgba(255,255,255,0.08)" },
          pointLabels: { color: "#F5F7FA", font: { size: 11 } },
          ticks: { color: "#8892B0", backdropColor: "transparent" }
        }
      },
      plugins: {
        legend: { labels: { color: "#F5F7FA" } }
      }
    }
  });

  if (gameGapChart) gameGapChart.destroy();
  gameGapChart = new Chart(gapCtx, {
    type: "bar",
    data: {
      labels: gap.labels || [],
      datasets: [
        {
          label: "Brecha vs rival",
          data: gap.values || [],
          backgroundColor: (gap.values || []).map((value) =>
            value >= 0 ? "rgba(66, 214, 151, 0.75)" : "rgba(255, 106, 61, 0.75)"
          )
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
      }
    }
  });

  if (radarContextEl) {
    radarContextEl.textContent = gameData?.context?.radar || "Comparación de fuerza narrativa por tema.";
  }
  if (gapContextEl) {
    gapContextEl.textContent = gameData?.context?.gap || "Brechas claves entre campañas.";
  }
}

function renderAnalysisOutputs(mediaData, campaignData, forecastData) {
  const execEl = document.getElementById("analysis-exec-summary");
  const dataEl = document.getElementById("analysis-data");
  const planEl = document.getElementById("analysis-plan-text");
  const speechEl = document.getElementById("analysis-speech");
  const chartEl = document.getElementById("analysis-chart");
  const generalEl = document.getElementById("analysis-general");

  // Informe ejecutivo: priorizar campaignData, luego mediaData
  const execSummary = campaignData?.analysis?.executive_summary 
    || mediaData?.summary?.executive_summary 
    || mediaData?.summary?.overview 
    || "No hay resumen ejecutivo disponible.";

  // Análisis de datos: priorizar campaignData, luego key_findings de mediaData
  const dataAnalysis = campaignData?.analysis?.data_analysis 
    || (mediaData?.summary?.key_findings?.length 
        ? mediaData.summary.key_findings.join("\n\n• ") 
        : "No hay análisis de datos disponible.");

  // Plan estratégico: de campaignData
  const plan = campaignData?.analysis?.strategic_plan 
    || (campaignData?.recommendations?.length 
        ? campaignData.recommendations.join("\n\n• ") 
        : "Plan estratégico no disponible. Se requiere un tema para generar el plan.");

  // Discurso: de campaignData
  const speech = campaignData?.analysis?.speech 
    || "Discurso no disponible. Se requiere un tema para generar el discurso.";

  // Sugerencia de gráfico: de campaignData o descripción por defecto
  const chartText = campaignData?.analysis?.chart_suggestion 
    || (forecastData?.forecast 
        ? "Gráfico sugerido: ICCE histórico vs forecast con intervalos de confianza. Muestra la evolución de la conversación y proyección a 14 días."
        : "Gráfico sugerido no disponible.");

  // Análisis general: de campaignData o fallback con metadata
  const general = campaignData?.analysis?.general_analysis 
    || (forecastData?.metadata?.model_type 
        ? `Análisis general basado en modelo ${forecastData.metadata.model_type}. ICCE y momentum calculados con datos de los últimos ${forecastData.metadata.days_back || 30} días.`
        : "Análisis general no disponible.");

  if (execEl) execEl.textContent = execSummary;
  if (dataEl) dataEl.textContent = dataAnalysis;
  if (planEl) planEl.textContent = plan;
  if (speechEl) speechEl.textContent = speech;
  if (chartEl) chartEl.textContent = chartText;
  if (generalEl) generalEl.textContent = general;
}

function renderTopics(mediaData) {
  const tableEl = document.getElementById("topics-table");
  if (!tableEl) return;
  tableEl.innerHTML = "";

  const topics = mediaData?.topics || [];
  if (!topics.length) {
    const empty = document.createElement("p");
    empty.textContent = "No hay temas disponibles.";
    tableEl.appendChild(empty);
    return;
  }

  topics.forEach((topic) => {
    const row = document.createElement("div");
    row.className = "topics-row";

    const title = document.createElement("div");
    const titleStrong = document.createElement("strong");
    titleStrong.textContent = topic.topic;
    const titleMeta = document.createElement("span");
    titleMeta.textContent = `${topic.tweet_count} menciones`;
    title.appendChild(titleStrong);
    title.appendChild(document.createElement("br"));
    title.appendChild(titleMeta);
    row.appendChild(title);

    const sentimentLabel = document.createElement("div");
    sentimentLabel.textContent = buildSentimentLabel(topic.sentiment);
    row.appendChild(sentimentLabel);

    const bar = document.createElement("div");
    bar.className = "sentiment-bar";
    const pos = document.createElement("span");
    pos.className = "pos";
    pos.style.width = `${(topic.sentiment.positive || 0) * 100}%`;
    const neu = document.createElement("span");
    neu.className = "neu";
    neu.style.width = `${(topic.sentiment.neutral || 0) * 100}%`;
    const neg = document.createElement("span");
    neg.className = "neg";
    neg.style.width = `${(topic.sentiment.negative || 0) * 100}%`;
    bar.appendChild(pos);
    bar.appendChild(neu);
    bar.appendChild(neg);
    row.appendChild(bar);

    tableEl.appendChild(row);
  });
}

function renderSentimentChart(mediaData, input) {
  const ctx = document.getElementById("sentiment-chart");
  const contextEl = document.getElementById("chart-sentiment-context");

  if (!ctx) return;
  if (!mediaData?.sentiment_overview) return;

  const sentiment = mediaData.sentiment_overview;
  const posPct = (sentiment.positive || 0) * 100;
  const neuPct = (sentiment.neutral || 0) * 100;
  const negPct = (sentiment.negative || 0) * 100;

  // Add context based on sentiment distribution
  if (contextEl) {
    if (negPct > 30) {
      contextEl.textContent = `Alerta: ${negPct.toFixed(0)}% de criticos. Considerar respuesta en ${input?.topic || "el tema"}.`;
    } else if (posPct > 50) {
      contextEl.textContent = `Balance favorable: ${posPct.toFixed(0)}% positivos. Aprovechar momentum.`;
    } else {
      contextEl.textContent = `Tono mixto: ${posPct.toFixed(0)}% positivo, ${negPct.toFixed(0)}% critico. Monitorear cambios.`;
    }
  }

  if (sentimentChart) sentimentChart.destroy();
  sentimentChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Positivo", "Neutral", "Negativo"],
      datasets: [
        {
          data: [posPct, neuPct, negPct],
          backgroundColor: ["rgba(66, 214, 151, 0.8)", "rgba(255, 255, 255, 0.4)", "rgba(255, 106, 61, 0.85)"]
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          labels: { color: "#F5F7FA" }
        }
      }
    }
  });
}

function renderForecastPanels(forecastData, mediaData) {
  const listEl = document.getElementById("forecast-details-list");
  const alertsEl = document.getElementById("forecast-alerts-list");
  if (listEl) listEl.innerHTML = "";
  if (alertsEl) alertsEl.innerHTML = "";

  const signals = extractForecastSignals(forecastData);
  const daysBack = forecastData?.metadata?.days_back || 30;
  const forecastDays = forecastData?.metadata?.forecast_days || 14;

  if (listEl) {
    const detailItems = [];
    
    // ICCE actual con interpretación
    if (signals.icce != null) {
      const icceInterpretation = signals.icce >= 60 
        ? "Clima narrativo favorable - ventana para amplificar mensaje"
        : signals.icce >= 45 
          ? "Clima narrativo neutral - mantener monitoreo activo"
          : "Clima narrativo crítico - considerar ajuste de estrategia";
      detailItems.push(`📊 ICCE actual: ${signals.icce.toFixed(1)} — ${icceInterpretation}`);
    }

    // Momentum con interpretación
    if (signals.momentum != null) {
      const momValue = (signals.momentum * 100).toFixed(2);
      const momInterpretation = signals.momentum > 0.02 
        ? "Tendencia alcista sostenida"
        : signals.momentum > 0 
          ? "Tendencia ligeramente positiva"
          : signals.momentum < -0.02 
            ? "Tendencia bajista - requiere atención"
            : "Tendencia estable";
      detailItems.push(`📈 Momentum: ${momValue > 0 ? '+' : ''}${momValue}% — ${momInterpretation}`);
    }

    // Proyección
    if (signals.forecastDirection) {
      detailItems.push(`🔮 Proyección ${forecastDays} días: ${signals.forecastDirection}`);
      detailItems.push("ℹ️ Cambios mayores a 5 pts suelen ser significativos en narrativa pública.");
    }

    // Ventana de análisis
    detailItems.push(`📅 Ventana analizada: últimos ${daysBack} días`);

    // Modelo usado
    if (forecastData?.metadata?.model_type) {
      detailItems.push(`🧮 Modelo: ${forecastData.metadata.model_type.replace('_', ' ').toUpperCase()}`);
    }

    fillList(listEl, detailItems, [], "Sin datos de forecast disponibles.");
  }

  if (alertsEl) {
    const alerts = buildEnhancedForecastAlerts(signals, forecastData, mediaData);
    fillList(alertsEl, alerts, [], "✓ Sin alertas narrativas activas. Situación estable.");
  }
}

function buildEnhancedForecastAlerts(signals, forecastData, mediaData) {
  const alerts = [];
  
  // Alerta de ICCE bajo
  if (signals.icce != null && signals.icce < 40) {
    alerts.push("⚠️ ALERTA: ICCE bajo (<40). Riesgo de desgaste narrativo. Considerar pausa táctica.");
  } else if (signals.icce != null && signals.icce < 50) {
    alerts.push("⚡ ATENCIÓN: ICCE en zona de riesgo (40-50). Monitorear de cerca.");
  }

  // Alerta de momentum negativo
  if (signals.momentum != null && signals.momentum < -0.03) {
    alerts.push("⚠️ ALERTA: Momentum negativo sostenido. La conversación está perdiendo tracción.");
  } else if (signals.momentum != null && signals.momentum < -0.01) {
    alerts.push("⚡ ATENCIÓN: Momentum ligeramente negativo. Vigilar evolución.");
  }

  // Oportunidades
  if (signals.icce != null && signals.icce >= 60 && signals.momentum != null && signals.momentum > 0) {
    alerts.push("✅ OPORTUNIDAD: ICCE alto + Momentum positivo. Ventana óptima para amplificar mensaje.");
  }

  const negative = mediaData?.sentiment_overview?.negative ?? null;
  if (negative != null && negative > 0.2) {
    alerts.push("⚠️ ALERTA: críticas sostenidas en seguridad. Preparar respuesta con datos y vocería.");
  }

  if (signals.forecastDirection && signals.forecastDirection.includes("sube")) {
    alerts.push("📈 POSITIVO: Proyección al alza. Mantener estrategia actual.");
  } else if (signals.forecastDirection && signals.forecastDirection.includes("baja")) {
    alerts.push("📉 ATENCIÓN: Proyección a la baja. Preparar plan de contingencia.");
  }

  return alerts;
}

function fillList(listEl, primaryItems, secondaryItems, fallback) {
  if (!listEl) return;
  listEl.innerHTML = "";
  const items = [...(primaryItems || []), ...(secondaryItems || [])].filter(Boolean).slice(0, 6);
  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = fallback;
    listEl.appendChild(li);
    return;
  }
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    listEl.appendChild(li);
  });
}

function renderUnifiedChart(forecastData, input) {
  const ctx = document.getElementById("unified-series-chart");
  const subtitleEl = document.getElementById("chart-series-subtitle");
  const contextEl = document.getElementById("chart-series-context");

  if (!ctx || !forecastData) return;

  const { labels, icceValues, forecastValues } = extractSeries(forecastData);
  if (!labels.length) return;

  // Update subtitle with dynamic info
  const daysBack = document.getElementById("unified-days-back")?.value || 30;
  const forecastDays = document.getElementById("unified-forecast-days")?.value || 14;
  if (subtitleEl) {
    subtitleEl.textContent = `Ventana historica: ${daysBack} dias | Proyeccion: ${forecastDays} dias. Importa para anticipar cambios.`;
  }

  // Add context based on trend
  if (contextEl) {
    const lastIcce = icceValues.filter(v => v != null).pop();
    const lastForecast = forecastValues.filter(v => v != null).pop();
    if (lastIcce && lastForecast) {
      const delta = lastForecast - lastIcce;
      if (delta > 5) {
        contextEl.textContent = `Proyeccion al alza (+${delta.toFixed(1)} pts). Ventana favorable para acciones tacticas.`;
      } else if (delta < -5) {
        contextEl.textContent = `Proyeccion a la baja (${delta.toFixed(1)} pts). Considerar medidas preventivas.`;
      } else {
        contextEl.textContent = `Proyeccion estable (${delta > 0 ? "+" : ""}${delta.toFixed(1)} pts). Mantener monitoreo.`;
      }
    }
  }

  if (unifiedChart) unifiedChart.destroy();

  unifiedChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "ICCE historico",
          data: icceValues,
          borderColor: "#FF6A3D",
          backgroundColor: "rgba(255, 106, 61, 0.15)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Forecast ICCE",
          data: forecastValues,
          borderColor: "#42d697",
          backgroundColor: "rgba(66, 214, 151, 0.15)",
          borderDash: [6, 6],
          tension: 0.35,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: "#F5F7FA" }
        }
      },
      scales: {
        x: {
          ticks: { color: "#8892B0" },
          grid: { color: "rgba(136, 146, 176, 0.15)" }
        },
        y: {
          ticks: { color: "#8892B0" },
          grid: { color: "rgba(136, 146, 176, 0.15)" }
        }
      }
    }
  });
}

function renderGeoPanel(mediaData, location) {
  const geoMapEl = document.getElementById("geo-map");
  const geoListEl = document.getElementById("geo-list");
  const geoContextEl = document.getElementById("geo-context");

  if (!geoMapEl || !geoListEl) return;

  const distribution = buildGeoDistribution(mediaData, location);
  geoMapEl.innerHTML = "";
  geoListEl.innerHTML = "";

  distribution.forEach((point, index) => {
    const dot = document.createElement("div");
    dot.className = "geo-dot";
    const size = 8 + point.weight * 18;
    dot.style.width = `${size}px`;
    dot.style.height = `${size}px`;
    dot.style.left = `${point.x}%`;
    dot.style.top = `${point.y}%`;
    dot.setAttribute("title", `${point.name} · ${(point.weight * 100).toFixed(1)}%`);
    geoMapEl.appendChild(dot);

    const li = document.createElement("li");
    li.innerHTML = `<span>${index + 1}. ${point.name}</span><strong>${(point.weight * 100).toFixed(1)}%</strong>`;
    geoListEl.appendChild(li);
  });

  // Add geographic context
  if (geoContextEl && distribution.length >= 2) {
    const top = distribution[0];
    const second = distribution[1];
    const concentration = top.weight * 100;
    if (concentration > 40) {
      geoContextEl.textContent = `Alta concentracion en ${top.name} (${concentration.toFixed(0)}%). Considerar diversificar hacia ${second.name}.`;
    } else {
      geoContextEl.textContent = `Distribucion balanceada. ${top.name} y ${second.name} lideran conversacion.`;
    }
  }
}

function setupUnifiedTabs() {
  const tabs = document.querySelectorAll("#unified-results .tab");
  const contents = document.querySelectorAll("#unified-results .tab-content");
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      contents.forEach((c) => {
        const isActive = c.id === `tab-${target}`;
        c.style.display = isActive ? "block" : "none";
        c.classList.toggle("active", isActive);
      });

      setTimeout(() => {
        if (target === "game") {
          if (gameRadarChart) gameRadarChart.resize();
          if (gameGapChart) gameGapChart.resize();
        }
        if (target === "charts") {
          if (unifiedChart) unifiedChart.resize();
          if (sentimentChart) sentimentChart.resize();
        }
      }, 0);
    });
  });
}

function setupGameRivalSelector() {
  const select = document.getElementById("game-rival-select");
  if (!select) return;
  select.addEventListener("change", () => {
    if (!lastGameContext) return;
    renderGameTheoryBlock(
      lastGameContext.mediaData,
      lastGameContext.forecastData,
      lastGameContext.trendingData,
      lastGameContext.campaignData,
      lastGameContext.input
    );
  });
}

function getSelectedRivalName() {
  const select = document.getElementById("game-rival-select");
  return select?.value || "Vicky Dávila";
}

function setupAccordion() {
  const toggles = document.querySelectorAll(".accordion-toggle");
  if (!toggles.length) return;

  toggles.forEach((toggle) => {
    toggle.addEventListener("click", () => {
      const target = toggle.dataset.target;
      const panel = document.getElementById(target);
      if (!panel) return;
      panel.classList.toggle("active");
    });
  });
}

function buildGeoDistribution(mediaData, location) {
  const provided = mediaData?.metadata?.geo_distribution;
  if (Array.isArray(provided) && provided.length) {
    return normalizeGeoPoints(provided);
  }
  return generateGeoFallback(location || "Colombia");
}

function generateGeoFallback(seedLabel) {
  const seed = hashString(seedLabel);
  const bounds = { latMin: -4.3, latMax: 13.5, lonMin: -79.5, lonMax: -66.8 };
  const points = COLOMBIA_POINTS.map((point, index) => {
    const weight = pseudoRandom(seed + index * 97);
    const x = ((point.lon - bounds.lonMin) / (bounds.lonMax - bounds.lonMin)) * 100;
    const y = ((bounds.latMax - point.lat) / (bounds.latMax - bounds.latMin)) * 100;
    return {
      name: point.name,
      weight,
      x: clamp(x, 4, 96),
      y: clamp(y, 6, 94)
    };
  });
  return normalizeGeoPoints(points);
}

function normalizeGeoPoints(points) {
  const total = points.reduce((sum, point) => sum + (point.weight || 0), 0) || 1;
  return points
    .map((point) => ({ ...point, weight: (point.weight || 0) / total }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, 8);
}

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i++) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function pseudoRandom(seed) {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function extractForecastSignals(forecastData) {
  if (!forecastData) {
    return { icce: null, momentum: null, forecastDirection: null };
  }

  const series = forecastData.series;
  if (series && Array.isArray(series.icce)) {
    const icceNow = (series.icce[series.icce.length - 1] || 0) * 100;
    const momentumNow = series.momentum?.[series.momentum.length - 1] || 0;
    const forecast = forecastData.forecast;
    const forecastDirection = buildForecastDirection(series, forecast);
    return {
      icce: icceNow,
      momentum: momentumNow,
      forecastDirection,
      momentumLabel: momentumLabel(momentumNow),
      icceLabel: `ICCE actual ${icceNow.toFixed(1)}`
    };
  }

  if (forecastData.icce) {
    const icceNow = forecastData.icce.current_icce;
    const momentumNow = forecastData.momentum?.current_momentum ?? null;
    return {
      icce: icceNow,
      momentum: momentumNow,
      forecastDirection: forecastData.forecast ? "Forecast disponible" : null,
      momentumLabel: momentumNow != null ? momentumLabel(momentumNow) : null,
      icceLabel: `ICCE actual ${icceNow.toFixed(1)}`
    };
  }

  return { icce: null, momentum: null, forecastDirection: null };
}

function buildForecastDirection(series, forecast) {
  if (!forecast || !forecast.icce_pred?.length) return "Sin proyeccion disponible";
  const latest = series.icce[series.icce.length - 1] || 0;
  const projected = forecast.icce_pred[forecast.icce_pred.length - 1] || 0;
  const delta = (projected - latest) * 100;
  const direction = delta >= 0 ? "sube" : "baja";
  return `Forecast ${direction} ${Math.abs(delta).toFixed(1)} pts (ICCE ${(latest * 100).toFixed(1)} → ${(projected * 100).toFixed(1)})`;
}

function extractSentiment(mediaData) {
  const sentiment = mediaData?.sentiment_overview;
  if (!sentiment) return { netLabel: null, detail: null };
  const net = sentiment.positive - sentiment.negative;
  const netLabel = `${net >= 0 ? "+" : ""}${(net * 100).toFixed(1)}%`;
  const detail = `Positivo ${(sentiment.positive * 100).toFixed(1)}% · Negativo ${(sentiment.negative * 100).toFixed(1)}%`;
  return { netLabel, detail, netValue: net };
}

function extractSeries(forecastData) {
  if (!forecastData?.series) return { labels: [], icceValues: [], forecastValues: [] };
  const historyLabels = forecastData.series.dates.map((date) => formatShortDate(date));
  const historyValues = forecastData.series.icce.map((value) => (value || 0) * 100);
  const forecastLabels = forecastData.forecast?.dates
    ? forecastData.forecast.dates.map((date) => formatShortDate(date))
    : [];

  const labels = [...historyLabels, ...forecastLabels];
  const icceValues = [...historyValues, ...new Array(forecastLabels.length).fill(null)];
  const forecastValues = buildForecastSeries(historyLabels.length, forecastData);
  return { labels, icceValues, forecastValues };
}

function buildForecastSeries(historyLength, forecastData) {
  const forecast = forecastData.forecast;
  const forecastLength = forecast?.icce_pred?.length || 0;
  const values = new Array(historyLength + forecastLength).fill(null);
  if (!forecast || !forecast.icce_pred?.length) return values;
  const startIndex = Math.max(historyLength - 1, 0);
  forecast.icce_pred.forEach((value, index) => {
    values[startIndex + index] = (value || 0) * 100;
  });
  return values;
}

function momentumLabel(momentum) {
  if (momentum > 0.03) return "Momentum fuerte al alza";
  if (momentum > 0.005) return "Momentum positivo";
  if (momentum < -0.03) return "Momentum fuerte a la baja";
  if (momentum < -0.005) return "Momentum negativo";
  return "Momentum estable";
}

function narrativeStrengthLabel(icce) {
  if (icce >= 70) return "fuerte";
  if (icce >= 45) return "media";
  return "debil";
}

function narrativePositionLabel(icce, netLabel) {
  if (icce == null) return "Sin posicion";
  const net = parseFloat(netLabel || "0");
  if (icce >= 60 && net >= 0) return "Ventaja narrativa";
  if (icce < 45 && net < 0) return "Riesgo narrativo";
  return "Equilibrio narrativo";
}

function formatSigned(value, decimals) {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}${Math.abs(value).toFixed(decimals)}`;
}

function narrativeRiskLabel(icce, momentum, netLabel) {
  const net = parseFloat(netLabel || "0");
  if ((icce != null && icce < 40) || net < -5 || (momentum != null && momentum < -0.03)) {
    return "alto";
  }
  if ((icce != null && icce < 55) || (momentum != null && momentum < -0.01)) {
    return "medio";
  }
  return "bajo";
}

function buildRecommendationText(icce, netLabel, topic) {
  const net = parseFloat(netLabel || "0");
  if (icce == null) return "Sin recomendacion disponible.";
  if (icce < 45 || net < 0) {
    return `Reforzar mensajes positivos en ${topic || "temas prioritarios"} y contener narrativa negativa.`;
  }
  if (icce >= 60 && net > 5) {
    return `Aprovechar ventana favorable con anuncios tacticos en ${topic || "temas clave"}.`;
  }
  return `Mantener consistencia narrativa y monitorear cambios en ${topic || "la agenda"}.`;
}

function buildSentimentLabel(sentiment) {
  if (!sentiment) return "Sin datos";
  const pos = (sentiment.positive || 0) * 100;
  const neg = (sentiment.negative || 0) * 100;
  if (pos - neg > 10) return "Predominio positivo";
  if (neg - pos > 10) return "Predominio negativo";
  return "Tono neutral";
}

function buildForecastAlerts(signals) {
  const alerts = [];
  if (signals.momentum != null && signals.momentum < -0.03) {
    alerts.push("Momentum negativo sostenido");
  }
  if (signals.icce != null && signals.icce < 40) {
    alerts.push("ICCE bajo, riesgo de desgaste");
  }
  if (signals.forecastDirection && signals.forecastDirection.includes("sube")) {
    alerts.push("Proyeccion al alza en corto plazo");
  }
  return alerts;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  return date.toLocaleDateString("es-ES", { month: "short", day: "numeric" });
}

function formatShortDate(value) {
  const date = new Date(value);
  return date.toLocaleDateString("es-ES", { month: "short", day: "numeric" });
}

/**
 * Genera datos de ejemplo completos para Paloma Valencia - Seguridad
 * Incluye: mediaData, forecastData, trendingData, campaignData
 */
function generatePalomaValenciaMockData() {
  // Generar fechas para los últimos 30 días
  const dates = [];
  const today = new Date();
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().split("T")[0]);
  }

  // Generar fechas de forecast (14 días adelante)
  const forecastDates = [];
  for (let i = 1; i <= 14; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    forecastDates.push(d.toISOString().split("T")[0]);
  }

  // ICCE histórico determinístico (cierre en 62.4)
  const icceValues = dates.map((_, i) => {
    const base = 0.58 + i * 0.0015 + (i % 4 === 0 ? 0.002 : 0);
    return Math.max(0.52, Math.min(0.75, base));
  });
  icceValues[icceValues.length - 1] = 0.624;

  // Momentum (último valor = +0.012)
  const momentumValues = icceValues.map((val, i) => {
    if (i === 0) return 0;
    return (val - icceValues[i - 1]) * 0.7;
  });
  momentumValues[momentumValues.length - 1] = 0.012;

  // Forecast ICCE (sube +5.8 pts)
  const lastIcce = icceValues[icceValues.length - 1];
  const targetIcce = lastIcce + 0.058;
  const forecastIcce = forecastDates.map((_, i) => {
    const step = (targetIcce - lastIcce) / (forecastDates.length);
    return Math.max(0.52, Math.min(0.82, lastIcce + step * (i + 1)));
  });

  // Media Data - Análisis de medios para Paloma Valencia
  const mediaData = {
    success: true,
    candidate_name: "Paloma Valencia",
    location: "Colombia",
    summary: {
      key_findings: [
        "Paloma Valencia lidera la conversación sobre seguridad ciudadana con propuestas concretas",
        "Aumento del 23% en menciones positivas tras declaraciones sobre reforma policial",
        "Narrativa de mano firme resonando en ciudades intermedias",
        "Críticos cuestionan posición sobre derechos humanos en operativos",
        "Alianzas con sectores empresariales fortalecen discurso de orden público"
      ],
      executive_summary: "Paloma Valencia se posiciona como la candidata de la seguridad, con un discurso de mano firme que resuena en sectores conservadores y ciudades intermedias. Su ICCE de 62.4 indica un clima narrativo favorable, aunque debe gestionar las críticas sobre derechos humanos. La ventana actual es óptima para amplificar propuestas de seguridad ciudadana.",
      key_stats: ["ICCE 62.4", "Momentum +0.012", "Sentimiento +33%", "2,590 tweets"],
      recommendations: [
        "Intensificar mensajes sobre seguridad en ciudades intermedias donde hay mayor receptividad",
        "Preparar respuestas a críticas sobre derechos humanos con casos de éxito",
        "Aprovechar momentum positivo para anuncios de política de seguridad"
      ]
    },
    topics: [
      { topic: "Seguridad ciudadana", tweet_count: 847, sentiment: { positive: 0.58, neutral: 0.28, negative: 0.14 } },
      { topic: "Reforma policial", tweet_count: 523, sentiment: { positive: 0.51, neutral: 0.31, negative: 0.18 } },
      { topic: "Crimen organizado", tweet_count: 412, sentiment: { positive: 0.42, neutral: 0.33, negative: 0.25 } },
      { topic: "Justicia penal", tweet_count: 298, sentiment: { positive: 0.48, neutral: 0.34, negative: 0.18 } },
      { topic: "Orden público", tweet_count: 276, sentiment: { positive: 0.62, neutral: 0.25, negative: 0.13 } },
      { topic: "Fuerzas Armadas", tweet_count: 234, sentiment: { positive: 0.68, neutral: 0.22, negative: 0.10 } }
    ],
    sentiment_overview: {
      positive: 0.54,
      negative: 0.21,
      neutral: 0.25
    },
    metadata: {
      tweets_analyzed: 2590,
      time_window_from: dates[0],
      time_window_to: dates[dates.length - 1],
      geo_distribution: [
        { name: "Bogotá", weight: 0.28, x: 52, y: 48 },
        { name: "Medellín", weight: 0.18, x: 38, y: 35 },
        { name: "Cali", weight: 0.14, x: 35, y: 62 },
        { name: "Barranquilla", weight: 0.12, x: 48, y: 12 },
        { name: "Bucaramanga", weight: 0.10, x: 58, y: 32 },
        { name: "Cartagena", weight: 0.08, x: 42, y: 15 },
        { name: "Pereira", weight: 0.06, x: 42, y: 52 },
        { name: "Manizales", weight: 0.04, x: 44, y: 48 }
      ]
    }
  };

  // Forecast Data - ICCE, Momentum y proyecciones
  const forecastData = {
    success: true,
    candidate: "PalomaValenciaL",
    candidate_name: "Paloma Valencia",
    location: "Colombia",
    series: {
      dates: dates,
      icce: icceValues,
      icce_smooth: icceValues.map((v, i) => {
        if (i < 3) return v;
        return (icceValues[i-2] + icceValues[i-1] + v) / 3;
      }),
      momentum: momentumValues
    },
    forecast: {
      dates: forecastDates,
      icce_pred: forecastIcce,
      pred_low: forecastIcce.map(v => Math.max(0.4, v - 0.08)),
      pred_high: forecastIcce.map(v => Math.min(0.9, v + 0.08))
    },
    metadata: {
      calculated_at: new Date().toISOString(),
      days_back: 30,
      forecast_days: 14,
      model_type: "holt_winters"
    }
  };

  // Trending Data - Temas en tendencia
  const trendingData = {
    success: true,
    trending_topics: [
      "Seguridad ciudadana",
      "Reforma policial",
      "Crimen organizado",
      "Justicia",
      "Orden público",
      "Economía"
    ],
    location: "Colombia"
  };

  // Campaign Data - Análisis de campaña
  const campaignData = {
    success: true,
    candidate_name: "Paloma Valencia",
    location: "Colombia",
    theme: "Seguridad",
    analysis: {
      executive_summary: "La campaña de Paloma Valencia en el tema de Seguridad muestra un posicionamiento sólido con ICCE de 62.4 y momentum positivo. La narrativa de 'mano firme' resuena especialmente en ciudades intermedias y sectores empresariales. Se recomienda intensificar la presencia en medios regionales y preparar respuestas a críticas sobre derechos humanos.",
      data_analysis: "Muestra: 2,590 tweets (últimos 30 días). Sentimiento: 54% positivo, 21% negativo, 25% neutral (SNA +33%). SOV estimado en seguridad: 55%. Picos: reforma policial (+23% menciones). Ciudades líder: Bogotá 28%, Medellín 18%, Cali 14%. Hashtags clave: #SeguridadCiudadana, #PalomaValencia, #OrdenPublico.",
      strategic_plan: "Plan de 14 días:\n\n1. Semana 1: Reforzar propuesta de seguridad en ciudades intermedias\n   - Evento en Bucaramanga sobre seguridad ciudadana\n   - Entrevistas en medios regionales\n   - Contenido para redes: testimonios de comerciantes\n\n2. Semana 2: Gestión de críticas y consolidación\n   - Respuesta estructurada sobre derechos humanos\n   - Alianzas con asociaciones de víctimas\n   - Anuncio de política de seguridad integral\n\nKPIs: Mantener ICCE > 60, aumentar sentimiento positivo a 60%",
      speech: "Colombianos y colombianas,\n\nHoy vengo a hablarles de lo que más nos duele: la inseguridad que viven nuestras familias. Sé que están cansados de promesas vacías. Por eso, mi compromiso es claro: orden, justicia y resultados.\n\nNo vamos a negociar con el crimen. Vamos a fortalecer nuestra Policía, a modernizar nuestras Fuerzas Armadas, y a garantizar que quien cometa un delito pague por él.\n\nPero también vamos a atacar las raíces: educación, empleo y oportunidades para nuestros jóvenes. Porque la verdadera seguridad se construye con justicia social.\n\n¡Colombia merece vivir en paz, y juntos lo vamos a lograr!",
      chart_suggestion: "Gráfico sugerido: barras horizontales con temas ordenados por menciones y color por sentimiento (verde positivo, rojo crítico, gris neutral). Ayuda a decidir dónde concentrar recursos.",
      general_analysis: "El clima narrativo para Paloma Valencia en seguridad es favorable (ICCE 62.4). El momentum de +0.012 indica tendencia al alza sostenida. Drivers: reforma policial y discurso de orden público. Riesgos: críticas sobre derechos humanos y concentración temática. Proyección 14 días: ICCE sube 5.8 pts si se mantiene la estrategia actual.",
      game_theory: {
        main_move: "Contrastar en seguridad: comunicado + video corto + 3 posts con hashtags",
        alternatives: [
          "Proponer economía: mensaje de costo de vida + entrevista regional",
          "Desviar a salud: financiación hospitalaria + visita a clínica"
        ],
        rival_signal: "Señal rival: domina seguridad con pico de conversación (+12%)",
        trigger: "Trigger: si ICCE cae >8 pts o SNA baja -10 en seguridad, activar respuesta en 48h.",
        payoff: "Payoff estimado: +12 ICCE · +8 SNA · costo medio",
        confidence: "Media",
        compare: {
          labels: ["Seguridad", "Economía", "Salud", "Paz", "SOV General", "SNA Neto"],
          campaign: [45, 65, 70, 60, 55, 50],
          rival: [75, 50, 40, 55, 70, 35]
        },
        gap: {
          labels: ["SOV", "SNA", "ICCE", "Momentum"],
          values: [-15, 15, 4.4, 1.2]
        },
        context: {
          radar: "Rival domina seguridad y SOV general. Ventaja tuya en salud y economía.",
          gap: "Brecha negativa en SOV; oportunidad en ICCE y Momentum."
        }
      }
    },
    drivers: [
      "Alta tracción en Seguridad (ICCE 62.4)",
      "Momentum positivo sostenido (+0.012)",
      "Sentimiento neto favorable (+33%)",
      "Fuerte presencia en ciudades intermedias"
    ],
    risks: [
      "Críticas sobre derechos humanos",
      "Asociación con sectores extremos",
      "Dependencia de un solo tema"
    ],
    recommendations: [
      "Amplificar mensaje en ciudades intermedias con mejor receptividad",
      "Preparar respuestas a críticas sobre derechos humanos",
      "Diversificar agenda sin abandonar posicionamiento en seguridad"
    ]
  };

  return {
    mediaData,
    forecastData,
    trendingData,
    campaignData
  };
}
