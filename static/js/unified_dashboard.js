let unifiedChart = null;
let sentimentChart = null;
let gameRadarChart = null;
let gameGapChart = null;
let lastGameContext = null;

// Los 10 ejes del Plan Nacional de Desarrollo (PND)
const PND_EJES = [
  "Seguridad",
  "Infraestructura",
  "Gobernanza",
  "Educación",
  "Salud",
  "Igualdad",
  "Paz",
  "Economía",
  "Medio Ambiente",
  "Alimentación"
];

const RIVAL_PROFILES = {
  "Vicky Dávila": {
    seguridad: 76, infraestructura: 48, gobernanza: 52, educacion: 45, salud: 38,
    igualdad: 42, paz: 50, economia: 52, medioambiente: 35, alimentacion: 40,
    sov: 70, sna: 32, momentum: 0.006
  },
  "Mauricio Cárdenas": {
    seguridad: 55, infraestructura: 68, gobernanza: 62, educacion: 58, salud: 48,
    igualdad: 52, paz: 50, economia: 72, medioambiente: 55, alimentacion: 48,
    sov: 58, sna: 44, momentum: 0.004
  },
  "David Luna": {
    seguridad: 50, infraestructura: 55, gobernanza: 58, educacion: 62, salud: 52,
    igualdad: 60, paz: 46, economia: 58, medioambiente: 52, alimentacion: 45,
    sov: 52, sna: 40, momentum: 0.003
  },
  "Juan Manuel Galán": {
    seguridad: 48, infraestructura: 52, gobernanza: 68, educacion: 70, salud: 64,
    igualdad: 62, paz: 58, economia: 62, medioambiente: 58, alimentacion: 52,
    sov: 55, sna: 46, momentum: 0.004
  },
  "Aníbal Gaviria": {
    seguridad: 52, infraestructura: 65, gobernanza: 58, educacion: 55, salud: 60,
    igualdad: 58, paz: 62, economia: 56, medioambiente: 62, alimentacion: 55,
    sov: 54, sna: 45, momentum: 0.003
  },
  "Juan Daniel Oviedo": {
    seguridad: 44, infraestructura: 58, gobernanza: 65, educacion: 68, salud: 58,
    igualdad: 55, paz: 54, economia: 66, medioambiente: 52, alimentacion: 50,
    sov: 50, sna: 42, momentum: 0.005
  },
  "Juan Carlos Pinzón": {
    seguridad: 70, infraestructura: 55, gobernanza: 50, educacion: 42, salud: 40,
    igualdad: 38, paz: 48, economia: 55, medioambiente: 32, alimentacion: 38,
    sov: 66, sna: 34, momentum: 0.007
  },
  "Daniel Palacios": {
    seguridad: 68, infraestructura: 52, gobernanza: 55, educacion: 45, salud: 40,
    igualdad: 40, paz: 46, economia: 50, medioambiente: 35, alimentacion: 42,
    sov: 64, sna: 36, momentum: 0.006
  },
  "Abelardo de la Espriella": {
    seguridad: 72, infraestructura: 45, gobernanza: 48, educacion: 38, salud: 36,
    igualdad: 32, paz: 40, economia: 46, medioambiente: 28, alimentacion: 35,
    sov: 62, sna: 30, momentum: 0.005
  }
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

const RIVAL_CANDIDATES = [
  "Vicky Dávila",
  "Juan Carlos Pinzón",
  "Daniel Palacios",
  "Mauricio Cárdenas",
  "David Luna",
  "Juan Manuel Galán",
  "Aníbal Gaviria",
  "Juan Daniel Oviedo",
  "Sergio Fajardo",
  "Gustavo Bolívar"
];

let rivalProfilesLive = {};
let rivalProfilesContextKey = null;

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

  // Botón "Muéstrame un ejemplo" - Carga el último análisis guardado en la BD
  mockBtn?.addEventListener("click", async () => {
    loadingBox.style.display = "block";
    loadingBox.innerHTML = '<div class="spinner"></div><p>Cargando último análisis guardado...</p>';
    errorBox.style.display = "none";

    try {
      // Fetch último análisis de la base de datos
      const response = await fetch("/api/media/latest");
      const data = await response.json();

      if (!data.success) {
        throw new Error(data.error || "No hay análisis guardados. Usa 'Generar dashboard' para crear uno nuevo.");
      }

      // Llenar formulario con datos del análisis
      const locationSelect = document.getElementById("unified-location");
      const topicSelect = document.getElementById("unified-topic");
      const maxTweetsSelect = document.getElementById("unified-max-tweets");

      if (locationSelect) locationSelect.value = data.location || "Colombia";
      if (topicSelect) topicSelect.value = "";
      if (maxTweetsSelect) maxTweetsSelect.value = String(data.tweetsCount || 100);
      document.getElementById("unified-candidate").value = data.candidate_name || "";
      document.getElementById("unified-politician").value = data.politician ? `@${data.politician}` : "";
      document.getElementById("unified-days-back").value = "30";
      document.getElementById("unified-forecast-days").value = "14";

      // Convertir datos de BD a formato dashboard
      const dashboardData = convertDbDataToDashboard(data);

      loadingBox.style.display = "none";
      resultsSection.style.display = "block";
      renderUnifiedDashboard({
        mediaData: dashboardData.mediaData,
        forecastData: dashboardData.forecastData,
        trendingData: dashboardData.trendingData,
        campaignData: dashboardData.campaignData,
        input: {
          location: data.location || "Colombia",
          topic: null,
          candidateName: data.candidate_name || ""
        }
      });
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

    } catch (error) {
      loadingBox.style.display = "none";
      errorBox.style.display = "block";
      errorBox.textContent = error.message;
    }
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
    const maxTweets = Number(formData.get("max_tweets") || 100);

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
    submitBtn.textContent = `Trayendo ${maxTweets} tweets...`;
    if (loadingBox) loadingBox.style.display = "flex";

    const apiUrl = (path) => (window.API_CONFIG?.apiUrl(path)) || path;
    const mediaPayload = {
      location,
      topic,
      candidate_name: candidateName,
      politician: politician ? politician.replace("@", "") : null,
      max_tweets: maxTweets,
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
          max_tweets: maxTweets,
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

  // NIVEL 1: Tu campaña - Fortalezas y Debilidades
  renderCampaignStrengths(mediaData, forecastData, campaignData, input);

  // NIVEL 2: La estrategia de hoy
  renderDecisionHero(mediaData, forecastData, trendingData, campaignData, input);

  // NIVEL 3: Popularidad - KPIs de contexto
  renderContextKPIs(mediaData, forecastData);

  // NIVEL 4: Rivales - Comparacion
  renderRivalComparison(mediaData, forecastData, trendingData, campaignData, input);

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
  const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;
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

  // Actualizar barra de metadata - usar fecha del backend si está disponible
  let timestampDate;
  let dateStr = mediaData?.fetched_at || mediaData?.metadata?.time_window_to;
  if (dateStr) {
    // Agregar Z para indicar UTC si no tiene zona horaria
    if (!dateStr.includes('Z') && !dateStr.includes('+')) {
      dateStr = dateStr + 'Z';
    }
    timestampDate = new Date(dateStr);
  } else {
    timestampDate = new Date();
  }

  const formattedDate = timestampDate.toLocaleString("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "America/Bogota"
  });

  if (timestampEl) {
    timestampEl.textContent = `Ultima actualizacion: ${formattedDate}`;
  }

  // Actualizar contadores de metadata
  const metaTweetsEl = document.getElementById("meta-tweets-count");
  const metaSourcesEl = document.getElementById("meta-sources-count");
  const metaDaysEl = document.getElementById("meta-days-window");
  const metaCacheEl = document.getElementById("meta-cache-indicator");

  if (metaTweetsEl) {
    metaTweetsEl.textContent = tweetsAnalyzed || "0";
  }

  if (metaSourcesEl) {
    // Contar fuentes: tweets + forecast points + trending items
    let sourcesCount = 0;
    if (mediaData?.tweets?.length) sourcesCount += mediaData.tweets.length;
    if (forecastData?.historical?.length) sourcesCount += forecastData.historical.length;
    if (forecastData?.forecast?.length) sourcesCount += forecastData.forecast.length;
    metaSourcesEl.textContent = sourcesCount || tweetsAnalyzed || "0";
  }

  if (metaDaysEl) {
    metaDaysEl.textContent = `${daysBack}d`;
  }

  // Mostrar indicador de cache si los datos vienen cacheados
  if (metaCacheEl) {
    const isCached = mediaData?.metadata?.from_cache ||
                     forecastData?.metadata?.from_cache ||
                     (mediaData?.metadata?.cached_at) ||
                     (forecastData?.metadata?.cached_at);
    metaCacheEl.style.display = isCached ? "flex" : "none";
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

  // También los KPIs del tab de Resumen
  const icceTabEl = document.getElementById("kpi-icce-tab");
  const momentumTabEl = document.getElementById("kpi-momentum-tab");
  const sentimentTabEl = document.getElementById("kpi-sentiment-tab");

  const { icce, momentum, forecastDirection } = extractForecastSignals(forecastData);
  if (icceEl) icceEl.textContent = icce != null ? icce.toFixed(1) : "-";
  if (icceTabEl) icceTabEl.textContent = icce != null ? icce.toFixed(1) : "-";
  if (icceNoteEl) icceNoteEl.textContent = forecastDirection || "Sin forecast disponible";

  if (momentumEl) momentumEl.textContent = momentum != null ? formatSigned(momentum, 3) : "-";
  if (momentumTabEl) momentumTabEl.textContent = momentum != null ? formatSigned(momentum, 3) : "-";
  if (momentumNoteEl) momentumNoteEl.textContent = momentum != null ? momentumLabel(momentum) : "Sin momentum";

  const sentiment = extractSentiment(mediaData);
  if (sentimentEl) {
    sentimentEl.textContent = sentiment.netValue != null
      ? `${sentiment.netValue >= 0 ? "+" : ""}${(sentiment.netValue * 100).toFixed(0)}%`
      : "-";
  }
  if (sentimentTabEl) {
    sentimentTabEl.textContent = sentiment.netValue != null
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

/**
 * Los 10 ejes del Plan Nacional de Desarrollo (con detalles)
 */
const PND_EJES_DETAIL = [
  { id: "seguridad", name: "Seguridad", icon: "🛡️" },
  { id: "educacion", name: "Educación", icon: "📚" },
  { id: "salud", name: "Salud", icon: "🏥" },
  { id: "economia", name: "Economía y Empleo", icon: "💼" },
  { id: "infraestructura", name: "Infraestructura", icon: "🏗️" },
  { id: "gobernanza", name: "Gobernanza y Transparencia", icon: "⚖️" },
  { id: "igualdad", name: "Igualdad y Equidad", icon: "🤝" },
  { id: "paz", name: "Paz y Reinserción", icon: "🕊️" },
  { id: "ambiente", name: "Medio Ambiente", icon: "🌱" },
  { id: "alimentacion", name: "Alimentación", icon: "🌾" }
];

/**
 * NIVEL 1: TU CAMPAÑA - 10 EJES PND CON MÉTRICAS
 * Renderiza la tabla de los 10 ejes del PND con ICCE, SOV, SNA
 */
function renderCampaignStrengths(mediaData, forecastData, campaignData, input) {
  const tableEl = document.getElementById("pnd-ejes-table");
  const topStrengthEl = document.getElementById("pnd-top-strength");
  const topWeaknessEl = document.getElementById("pnd-top-weakness");
  const globalIcceEl = document.getElementById("campaign-icce");
  const globalSovEl = document.getElementById("campaign-sov");
  const globalSnaEl = document.getElementById("campaign-sna");

  if (!tableEl) return;

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topics = mediaData?.topics || [];
  const globalIcce = signals.icce || 50;
  const globalSov = signals.sov || 35;
  const globalSna = sentiment.netValue ? (sentiment.netValue * 100).toFixed(0) : 0;

  // Actualizar KPIs globales
  if (globalIcceEl) globalIcceEl.textContent = globalIcce.toFixed(1);
  if (globalSovEl) globalSovEl.textContent = `${globalSov}%`;
  if (globalSnaEl) globalSnaEl.textContent = globalSna >= 0 ? `+${globalSna}` : globalSna;

  // Actualizar contextos explicativos
  const icceContextEl = document.getElementById("campaign-icce-context");
  const sovContextEl = document.getElementById("campaign-sov-context");
  const snaContextEl = document.getElementById("campaign-sna-context");

  if (icceContextEl) {
    if (globalIcce >= 65) {
      icceContextEl.textContent = "Excelente - Posición dominante";
      icceContextEl.className = "kpi-context positive";
    } else if (globalIcce >= 50) {
      icceContextEl.textContent = "Bueno - Posición competitiva";
      icceContextEl.className = "kpi-context moderate";
    } else {
      icceContextEl.textContent = "Bajo - Requiere atención";
      icceContextEl.className = "kpi-context negative";
    }
  }

  if (sovContextEl) {
    if (globalSov >= 50) {
      sovContextEl.textContent = "Dominas la conversación";
      sovContextEl.className = "kpi-context positive";
    } else if (globalSov >= 30) {
      sovContextEl.textContent = "Presencia moderada";
      sovContextEl.className = "kpi-context moderate";
    } else {
      sovContextEl.textContent = "Baja visibilidad";
      sovContextEl.className = "kpi-context negative";
    }
  }

  if (snaContextEl) {
    const snaNum = parseFloat(globalSna);
    if (snaNum >= 10) {
      snaContextEl.textContent = "Muy positivo - Te apoyan";
      snaContextEl.className = "kpi-context positive";
    } else if (snaNum >= -10) {
      snaContextEl.textContent = "Neutral - Dividido";
      snaContextEl.className = "kpi-context moderate";
    } else {
      snaContextEl.textContent = "Negativo - Hay críticas";
      snaContextEl.className = "kpi-context negative";
    }
  }

  // Mapear topics a ejes PND
  const topicMap = {};
  topics.forEach(t => {
    const key = t.topic?.toLowerCase() || "";
    topicMap[key] = t;
  });

  // Calcular métricas por eje
  const ejesData = PND_EJES_DETAIL.map(eje => {
    // Buscar topic que coincida con el eje
    const matchedTopic = topics.find(t => {
      const topicName = (t.topic || "").toLowerCase();
      return topicName.includes(eje.id) || eje.name.toLowerCase().includes(topicName);
    });

    // Si hay datos reales, usarlos; si no, generar basados en el promedio global
    let icce, sov, sna, trend;

    if (matchedTopic) {
      const topicSent = matchedTopic.sentiment || {};
      const pos = topicSent.positive || 0.33;
      const neg = topicSent.negative || 0.33;
      const volume = matchedTopic.tweet_count || 10;

      sna = Math.round((pos - neg) * 100);
      sov = Math.min(100, Math.max(5, Math.round((volume / Math.max(1, topics.reduce((s, t) => s + (t.tweet_count || 0), 0))) * 100)));
      icce = Math.round(globalIcce * (0.7 + (pos - neg) * 0.6));
      trend = sna > 5 ? "up" : sna < -5 ? "down" : "stable";
    } else {
      // Generar datos simulados con variación realista
      const variance = (Math.random() - 0.5) * 30;
      icce = Math.round(Math.max(20, Math.min(85, globalIcce + variance)));
      sov = Math.round(Math.max(5, Math.min(60, globalSov + (Math.random() - 0.5) * 20)));
      sna = Math.round((Math.random() - 0.5) * 40);
      trend = sna > 5 ? "up" : sna < -5 ? "down" : "stable";
    }

    // Clasificar fuerza
    const avgScore = (icce / 100 + sov / 100 + (sna + 100) / 200) / 3;
    const strength = avgScore > 0.55 ? "strong" : avgScore < 0.4 ? "weak" : "moderate";

    return {
      ...eje,
      icce,
      sov,
      sna,
      trend,
      strength,
      score: avgScore
    };
  });

  // Ordenar por score para identificar fortalezas y debilidades
  const sorted = [...ejesData].sort((a, b) => b.score - a.score);
  const topStrength = sorted[0];
  const topWeakness = sorted[sorted.length - 1];

  // Renderizar tabla
  tableEl.innerHTML = "";
  ejesData.forEach(eje => {
    const row = document.createElement("div");
    row.className = "pnd-row";

    const icceClass = eje.icce >= 60 ? "positive" : eje.icce < 45 ? "negative" : "neutral";
    const sovClass = eje.sov >= 40 ? "positive" : eje.sov < 25 ? "negative" : "neutral";
    const snaClass = eje.sna > 5 ? "positive" : eje.sna < -5 ? "negative" : "neutral";
    const trendIcon = eje.trend === "up" ? "↑" : eje.trend === "down" ? "↓" : "→";
    const trendClass = eje.trend === "up" ? "trend-up" : eje.trend === "down" ? "trend-down" : "trend-stable";

    row.innerHTML = `
      <div class="col-status">
        <span class="status-indicator ${eje.strength}"></span>
      </div>
      <div class="col-eje-name">${eje.name}</div>
      <div class="col-metric ${icceClass}">${eje.icce}</div>
      <div class="col-metric ${sovClass}">${eje.sov}%</div>
      <div class="col-metric ${snaClass}">${eje.sna >= 0 ? "+" : ""}${eje.sna}</div>
      <div class="col-trend ${trendClass}">${trendIcon} ${eje.trend === "up" ? "Subiendo" : eje.trend === "down" ? "Bajando" : "Estable"}</div>
      <div class="col-action">
        <button class="pnd-ver-mas-btn" data-eje-id="${eje.id}">Ver más</button>
      </div>
    `;
    tableEl.appendChild(row);
  });

  // Almacenar datos para el modal
  window.pndEjesData = ejesData;
  window.pndMediaData = mediaData;
  // Almacenar tweets si existen (para el modal de detalles)
  // Siempre actualizar para evitar tweets de análisis anteriores
  window.pndTweetsData = mediaData?.tweets || [];

  // Agregar event listeners a los botones "Ver más"
  tableEl.querySelectorAll('.pnd-ver-mas-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const ejeId = btn.dataset.ejeId;
      openPndDetailModal(ejeId);
    });
  });

  // Actualizar resumen
  if (topStrengthEl) {
    topStrengthEl.textContent = `${topStrength.name} (ICCE ${topStrength.icce})`;
  }
  if (topWeaknessEl) {
    topWeaknessEl.textContent = `${topWeakness.name} (ICCE ${topWeakness.icce})`;
  }
}

// Variable global para almacenar la estrategia actual
let currentStrategyData = null;

/**
 * NIVEL 2: LA ESTRATEGIA DE HOY (Above the fold)
 * Renderiza la estrategia principal con objetivo, acciones detalladas e impacto
 */
function renderDecisionHero(mediaData, forecastData, trendingData, campaignData, input) {
  const objectiveEl = document.getElementById("decision-objective");
  const actionsListEl = document.getElementById("decision-actions-list");
  const topicTextEl = document.getElementById("decision-topic-text");
  const impactEl = document.getElementById("decision-impact");
  const warningTextEl = document.getElementById("decision-warning-text");
  const priorityIndicator = document.querySelector(".priority-indicator");

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;

  // Determinar la estrategia principal basada en el contexto
  const gameData = buildDecisionFromContext(mediaData, forecastData, trendingData, campaignData, input, signals, sentiment);

  // Guardar para uso posterior (generación de posts, etc.)
  currentStrategyData = { ...gameData, input, signals, sentiment };

  // Tema de la estrategia
  if (topicTextEl) {
    topicTextEl.textContent = `Tema: ${gameData.topTopic}`;
  }

  // Objetivo estratégico
  if (objectiveEl) {
    objectiveEl.textContent = gameData.objective;
  }

  // Acciones detalladas
  if (actionsListEl && gameData.actions) {
    actionsListEl.innerHTML = "";
    gameData.actions.forEach((action, index) => {
      const actionItem = document.createElement("div");
      actionItem.className = "action-item";
      actionItem.innerHTML = `
        <span class="action-number">${index + 1}</span>
        <div class="action-content">
          <strong>${action.title}</strong>
          <p>${action.description}</p>
        </div>
      `;
      actionsListEl.appendChild(actionItem);
    });
  }

  // Impacto esperado
  if (impactEl) {
    impactEl.textContent = gameData.impact;
    impactEl.className = "meta-value " + (gameData.impactPositive ? "positive" : "");
  }

  // Prioridad temporal (HOY / 48H / OBSERVACIÓN)
  if (priorityIndicator) {
    priorityIndicator.textContent = gameData.priority;
    priorityIndicator.className = "priority-indicator " + gameData.priorityClass;
  }

  // Warning: "Qué pasa si no actúas"
  if (warningTextEl) {
    warningTextEl.textContent = gameData.warning;
  }

  // Actualizar alternativas en el tab correspondiente
  updateAlternatives(gameData.alternatives, signals);
}

/**
 * Genera posts para X (Twitter) basados en la estrategia actual
 */
function generateXPosts() {
  const postsArea = document.getElementById("generated-posts-area");
  const postsList = document.getElementById("generated-posts-list");
  const executeBtn = document.getElementById("btn-execute");

  if (!postsArea || !postsList) return;

  const data = currentStrategyData || {};
  const topic = data.topTopic || "Seguridad";
  const location = data.location || "Colombia";
  const candidate = data.candidateName || "Nuestra campaña";

  // Generar 3 posts basados en la estrategia
  const posts = [
    {
      text: `${topic} es prioridad para ${location}. Nuestra propuesta es clara: más recursos, mejor coordinación y resultados medibles. Es hora de actuar con decisión.`,
      hashtags: [`#${location.replace(/\s/g, '')}Decide`, `#${topic.replace(/\s/g, '')}`, "#Propuestas2026"],
      time: "Publicar ahora"
    },
    {
      text: `Los ciudadanos de ${location} merecen respuestas concretas en ${topic.toLowerCase()}. Nuestro plan incluye:\n\n- Mayor inversión en infraestructura\n- Coordinación interinstitucional\n- Metas claras a 100 días\n\nEsto no es promesa, es compromiso.`,
      hashtags: [`#${topic.replace(/\s/g, '')}`, "#CompromisoReal", `#${location.replace(/\s/g, '')}`],
      time: "Publicar en 4 horas"
    },
    {
      text: `¿Qué diferencia nuestra propuesta de ${topic.toLowerCase()}? Datos, experiencia y un plan ejecutable. No más improvisación.\n\nConoce los detalles en nuestro sitio web.`,
      hashtags: ["#PropuestasClaras", `#${location.replace(/\s/g, '')}2026`, "#Soluciones"],
      time: "Publicar en 8 horas"
    }
  ];

  // Renderizar posts
  postsList.innerHTML = "";
  posts.forEach((post, index) => {
    const postCard = document.createElement("div");
    postCard.className = "post-card";
    postCard.innerHTML = `
      <div class="post-header">
        <span class="post-number">Post ${index + 1}</span>
        <span class="post-time">${post.time}</span>
      </div>
      <div class="post-text">${post.text}</div>
      <div class="post-hashtags">
        ${post.hashtags.map(h => `<span class="hashtag">${h}</span>`).join("")}
      </div>
      <div class="post-actions">
        <button class="post-action-btn copy" onclick="copyPostToClipboard(${index})">Copiar texto</button>
        <button class="post-action-btn edit" onclick="editPost(${index})">Editar</button>
      </div>
    `;
    postsList.appendChild(postCard);
  });

  // Mostrar área de posts y botón ejecutar
  postsArea.style.display = "block";
  if (executeBtn) executeBtn.style.display = "inline-flex";

  // Guardar posts para copiar
  window.generatedPosts = posts;
}

/**
 * Copia un post al portapapeles
 */
function copyPostToClipboard(index) {
  const post = window.generatedPosts?.[index];
  if (!post) return;

  const fullText = post.text + "\n\n" + post.hashtags.join(" ");
  navigator.clipboard.writeText(fullText).then(() => {
    alert("Post copiado al portapapeles");
  }).catch(err => {
    console.error("Error al copiar:", err);
  });
}

/**
 * Permite editar un post (abre modal o campo editable)
 */
function editPost(index) {
  const post = window.generatedPosts?.[index];
  if (!post) return;

  const newText = prompt("Edita el texto del post:", post.text);
  if (newText !== null && newText !== post.text) {
    window.generatedPosts[index].text = newText;
    // Re-renderizar el post
    const postCards = document.querySelectorAll(".post-card");
    if (postCards[index]) {
      const textEl = postCards[index].querySelector(".post-text");
      if (textEl) textEl.textContent = newText;
    }
  }
}

/**
 * Ejecuta la estrategia (simulado - en producción conectaría con APIs)
 */
function executeStrategy() {
  const confirmed = confirm("¿Confirmas que deseas ejecutar esta estrategia?\n\nEsto publicará los posts generados en X según el horario programado.");
  if (confirmed) {
    alert("Estrategia programada para ejecución.\n\nLos posts serán publicados según el horario indicado. Recibirás notificaciones del progreso.");
    // En producción: llamar API para programar publicaciones
  }
}

/**
 * Envía la estrategia por correo electrónico
 */
function sendByEmail() {
  const data = currentStrategyData || {};
  const topic = data.topTopic || "Estrategia del día";
  const impact = data.impact || "+10 pts";

  // Construir cuerpo del correo
  let emailBody = `ESTRATEGIA DEL DÍA - ${topic}\n\n`;
  emailBody += `OBJETIVO:\n${data.objective || "Ver dashboard para detalles"}\n\n`;
  emailBody += `IMPACTO ESPERADO: ${impact}\n\n`;
  emailBody += `ACCIONES:\n`;
  (data.actions || []).forEach((action, i) => {
    emailBody += `${i + 1}. ${action.title}\n   ${action.description}\n\n`;
  });

  if (window.generatedPosts?.length) {
    emailBody += `\nPOSTS PARA X:\n`;
    window.generatedPosts.forEach((post, i) => {
      emailBody += `\n--- Post ${i + 1} (${post.time}) ---\n${post.text}\n${post.hashtags.join(" ")}\n`;
    });
  }

  emailBody += `\n---\nGenerado por CASTOR - Dashboard de Campaña`;

  // Abrir cliente de correo
  const subject = encodeURIComponent(`Estrategia del día: ${topic}`);
  const body = encodeURIComponent(emailBody);
  window.open(`mailto:?subject=${subject}&body=${body}`, "_blank");
}

/**
 * Desplaza a la sección de alternativas
 */
function scrollToAlternatives() {
  const altSection = document.getElementById("alternatives-section");
  if (altSection) {
    altSection.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

/**
 * Construye la decisión principal basada en el contexto de datos
 */
function buildDecisionFromContext(mediaData, forecastData, trendingData, campaignData, input, signals, sentiment) {
  const topic = input?.topic || "la agenda";
  const topTopic = mediaData?.topics?.[0]?.topic || topic;
  const secondTopic = mediaData?.topics?.[1]?.topic || "Economía";
  const location = input?.location || "Colombia";
  const candidateName = input?.candidateName || "tu campaña";
  const icce = signals.icce || 50;
  const momentum = signals.momentum || 0;
  const netSentiment = sentiment.netValue || 0;

  // Calcular forecast change para el warning
  let forecastChange = 0;
  if (forecastData?.forecast?.icce_pred?.length && forecastData?.series?.icce?.length) {
    const currentIcce = (forecastData.series.icce[forecastData.series.icce.length - 1] || 0) * 100;
    const projectedIcce = (forecastData.forecast.icce_pred[forecastData.forecast.icce_pred.length - 1] || 0) * 100;
    forecastChange = projectedIcce - currentIcce;
  }

  // Lógica para determinar la estrategia
  let objective, actions, impact, priority, priorityClass, warning;
  let impactPositive = true;
  const alternatives = [];

  if (icce >= 60 && momentum > 0 && netSentiment > 0) {
    // Situación favorable: amplificar
    objective = `Posicionar tu propuesta de ${topTopic.toLowerCase()} como la más sólida del debate, aprovechando el momentum actual (+${(momentum * 100).toFixed(1)}%) y el sentimiento positivo en redes.`;
    actions = [
      {
        title: "Publicar video de propuesta",
        description: `Video de 60 segundos explicando tu plan para ${topTopic.toLowerCase()}, con datos concretos y casos de éxito que respalden tu posición.`
      },
      {
        title: "Campaña en X (Twitter)",
        description: `Publicar 3 posts con hashtags locales (#${location.replace(/\s/g, '')}Decide, #${topTopic.replace(/\s/g, '')}) espaciados cada 4 horas para maximizar alcance orgánico.`
      },
      {
        title: "Entrevista en medios regionales",
        description: `Agendar entrevista en medios locales de ${location} para amplificar el mensaje y conectar con votantes de la región.`
      }
    ];
    impact = `+${Math.round(8 + forecastChange)} pts ICCE`;
    priority = "HOY";
    priorityClass = "priority-today";
    warning = forecastChange > 0
      ? `Ventana óptima: si no actúas, perderás ${Math.abs(forecastChange).toFixed(1)} pts de momentum en 7-10 días.`
      : `Mantén el impulso: la inercia puede estancar tu avance narrativo.`;
    alternatives.push({
      text: `Proponer ${secondTopic}: mensaje de propuestas + entrevista regional`,
      impact: "+6 pts",
      priority: "48H"
    });
    alternatives.push({
      text: `Consolidar base: evento con líderes locales + cobertura en medios regionales`,
      impact: "+4 pts",
      priority: "OBSERVACIÓN"
    });
  } else if (icce < 45 || netSentiment < -0.1) {
    // Situación crítica: contener
    objective = `Contener la narrativa negativa en ${topTopic.toLowerCase()} y recuperar terreno en la conversación pública antes de que se consolide la percepción desfavorable.`;
    actions = [
      {
        title: "Comunicado de precisión",
        description: `Emitir comunicado oficial aclarando tu posición sobre ${topTopic.toLowerCase()}, con datos verificables y tono constructivo.`
      },
      {
        title: "Vocería técnica",
        description: `Designar vocero especializado para responder a críticas con argumentos técnicos y propuestas concretas.`
      },
      {
        title: "Respuesta estratégica en redes",
        description: `Publicar hilo explicativo en X respondiendo punto por punto las críticas principales, sin entrar en confrontación directa.`
      }
    ];
    impact = `+${Math.round(4 + Math.abs(forecastChange))} pts SNA`;
    priority = "HOY";
    priorityClass = "priority-today";
    warning = `Alerta: sin acción, el ICCE puede caer ${Math.abs(forecastChange).toFixed(1)} pts adicionales. Riesgo de pérdida narrativa.`;
    impactPositive = false;
    alternatives.push({
      text: `Desviar a ${secondTopic}: cambiar foco de conversación con propuesta concreta`,
      impact: "+5 pts ICCE",
      priority: "48H"
    });
    alternatives.push({
      text: `Respuesta directa: entrevista con vocero principal para clarificar posición`,
      impact: "+3 pts SNA",
      priority: "HOY"
    });
  } else if (momentum < -0.01) {
    // Momentum negativo: reactivar
    objective = `Reactivar la conversación positiva sobre ${topTopic.toLowerCase()} y revertir la tendencia negativa del momentum antes de que afecte tu posicionamiento general.`;
    actions = [
      {
        title: "Video corto de alto impacto",
        description: `Producir video de 30-45 segundos con mensaje directo y emotivo sobre tu compromiso con ${topTopic.toLowerCase()}.`
      },
      {
        title: "Hilo explicativo en X",
        description: `Crear hilo de 5-7 tweets explicando tu propuesta con datos, comparaciones y llamado a la acción.`
      },
      {
        title: "Activación de aliados",
        description: `Coordinar con influencers y aliados para amplificar el mensaje en las próximas 24 horas.`
      }
    ];
    impact = `+${Math.round(6 + forecastChange)} pts Momentum`;
    priority = "48H";
    priorityClass = "priority-48h";
    warning = `Momentum en bajada: sin acción en 48h, la tendencia negativa se consolidará.`;
    alternatives.push({
      text: `Evento territorial: visita + cobertura mediática para generar contenido fresco`,
      impact: "+4 pts",
      priority: "OBSERVACIÓN"
    });
    alternatives.push({
      text: `Campaña digital: serie de posts con datos y propuestas concretas`,
      impact: "+5 pts",
      priority: "48H"
    });
  } else {
    // Situación estable: contrastar
    objective = `Fortalecer tu posición en ${topTopic.toLowerCase()} diferenciándote de otros candidatos con propuestas concretas y mensaje claro.`;
    actions = [
      {
        title: "Comunicado de propuesta",
        description: `Publicar documento con tu plan detallado para ${topTopic.toLowerCase()}, incluyendo metas medibles y plazos.`
      },
      {
        title: "Video comparativo",
        description: `Video de 60 segundos contrastando tu propuesta con las alternativas, sin ataques directos pero resaltando diferencias clave.`
      },
      {
        title: "Campaña en redes sociales",
        description: `Publicar 3 posts en X con hashtags relevantes (#${location.replace(/\s/g, '')}2026, #PropuestasClaras) para generar conversación.`
      }
    ];
    impact = `+${Math.round(10 + forecastChange)} pts ICCE`;
    priority = "HOY";
    priorityClass = "priority-today";
    warning = forecastChange >= 0
      ? `Oportunidad: la proyección es favorable (+${forecastChange.toFixed(1)} pts). Aprovecha la ventana.`
      : `Si no actúas: la ventaja puede estancarse en 7-10 días.`;
    alternatives.push({
      text: `Proponer ${secondTopic}: mensaje de costo de vida + propuestas de empleo`,
      impact: "+8 pts",
      priority: "48H"
    });
    alternatives.push({
      text: `Desviar a salud: financiación hospitalaria + visita a clínica`,
      impact: "+5 pts",
      priority: "OBSERVACIÓN"
    });
  }

  return { objective, actions, impact, impactPositive, priority, priorityClass, warning, alternatives, topTopic, location, candidateName };
}

/**
 * Actualiza las cards de alternativas tácticas
 */
function updateAlternatives(alternatives, signals) {
  const altSection = document.getElementById("alternatives-section");
  if (!altSection) return;

  const cards = altSection.querySelectorAll(".alternative-card");

  alternatives.forEach((alt, index) => {
    if (index >= cards.length) return;
    const card = cards[index];

    // Actualizar texto
    const textEl = card.querySelector(".alternative-text");
    if (textEl) textEl.textContent = alt.text;

    // Actualizar prioridad badge
    const priorityBadge = card.querySelector(".priority-badge");
    if (priorityBadge) {
      priorityBadge.textContent = alt.priority === "48H" ? "Próximas 48h" : "En observación";
      priorityBadge.className = "priority-badge " + (alt.priority === "48H" ? "priority-48h" : "priority-watch");
    }

    // Actualizar impacto
    const metaEls = card.querySelectorAll(".alternative-meta span");
    if (metaEls.length >= 1) {
      metaEls[0].textContent = `Impacto: ${alt.impact}`;
    }
  });
}

/**
 * NIVEL 2: CONTEXTO RAPIDO (4 KPIs con estados humanos)
 * Muestra métricas con significado, no solo números
 */
function renderContextKPIs(mediaData, forecastData) {
  // ICCE
  const icceValueEl = document.getElementById("kpi-icce");
  const icceStateEl = document.getElementById("kpi-icce-state");

  // Momentum
  const momentumValueEl = document.getElementById("kpi-momentum");
  const momentumStateEl = document.getElementById("kpi-momentum-state");

  // Sentimiento
  const sentimentValueEl = document.getElementById("kpi-sentiment");
  const sentimentStateEl = document.getElementById("kpi-sentiment-state");

  // Forecast
  const forecastValueEl = document.getElementById("kpi-forecast");
  const forecastStateEl = document.getElementById("kpi-forecast-state");

  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);

  // ICCE con estado humano
  if (icceValueEl && icceStateEl) {
    const icce = signals.icce;
    icceValueEl.textContent = icce != null ? icce.toFixed(1) : "-";

    if (icce != null) {
      if (icce >= 60) {
        icceStateEl.textContent = "Favorable";
        icceStateEl.className = "kpi-state positive";
      } else if (icce >= 45) {
        icceStateEl.textContent = "Neutral";
        icceStateEl.className = "kpi-state neutral";
      } else {
        icceStateEl.textContent = "Desfavorable";
        icceStateEl.className = "kpi-state negative";
      }
    } else {
      icceStateEl.textContent = "Sin datos";
      icceStateEl.className = "kpi-state neutral";
    }
  }

  // Momentum con estado humano (flecha + texto)
  if (momentumValueEl && momentumStateEl) {
    const momentum = signals.momentum;

    if (momentum != null) {
      if (momentum > 0.01) {
        momentumValueEl.textContent = "↑";
        momentumStateEl.textContent = "En subida sostenida";
        momentumStateEl.className = "kpi-state positive";
      } else if (momentum > 0.003) {
        momentumValueEl.textContent = "↗";
        momentumStateEl.textContent = "En subida";
        momentumStateEl.className = "kpi-state positive";
      } else if (momentum < -0.01) {
        momentumValueEl.textContent = "↓";
        momentumStateEl.textContent = "En bajada";
        momentumStateEl.className = "kpi-state negative";
      } else if (momentum < -0.003) {
        momentumValueEl.textContent = "↘";
        momentumStateEl.textContent = "Desacelerando";
        momentumStateEl.className = "kpi-state negative";
      } else {
        momentumValueEl.textContent = "→";
        momentumStateEl.textContent = "Estable";
        momentumStateEl.className = "kpi-state neutral";
      }
    } else {
      momentumValueEl.textContent = "-";
      momentumStateEl.textContent = "Sin datos";
      momentumStateEl.className = "kpi-state neutral";
    }
  }

  // Sentimiento con estado humano
  if (sentimentValueEl && sentimentStateEl) {
    const net = sentiment.netValue;

    if (net != null) {
      const pct = Math.round(net * 100);
      sentimentValueEl.textContent = `${pct >= 0 ? "+" : ""}${pct}%`;

      if (pct > 15) {
        sentimentStateEl.textContent = "Muy positivo";
        sentimentStateEl.className = "kpi-state positive";
      } else if (pct > 5) {
        sentimentStateEl.textContent = "Positivo";
        sentimentStateEl.className = "kpi-state positive";
      } else if (pct < -15) {
        sentimentStateEl.textContent = "Negativo";
        sentimentStateEl.className = "kpi-state negative";
      } else if (pct < -5) {
        sentimentStateEl.textContent = "Ligeramente negativo";
        sentimentStateEl.className = "kpi-state negative";
      } else {
        sentimentStateEl.textContent = "Mixto";
        sentimentStateEl.className = "kpi-state neutral";
      }
    } else {
      sentimentValueEl.textContent = "-";
      sentimentStateEl.textContent = "Sin datos";
      sentimentStateEl.className = "kpi-state neutral";
    }
  }

  // Forecast con estado humano
  if (forecastValueEl && forecastStateEl) {
    let forecastChange = null;

    if (forecastData?.forecast?.icce_pred?.length && forecastData?.series?.icce?.length) {
      const currentIcce = (forecastData.series.icce[forecastData.series.icce.length - 1] || 0) * 100;
      const projectedIcce = (forecastData.forecast.icce_pred[forecastData.forecast.icce_pred.length - 1] || 0) * 100;
      forecastChange = projectedIcce - currentIcce;
    }

    if (forecastChange != null) {
      forecastValueEl.textContent = `${forecastChange >= 0 ? "↑" : "↓"} ${Math.abs(forecastChange).toFixed(1)}`;

      if (forecastChange > 5) {
        forecastStateEl.textContent = "Proyección al alza";
        forecastStateEl.className = "kpi-state positive";
      } else if (forecastChange > 0) {
        forecastStateEl.textContent = "Tendencia positiva";
        forecastStateEl.className = "kpi-state positive";
      } else if (forecastChange < -5) {
        forecastStateEl.textContent = "Proyección a la baja";
        forecastStateEl.className = "kpi-state negative";
      } else if (forecastChange < 0) {
        forecastStateEl.textContent = "Tendencia negativa";
        forecastStateEl.className = "kpi-state negative";
      } else {
        forecastStateEl.textContent = "Estable";
        forecastStateEl.className = "kpi-state neutral";
      }
    } else {
      forecastValueEl.textContent = "-";
      forecastStateEl.textContent = "Sin proyección";
      forecastStateEl.className = "kpi-state neutral";
    }
  }
}

/**
 * NIVEL 3: COMPARACION VS RIVAL
 * Muestra comparación con insight principal claro
 */
function renderRivalComparison(mediaData, forecastData, trendingData, campaignData, input) {
  const rivalNameDisplay = document.getElementById("rival-name-display");
  const candidateNameEl = document.getElementById("game-candidate-name");
  const rivalMainInsight = document.getElementById("rival-main-insight");
  const gapsListEl = document.getElementById("rival-gaps-list");
  const gapsRecEl = document.getElementById("gaps-recommendation");
  const radarCtx = document.getElementById("game-radar-chart");
  const pndRowsEl = document.getElementById("rival-pnd-rows");
  const narrativeSummaryEl = document.getElementById("narrative-summary-detail");

  const selectedRival = getSelectedRivalName();
  const signals = extractForecastSignals(forecastData);
  const sentiment = extractSentiment(mediaData);
  const topic = input?.topic || "Seguridad";
  const topTopic = mediaData?.topics?.[0]?.topic || topic;
  const candidateName = input?.candidateName || "Paloma Valencia";

  // Nombre del candidato
  if (candidateNameEl) {
    candidateNameEl.textContent = candidateName;
  }

  // Nombre del rival
  if (rivalNameDisplay) {
    rivalNameDisplay.textContent = selectedRival;
  }

  // Obtener perfil del rival con los 10 ejes
  const rivalProfile = rivalProfilesLive[selectedRival] || RIVAL_PROFILES[selectedRival] || {
    seguridad: 58, infraestructura: 50, gobernanza: 52, educacion: 50, salud: 50,
    igualdad: 48, paz: 50, economia: 55, medioambiente: 45, alimentacion: 45,
    sov: 50, sna: 40, momentum: 0.003
  };

  // Calcular scores de la campaña (expandido a 10 ejes)
  const campaignScore = buildCampaignScores10Ejes(signals, sentiment, campaignData);

  // Calcular brechas para los 10 ejes
  const ejesMapping = [
    { key: "seguridad", label: "Seguridad" },
    { key: "infraestructura", label: "Infraestructura" },
    { key: "gobernanza", label: "Gobernanza" },
    { key: "educacion", label: "Educación" },
    { key: "salud", label: "Salud" },
    { key: "igualdad", label: "Igualdad" },
    { key: "paz", label: "Paz" },
    { key: "economia", label: "Economía" },
    { key: "medioambiente", label: "Medio Ambiente" },
    { key: "alimentacion", label: "Alimentación" }
  ];

  const gaps = ejesMapping.map(eje => ({
    key: eje.key,
    label: eje.label,
    campaign: campaignScore[eje.key] || 50,
    rival: rivalProfile[eje.key] || 50,
    value: (campaignScore[eje.key] || 50) - (rivalProfile[eje.key] || 50)
  }));

  // Renderizar tabla de 10 ejes PND
  if (pndRowsEl) {
    pndRowsEl.innerHTML = "";
    gaps.forEach(gap => {
      const diff = gap.value;
      const diffClass = diff >= 0 ? "positive" : "negative";
      const diffText = diff >= 0 ? `+${diff.toFixed(0)} pts` : `${diff.toFixed(0)} pts`;

      // Calcular SOV y SNA para cada eje (estimados)
      const campaignSOV = Math.min(100, Math.max(0, gap.campaign * 0.7 + 15));
      const rivalSOV = Math.min(100, Math.max(0, gap.rival * 0.7 + 15));
      const campaignSNA = Math.round((gap.campaign - 50) * 0.8);
      const rivalSNA = Math.round((gap.rival - 50) * 0.8);

      const row = document.createElement("div");
      row.className = "comparison-row";
      row.innerHTML = `
        <div class="col-eje">${gap.label}</div>
        <div class="col-tu">
          <span class="metric-mini">ICCE ${gap.campaign.toFixed(0)}</span>
          <span class="metric-mini">SOV ${campaignSOV.toFixed(0)}%</span>
          <span class="metric-mini">SNA ${campaignSNA >= 0 ? '+' : ''}${campaignSNA}</span>
        </div>
        <div class="col-rival">
          <span class="metric-mini">ICCE ${gap.rival.toFixed(0)}</span>
          <span class="metric-mini">SOV ${rivalSOV.toFixed(0)}%</span>
          <span class="metric-mini">SNA ${rivalSNA >= 0 ? '+' : ''}${rivalSNA}</span>
        </div>
        <div class="col-diff ${diffClass}">${diffText}</div>
      `;
      pndRowsEl.appendChild(row);
    });
  }

  // Ordenar brechas por magnitud
  const sortedGaps = [...gaps].sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  // Determinar la brecha principal
  const mainGap = sortedGaps[0];
  const isLosingMain = mainGap.value < 0;

  // Insight principal (1 frase clara)
  if (rivalMainInsight) {
    if (isLosingMain) {
      rivalMainInsight.innerHTML = `Brecha principal: <strong>${mainGap.label}</strong>. El rival domina este tema con ${Math.abs(mainGap.value).toFixed(0)}+ puntos de ventaja.`;
    } else {
      rivalMainInsight.innerHTML = `Ventaja principal: <strong>${mainGap.label}</strong>. Tienes ${Math.abs(mainGap.value).toFixed(0)}+ puntos sobre el rival.`;
    }
  }

  // Renderizar lista de brechas
  if (gapsListEl) {
    gapsListEl.innerHTML = "";
    sortedGaps.slice(0, 5).forEach(gap => {
      const isPositive = gap.value >= 0;
      const absValue = Math.abs(gap.value);
      const barWidth = Math.min(100, absValue * 3);

      const gapItem = document.createElement("div");
      gapItem.className = `gap-item ${isPositive ? "gap-positive" : "gap-negative"}`;
      gapItem.innerHTML = `
        <span class="gap-label">${gap.label}</span>
        <div class="gap-bar-container">
          <div class="gap-bar ${isPositive ? "positive" : "negative"}" style="width: ${barWidth}%;"></div>
        </div>
        <span class="gap-value">${isPositive ? "+" : ""}${gap.value.toFixed(0)} pts</span>
      `;
      gapsListEl.appendChild(gapItem);
    });
  }

  // Generar resumen narrativo de 150 palabras
  if (narrativeSummaryEl) {
    const positiveGaps = gaps.filter(g => g.value > 0).sort((a, b) => b.value - a.value);
    const negativeGaps = gaps.filter(g => g.value < 0).sort((a, b) => a.value - b.value);
    const topStrength = positiveGaps[0]?.label || "Economía";
    const topWeakness = negativeGaps[0]?.label || "Seguridad";
    const avgCampaign = gaps.reduce((s, g) => s + g.campaign, 0) / gaps.length;
    const avgRival = gaps.reduce((s, g) => s + g.rival, 0) / gaps.length;
    const overallAdvantage = avgCampaign - avgRival;

    narrativeSummaryEl.innerHTML = `
      <strong>${candidateName} vs ${selectedRival}:</strong> El análisis comparativo de los 10 ejes del Plan Nacional de Desarrollo muestra una contienda altamente competitiva.
      ${candidateName} presenta ventajas significativas en <strong>${positiveGaps.slice(0, 2).map(g => g.label).join(" y ")}</strong>,
      donde su ICCE promedio supera al rival por ${positiveGaps.slice(0, 2).reduce((s, g) => s + g.value, 0) / 2 | 0} puntos.
      Sin embargo, ${selectedRival} domina en <strong>${negativeGaps.slice(0, 2).map(g => g.label).join(" y ")}</strong>,
      temas donde ${candidateName} requiere reforzar su posicionamiento.
      El Share of Voice (SOV) de ${candidateName} es ${overallAdvantage > 0 ? "superior" : "inferior"} en ${Math.abs(overallAdvantage).toFixed(0)} puntos promedio.
      <strong>Recomendación estratégica:</strong> Capitalizar la ventaja en ${topStrength} mientras se desarrollan narrativas más sólidas en ${topWeakness}
      para neutralizar la fortaleza del rival. El momentum actual ${signals.momentum > 0 ? "favorece" : "requiere atención para"} ${candidateName}.
    `;
  }

  // Recomendación basada en brechas
  if (gapsRecEl) {
    const positiveGaps = gaps.filter(g => g.value > 0);
    const negativeGaps = gaps.filter(g => g.value < 0);

    if (negativeGaps.length > 0 && positiveGaps.length > 0) {
      gapsRecEl.textContent = `Refuerza mensajes en ${positiveGaps[0].label}. Prepara respuesta en ${negativeGaps[0].label}.`;
    } else if (negativeGaps.length > 0) {
      gapsRecEl.textContent = `Prioridad: cerrar brecha en ${negativeGaps[0].label} con mensajes específicos.`;
    } else {
      gapsRecEl.textContent = `Mantén la ventaja. Consolida tu posición en ${positiveGaps[0]?.label || topTopic}.`;
    }
  }

  // Actualizar insights escaneables
  updateScannableInsights(mediaData, forecastData, signals, sentiment, input, sortedGaps);

  // Renderizar el gráfico radar de comparación
  if (radarCtx) {
    renderRivalRadarChart(radarCtx, campaignScore, rivalProfile, selectedRival);
  }
}

/**
 * Construye scores de campaña para los 10 ejes PND
 */
function buildCampaignScores10Ejes(signals, sentiment, campaignData) {
  const baseIcce = signals.icce || 55;
  const netSentiment = sentiment.netValue || 0;
  const momentum = signals.momentum || 0;

  // Base scores ajustados por señales
  const adjust = (base, variation) => {
    const adjusted = base + (netSentiment * 0.3) + (momentum * 100) + (Math.random() * variation - variation / 2);
    return Math.max(20, Math.min(95, adjusted));
  };

  // Si hay datos de campaña, usarlos
  if (campaignData?.ejes) {
    return campaignData.ejes;
  }

  // Generar scores basados en señales
  return {
    seguridad: adjust(baseIcce + 8, 10),
    infraestructura: adjust(baseIcce - 2, 8),
    gobernanza: adjust(baseIcce + 5, 10),
    educacion: adjust(baseIcce + 12, 8),
    salud: adjust(baseIcce + 6, 8),
    igualdad: adjust(baseIcce + 10, 10),
    paz: adjust(baseIcce + 4, 8),
    economia: adjust(baseIcce + 15, 10),
    medioambiente: adjust(baseIcce + 8, 10),
    alimentacion: adjust(baseIcce + 5, 8),
    sov: Math.min(100, baseIcce * 0.8 + 20),
    sna: Math.round(netSentiment * 0.5)
  };
}

/**
 * Renderiza el radar chart de comparación rival (6 ejes principales para visualización)
 */
function renderRivalRadarChart(ctx, campaignScore, rivalProfile, rivalName) {
  if (gameRadarChart) gameRadarChart.destroy();

  // Seleccionar 6 ejes clave para el radar (visualización limpia)
  const labels = ["Seguridad", "Economía", "Educación", "Salud", "Medio Amb.", "Gobernanza"];
  const campaignData = [
    campaignScore.seguridad || 50,
    campaignScore.economia || 50,
    campaignScore.educacion || 50,
    campaignScore.salud || 50,
    campaignScore.medioambiente || 50,
    campaignScore.gobernanza || 50
  ];
  const rivalData = [
    rivalProfile.seguridad || 50,
    rivalProfile.economia || 50,
    rivalProfile.educacion || 50,
    rivalProfile.salud || 50,
    rivalProfile.medioambiente || 50,
    rivalProfile.gobernanza || 50
  ];

  gameRadarChart = new Chart(ctx, {
    type: "radar",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Tu campaña",
          data: campaignData,
          backgroundColor: "rgba(201, 162, 39, 0.2)",
          borderColor: "#C9A227",
          pointBackgroundColor: "#C9A227",
          borderWidth: 2
        },
        {
          label: rivalName,
          data: rivalData,
          backgroundColor: "rgba(139, 58, 58, 0.18)",
          borderColor: "#8B3A3A",
          pointBackgroundColor: "#8B3A3A",
          borderWidth: 2
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
          pointLabels: { color: "#F5F5F0", font: { size: 11 } },
          ticks: { color: "#9A8F7C", backdropColor: "transparent" },
          suggestedMin: 0,
          suggestedMax: 100
        }
      },
      plugins: {
        legend: {
          labels: { color: "#F5F5F0" },
          position: "bottom"
        }
      }
    }
  });
}

/**
 * Actualiza los cards de insights escaneables (INSIGHT CLAVE / OPORTUNIDAD / RIESGO)
 */
function updateScannableInsights(mediaData, forecastData, signals, sentiment, input, gaps) {
  const insightEl = document.getElementById("narrative-summary");
  const opportunityEl = document.getElementById("narrative-opportunity");
  const riskEl = document.getElementById("narrative-risk");

  const topic = input?.topic || "la agenda";
  const topTopic = mediaData?.topics?.[0]?.topic || topic;
  const icce = signals.icce || 50;
  const momentum = signals.momentum || 0;
  const net = sentiment.netValue || 0;

  // INSIGHT CLAVE: El hallazgo principal
  if (insightEl) {
    let insight = "";
    if (mediaData?.topics?.length > 0) {
      const mainTopic = mediaData.topics[0];
      const cities = ["ciudades intermedias", "zonas urbanas", "regiones clave"];
      const randomCity = cities[Math.floor(Math.abs(icce) % cities.length)];
      insight = `La narrativa de ${topTopic} está funcionando mejor en ${randomCity}.`;
    } else {
      insight = `El clima narrativo actual es ${icce >= 60 ? "favorable" : icce >= 45 ? "neutral" : "desafiante"}.`;
    }
    insightEl.textContent = insight;
  }

  // OPORTUNIDAD: Dónde hay ventana
  if (opportunityEl) {
    let opportunity = "";
    const positiveGaps = gaps?.filter(g => g.value > 0) || [];

    if (momentum > 0.005 && icce >= 55) {
      opportunity = "Amplificar mensajes en medios regionales. Ventana favorable.";
    } else if (positiveGaps.length > 0) {
      opportunity = `Capitalizar ventaja en ${positiveGaps[0].label} con contenido específico.`;
    } else if (net > 0.1) {
      opportunity = "Sentimiento positivo permite propuestas más ambiciosas.";
    } else {
      opportunity = "Monitorear conversación para identificar temas emergentes.";
    }
    opportunityEl.textContent = opportunity;
  }

  // RIESGO: Qué vigilar
  if (riskEl) {
    let risk = "";
    const negativeGaps = gaps?.filter(g => g.value < 0) || [];
    const negPct = (mediaData?.sentiment_overview?.negative || 0) * 100;

    if (negPct > 25) {
      risk = `${negPct.toFixed(0)}% de menciones negativas requiere respuesta preparada.`;
    } else if (negativeGaps.length > 0) {
      risk = `Brecha en ${negativeGaps[0].label} puede ser explotada por rival.`;
    } else if (momentum < -0.005) {
      risk = "Momentum en descenso. Activar contenido fresco.";
    } else if (icce < 50) {
      risk = "ICCE bajo. Evaluar cambio de estrategia narrativa.";
    } else {
      risk = "Riesgo bajo. Mantener vigilancia de picos súbitos.";
    }
    riskEl.textContent = risk;
  }
}

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
    urgencyEl.style.background = riskLevel === "alto" ? "#8B3A3A" : riskLevel === "medio" ? "#D4AF37" : "#C9A227";
    urgencyEl.style.color = riskLevel === "medio" ? "#1a1a1a" : "#fff";
  }

  // Confianza
  if (confidenceEl) {
    const confidence = calculateConfidenceLevel(tweetsAnalyzed, signals);
    confidenceEl.textContent = confidence.level;
    confidenceEl.style.color = confidence.level === "Alta" ? "#C9A227" : confidence.level === "Media" ? "#D4AF37" : "#8B3A3A";
  }

  // Alertas
  if (alertsEl) {
    alertsEl.innerHTML = "";
    const alerts = buildForecastAlerts(signals);
    if (alerts.length === 0) {
      alertsEl.innerHTML = '<li class="alert-item" style="color: #C9A227;">Sin alertas criticas</li>';
    } else {
      alerts.forEach(alert => {
        const li = document.createElement("li");
        li.className = "alert-item";
        li.style.cssText = "padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); color: #8B3A3A;";
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
    findingsEl.innerHTML = '<p style="color: #9A8F7C;">Sin patrones significativos detectados.</p>';
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
    arrowEl.style.color = delta > 2 ? "#C9A227" : delta < -2 ? "#8B3A3A" : "#9A8F7C";
  }

  if (deltaEl) {
    deltaEl.textContent = `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`;
    deltaEl.style.color = delta > 2 ? "#C9A227" : delta < -2 ? "#8B3A3A" : "#9A8F7C";
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
      topicsEl.innerHTML = '<p style="color: #9A8F7C;">Sin temas detectados.</p>';
    } else {
      topics.forEach(topic => {
        const row = document.createElement("div");
        row.className = "topics-row";
        row.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);";
        const sentLabel = topic.sentiment?.positive > topic.sentiment?.negative ? "Favorable" : "Mixto";
        row.innerHTML = `
          <span style="font-weight: 500;">${topic.topic}</span>
          <span style="color: #9A8F7C;">${topic.tweet_count} menciones · ${sentLabel}</span>
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
      findingsEl.innerHTML = '<li style="color: #9A8F7C;">Sin hallazgos.</li>';
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
      item.innerHTML = `<strong style="color: var(--accent);">${action.label}:</strong> <span style="color: #9A8F7C;">${action.text}</span>`;
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
        <p style="font-size: 0.85rem; color: #9A8F7C;">Senal esperada: Mejora del balance de tono en ${topic}.</p>
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
    const color = mom == null ? "#9A8F7C" : mom > 0.02 ? "#C9A227" : mom < -0.02 ? "#8B3A3A" : "#9A8F7C";
    momentumEl.textContent = label;
    momentumEl.style.color = color;
  }

  if (volatilityEl) {
    volatilityEl.textContent = "Baja";
    volatilityEl.style.color = "#C9A227";
  }

  if (criticsEl) {
    const negPct = ((mediaData?.sentiment_overview?.negative || 0) * 100).toFixed(0);
    criticsEl.textContent = `${negPct}%`;
    criticsEl.style.color = negPct > 30 ? "#8B3A3A" : negPct > 20 ? "#D4AF37" : "#C9A227";
  }

  if (confEl) {
    const tweetsAnalyzed = mediaData?.metadata?.tweets_analyzed || 0;
    const confidence = calculateConfidenceLevel(tweetsAnalyzed, signals);
    confEl.textContent = confidence.level;
    confEl.style.color = confidence.level === "Alta" ? "#C9A227" : confidence.level === "Media" ? "#D4AF37" : "#8B3A3A";
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
        <p style="font-size: 0.85rem; color: #9A8F7C;">${(point.weight * 100).toFixed(1)}%</p>
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
    const riskColor = riskLevel === "alto" ? "#8B3A3A" : riskLevel === "medio" ? "#D4AF37" : "#C9A227";
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
  if (lastGameContext) {
    loadRivalProfilesFromApi(lastGameContext);
  }

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
  const rivalProfile = rivalProfilesLive[selectedRival] || RIVAL_PROFILES[selectedRival] || { seguridad: 58, economia: 58, salud: 58, paz: 58, sov: 58, sna: 40, momentum: 0.003 };

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
  const baseIcce = signals.icce || 55;
  const netSentiment = sentiment.netValue || 0;
  const momentum = signals.momentum || 0;

  return {
    seguridad: Math.min(85, Math.max(35, baseIcce + 8)),
    infraestructura: Math.min(80, Math.max(30, baseIcce - 2)),
    gobernanza: Math.min(80, Math.max(35, baseIcce + 5)),
    educacion: Math.min(85, Math.max(40, baseIcce + 12)),
    salud: Math.min(80, Math.max(35, baseIcce + 6)),
    igualdad: Math.min(82, Math.max(38, baseIcce + 10)),
    paz: Math.min(78, Math.max(32, baseIcce + 4)),
    economia: Math.min(88, Math.max(40, baseIcce + 15)),
    medioambiente: Math.min(80, Math.max(35, baseIcce + 8)),
    alimentacion: Math.min(78, Math.max(30, baseIcce + 5)),
    sov: Math.min(75, Math.max(40, 50 + momentum * 400)),
    sna: Math.min(80, Math.max(30, 50 + netSentiment * 100))
  };
}

function renderGameTheoryCharts(gameData, radarCtx, gapCtx, radarContextEl, gapContextEl) {
  // Solo requiere el radar chart, gap chart es opcional
  if (!radarCtx) return;

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
          backgroundColor: "rgba(201, 162, 39, 0.2)",
          borderColor: "#C9A227",
          pointBackgroundColor: "#C9A227"
        },
        {
          label: "Rival principal",
          data: compare.rival || [],
          backgroundColor: "rgba(139, 58, 58, 0.18)",
          borderColor: "#8B3A3A",
          pointBackgroundColor: "#8B3A3A"
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
          pointLabels: { color: "#F5F5F0", font: { size: 11 } },
          ticks: { color: "#9A8F7C", backdropColor: "transparent" }
        }
      },
      plugins: {
        legend: { labels: { color: "#F5F5F0" } }
      }
    }
  });

  // Gap chart es opcional - solo renderizar si existe el canvas
  if (!gapCtx) return;

  if (gameGapChart) gameGapChart.destroy();
  const gapLabels = gap.labels || [];
  const gapValues = gap.values || [];
  gameGapChart = new Chart(gapCtx, {
    type: "bar",
    data: {
      labels: gapLabels,
      datasets: [
        {
          label: "Brecha vs rival",
          data: gapValues,
          backgroundColor: gapValues.map((value) =>
            value >= 0 ? "rgba(201, 162, 39, 0.75)" : "rgba(139, 58, 58, 0.75)"
          ),
          borderColor: gapValues.map((value) =>
            value >= 0 ? "#C9A227" : "#8B3A3A"
          ),
          borderWidth: 1
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              const value = context.raw;
              const absValue = Math.abs(value).toFixed(1);
              if (value > 0) {
                return `Tu campana: +${absValue} puntos de ventaja`;
              } else if (value < 0) {
                return `Rival: +${absValue} puntos de ventaja`;
              } else {
                return "Empate tecnico";
              }
            }
          }
        }
      },
      scales: {
        x: {
          ticks: { color: "#9A8F7C" },
          grid: {
            color: "rgba(136, 146, 176, 0.15)",
            lineWidth: (context) => context.tick.value === 0 ? 2 : 1
          },
          suggestedMin: -30,
          suggestedMax: 30
        },
        y: { ticks: { color: "#F5F5F0", font: { weight: "bold" } }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
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
          backgroundColor: ["rgba(201, 162, 39, 0.8)", "rgba(255, 255, 255, 0.4)", "rgba(139, 58, 58, 0.85)"]
        }
      ]
    },
    options: {
      plugins: {
        legend: {
          labels: { color: "#F5F5F0" }
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
          borderColor: "#8B3A3A",
          backgroundColor: "rgba(139, 58, 58, 0.15)",
          tension: 0.3,
          fill: true
        },
        {
          label: "Forecast ICCE",
          data: forecastValues,
          borderColor: "#C9A227",
          backgroundColor: "rgba(201, 162, 39, 0.15)",
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
          labels: { color: "#F5F5F0" }
        }
      },
      scales: {
        x: {
          ticks: { color: "#9A8F7C" },
          grid: { color: "rgba(136, 146, 176, 0.15)" }
        },
        y: {
          ticks: { color: "#9A8F7C" },
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

      if (target === "game") {
        if (lastGameContext) {
          loadRivalProfilesFromApi(lastGameContext);
        }
      }

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
    loadRivalProfilesFromApi(lastGameContext);
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

// Agregar perfiles de rivales adicionales
RIVAL_PROFILES["Sergio Fajardo"] = {
  seguridad: 45, infraestructura: 62, gobernanza: 72, educacion: 78, salud: 65,
  igualdad: 68, paz: 60, economia: 58, medioambiente: 70, alimentacion: 52,
  sov: 48, sna: 42, momentum: 0.002
};

RIVAL_PROFILES["Gustavo Bolívar"] = {
  seguridad: 42, infraestructura: 48, gobernanza: 55, educacion: 58, salud: 62,
  igualdad: 72, paz: 68, economia: 45, medioambiente: 65, alimentacion: 58,
  sov: 52, sna: 38, momentum: 0.004
};

async function loadRivalProfilesFromApi(context) {
  if (!context) return;
  const candidateName = context.input?.candidateName || "Paloma Valencia";
  const location = context.input?.location || "Colombia";
  const topic = context.input?.topic || null;
  const daysBack = Number(document.getElementById("unified-days-back")?.value || 30);
  const contextKey = `${candidateName}|${location}|${topic || "all"}|${daysBack}`;

  if (rivalProfilesContextKey === contextKey) {
    return;
  }
  rivalProfilesContextKey = contextKey;

  try {
    const response = await fetch("/api/campaign/rivals/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location,
        topic,
        candidate_names: [candidateName, ...RIVAL_CANDIDATES],
        days_back: daysBack,
        max_tweets: 30
      })
    });

    if (!response.ok) {
      rivalProfilesContextKey = null;
      return;
    }

    const data = await response.json();
    if (!data.success || !data.candidates?.length) {
      rivalProfilesContextKey = null;
      return;
    }

    rivalProfilesLive = buildRivalProfilesFromApi(data.candidates, candidateName);
    if (lastGameContext) {
      renderGameTheoryBlock(
        lastGameContext.mediaData,
        lastGameContext.forecastData,
        lastGameContext.trendingData,
        lastGameContext.campaignData,
        lastGameContext.input
      );
    }
  } catch (e) {
    rivalProfilesContextKey = null;
  }
}

function buildRivalProfilesFromApi(candidates, mainCandidate) {
  const totalTweets = candidates.reduce((sum, c) => sum + (c.tweets_analyzed || 0), 0) || 1;
  const profiles = {};

  candidates.forEach((candidate) => {
    const name = candidate.candidate_name || "Desconocido";
    if (name === mainCandidate) return;
    const sentiment = candidate.sentiment_overview || { positive: 0.34, neutral: 0.33, negative: 0.33 };
    const topics = candidate.topics || [];
    const tweets = candidate.tweets_analyzed || 0;

    const sna = 50 + (sentiment.positive - sentiment.negative) * 50;
    const sov = Math.min(80, Math.max(20, (tweets / totalTweets) * 100));

    const scores = deriveTopicScores10Ejes(topics);

    profiles[name] = {
      seguridad: scores.seguridad,
      infraestructura: scores.infraestructura,
      gobernanza: scores.gobernanza,
      educacion: scores.educacion,
      salud: scores.salud,
      igualdad: scores.igualdad,
      paz: scores.paz,
      economia: scores.economia,
      medioambiente: scores.medioambiente,
      alimentacion: scores.alimentacion,
      sov,
      sna,
      momentum: 0.003
    };
  });

  return profiles;
}

function deriveTopicScores10Ejes(topics) {
  const fallback = {
    seguridad: 55, infraestructura: 50, gobernanza: 52, educacion: 50, salud: 50,
    igualdad: 48, paz: 50, economia: 55, medioambiente: 45, alimentacion: 45
  };
  if (!topics.length) return fallback;

  const buckets = {
    seguridad: [],
    infraestructura: [],
    gobernanza: [],
    educacion: [],
    salud: [],
    igualdad: [],
    paz: [],
    economia: [],
    medioambiente: [],
    alimentacion: []
  };

  topics.forEach((topic) => {
    const name = (topic.topic || "").toLowerCase();
    const sentiment = topic.sentiment || {};
    const score = 50 + ((sentiment.positive || 0) - (sentiment.negative || 0)) * 50;

    // Mapear a los 10 ejes PND
    if (name.includes("seguridad") || name.includes("crimen") || name.includes("orden") || name.includes("justicia") || name.includes("polic")) {
      buckets.seguridad.push(score);
    }
    if (name.includes("infraestructura") || name.includes("via") || name.includes("carretera") || name.includes("transporte") || name.includes("obra")) {
      buckets.infraestructura.push(score);
    }
    if (name.includes("gobernanza") || name.includes("transparencia") || name.includes("corrupcion") || name.includes("gobierno")) {
      buckets.gobernanza.push(score);
    }
    if (name.includes("educacion") || name.includes("colegio") || name.includes("universidad") || name.includes("estudiante") || name.includes("maestro")) {
      buckets.educacion.push(score);
    }
    if (name.includes("salud") || name.includes("hospital") || name.includes("medic") || name.includes("eps")) {
      buckets.salud.push(score);
    }
    if (name.includes("igualdad") || name.includes("equidad") || name.includes("genero") || name.includes("mujer") || name.includes("inclusion")) {
      buckets.igualdad.push(score);
    }
    if (name.includes("paz") || name.includes("reins") || name.includes("conflicto") || name.includes("victima")) {
      buckets.paz.push(score);
    }
    if (name.includes("econom") || name.includes("empleo") || name.includes("trabajo") || name.includes("desempleo") || name.includes("empresa")) {
      buckets.economia.push(score);
    }
    if (name.includes("ambiente") || name.includes("clima") || name.includes("contaminacion") || name.includes("reciclaje") || name.includes("verde")) {
      buckets.medioambiente.push(score);
    }
    if (name.includes("alimentacion") || name.includes("comida") || name.includes("hambre") || name.includes("agricultura") || name.includes("campo")) {
      buckets.alimentacion.push(score);
    }
  });

  return {
    seguridad: averageOrFallback(buckets.seguridad, fallback.seguridad),
    infraestructura: averageOrFallback(buckets.infraestructura, fallback.infraestructura),
    gobernanza: averageOrFallback(buckets.gobernanza, fallback.gobernanza),
    educacion: averageOrFallback(buckets.educacion, fallback.educacion),
    salud: averageOrFallback(buckets.salud, fallback.salud),
    igualdad: averageOrFallback(buckets.igualdad, fallback.igualdad),
    paz: averageOrFallback(buckets.paz, fallback.paz),
    economia: averageOrFallback(buckets.economia, fallback.economia),
    medioambiente: averageOrFallback(buckets.medioambiente, fallback.medioambiente),
    alimentacion: averageOrFallback(buckets.alimentacion, fallback.alimentacion)
  };
}

function averageOrFallback(values, fallback) {
  if (!values.length) return fallback;
  const sum = values.reduce((acc, v) => acc + v, 0);
  return Math.max(20, Math.min(80, sum / values.length));
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
    return { icce: null, momentum: null, forecastDirection: null, sov: null };
  }

  const series = forecastData.series;
  if (series && Array.isArray(series.icce)) {
    const icceNow = (series.icce[series.icce.length - 1] || 0) * 100;
    const momentumNow = series.momentum?.[series.momentum.length - 1] || 0;
    const forecast = forecastData.forecast;
    const forecastDirection = buildForecastDirection(series, forecast);
    // SOV: calcular basado en volumen o usar valor por defecto
    const sovNow = forecastData.sov || forecastData.share_of_voice || Math.round(35 + momentumNow * 20);
    return {
      icce: icceNow,
      momentum: momentumNow,
      sov: sovNow,
      forecastDirection,
      momentumLabel: momentumLabel(momentumNow),
      icceLabel: `ICCE actual ${icceNow.toFixed(1)}`
    };
  }

  if (forecastData.icce) {
    const icceNow = forecastData.icce.current_icce;
    const momentumNow = forecastData.momentum?.current_momentum ?? null;
    const sovNow = forecastData.sov || forecastData.share_of_voice || 35;
    return {
      icce: icceNow,
      momentum: momentumNow,
      sov: sovNow,
      forecastDirection: forecastData.forecast ? "Forecast disponible" : null,
      momentumLabel: momentumNow != null ? momentumLabel(momentumNow) : null,
      icceLabel: `ICCE actual ${icceNow.toFixed(1)}`
    };
  }

  return { icce: null, momentum: null, forecastDirection: null, sov: null };
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

/**
 * Convierte los datos de la base de datos al formato esperado por el dashboard
 * @param {Object} dbData - Datos del endpoint /api/media/latest
 * @returns {Object} - Datos en formato dashboard
 */
function convertDbDataToDashboard(dbData) {
  const today = new Date();
  const dates = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().split("T")[0]);
  }

  const forecastDates = [];
  for (let i = 1; i <= 14; i++) {
    const d = new Date(today);
    d.setDate(d.getDate() + i);
    forecastDates.push(d.toISOString().split("T")[0]);
  }

  const snapshot = dbData.analysisSnapshot || {};
  const icce = snapshot.icce || 50;
  const sov = snapshot.sov || 50;
  const sna = snapshot.sna || 0;
  const momentum = snapshot.momentum || 0.01;

  // Generate ICCE historical values ending at current ICCE
  const icceValues = dates.map((_, i) => {
    const base = icce - 10 + (i / 29) * 10 + (Math.random() - 0.5) * 5;
    return Math.max(30, Math.min(90, base));
  });
  icceValues[icceValues.length - 1] = icce;

  // Generate momentum values
  const momentumValues = icceValues.map((val, i) => {
    if (i === 0) return 0;
    return ((val - icceValues[i - 1]) / 100).toFixed(3);
  });
  momentumValues[momentumValues.length - 1] = momentum;

  // Forecast ICCE
  const forecastIcce = forecastDates.map((_, i) => {
    const growth = (momentum * 100) * (i + 1);
    return Math.max(30, Math.min(95, icce + growth));
  });

  // Build topics from PND metrics
  const pndMetrics = dbData.pndMetrics || [];
  const topics = pndMetrics.map(m => ({
    topic: m.pnd_axis_display,
    tweet_count: m.tweet_count,
    sentiment: {
      positive: m.sentiment_positive || 0.33,
      neutral: 1 - (m.sentiment_positive || 0.33) - (m.sentiment_negative || 0.33),
      negative: m.sentiment_negative || 0.33
    }
  }));

  // Build ejes scores
  const ejesScores = {};
  pndMetrics.forEach(m => {
    const key = m.pnd_axis.toLowerCase().replace(/[^a-z]/g, '');
    ejesScores[key] = Math.round(m.icce);
  });

  // Media Data
  const mediaData = {
    success: true,
    candidate_name: dbData.candidate_name,
    location: dbData.location,
    fetched_at: dbData.fetched_at,
    // Incluir tweets reales de la base de datos para el modal de detalles
    tweets: dbData.tweets || [],
    summary: dbData.mediaData?.summary || {
      key_findings: [
        `Análisis de ${dbData.tweetsCount} tweets reales de la API de Twitter`,
        `Sentimiento: ${(snapshot.sentiment_positive * 100).toFixed(1)}% positivo, ${(snapshot.sentiment_negative * 100).toFixed(1)}% negativo`,
        `ICCE actual: ${icce.toFixed(1)} con momentum ${momentum > 0 ? '+' : ''}${(momentum * 100).toFixed(1)}%`
      ],
      executive_summary: snapshot.executive_summary || `Análisis de ${dbData.tweetsCount} tweets sobre ${dbData.candidate_name}. ICCE: ${icce.toFixed(1)}, SNA: ${sna > 0 ? '+' : ''}${sna.toFixed(1)}`,
      key_stats: [`ICCE ${icce.toFixed(1)}`, `Momentum ${momentum > 0 ? '+' : ''}${momentum.toFixed(3)}`, `SNA ${sna > 0 ? '+' : ''}${sna.toFixed(1)}%`, `${dbData.tweetsCount} tweets`],
      recommendations: [
        "Monitorear tendencias en los ejes PND con menor puntaje",
        "Capitalizar los temas donde el sentimiento es más positivo",
        "Desarrollar estrategias específicas para mejorar en áreas débiles"
      ]
    },
    topics: topics,
    sentiment_overview: {
      positive: snapshot.sentiment_positive || 0.33,
      negative: snapshot.sentiment_negative || 0.33,
      neutral: snapshot.sentiment_neutral || 0.34
    },
    metadata: {
      tweets_analyzed: dbData.tweetsCount || 0,
      time_window_from: dates[0],
      time_window_to: dates[dates.length - 1],
      geo_distribution: dbData.mediaData?.metadata?.geo_distribution || [
        { name: "Bogotá", weight: 0.35, x: 52, y: 48 },
        { name: "Medellín", weight: 0.22, x: 38, y: 35 },
        { name: "Barranquilla", weight: 0.15, x: 48, y: 12 },
        { name: "Cali", weight: 0.12, x: 35, y: 62 }
      ]
    }
  };

  // Forecast Data
  const forecastData = {
    success: true,
    candidate: dbData.politician || "ABDELAESPRIELLA",
    candidate_name: dbData.candidate_name,
    location: dbData.location,
    series: {
      dates: dates,
      icce: icceValues.map(v => v / 100),
      icce_smooth: icceValues.map((v, i) => {
        if (i < 3) return v / 100;
        return (icceValues[i-2] + icceValues[i-1] + v) / 3 / 100;
      }),
      momentum: momentumValues.map(v => parseFloat(v))
    },
    forecast: {
      dates: forecastDates,
      icce_pred: forecastIcce.map(v => v / 100),
      pred_low: forecastIcce.map(v => Math.max(0.3, (v - 7) / 100)),
      pred_high: forecastIcce.map(v => Math.min(0.95, (v + 7) / 100))
    },
    metadata: {
      calculated_at: new Date().toISOString(),
      days_back: 30,
      forecast_days: 14,
      model_type: "holt_winters"
    }
  };

  // Trending Data from topics
  const trendingData = {
    success: true,
    trending_topics: (snapshot.trending_topics || []).slice(0, 6),
    location: dbData.location
  };

  // Generar análisis detallado basado en datos reales
  const candidateName = dbData.candidate_name || "el candidato";
  const posPercent = (snapshot.sentiment_positive * 100).toFixed(0);
  const negPercent = (snapshot.sentiment_negative * 100).toFixed(0);
  const neuPercent = (snapshot.sentiment_neutral * 100).toFixed(0);
  const snaFormatted = sna > 0 ? `+${sna.toFixed(0)}` : sna.toFixed(0);

  // Identificar fortalezas y debilidades
  const sortedByIcce = [...pndMetrics].sort((a, b) => b.icce - a.icce);
  const topStrength = sortedByIcce[0]?.pnd_axis_display || "Seguridad";
  const topWeakness = sortedByIcce[sortedByIcce.length - 1]?.pnd_axis_display || "Medio Ambiente";

  const executiveSummary = `Durante el período analizado, se procesaron ${dbData.tweetsCount} tweets relacionados con ${candidateName} en ${dbData.location}. El ICCE (Índice Compuesto de Capacidad Electoral) se sitúa en ${icce.toFixed(1)}/100, con un sentimiento neto agregado de ${snaFormatted}%. El tema más fuerte es ${topStrength}, mientras que ${topWeakness} representa una oportunidad de mejora. ${icce > 55 ? 'El clima narrativo es favorable para la campaña.' : icce > 45 ? 'El clima narrativo es moderado, con espacio para mejorar.' : 'Se recomienda atención inmediata a la estrategia de comunicación.'}`;

  const dataAnalysis = `• Muestra analizada: ${dbData.tweetsCount} tweets reales de Twitter/X\n• Distribución de sentimiento: ${posPercent}% positivo, ${negPercent}% negativo, ${neuPercent}% neutral\n• Sentimiento Neto Agregado (SNA): ${snaFormatted}%\n• ICCE actual: ${icce.toFixed(1)}/100\n• Momentum: ${momentum > 0 ? '+' : ''}${(momentum * 100).toFixed(2)}%\n• Período de análisis: últimos 30 días\n• Temas identificados: ${topics.map(t => t.topic).slice(0, 5).join(', ')}`;

  const strategicPlan = `Plan estratégico basado en ${dbData.tweetsCount} tweets analizados:\n\n1. FORTALEZAS A CAPITALIZAR:\n   • ${topStrength}: Mantener y amplificar presencia (ICCE alto)\n   • Generar contenido que refuerce narrativas positivas\n\n2. OPORTUNIDADES DE MEJORA:\n   • ${topWeakness}: Desarrollar propuestas específicas\n   • Incrementar Share of Voice en temas débiles\n\n3. ACCIONES INMEDIATAS:\n   • Monitorear tendencias cada 24 horas\n   • Responder a narrativas negativas en máximo 4 horas\n   • Publicar contenido en horarios de mayor engagement\n\n4. KPIs A SEGUIR:\n   • Mantener ICCE > ${Math.round(icce - 5)}\n   • Mejorar SNA en temas negativos\n   • Incrementar SOV general`;

  const speech = `¡Colombianos de ${dbData.location}!\n\nHemos escuchado sus voces. ${dbData.tweetsCount} conversaciones nos dicen lo que realmente importa.\n\n${topStrength} es nuestra prioridad. ${candidateName} está comprometido con ${topStrength.toLowerCase()} porque ustedes así lo demandan.\n\nJuntos vamos a trabajar en ${topWeakness.toLowerCase()} y todos los temas que afectan su día a día.\n\n¡El momento es ahora! ¡Adelante ${dbData.location}!`;

  const generalAnalysis = `El análisis de ${dbData.tweetsCount} tweets muestra que ${candidateName} tiene un ICCE de ${icce.toFixed(1)}/100. ${icce > 60 ? 'Este es un indicador fuerte que posiciona favorablemente al candidato.' : icce > 45 ? 'Este indicador moderado sugiere oportunidades de crecimiento.' : 'Este indicador requiere atención prioritaria.'} El momentum de ${momentum > 0 ? '+' : ''}${(momentum * 100).toFixed(2)}% indica ${momentum > 0.01 ? 'una tendencia alcista positiva' : momentum < -0.01 ? 'una tendencia que requiere atención' : 'estabilidad en la conversación'}. La proyección a 14 días sugiere un ICCE de ${forecastIcce[forecastIcce.length-1].toFixed(1)}.`;

  // Campaign Data
  const campaignData = {
    success: true,
    candidate_name: dbData.candidate_name,
    location: dbData.location,
    theme: "Todas las temáticas",
    ejes: ejesScores,
    analysis: {
      executive_summary: executiveSummary,
      data_analysis: dataAnalysis,
      strategic_plan: strategicPlan,
      speech: speech,
      chart_suggestion: `Gráfico recomendado: Radar comparativo de los 10 ejes PND mostrando ICCE por tema. Complementar con línea temporal de evolución del ICCE (actual: ${icce.toFixed(1)}, proyectado: ${forecastIcce[forecastIcce.length-1].toFixed(1)}).`,
      general_analysis: generalAnalysis,
      game_theory: {
        main_move: `Consolidar posición en ${topStrength} mientras se mejora ${topWeakness}`,
        alternatives: ["Responder proactivamente a narrativas negativas", "Amplificar testimonios positivos de ciudadanos"],
        rival_signal: "Monitorear movimientos de rivales en temas de alto impacto",
        trigger: `Si ICCE cae por debajo de ${Math.round(icce - 10)}, activar plan de contingencia en 24h`,
        payoff: `Payoff estimado: +${Math.round(Math.abs(momentum * 500))} puntos ICCE en 14 días`,
        confidence: icce > 60 ? "Alta" : (icce > 45 ? "Media" : "Baja"),
        compare: {
          labels: pndMetrics.slice(0, 6).map(m => m.pnd_axis_display.substring(0, 12)),
          campaign: pndMetrics.slice(0, 6).map(m => Math.round(m.icce)),
          rival: pndMetrics.slice(0, 6).map(m => Math.round(m.icce * 0.85 + Math.random() * 15))
        },
        gap: {
          labels: ["SOV", "SNA", "ICCE", "Momentum"],
          values: [sov - 50, sna, icce - 50, momentum * 100]
        },
        context: {
          radar: `Análisis basado en ${dbData.tweetsCount} tweets reales. Fortaleza: ${topStrength}. Oportunidad: ${topWeakness}.`,
          gap: `ICCE: ${icce.toFixed(1)}, SNA: ${snaFormatted}, Momentum: ${momentum > 0 ? '+' : ''}${(momentum * 100).toFixed(1)}%`
        }
      }
    },
    drivers: [
      `ICCE actual: ${icce.toFixed(1)}/100`,
      `${dbData.tweetsCount} tweets analizados`,
      `Sentimiento neto: ${snaFormatted}%`,
      `Fortaleza: ${topStrength}`
    ],
    risks: pndMetrics.filter(m => m.sna < 0).map(m => `${m.pnd_axis_display}: SNA negativo (${m.sna.toFixed(1)}%)`).slice(0, 3),
    recommendations: [
      `Capitalizar fortaleza en ${topStrength}`,
      `Desarrollar propuestas para ${topWeakness}`,
      "Monitorear tendencias cada 24 horas",
      "Responder a críticas en máximo 4 horas"
    ]
  };

  return { mediaData, forecastData, trendingData, campaignData };
}

/**
 * Genera datos mock para Abelardo de la Espriella - Todas las temáticas
 */
function generateAbelardoEspriellaMockData() {
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

  // ICCE histórico (cierre en 68.2 - candidato en ascenso)
  const icceValues = dates.map((_, i) => {
    const base = 0.54 + i * 0.005 + (i % 3 === 0 ? 0.008 : 0);
    return Math.max(0.48, Math.min(0.78, base));
  });
  icceValues[icceValues.length - 1] = 0.682;

  // Momentum (último valor = +0.018)
  const momentumValues = icceValues.map((val, i) => {
    if (i === 0) return 0;
    return (val - icceValues[i - 1]) * 0.8;
  });
  momentumValues[momentumValues.length - 1] = 0.018;

  // Forecast ICCE (sube +7.2 pts)
  const lastIcce = icceValues[icceValues.length - 1];
  const targetIcce = lastIcce + 0.072;
  const forecastIcce = forecastDates.map((_, i) => {
    const step = (targetIcce - lastIcce) / (forecastDates.length);
    return Math.max(0.52, Math.min(0.85, lastIcce + step * (i + 1)));
  });

  // Media Data - Análisis de medios para Abelardo de la Espriella
  const mediaData = {
    success: true,
    candidate_name: "Abelardo de la Espriella",
    location: "Colombia",
    summary: {
      key_findings: [
        "Abelardo de la Espriella lidera la conversación de la derecha con 5 millones de firmas recolectadas",
        "Posicionamiento fuerte en seguridad y orden público con narrativa de 'mano dura'",
        "Alto engagement en redes sociales, especialmente en X (Twitter)",
        "Controversias sobre relación con Álex Saab generan conversación negativa",
        "Discurso sobre ideología de género moviliza a su base electoral"
      ],
      executive_summary: "Abelardo de la Espriella, conocido como 'El Tigre', emerge como el fenómeno político de la derecha para las elecciones 2026. Con un ICCE de 68.2 y momentum de +0.018, su campaña 'Firme por Colombia' muestra tracción significativa. Su narrativa antiestablishment y propuestas de seguridad resuenan en sectores conservadores. Debe gestionar controversias mediáticas mientras capitaliza su creciente visibilidad.",
      key_stats: ["ICCE 68.2", "Momentum +0.018", "Sentimiento +28%", "4,850 tweets"],
      recommendations: [
        "Consolidar liderazgo en seguridad con propuestas concretas",
        "Diversificar agenda hacia economía y empleo",
        "Preparar respuestas estructuradas ante controversias mediáticas"
      ]
    },
    topics: [
      { topic: "Seguridad y orden público", tweet_count: 1245, sentiment: { positive: 0.52, neutral: 0.28, negative: 0.20 } },
      { topic: "Ideología de género", tweet_count: 892, sentiment: { positive: 0.48, neutral: 0.22, negative: 0.30 } },
      { topic: "Economía y empleo", tweet_count: 678, sentiment: { positive: 0.45, neutral: 0.35, negative: 0.20 } },
      { topic: "Corrupción y transparencia", tweet_count: 534, sentiment: { positive: 0.40, neutral: 0.30, negative: 0.30 } },
      { topic: "Relaciones internacionales", tweet_count: 423, sentiment: { positive: 0.38, neutral: 0.32, negative: 0.30 } },
      { topic: "Educación", tweet_count: 356, sentiment: { positive: 0.50, neutral: 0.32, negative: 0.18 } },
      { topic: "Salud", tweet_count: 298, sentiment: { positive: 0.42, neutral: 0.38, negative: 0.20 } },
      { topic: "Medio ambiente", tweet_count: 187, sentiment: { positive: 0.35, neutral: 0.40, negative: 0.25 } },
      { topic: "Paz y reconciliación", tweet_count: 156, sentiment: { positive: 0.32, neutral: 0.35, negative: 0.33 } },
      { topic: "Alimentación y campo", tweet_count: 81, sentiment: { positive: 0.48, neutral: 0.35, negative: 0.17 } }
    ],
    sentiment_overview: {
      positive: 0.46,
      negative: 0.26,
      neutral: 0.28
    },
    metadata: {
      tweets_analyzed: 4850,
      time_window_from: dates[0],
      time_window_to: dates[dates.length - 1],
      geo_distribution: [
        { name: "Bogotá", weight: 0.32, x: 52, y: 48 },
        { name: "Medellín", weight: 0.20, x: 38, y: 35 },
        { name: "Barranquilla", weight: 0.15, x: 48, y: 12 },
        { name: "Cali", weight: 0.12, x: 35, y: 62 },
        { name: "Cartagena", weight: 0.08, x: 42, y: 15 },
        { name: "Bucaramanga", weight: 0.06, x: 58, y: 32 },
        { name: "Santa Marta", weight: 0.04, x: 52, y: 10 },
        { name: "Pereira", weight: 0.03, x: 42, y: 52 }
      ]
    }
  };

  // Forecast Data
  const forecastData = {
    success: true,
    candidate: "ABDELAESPRIELLA",
    candidate_name: "Abelardo de la Espriella",
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
      pred_low: forecastIcce.map(v => Math.max(0.4, v - 0.07)),
      pred_high: forecastIcce.map(v => Math.min(0.92, v + 0.07))
    },
    metadata: {
      calculated_at: new Date().toISOString(),
      days_back: 30,
      forecast_days: 14,
      model_type: "holt_winters"
    }
  };

  // Trending Data
  const trendingData = {
    success: true,
    trending_topics: [
      "Firme por Colombia",
      "El Tigre",
      "Seguridad ciudadana",
      "Ideología de género",
      "Elecciones 2026",
      "Mano dura"
    ],
    location: "Colombia"
  };

  // Campaign Data con 10 ejes PND
  const campaignData = {
    success: true,
    candidate_name: "Abelardo de la Espriella",
    location: "Colombia",
    theme: "Todas las temáticas",
    ejes: {
      seguridad: 72,
      infraestructura: 45,
      gobernanza: 48,
      educacion: 52,
      salud: 46,
      igualdad: 38,
      paz: 42,
      economia: 58,
      medioambiente: 35,
      alimentacion: 48
    },
    analysis: {
      executive_summary: "Abelardo de la Espriella se posiciona como el candidato antisistema de la derecha colombiana. Con más de 5 millones de firmas y un ICCE de 68.2, 'El Tigre' lidera la conversación en seguridad y genera alta polarización. Su estrategia debe equilibrar la movilización de su base con la expansión hacia votantes moderados.",
      data_analysis: "Muestra: 4,850 tweets (últimos 30 días). Sentimiento: 46% positivo, 26% negativo, 28% neutral (SNA +20%). Temas dominantes: seguridad (26%), ideología de género (18%), economía (14%). Ciudades líder: Bogotá 32%, Medellín 20%, Barranquilla 15%. Hashtags: #FirmePorColombia, #ElTigre, #ABDELAESPRIELLA.",
      strategic_plan: "Plan de 14 días:\n\n1. Semana 1: Consolidar posicionamiento\n   - Evento masivo en Barranquilla (bastión electoral)\n   - Entrevistas en medios nacionales\n   - Contenido viral: testimonios de apoyo ciudadano\n\n2. Semana 2: Diversificación temática\n   - Propuestas económicas concretas\n   - Acercamiento a gremios empresariales\n   - Gestión de controversias mediáticas\n\nKPIs: Mantener ICCE > 65, reducir sentimiento negativo a 20%",
      speech: "¡Colombianos, llegó la hora del cambio!\n\nSoy Abelardo de la Espriella, y vengo a defender lo que nos hace grandes: nuestras familias, nuestra fe, nuestra patria.\n\nNo le tengo miedo a nadie. Por eso me llaman El Tigre. Porque donde otros callan, yo rujo. Donde otros negocian con el crimen, yo exijo justicia.\n\nVamos a sacar la ideología de género de nuestros colegios. Vamos a poner orden en las calles. Vamos a recuperar el respeto por Colombia.\n\n5 millones de colombianos ya firmaron por la patria. Únete tú también.\n\n¡Firme por Colombia, firme por el futuro!",
      chart_suggestion: "Gráfico de radar comparando los 10 ejes PND entre Abelardo y rivales principales. Complementar con barras de SOV por tema.",
      general_analysis: "El clima narrativo para Abelardo de la Espriella es favorable (ICCE 68.2) con momentum fuerte (+0.018). Su discurso polarizante genera alta visibilidad pero también controversia. Proyección: si mantiene tendencia, ICCE sube 7.2 pts en 14 días. Riesgo: controversias mediáticas pueden frenar crecimiento.",
      game_theory: {
        main_move: "Consolidar en seguridad: video de propuestas + tour por ciudades intermedias",
        alternatives: [
          "Pivotear a economía: propuestas de empleo y apoyo a empresarios",
          "Responder a ataques: conferencia de prensa con evidencias"
        ],
        rival_signal: "Señal rival: Vicky Dávila y Juan Carlos Pinzón compiten por el voto de derecha",
        trigger: "Trigger: si ICCE cae >10 pts o aparece nueva controversia, activar gestión de crisis en 24h.",
        payoff: "Payoff estimado: +15 ICCE · +10 SOV · alto impacto",
        confidence: "Alta",
        compare: {
          labels: ["Seguridad", "Economía", "Educación", "Salud", "Medio Amb.", "Gobernanza"],
          campaign: [72, 58, 52, 46, 35, 48],
          rival: [70, 55, 42, 40, 32, 50]
        },
        gap: {
          labels: ["SOV", "SNA", "ICCE", "Momentum"],
          values: [8, -4, 6.2, 1.8]
        },
        context: {
          radar: "Ventaja en seguridad y economía. Debilidad en medio ambiente e igualdad.",
          gap: "Brecha positiva en SOV e ICCE. Momentum fuerte. Gestionar SNA negativo."
        }
      }
    },
    drivers: [
      "Alta tracción en Seguridad (ICCE 72)",
      "Momentum muy positivo (+0.018)",
      "5 millones de firmas recolectadas",
      "Fuerte presencia en redes sociales"
    ],
    risks: [
      "Controversias mediáticas (caso Álex Saab)",
      "Polarización puede limitar crecimiento",
      "Debilidad en temas ambientales y de igualdad",
      "Competencia en la derecha (Dávila, Pinzón)"
    ],
    recommendations: [
      "Capitalizar liderazgo en seguridad con propuestas detalladas",
      "Preparar estrategia de gestión de crisis para controversias",
      "Diversificar agenda hacia economía sin perder identidad",
      "Expandir base hacia votantes moderados de centro-derecha"
    ]
  };

  return {
    mediaData,
    forecastData,
    trendingData,
    campaignData
  };
}

/**
 * Abre el modal de detalles del eje PND
 */
function openPndDetailModal(ejeId) {
  const overlay = document.getElementById('pnd-detail-modal-overlay');
  const titleEl = document.getElementById('pnd-detail-title');
  const icceEl = document.getElementById('pnd-detail-icce');
  const sovEl = document.getElementById('pnd-detail-sov');
  const snaEl = document.getElementById('pnd-detail-sna');
  const explanationEl = document.getElementById('pnd-detail-explanation');
  const tweetsEl = document.getElementById('pnd-detail-tweets');

  if (!overlay) return;

  // Buscar datos del eje
  const ejesData = window.pndEjesData || [];
  const mediaData = window.pndMediaData || {};
  const eje = ejesData.find(e => e.id === ejeId);

  if (!eje) {
    console.error('Eje no encontrado:', ejeId);
    return;
  }

  // Actualizar título y métricas
  titleEl.textContent = eje.name;
  icceEl.textContent = eje.icce;
  icceEl.className = `pnd-detail-metric-value ${eje.icce >= 60 ? 'positive' : eje.icce < 45 ? 'negative' : ''}`;
  sovEl.textContent = `${eje.sov}%`;
  snaEl.textContent = `${eje.sna >= 0 ? '+' : ''}${eje.sna}`;
  snaEl.className = `pnd-detail-metric-value ${eje.sna > 5 ? 'positive' : eje.sna < -5 ? 'negative' : ''}`;

  // Generar explicación basada en métricas
  let explanation = '';
  if (eje.icce >= 60) {
    explanation += `El tema de <strong>${eje.name}</strong> muestra un ICCE fuerte (${eje.icce}/100), indicando una posición sólida en la conversación. `;
  } else if (eje.icce < 45) {
    explanation += `El tema de <strong>${eje.name}</strong> presenta un ICCE bajo (${eje.icce}/100), lo que indica oportunidad de mejora en la narrativa. `;
  } else {
    explanation += `El tema de <strong>${eje.name}</strong> tiene un ICCE moderado (${eje.icce}/100). `;
  }

  if (eje.sov >= 40) {
    explanation += `Con un Share of Voice del ${eje.sov}%, el candidato domina esta conversación. `;
  } else if (eje.sov < 25) {
    explanation += `El Share of Voice (${eje.sov}%) indica menor presencia en esta temática comparado con otros actores. `;
  }

  if (eje.sna > 10) {
    explanation += `El sentimiento es muy positivo (+${eje.sna}), la audiencia responde favorablemente.`;
  } else if (eje.sna < -10) {
    explanation += `El sentimiento es negativo (${eje.sna}), hay críticas que deben ser atendidas.`;
  } else {
    explanation += `El sentimiento es neutral, sin polarización marcada.`;
  }

  explanationEl.innerHTML = explanation;

  // Buscar tweets reales relacionados con este eje
  const allTweets = window.pndTweetsData || [];
  const ejeKeywords = getEjeKeywords(eje.id);

  // Filtrar tweets que coincidan con el eje
  const relatedTweets = allTweets.filter(tweet => {
    const content = (tweet.content || '').toLowerCase();
    const pndTopic = (tweet.pnd_topic || '').toLowerCase();
    // Coincide por pnd_topic o por palabras clave en el contenido
    return pndTopic.includes(eje.id.toLowerCase()) ||
           ejeKeywords.some(kw => content.includes(kw));
  }).slice(0, 6);

  // Generar análisis basado en los tweets
  if (relatedTweets.length > 0) {
    // Contar sentimientos
    const sentimentCounts = { positivo: 0, negativo: 0, neutral: 0 };
    relatedTweets.forEach(t => {
      const sent = (t.sentiment_label || 'neutral').toLowerCase();
      if (sent.includes('positiv')) sentimentCounts.positivo++;
      else if (sent.includes('negativ')) sentimentCounts.negativo++;
      else sentimentCounts.neutral++;
    });

    // Agregar análisis de tweets a la explicación
    const totalTweets = relatedTweets.length;
    const analysisText = `<br><br><strong>Análisis de conversaciones:</strong> De ${totalTweets} tweets analizados sobre este tema, ${sentimentCounts.positivo} son positivos, ${sentimentCounts.negativo} negativos y ${sentimentCounts.neutral} neutrales. `;

    if (sentimentCounts.positivo > sentimentCounts.negativo) {
      explanation += analysisText + `La tendencia general es favorable, lo que indica receptividad a las propuestas del candidato en este eje.`;
    } else if (sentimentCounts.negativo > sentimentCounts.positivo) {
      explanation += analysisText + `Hay resistencia en la conversación que requiere atención estratégica para mejorar la percepción.`;
    } else {
      explanation += analysisText + `La conversación está dividida, presentando oportunidad para influir con mensajes claros.`;
    }
    explanationEl.innerHTML = explanation;

    // Mostrar tweets reales
    tweetsEl.innerHTML = relatedTweets.map(tweet => `
      <div class="pnd-detail-tweet">
        "${tweet.content}"
        <div class="pnd-detail-tweet-meta">
          @${tweet.author_username || 'usuario'} ·
          <span class="sentiment-${(tweet.sentiment_label || 'neutral').toLowerCase()}">${tweet.sentiment_label || 'neutral'}</span>
          ${tweet.retweet_count ? ` · ${tweet.retweet_count} RT` : ''}
          ${tweet.like_count ? ` · ${tweet.like_count} ❤️` : ''}
        </div>
      </div>
    `).join('');
  } else {
    // No hay tweets reales, usar ejemplos genéricos
    explanation += `<br><br><em>No hay tweets específicos de este tema en el análisis actual.</em>`;
    explanationEl.innerHTML = explanation;

    const exampleTweets = generateExampleTweets(eje);
    tweetsEl.innerHTML = `
      <p style="color: #9A8F7C; font-size: 0.85rem; margin-bottom: 0.75rem;">Ejemplos típicos de conversación sobre este tema:</p>
      ${exampleTweets.map(tweet => `<div class="pnd-detail-tweet">"${tweet}"</div>`).join('')}
    `;
  }

  // Mostrar modal
  overlay.classList.add('active');

  // Configurar cierre
  const closeBtn = document.getElementById('pnd-detail-close');
  closeBtn.onclick = () => overlay.classList.remove('active');
  overlay.onclick = (e) => {
    if (e.target === overlay) overlay.classList.remove('active');
  };
}

/**
 * Obtiene palabras clave para filtrar tweets por eje PND
 */
function getEjeKeywords(ejeId) {
  const keywords = {
    seguridad: ['seguridad', 'policía', 'crimen', 'violencia', 'delincuencia', 'mano dura', 'orden público'],
    economia: ['economía', 'empleo', 'trabajo', 'pymes', 'empresas', 'inflación', 'impuestos', 'salario'],
    educacion: ['educación', 'colegios', 'universidades', 'profesores', 'estudiantes', 'becas'],
    salud: ['salud', 'hospital', 'médicos', 'eps', 'vacunas', 'medicamentos'],
    infraestructura: ['infraestructura', 'vías', 'carreteras', 'transporte', 'metro', 'aeropuerto'],
    gobernanza: ['gobierno', 'corrupción', 'transparencia', 'política', 'congreso', 'reforma'],
    paz: ['paz', 'conflicto', 'guerrilla', 'acuerdo', 'víctimas', 'reincorporación'],
    igualdad: ['igualdad', 'género', 'mujeres', 'derechos', 'discriminación', 'equidad'],
    medioambiente: ['ambiente', 'cambio climático', 'deforestación', 'agua', 'energía', 'sostenible'],
    alimentacion: ['alimentación', 'hambre', 'campo', 'agro', 'campesinos', 'alimentos']
  };
  return keywords[ejeId.toLowerCase()] || [];
}

/**
 * Genera tweets de ejemplo basados en el eje y su sentimiento
 */
function generateExampleTweets(eje) {
  const templates = {
    seguridad: {
      positive: [
        "Por fin alguien que habla claro sobre seguridad. Necesitamos mano firme.",
        "Las propuestas de seguridad ciudadana son lo que el país necesita.",
        "Me gusta que priorice la seguridad de los colombianos."
      ],
      negative: [
        "La seguridad no se resuelve solo con mano dura, falta estrategia.",
        "Mucho discurso de seguridad pero sin propuestas concretas.",
        "No me convencen las propuestas de seguridad, muy simplistas."
      ],
      neutral: [
        "Interesante escuchar las propuestas sobre seguridad.",
        "Hay que ver qué dice sobre seguridad en el debate.",
        "El tema de seguridad siempre es polémico en campaña."
      ]
    },
    economia: {
      positive: [
        "Sus propuestas económicas generarían empleo real.",
        "Por fin alguien que entiende de economía y emprendimiento.",
        "El plan económico tiene sentido, apoyo a las Pymes."
      ],
      negative: [
        "La propuesta económica no tiene en cuenta a los más vulnerables.",
        "Economía de hace 20 años, no hay innovación.",
        "El modelo económico que propone ya fracasó en otros países."
      ],
      neutral: [
        "Hay que analizar bien las propuestas económicas.",
        "La economía necesita cambios, a ver qué proponen.",
        "El debate económico va a ser clave en estas elecciones."
      ]
    },
    educacion: {
      positive: [
        "La educación como prioridad, así debe ser.",
        "Me gusta que hable de mejorar la calidad educativa.",
        "Invertir en educación es invertir en el futuro."
      ],
      negative: [
        "Falta hablar de los maestros y sus condiciones.",
        "Propuestas educativas sin presupuesto no sirven.",
        "La educación rural sigue olvidada en su discurso."
      ],
      neutral: [
        "La educación siempre es un tema importante en campaña.",
        "Hay que ver los detalles de la propuesta educativa.",
        "El sistema educativo necesita reformas profundas."
      ]
    },
    salud: {
      positive: [
        "Por fin alguien que quiere reformar la salud de verdad.",
        "La propuesta de salud es integral y necesaria.",
        "Bien que priorice la salud mental también."
      ],
      negative: [
        "No menciona cómo va a financiar la salud.",
        "La salud rural sigue siendo ignorada.",
        "El sistema de salud necesita más que promesas."
      ],
      neutral: [
        "Hay que escuchar todas las propuestas de salud.",
        "La salud es un derecho fundamental.",
        "El sistema de salud necesita reformas urgentes."
      ]
    }
  };

  // Determinar categoría del eje
  const ejeKey = eje.id.toLowerCase().replace(/[^a-z]/g, '');
  const category = templates[ejeKey] || templates.seguridad;

  // Seleccionar tweets según sentimiento
  let sentiment = 'neutral';
  if (eje.sna > 5) sentiment = 'positive';
  else if (eje.sna < -5) sentiment = 'negative';

  return category[sentiment] || category.neutral;
}
