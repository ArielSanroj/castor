let unifiedChart = null;
let sentimentChart = null;
let momentumChart = null;
const kpiCharts = {
  icce: null,
  momentum: null
};

// RAG Chat state
let currentChatTopic = null;
let chatContext = null;
let analysisData = null;

// =====================================================
// RAG CHAT FUNCTIONS
// =====================================================

function selectTopicForChat(topicName, topicData) {
  currentChatTopic = topicName;
  chatContext = topicData;

  const badge = document.getElementById("chat-topic-badge");
  if (badge) {
    badge.textContent = topicName;
    badge.style.background = "rgba(66,214,151,0.2)";
    badge.style.color = "#42d697";
  }

  const messagesEl = document.getElementById("chat-messages");
  if (messagesEl) {
    messagesEl.innerHTML = `
      <div class="chat-message assistant" style="background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;">
        <p style="margin: 0; color: #F5F7FA;">Tema seleccionado: <strong>${topicName}</strong></p>
        <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: #8892B0;">
          ${topicData?.tweet_count || 0} menciones detectadas.
          Tono: ${topicData?.sentiment?.positive > topicData?.sentiment?.negative ? "mayormente favorable" : topicData?.sentiment?.negative > 0.4 ? "mayormente critico" : "mixto"}.
        </p>
        <p style="margin: 0.5rem 0 0; font-size: 0.85rem; color: #8892B0;">Preguntame que quieres saber sobre este tema.</p>
      </div>`;
  }

  // Scroll chat into view
  document.getElementById("topic-chat-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
}

function askSuggestion(question) {
  document.getElementById("chat-input").value = question;
  sendTopicQuestion();
}

async function sendTopicQuestion() {
  const input = document.getElementById("chat-input");
  const messagesEl = document.getElementById("chat-messages");
  const question = input?.value?.trim();

  if (!question) return;

  // Add user message
  const userMsg = document.createElement("div");
  userMsg.className = "chat-message user";
  userMsg.style.cssText = "background: rgba(255,106,61,0.15); padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem; text-align: right;";
  userMsg.innerHTML = `<p style="margin: 0; color: #F5F7FA;">${question}</p>`;
  messagesEl.appendChild(userMsg);

  input.value = "";

  // Show loading
  const loadingMsg = document.createElement("div");
  loadingMsg.className = "chat-message loading";
  loadingMsg.style.cssText = "padding: 0.75rem; color: #8892B0;";
  loadingMsg.innerHTML = '<p style="margin: 0;">Analizando...</p>';
  messagesEl.appendChild(loadingMsg);
  messagesEl.scrollTop = messagesEl.scrollHeight;

  try {
    const response = await fetch("/api/chat/topic", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: question,
        topic: currentChatTopic,
        context: chatContext,
        analysis_data: analysisData
      })
    });

    const data = await response.json();
    loadingMsg.remove();

    const assistantMsg = document.createElement("div");
    assistantMsg.className = "chat-message assistant";
    assistantMsg.style.cssText = "background: rgba(255,255,255,0.03); padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;";

    if (data.success) {
      assistantMsg.innerHTML = `<p style="margin: 0; color: #F5F7FA; white-space: pre-wrap; line-height: 1.5;">${data.answer}</p>`;
    } else {
      assistantMsg.innerHTML = `<p style="margin: 0; color: #FF6A3D;">Error: ${data.error || "No se pudo procesar la pregunta"}</p>`;
    }
    messagesEl.appendChild(assistantMsg);

  } catch (err) {
    loadingMsg.remove();
    const errorMsg = document.createElement("div");
    errorMsg.className = "chat-message error";
    errorMsg.style.cssText = "background: rgba(255,106,61,0.1); padding: 0.75rem; border-radius: 8px; margin-bottom: 0.5rem;";
    errorMsg.innerHTML = `<p style="margin: 0; color: #FF6A3D;">Error de conexion. Intenta de nuevo.</p>`;
    messagesEl.appendChild(errorMsg);
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Make functions globally available
window.sendTopicQuestion = sendTopicQuestion;
window.askSuggestion = askSuggestion;
window.selectTopicForChat = selectTopicForChat;

// Colombia cities with SVG coordinates (mapped to viewBox 0-400 x 0-500)
const COLOMBIA_POINTS = [
  { name: "Bogota", lat: 4.711, lon: -74.072, svgX: 200, svgY: 250 },
  { name: "Medellin", lat: 6.244, lon: -75.581, svgX: 160, svgY: 190 },
  { name: "Cali", lat: 3.451, lon: -76.532, svgX: 130, svgY: 300 },
  { name: "Barranquilla", lat: 10.968, lon: -74.781, svgX: 195, svgY: 65 },
  { name: "Cartagena", lat: 10.391, lon: -75.479, svgX: 160, svgY: 80 },
  { name: "Bucaramanga", lat: 7.119, lon: -73.119, svgX: 245, svgY: 155 },
  { name: "Pereira", lat: 4.815, lon: -75.694, svgX: 145, svgY: 245 },
  { name: "Manizales", lat: 5.07, lon: -75.513, svgX: 155, svgY: 230 },
  { name: "Santa Marta", lat: 11.241, lon: -74.205, svgX: 210, svgY: 50 },
  { name: "Villavicencio", lat: 4.142, lon: -73.627, svgX: 235, svgY: 270 },
  { name: "Cucuta", lat: 7.894, lon: -72.503, svgX: 280, svgY: 130 },
  { name: "Ibague", lat: 4.438, lon: -75.232, svgX: 170, svgY: 265 },
  { name: "Pasto", lat: 1.214, lon: -77.281, svgX: 110, svgY: 400 },
  { name: "Neiva", lat: 2.927, lon: -75.282, svgX: 170, svgY: 330 },
  { name: "Monteria", lat: 8.757, lon: -75.881, svgX: 130, svgY: 130 }
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

  mockBtn?.addEventListener("click", () => {
    // Fill form fields
    document.getElementById("unified-location").value = "Colombia";
    document.getElementById("unified-topic").value = "Seguridad";
    document.getElementById("unified-candidate").value = "Paloma Valencia";
    document.getElementById("unified-politician").value = "@PalomaValenciaL";
    document.getElementById("unified-days-back").value = "30";
    document.getElementById("unified-forecast-days").value = "14";

    // Generate and render mock data
    const mockData = generatePalomaValenciaMockData();
    resultsSection.style.display = "block";
    renderUnifiedDashboard(mockData);
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

    const startedAt = performance.now();
    submitBtn.disabled = true;
    submitBtn.textContent = "Ejecutando...";
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
      const runtimeMs = performance.now() - startedAt;
      renderUnifiedDashboard({
        mediaData,
        forecastData,
        trendingData,
        campaignData,
        input: { location, topic, candidateName },
        runtimeMs
      });
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (err) {
      console.error(err);
      errorBox.textContent = err.message || "Error al generar el dashboard.";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Ejecutar analisis";
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
    throw new Error(`HTTP ${response.status}: ${text}`);
  }

  const data = await response.json();
  if (data && data.success === false) {
    throw new Error(data.error || "Respuesta sin exito");
  }
  return data;
}

function pickSuccessful(result) {
  if (!result || result.status !== "fulfilled") return null;
  return result.value;
}

function renderUnifiedDashboard({ mediaData, forecastData, trendingData, campaignData, input, runtimeMs }) {
  // Tab 1: Lectura rápida
  renderContextBar(mediaData, input, runtimeMs);
  renderKPIs(mediaData, forecastData);
  renderSparklines(forecastData);
  renderDiagnosis(mediaData, forecastData, input);
  renderDecisionBlock(mediaData, forecastData, input);
  renderTopPatterns(mediaData);
  renderProjectionSummary(forecastData, input);

  // Tab 2: Evidencia
  renderEvidenceTab(mediaData, input);

  // Tab 3: Acciones
  renderActionsTab(campaignData, mediaData, forecastData, input);

  // Tab 4: Vigilancia
  renderVigilanceTab(forecastData, mediaData, input);

  // Tab 5: Geografía
  renderGeoPanel(mediaData, input?.location);

  // Tab 6: Exploración (gráficos)
  renderCharts(mediaData, forecastData);

  // Setup toggles
  setupBriefToggle();
}

function renderDiagnosis(mediaData, forecastData, input) {
  // Card 1: Qué domina la conversación
  const dominaEl = document.getElementById("diagnosis-domina");
  const dominaContextEl = document.getElementById("diagnosis-domina-context");
  if (dominaEl) {
    const topics = mediaData?.topics || [];
    if (topics.length > 0) {
      const topTopic = topics[0];
      dominaEl.textContent = `${topTopic.topic}`;
      if (dominaContextEl) {
        dominaContextEl.textContent = `${topTopic.tweet_count} menciones · ${((topTopic.sentiment?.positive || 0) * 100).toFixed(0)}% favorable`;
      }
    } else {
      dominaEl.textContent = "Sin temas dominantes";
      if (dominaContextEl) dominaContextEl.textContent = "Datos insuficientes para determinar tema principal";
    }
  }

  // Card 2: Cómo se percibe
  const percibeEl = document.getElementById("diagnosis-percibe");
  const percibeContextEl = document.getElementById("diagnosis-percibe-context");
  if (percibeEl) {
    const sentiment = mediaData?.sentiment_overview;
    if (sentiment) {
      const pos = (sentiment.positive || 0) * 100;
      const neg = (sentiment.negative || 0) * 100;
      const net = pos - neg;
      const label = net > 5 ? "Favorable" : net < -5 ? "Critico" : "Neutral";
      percibeEl.textContent = label;
      if (percibeContextEl) {
        percibeContextEl.textContent = `${pos.toFixed(0)}% positivo · ${neg.toFixed(0)}% critico`;
      }
    } else {
      percibeEl.textContent = "Sin datos";
      if (percibeContextEl) percibeContextEl.textContent = "Percepcion no disponible";
    }
  }

  // Card 3: Qué implica
  const implicaEl = document.getElementById("diagnosis-implica");
  const implicaContextEl = document.getElementById("diagnosis-implica-context");
  if (implicaEl) {
    const signals = extractForecastSignals(forecastData);
    const sentiment = extractSentiment(mediaData);
    const implication = buildImplication(signals, sentiment, input?.topic);
    implicaEl.textContent = implication.split(".")[0];
    if (implicaContextEl && implication.includes(".")) {
      implicaContextEl.textContent = implication.split(".").slice(1).join(".").trim() || "Evaluar contexto para acciones";
    }
  }
}

function buildImplication(signals, sentiment, topic) {
  const icce = signals.icce;
  const momentum = signals.momentum;
  const net = parseFloat((sentiment.netLabel || "0").replace("%", ""));

  if (icce == null) return "Sin suficiente información para valorar implicaciones.";

  if (icce >= 60 && net > 0 && momentum > 0) {
    return `Ventana favorable para ${topic || "posicionamiento"}. El clima es receptivo.`;
  }
  if (icce < 45 || net < -5) {
    return `Atención: territorio crítico. Priorizar contención en ${topic || "temas sensibles"}.`;
  }
  if (momentum < -0.02) {
    return `Momentum negativo. Evaluar ajuste de mensaje antes de amplificar.`;
  }
  return `Clima estable. Mantener consistencia y monitorear cambios.`;
}

function renderDecisionBlock(mediaData, forecastData, input) {
  const decisionEl = document.getElementById("action-recommendation");
  const urgencyEl = document.getElementById("action-urgency");
  const horizonEl = document.getElementById("action-horizon");
  const confidenceEl = document.getElementById("action-confidence");
  const alertsEl = document.getElementById("active-alerts");

  if (decisionEl) {
    const signals = extractForecastSignals(forecastData);
    const sentiment = extractSentiment(mediaData);
    const decision = buildDecision(signals, sentiment, input?.topic);
    decisionEl.textContent = decision;

    // Set urgency badge
    if (urgencyEl) {
      const riskLevel = narrativeRiskLabel(signals.icce, signals.momentum, sentiment.netLabel);
      urgencyEl.textContent = riskLevel === "alto" ? "URGENTE" : riskLevel === "medio" ? "ATENCIÓN" : "NORMAL";
      urgencyEl.style.background = riskLevel === "alto" ? "rgba(255,106,61,0.3)" : riskLevel === "medio" ? "rgba(245,184,0,0.3)" : "rgba(66,214,151,0.3)";
      urgencyEl.style.color = riskLevel === "alto" ? "#ffb19a" : riskLevel === "medio" ? "#f5d68a" : "#8ae9bf";
    }

    // Set horizon and confidence
    if (horizonEl) horizonEl.textContent = "Proximas 72h";
    if (confidenceEl) {
      const conf = signals.icce ? (signals.icce > 50 ? "Alta" : signals.icce > 35 ? "Media" : "Baja") : "Media";
      confidenceEl.textContent = conf;
    }
  }

  if (alertsEl) {
    alertsEl.innerHTML = "";
    const alerts = buildQuickAlerts(mediaData, forecastData);
    if (alerts.length === 0) {
      alertsEl.innerHTML = '<li class="alert-item" style="padding: 0.5rem 0; color: #42d697;">Sin alertas criticas</li>';
    } else {
      alerts.forEach((alert) => {
        const li = document.createElement("li");
        li.className = "alert-item";
        li.style.padding = "0.5rem 0";
        li.style.borderBottom = "1px solid rgba(255,255,255,0.05)";
        li.style.color = alert.level === "high" ? "#FF6A3D" : alert.level === "medium" ? "#F5B800" : "#8892B0";
        li.textContent = alert.text;
        alertsEl.appendChild(li);
      });
    }
  }
}

function buildDecision(signals, sentiment, topic) {
  const icce = signals.icce;
  const momentum = signals.momentum;
  const net = parseFloat((sentiment.netLabel || "0").replace("%", ""));

  if (icce == null) return "Recopilar más datos antes de decidir.";

  if (icce >= 60 && net > 0) {
    return `AVANZAR: Amplificar mensaje en ${topic || "temas clave"}. Clima favorable.`;
  }
  if (icce < 40 || net < -10) {
    return `PAUSAR: Contener exposición. Priorizar escucha y ajuste de tono.`;
  }
  if (momentum < -0.02) {
    return `EVALUAR: Momentum negativo. Revisar posicionamiento antes de actuar.`;
  }
  return `MANTENER: Continuar estrategia actual. Monitorear cambios.`;
}

function buildQuickAlerts(mediaData, forecastData) {
  const alerts = [];
  const signals = extractForecastSignals(forecastData);
  const topics = mediaData?.topics || [];

  // Check for high-negative topics
  const riskTopics = topics.filter((t) => (t.sentiment?.negative || 0) > 0.4);
  riskTopics.slice(0, 2).forEach((topic) => {
    alerts.push({
      level: "high",
      text: `${topic.topic}: ${(topic.sentiment.negative * 100).toFixed(0)}% tono crítico`
    });
  });

  // Check momentum
  if (signals.momentum != null && signals.momentum < -0.03) {
    alerts.push({ level: "medium", text: "Momentum negativo sostenido" });
  }

  // Check ICCE
  if (signals.icce != null && signals.icce < 40) {
    alerts.push({ level: "high", text: "Clima narrativo bajo (ICCE < 40)" });
  }

  return alerts.slice(0, 3);
}

function renderTopPatterns(mediaData) {
  const gridEl = document.getElementById("top-findings");
  if (!gridEl) return;

  gridEl.innerHTML = "";
  const patterns = buildTopPatterns(mediaData);

  if (patterns.length === 0) {
    gridEl.innerHTML = '<div class="finding-card" style="background: rgba(255,255,255,0.02); border-radius: 0.5rem; padding: 1rem;">Sin patrones detectados</div>';
    return;
  }

  patterns.forEach((pattern, idx) => {
    const card = document.createElement("div");
    card.className = "finding-card";
    card.style.cssText = "background: rgba(255,255,255,0.02); border-radius: 0.5rem; padding: 1rem; border-left: 3px solid " + (idx === 0 ? "var(--accent)" : idx === 1 ? "#42d697" : "#F5B800");
    card.innerHTML = `<p style="font-size: 0.75rem; color: #6B7280; text-transform: uppercase; margin: 0 0 0.25rem;">${pattern.label}</p><p style="font-size: 0.95rem; color: var(--text); margin: 0;">${pattern.detail}</p>`;
    gridEl.appendChild(card);
  });
}

function buildTopPatterns(mediaData) {
  const patterns = [];
  const topics = mediaData?.topics || [];
  const sentiment = mediaData?.sentiment_overview;

  // Pattern 1: Dominant topic
  if (topics.length > 0) {
    const top = topics[0];
    patterns.push({
      label: "Tema dominante",
      detail: `${top.topic} (${top.tweet_count} menciones)`
    });
  }

  // Pattern 2: Sentiment distribution
  if (sentiment) {
    const pos = (sentiment.positive || 0) * 100;
    const neg = (sentiment.negative || 0) * 100;
    const dominant = pos > neg ? "favorable" : neg > pos ? "crítico" : "equilibrado";
    patterns.push({
      label: "Tono predominante",
      detail: `${dominant} (${pos.toFixed(0)}% pos / ${neg.toFixed(0)}% neg)`
    });
  }

  // Pattern 3: Risk topics
  const riskTopics = topics.filter((t) => (t.sentiment?.negative || 0) > 0.35);
  if (riskTopics.length > 0) {
    patterns.push({
      label: "Temas sensibles",
      detail: riskTopics.map((t) => t.topic).join(", ")
    });
  }

  return patterns.slice(0, 3);
}

function renderProjectionSummary(forecastData, input) {
  const arrowEl = document.getElementById("projection-arrow");
  const deltaEl = document.getElementById("projection-delta");
  const labelEl = document.getElementById("projection-label");
  const contextEl = document.getElementById("projection-context");
  const daysLabelEl = document.getElementById("forecast-days-label");

  const forecastDays = document.getElementById("unified-forecast-days")?.value || 14;
  if (daysLabelEl) daysLabelEl.textContent = forecastDays;

  const summary = buildForecastSummary(forecastData, input?.topic);

  if (!forecastData?.forecast?.icce_pred?.length) {
    if (arrowEl) arrowEl.textContent = "—";
    if (deltaEl) deltaEl.textContent = "Sin datos";
    if (labelEl) labelEl.textContent = "Proyeccion no disponible";
    if (contextEl) contextEl.textContent = "Ejecuta analisis para ver proyeccion";
    return;
  }

  const latest = (forecastData.series?.icce?.[forecastData.series.icce.length - 1] || 0) * 100;
  const projected = (forecastData.forecast.icce_pred[forecastData.forecast.icce_pred.length - 1] || 0) * 100;
  const delta = projected - latest;
  const isUp = delta >= 0;

  if (arrowEl) {
    arrowEl.textContent = isUp ? "↗" : "↘";
    arrowEl.style.color = isUp ? "#42d697" : "#FF6A3D";
  }
  if (deltaEl) {
    deltaEl.textContent = `${isUp ? "+" : ""}${delta.toFixed(1)} pts`;
    deltaEl.style.color = isUp ? "#42d697" : "#FF6A3D";
  }
  if (labelEl) {
    labelEl.textContent = isUp ? "Tendencia al alza" : "Tendencia a la baja";
  }
  if (contextEl) {
    contextEl.textContent = summary.range || `ICCE proyectado: ${projected.toFixed(1)} en ${forecastDays} dias`;
  }
}

function renderContextBar(mediaData, input, runtimeMs) {
  const paramsEl = document.getElementById("context-params");
  const timestampEl = document.getElementById("context-timestamp");
  const runtimeEl = document.getElementById("context-runtime");

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

  if (runtimeEl) {
    if (typeof runtimeMs === "number") {
      runtimeEl.textContent = `Tiempo de proceso: ${(runtimeMs / 1000).toFixed(1)}s`;
    } else {
      runtimeEl.textContent = "Tiempo de proceso: -";
    }
  }

  if (timestampEl) {
    const stamp = mediaData?.metadata?.time_window_to || new Date().toISOString();
    timestampEl.textContent = `Ultima actualizacion: ${formatTimestamp(stamp)}`;
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

  const signals = extractForecastSignals(forecastData);
  if (icceEl) icceEl.textContent = signals.icce != null ? signals.icce.toFixed(1) : "-";
  if (icceNoteEl) icceNoteEl.textContent = signals.icceLabel || "Sin ICCE";

  if (momentumEl) {
    momentumEl.textContent = signals.momentum != null ? signals.momentum.toFixed(3) : "-";
    if (signals.momentum != null) {
      momentumEl.style.color = signals.momentum > 0.01 ? "#42d697" : signals.momentum < -0.01 ? "#FF6A3D" : "#8892B0";
    }
  }
  if (momentumNoteEl) momentumNoteEl.textContent = signals.momentumLabel || "Sin momentum";

  const sentiment = extractSentiment(mediaData);
  if (sentimentEl) {
    sentimentEl.textContent = sentiment.netLabel || "-";
    const netValue = parseFloat((sentiment.netLabel || "0").replace("%", ""));
    if (!Number.isNaN(netValue)) {
      sentimentEl.style.color = netValue > 1 ? "#42d697" : netValue < -1 ? "#FF6A3D" : "#8892B0";
    }
  }
  if (sentimentNoteEl) sentimentNoteEl.textContent = sentiment.detail || "Sin sentimiento";

  if (volumeEl) volumeEl.textContent = mediaData?.metadata?.tweets_analyzed != null
    ? `${mediaData.metadata.tweets_analyzed}`
    : "-";
  if (volumeNoteEl) volumeNoteEl.textContent = mediaData?.metadata?.time_window_to
    ? `Ventana ${formatDate(mediaData.metadata.time_window_from)} - ${formatDate(mediaData.metadata.time_window_to)}`
    : "Ventana no disponible";
}

function renderSparklines(forecastData) {
  const icceCanvas = document.getElementById("kpi-icce-spark");
  const momentumCanvas = document.getElementById("kpi-momentum-spark");
  if (!icceCanvas || !momentumCanvas) return;

  const series = forecastData?.series;
  if (!series?.icce?.length) return;

  const icceValues = series.icce.slice(-7).map((val) => (val || 0) * 100);
  const momentumValues = (series.momentum || []).slice(-7);
  renderSparkline(icceCanvas, icceValues, "#FF6A3D");
  renderSparkline(momentumCanvas, momentumValues, "#42d697");
}

function renderNarrativeBrief(mediaData, forecastData, trendingData, input) {
  const summaryEl = document.getElementById("brief-summary");
  const driversEl = document.getElementById("brief-drivers");
  const risksEl = document.getElementById("brief-risks");
  const forecastEl = document.getElementById("brief-forecast");
  const rangeEl = document.getElementById("brief-forecast-range");

  const overview = mediaData?.summary?.overview || "Sin resumen disponible.";
  if (summaryEl) summaryEl.textContent = overview;

  if (driversEl) {
    driversEl.innerHTML = "";
    const drivers = mediaData?.summary?.key_findings?.slice(0, 3) || buildDriversFromTopics(mediaData);
    fillList(driversEl, drivers, [], "Sin drivers detectados.");
  }

  if (risksEl) {
    risksEl.innerHTML = "";
    const risks = buildRiskSignals(mediaData, forecastData);
    fillList(risksEl, risks, [], "Sin riesgos relevantes.");
  }

  const forecastSummary = buildForecastSummary(forecastData, input?.topic);
  if (forecastEl) forecastEl.textContent = forecastSummary.text;
  if (rangeEl) rangeEl.textContent = forecastSummary.range;

  renderSentimentStack(mediaData);
}

function renderSentimentStack(mediaData) {
  const sentiment = mediaData?.sentiment_overview;
  if (!sentiment) return;

  const pos = sentiment.positive || 0;
  const neu = sentiment.neutral || 0;
  const neg = sentiment.negative || 0;

  // Evidence tab - bar segments
  const posBarEl = document.getElementById("sent-bar-pos");
  const neuBarEl = document.getElementById("sent-bar-neu");
  const negBarEl = document.getElementById("sent-bar-neg");

  if (posBarEl) posBarEl.style.width = `${(pos * 100).toFixed(1)}%`;
  if (neuBarEl) neuBarEl.style.width = `${(neu * 100).toFixed(1)}%`;
  if (negBarEl) negBarEl.style.width = `${(neg * 100).toFixed(1)}%`;

  // Evidence tab - percentage labels
  const posPctEl = document.getElementById("sent-pct-pos");
  const neuPctEl = document.getElementById("sent-pct-neu");
  const negPctEl = document.getElementById("sent-pct-neg");

  if (posPctEl) posPctEl.textContent = `${(pos * 100).toFixed(0)}`;
  if (neuPctEl) neuPctEl.textContent = `${(neu * 100).toFixed(0)}`;
  if (negPctEl) negPctEl.textContent = `${(neg * 100).toFixed(0)}`;
}

function renderActionsList(mediaData, forecastData, input) {
  const actionsEl = document.getElementById("actions-list");
  const explainBtn = document.getElementById("actions-explain");
  if (!actionsEl) return;

  actionsEl.innerHTML = "";
  const actions = buildActionItems(mediaData, forecastData, input?.topic);

  if (!actions.length) {
    actionsEl.innerHTML = '<p class="kpi-meta">Sin acciones sugeridas.</p>';
    return;
  }

  actions.forEach((action) => {
    const row = document.createElement("div");
    row.className = "action-item";

    const label = document.createElement("span");
    label.textContent = action.label;

    const badge = document.createElement("span");
    badge.className = `action-priority priority-${action.priority}`;
    badge.textContent = action.priority.toUpperCase();

    row.appendChild(label);
    row.appendChild(badge);
    actionsEl.appendChild(row);
  });

  if (explainBtn) {
    if (!explainBtn.dataset.bound) {
      explainBtn.dataset.bound = "true";
      explainBtn.addEventListener("click", () => {
        document.querySelector(".methodology-details")?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    }
  }
}

function renderNarrativeMap(mediaData) {
  const summaryEl = document.getElementById("map-summary");
  const findingsEl = document.getElementById("map-findings");

  if (summaryEl) {
    const stats = mediaData?.summary?.key_stats?.slice(0, 2) || [];
    summaryEl.textContent = stats.length ? stats.join(" · ") : "Resumen narrativo no disponible.";
  }

  if (findingsEl) {
    findingsEl.innerHTML = "";
    const findings = mediaData?.summary?.key_findings || [];
    fillList(findingsEl, findings.slice(0, 4), [], "Sin hallazgos.");
  }

  renderTopicsTable(mediaData, "topics-table");
}

function renderCharts(mediaData, forecastData) {
  // Vigilance tab chart
  renderUnifiedChart(forecastData);

  // Exploration tab charts
  renderExploreIcceChart(forecastData);
  renderExploreMomentumChart(forecastData);
  renderSentimentChart(mediaData);
  renderTopicsTable(mediaData, "topics-table");

  const seriesContext = document.getElementById("chart-series-context");
  const signals = extractForecastSignals(forecastData);
  if (seriesContext) {
    seriesContext.textContent = signals.forecastDirection || "Serie historica disponible.";
  }
}

let exploreIcceChart = null;
let exploreMomentumChart = null;

function renderExploreIcceChart(forecastData) {
  const ctx = document.getElementById("explore-icce-chart");
  if (!ctx || !forecastData?.series?.icce) return;

  const labels = forecastData.series.dates.map((date) => formatShortDate(date));
  const values = forecastData.series.icce.map((val) => (val || 0) * 100);

  if (exploreIcceChart) exploreIcceChart.destroy();

  exploreIcceChart = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "ICCE",
        data: values,
        borderColor: "#FF6A3D",
        backgroundColor: "rgba(255, 106, 61, 0.15)",
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: "#F5F7FA" } }
      },
      scales: {
        x: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: {
          ticks: { color: "#8892B0" },
          grid: { color: "rgba(136, 146, 176, 0.15)" },
          min: 0,
          max: 100
        }
      }
    }
  });
}

function renderExploreMomentumChart(forecastData) {
  const ctx = document.getElementById("explore-momentum-chart");
  if (!ctx || !forecastData?.series?.momentum) return;

  const labels = forecastData.series.dates.map((date) => formatShortDate(date));
  const values = forecastData.series.momentum;

  if (exploreMomentumChart) exploreMomentumChart.destroy();

  exploreMomentumChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Momentum",
        data: values,
        backgroundColor: values.map((v) => (v >= 0 ? "rgba(66, 214, 151, 0.7)" : "rgba(255, 106, 61, 0.7)")),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
      }
    }
  });
}

function renderEvidenceTab(mediaData, input) {
  // Sample metadata
  const tweetsEl = document.getElementById("evidence-tweets");
  const windowEl = document.getElementById("evidence-window");
  const locationEl = document.getElementById("evidence-location");

  if (tweetsEl) tweetsEl.textContent = mediaData?.metadata?.tweets_analyzed || "-";
  if (windowEl) {
    const daysBack = document.getElementById("unified-days-back")?.value || 30;
    windowEl.textContent = `${daysBack} días`;
  }
  if (locationEl) locationEl.textContent = input?.location || "-";

  // Sentiment bar (única fuente de verdad)
  renderSentimentStack(mediaData);

  // Topics table
  renderTopicsTable(mediaData, "topics-evidence");

  // Findings
  const findingsEl = document.getElementById("evidence-findings");
  if (findingsEl) {
    findingsEl.innerHTML = "";
    const findings = mediaData?.summary?.key_findings || [];
    fillList(findingsEl, findings.slice(0, 5), [], "Sin hallazgos detectados.");
  }
}

function renderActionsTab(campaignData, mediaData, forecastData, input) {
  // Brief ejecutivo
  const briefEl = document.getElementById("action-brief");
  if (briefEl) {
    const brief = buildExecutiveBrief(campaignData, mediaData, input);
    briefEl.textContent = brief;
  }

  // Oportunidades
  const oppsEl = document.getElementById("action-opportunities");
  if (oppsEl) {
    oppsEl.innerHTML = "";
    const opportunities = buildOpportunities(mediaData, forecastData, input);
    opportunities.forEach((opp) => {
      const li = document.createElement("li");
      li.textContent = opp;
      oppsEl.appendChild(li);
    });
  }

  // Fricciones
  const frictionsEl = document.getElementById("action-frictions");
  if (frictionsEl) {
    frictionsEl.innerHTML = "";
    const frictions = buildFrictions(mediaData);
    frictions.forEach((friction) => {
      const li = document.createElement("li");
      li.textContent = friction;
      frictionsEl.appendChild(li);
    });
  }

  // Acciones internas
  const actionsEl = document.getElementById("action-items");
  if (actionsEl) {
    actionsEl.innerHTML = "";
    const actions = buildInternalActions(campaignData, mediaData, input);
    actions.forEach((action) => {
      const div = document.createElement("div");
      div.className = "action-item";
      div.style.cssText = "display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: 0.85rem 1rem; background: rgba(255,255,255,0.03); border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 0.5rem;";
      const priorityColor = action.priority === "URGENTE" ? "#ffb19a" : action.priority === "ESTRATÉGICO" ? "#f5d68a" : "#8ae9bf";
      const priorityBg = action.priority === "URGENTE" ? "rgba(255,106,61,0.2)" : action.priority === "ESTRATÉGICO" ? "rgba(245,184,0,0.2)" : "rgba(66,214,151,0.2)";
      div.innerHTML = `<span style="color: var(--text); font-weight: 500;">${action.text}</span><span style="font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 999px; text-transform: uppercase; background: ${priorityBg}; color: ${priorityColor};">${action.priority}</span>`;
      actionsEl.appendChild(div);
    });
  }

  // Plan por tema
  const planEl = document.getElementById("action-plan-by-topic");
  if (planEl) {
    planEl.innerHTML = "";
    const plan = buildTopicPlan(campaignData, mediaData);
    plan.forEach((item) => {
      const div = document.createElement("div");
      div.className = "plan-item";
      div.style.cssText = "padding: 1rem; background: rgba(255,255,255,0.02); border-radius: 0.5rem; border-left: 3px solid var(--accent); margin-bottom: 0.75rem;";
      div.innerHTML = `<p style="font-weight: 600; margin: 0 0 0.25rem; color: var(--text);">${item.topic}</p><p style="font-size: 0.9rem; color: #8892B0; margin: 0;">${item.action}</p>`;
      planEl.appendChild(div);
    });
  }

  // Discurso IA
  const speechEl = document.getElementById("action-speech");
  const speechFullEl = document.getElementById("action-speech-full");
  if (speechEl) {
    const speechText = campaignData?.speech?.content || "Discurso no disponible. Requiere análisis con tema específico.";
    const preview = speechText.split(". ").slice(0, 2).join(". ");
    speechEl.textContent = preview ? `${preview}.` : speechText;
    if (speechFullEl) {
      speechFullEl.textContent = speechText;
      speechFullEl.style.display = "none";
    }
  }
}

function buildExecutiveBrief(campaignData, mediaData, input) {
  if (campaignData?.executive_summary?.overview) {
    return campaignData.executive_summary.overview;
  }
  const sentiment = mediaData?.sentiment_overview;
  if (!sentiment) return "Brief no disponible. Ejecutar análisis con tema específico.";

  const pos = (sentiment.positive || 0) * 100;
  const neg = (sentiment.negative || 0) * 100;
  const topic = input?.topic || "la conversación";
  const candidate = input?.candidateName || "el candidato";

  if (pos > neg + 10) {
    return `${candidate} tiene ventana favorable en ${topic}. El tono general es positivo (${pos.toFixed(0)}%). Oportunidad para amplificar mensaje.`;
  }
  if (neg > pos + 10) {
    return `${candidate} enfrenta territorio crítico en ${topic}. Tono negativo (${neg.toFixed(0)}%). Priorizar contención y ajuste de narrativa.`;
  }
  return `${candidate} en territorio neutral en ${topic}. Equilibrio entre tonos positivo y negativo. Mantener consistencia.`;
}

function buildOpportunities(mediaData, forecastData, input) {
  const opportunities = [];
  const signals = extractForecastSignals(forecastData);
  const topics = mediaData?.topics || [];

  // Positive topics
  const posTopics = topics.filter((t) => (t.sentiment?.positive || 0) > 0.5);
  posTopics.slice(0, 2).forEach((topic) => {
    opportunities.push(`${topic.topic}: tono favorable (${((topic.sentiment.positive) * 100).toFixed(0)}%). Amplificar.`);
  });

  // Momentum positive
  if (signals.momentum > 0.01) {
    opportunities.push("Momentum positivo: clima receptivo para nuevos mensajes.");
  }

  // High ICCE
  if (signals.icce > 55) {
    opportunities.push("Clima narrativo favorable para posicionamiento.");
  }

  return opportunities.length ? opportunities : ["Analizar más datos para identificar oportunidades."];
}

function buildFrictions(mediaData) {
  const frictions = [];
  const topics = mediaData?.topics || [];

  // Negative topics
  const negTopics = topics.filter((t) => (t.sentiment?.negative || 0) > 0.35);
  negTopics.slice(0, 3).forEach((topic) => {
    frictions.push(`${topic.topic}: ${((topic.sentiment.negative) * 100).toFixed(0)}% tono crítico. Monitorear.`);
  });

  return frictions.length ? frictions : ["Sin fricciones significativas detectadas."];
}

function buildInternalActions(campaignData, mediaData, input) {
  const actions = [];
  const topics = mediaData?.topics || [];

  // From campaign data
  if (campaignData?.strategic_plan?.actions?.length) {
    campaignData.strategic_plan.actions.slice(0, 2).forEach((action) => {
      actions.push({ priority: "ESTRATÉGICO", text: action.action || action });
    });
  }

  // Risk topics
  const riskTopic = topics.find((t) => (t.sentiment?.negative || 0) > 0.4);
  if (riskTopic) {
    actions.push({ priority: "URGENTE", text: `Preparar Q&A defensivo para ${riskTopic.topic}` });
  }

  // Default actions
  if (actions.length === 0) {
    actions.push({ priority: "RUTINA", text: "Mantener monitoreo de conversación" });
    actions.push({ priority: "RUTINA", text: "Actualizar contenido según hallazgos" });
  }

  return actions.slice(0, 4);
}

function buildTopicPlan(campaignData, mediaData) {
  const plan = [];
  const topics = mediaData?.topics || [];

  topics.slice(0, 3).forEach((topic) => {
    const sentiment = topic.sentiment || {};
    const pos = (sentiment.positive || 0) * 100;
    const neg = (sentiment.negative || 0) * 100;

    let action;
    if (pos > neg + 15) {
      action = "Amplificar mensaje positivo";
    } else if (neg > pos + 15) {
      action = "Contener y preparar respuesta";
    } else {
      action = "Monitorear evolución";
    }

    plan.push({ topic: topic.topic, action });
  });

  return plan.length ? plan : [{ topic: "General", action: "Ejecutar análisis con tema específico" }];
}

function renderVigilanceTab(forecastData, mediaData, input) {
  // Update forecast days label
  const forecastDaysLabel = document.getElementById("vigilance-forecast-days");
  if (forecastDaysLabel) {
    forecastDaysLabel.textContent = document.getElementById("unified-forecast-days")?.value || 14;
  }

  // Scenario: Si sube
  const scenarioUpEl = document.getElementById("scenario-up");
  if (scenarioUpEl) {
    scenarioUpEl.textContent = buildScenarioUp(forecastData, input);
  }

  // Scenario: Si baja
  const scenarioDownEl = document.getElementById("scenario-down");
  if (scenarioDownEl) {
    scenarioDownEl.textContent = buildScenarioDown(forecastData, input);
  }

  // Alertas narrativas
  const alertsEl = document.getElementById("forecast-alerts-list");
  if (alertsEl) {
    alertsEl.innerHTML = "";
    const alerts = buildVigilanceAlerts(forecastData, mediaData);
    alerts.forEach((alert) => {
      const li = document.createElement("li");
      li.style.cssText = "padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.05);";
      li.style.color = alert.level === "high" ? "#FF6A3D" : alert.level === "medium" ? "#F5B800" : "#8892B0";
      li.textContent = alert.text;
      alertsEl.appendChild(li);
    });
  }

  // Señales de riesgo
  const signals = extractForecastSignals(forecastData);
  const riskMomentumEl = document.getElementById("risk-momentum");
  const riskVolatilityEl = document.getElementById("risk-volatility");
  const riskCriticsEl = document.getElementById("risk-critics");
  const riskConfidenceEl = document.getElementById("risk-confidence");

  if (riskMomentumEl) {
    const momLabel = signals.momentum != null
      ? (signals.momentum > 0.01 ? "Positivo" : signals.momentum < -0.01 ? "Negativo" : "Estable")
      : "Sin datos";
    riskMomentumEl.textContent = momLabel;
    riskMomentumEl.style.color = signals.momentum > 0.01 ? "#42d697" : signals.momentum < -0.01 ? "#FF6A3D" : "#8892B0";
  }

  if (riskVolatilityEl) {
    const volatility = forecastData?.series?.icce
      ? calculateVolatility(forecastData.series.icce)
      : null;
    riskVolatilityEl.textContent = volatility != null
      ? (volatility > 0.05 ? "Alta" : volatility > 0.02 ? "Media" : "Baja")
      : "Sin datos";
  }

  if (riskCriticsEl) {
    const negPercent = (mediaData?.sentiment_overview?.negative || 0) * 100;
    riskCriticsEl.textContent = `${negPercent.toFixed(0)}%`;
    riskCriticsEl.style.color = negPercent > 35 ? "#FF6A3D" : negPercent > 20 ? "#F5B800" : "#42d697";
  }

  if (riskConfidenceEl) {
    const conf = signals.icce
      ? (signals.icce > 50 ? "Alta" : signals.icce > 35 ? "Media" : "Baja")
      : "Media";
    riskConfidenceEl.textContent = conf;
  }

  // Render forecast chart in vigilance tab
  renderVigilanceChart(forecastData);
}

function calculateVolatility(values) {
  if (!values || values.length < 2) return null;
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const variance = values.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / values.length;
  return Math.sqrt(variance);
}

function buildScenarioUp(forecastData, input) {
  const signals = extractForecastSignals(forecastData);
  const topic = input?.topic || "la conversación";

  if (!signals.icce) {
    return "Si mejora el clima: oportunidad para posicionamiento proactivo.";
  }

  const projected = forecastData?.forecast?.icce_pred?.slice(-1)[0];
  if (projected && projected > (signals.icce / 100)) {
    return `Si ICCE sube a ${(projected * 100).toFixed(0)}: ventana para amplificar mensaje en ${topic}. Preparar contenido ofensivo.`;
  }

  return `Si mejora el tono en ${topic}: aprovechar para lanzar iniciativas. Clima receptivo.`;
}

function buildScenarioDown(forecastData, input) {
  const signals = extractForecastSignals(forecastData);
  const topic = input?.topic || "la conversación";

  if (!signals.icce) {
    return "Si empeora el clima: activar protocolo de contención.";
  }

  return `Si ICCE baja de 40: pausar exposición en ${topic}. Priorizar escucha y ajuste de narrativa.`;
}

function buildVigilanceAlerts(forecastData, mediaData) {
  const alerts = [];
  const signals = extractForecastSignals(forecastData);

  // ICCE threshold
  alerts.push({
    level: signals.icce && signals.icce < 45 ? "high" : "low",
    text: `ICCE < 45: ${signals.icce ? "ACTIVA" : "Configurada"}`
  });

  // Momentum threshold
  alerts.push({
    level: signals.momentum && signals.momentum < -0.02 ? "medium" : "low",
    text: `Momentum negativo: ${signals.momentum && signals.momentum < -0.02 ? "ACTIVA" : "Configurada"}`
  });

  // Topic risk
  const topics = mediaData?.topics || [];
  const riskTopic = topics.find((t) => (t.sentiment?.negative || 0) > 0.4);
  alerts.push({
    level: riskTopic ? "high" : "low",
    text: `Tema crítico (>40% neg): ${riskTopic ? "ACTIVA - " + riskTopic.topic : "Configurada"}`
  });

  return alerts;
}

function renderVigilanceChart(forecastData) {
  const ctx = document.getElementById("vigilance-chart");
  if (!ctx || !forecastData) return;

  // Reuse the unified chart logic
  renderUnifiedChart(forecastData);
}

function renderBriefsTab(campaignData) {
  const planEl = document.getElementById("brief-plan");
  const speechEl = document.getElementById("brief-speech");
  const speechFullEl = document.getElementById("brief-speech-full");

  if (planEl) {
    if (campaignData?.strategic_plan?.objectives?.length) {
      const objectives = campaignData.strategic_plan.objectives.slice(0, 2).join(" · ");
      const impact = campaignData.strategic_plan.expected_impact || "Impacto no especificado.";
      const actions = (campaignData.strategic_plan.actions || [])
        .slice(0, 2)
        .map((item) => item.action)
        .filter(Boolean)
        .join(" · ");
      planEl.textContent = `Necesidad: ${objectives}. Propuesta: ${actions || "Acciones priorizadas"}. Impacto: ${impact}.`;
    } else {
      planEl.textContent = "Plan estrategico no disponible (tema requerido).";
    }
  }

  if (speechEl) {
    const speechText = campaignData?.speech?.content || "Discurso no disponible.";
    const preview = speechText.split(". ").slice(0, 2).join(". ");
    speechEl.textContent = preview ? `${preview}.` : speechText;
    if (speechFullEl) {
      speechFullEl.textContent = speechText;
      speechFullEl.style.display = "none";
    }
  }
}

function setupBriefToggle() {
  const toggle = document.getElementById("brief-speech-toggle");
  const fullEl = document.getElementById("brief-speech-full");
  if (!toggle || !fullEl) return;

  if (toggle.dataset.bound === "true") return;
  toggle.dataset.bound = "true";
  toggle.addEventListener("click", () => {
    const isHidden = fullEl.style.display === "none" || !fullEl.style.display;
    fullEl.style.display = isHidden ? "block" : "none";
    toggle.textContent = isHidden ? "Ocultar" : "Ver completo";
  });
}
function renderGeoPanel(mediaData, location) {
  const geoListEl = document.getElementById("geo-list");
  const geoConcentrationEl = document.getElementById("geo-concentration");
  const geoDominantEl = document.getElementById("geo-dominant");
  const geoOpportunityEl = document.getElementById("geo-opportunity");
  const geoSentimentGridEl = document.getElementById("geo-sentiment-grid");
  const cityMarkersEl = document.getElementById("city-markers");
  const cityLabelsEl = document.getElementById("city-labels");

  const distribution = buildGeoDistribution(mediaData, location);

  // Render SVG city markers on Colombia map
  if (cityMarkersEl && cityLabelsEl) {
    cityMarkersEl.innerHTML = "";
    cityLabelsEl.innerHTML = "";

    distribution.forEach((point, idx) => {
      // Find SVG coordinates from COLOMBIA_POINTS
      const cityData = COLOMBIA_POINTS.find(c => c.name === point.name);
      if (!cityData) return;

      const size = 6 + point.weight * 25;
      const opacity = 0.5 + point.weight * 0.5;

      // Create circle marker
      const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      circle.setAttribute("cx", cityData.svgX);
      circle.setAttribute("cy", cityData.svgY);
      circle.setAttribute("r", size);
      circle.setAttribute("fill", `rgba(255, 106, 61, ${opacity})`);
      circle.setAttribute("stroke", "rgba(255, 255, 255, 0.3)");
      circle.setAttribute("stroke-width", "1");
      circle.setAttribute("filter", "url(#glow)");
      circle.style.cursor = "pointer";
      circle.setAttribute("data-city", point.name);
      circle.setAttribute("data-weight", (point.weight * 100).toFixed(1));

      // Add hover tooltip
      const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
      title.textContent = `${point.name}: ${(point.weight * 100).toFixed(1)}% de la conversacion`;
      circle.appendChild(title);

      cityMarkersEl.appendChild(circle);

      // Add label for top 5 cities
      if (idx < 5) {
        const text = document.createElementNS("http://www.w3.org/2000/svg", "text");
        text.setAttribute("x", cityData.svgX + size + 4);
        text.setAttribute("y", cityData.svgY + 3);
        text.setAttribute("fill", "#F5F7FA");
        text.setAttribute("font-size", "9");
        text.setAttribute("font-weight", "500");
        text.textContent = point.name;
        cityLabelsEl.appendChild(text);
      }
    });
  }

  // Render city list
  if (geoListEl) {
    geoListEl.innerHTML = "";
    distribution.slice(0, 6).forEach((point, index) => {
      const li = document.createElement("li");
      const barWidth = Math.max(10, point.weight * 100);
      li.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
          <span style="font-weight: 500;">${index + 1}. ${point.name}</span>
          <div style="display: flex; align-items: center; gap: 8px;">
            <div style="width: 60px; height: 6px; background: rgba(255,255,255,0.1); border-radius: 3px; overflow: hidden;">
              <div style="width: ${barWidth}%; height: 100%; background: linear-gradient(90deg, #FF6A3D, #FF8C5A); border-radius: 3px;"></div>
            </div>
            <strong style="min-width: 40px; text-align: right;">${(point.weight * 100).toFixed(1)}%</strong>
          </div>
        </div>`;
      geoListEl.appendChild(li);
    });
  }

  // Geographic context
  const topCity = distribution[0]?.name || location || "Colombia";
  const topPercent = distribution[0] ? (distribution[0].weight * 100).toFixed(0) : "-";
  const secondCity = distribution[1]?.name || "";
  const top3Percent = distribution.slice(0, 3).reduce((sum, p) => sum + p.weight, 0) * 100;

  if (geoConcentrationEl) {
    geoConcentrationEl.textContent = `Top 3 ciudades concentran ${top3Percent.toFixed(0)}% de menciones`;
  }

  if (geoDominantEl) {
    geoDominantEl.textContent = `${topCity} (${topPercent}%)${secondCity ? `, ${secondCity}` : ""}`;
  }

  if (geoOpportunityEl) {
    const lowCities = distribution.slice(4).map(p => p.name).slice(0, 2).join(", ");
    geoOpportunityEl.textContent = lowCities
      ? `Menor presencia en: ${lowCities}`
      : "Cobertura distribuida uniformemente";
  }

  // Sentiment by region
  if (geoSentimentGridEl) {
    geoSentimentGridEl.innerHTML = "";
    const sentiment = mediaData?.sentiment_overview || { positive: 0.33, neutral: 0.34, negative: 0.33 };

    distribution.slice(0, 4).forEach((point) => {
      const variation = (hashString(point.name) % 20 - 10) / 100;
      const regionalPos = Math.max(0, Math.min(1, (sentiment.positive || 0) + variation));
      const regionalNeg = Math.max(0, Math.min(1, (sentiment.negative || 0) - variation));

      const div = document.createElement("div");
      div.className = "geo-sentiment-row";
      div.style.cssText = "display: flex; justify-content: space-between; align-items: center; padding: 0.5rem; background: rgba(255,255,255,0.02); border-radius: 6px;";
      const label = regionalPos > regionalNeg + 0.1 ? "favorable" : regionalNeg > regionalPos + 0.1 ? "critico" : "neutral";
      const color = label === "favorable" ? "#42d697" : label === "critico" ? "#FF6A3D" : "#8892B0";
      const bgColor = label === "favorable" ? "rgba(66,214,151,0.15)" : label === "critico" ? "rgba(255,106,61,0.15)" : "rgba(255,255,255,0.1)";
      div.innerHTML = `<span style="color: var(--text); font-weight: 500;">${point.name}</span><span style="padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: ${bgColor}; color: ${color}; text-transform: capitalize;">${label}</span>`;
      geoSentimentGridEl.appendChild(div);
    });
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
    });
  });
}

function renderSparkline(canvas, values, color) {
  if (!canvas || !values?.length) return;
  const key = canvas.id.includes("icce") ? "icce" : "momentum";
  if (kpiCharts[key]) {
    kpiCharts[key].destroy();
  }

  kpiCharts[key] = new Chart(canvas, {
    type: "line",
    data: {
      labels: values.map((_, idx) => idx + 1),
      datasets: [
        {
          data: values,
          borderColor: color,
          backgroundColor: "rgba(255,255,255,0)",
          tension: 0.35,
          pointRadius: 0,
          borderWidth: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: { display: false },
        y: { display: false }
      }
    }
  });
}

function renderUnifiedChart(forecastData) {
  const ctx = document.getElementById("unified-series-chart");
  if (!ctx || !forecastData) return;

  const { labels, icceValues, forecastValues } = extractSeries(forecastData);
  if (!labels.length) return;

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
          label: "Forecast",
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
        legend: { labels: { color: "#F5F7FA" } }
      },
      scales: {
        x: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
      }
    }
  });
}

function renderMomentumChart(forecastData) {
  const ctx = document.getElementById("momentum-chart");
  if (!ctx || !forecastData?.series?.momentum) return;
  const values = forecastData.series.momentum;
  const labels = forecastData.series.dates.map((date) => formatShortDate(date));

  if (momentumChart) momentumChart.destroy();

  momentumChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Momentum",
          data: values,
          backgroundColor: values.map((v) => (v >= 0 ? "rgba(66, 214, 151, 0.7)" : "rgba(255, 106, 61, 0.7)"))
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: { ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
      }
    }
  });
}

function renderSentimentChart(mediaData) {
  const ctx = document.getElementById("sentiment-chart");
  if (!ctx || !mediaData?.sentiment_overview) return;

  const sentiment = mediaData.sentiment_overview;
  if (sentimentChart) sentimentChart.destroy();

  sentimentChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Tono"],
      datasets: [
        {
          label: "Favorable",
          data: [(sentiment.positive || 0) * 100],
          backgroundColor: "rgba(66, 214, 151, 0.8)"
        },
        {
          label: "Neutral",
          data: [(sentiment.neutral || 0) * 100],
          backgroundColor: "rgba(255, 255, 255, 0.4)"
        },
        {
          label: "Critico",
          data: [(sentiment.negative || 0) * 100],
          backgroundColor: "rgba(255, 106, 61, 0.85)"
        }
      ]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: "#F5F7FA" } } },
      scales: {
        x: { stacked: true, ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } },
        y: { stacked: true, ticks: { color: "#8892B0" }, grid: { color: "rgba(136, 146, 176, 0.15)" } }
      }
    }
  });

  const contextEl = document.getElementById("chart-sentiment-context");
  if (contextEl) {
    contextEl.textContent = `Favorable ${(sentiment.positive * 100).toFixed(0)}% · Neutral ${(sentiment.neutral * 100).toFixed(0)}% · Critico ${(sentiment.negative * 100).toFixed(0)}%`;
  }
}

function renderTopicsTable(mediaData, targetId) {
  const tableEl = document.getElementById(targetId);
  if (!tableEl) return;
  tableEl.innerHTML = "";

  const topics = mediaData?.topics || [];
  if (!topics.length) {
    const empty = document.createElement("p");
    empty.textContent = "No hay temas disponibles.";
    tableEl.appendChild(empty);
    return;
  }

  // Store analysis data for chat
  analysisData = mediaData;

  topics.forEach((topic) => {
    const row = document.createElement("div");
    row.className = "topics-row";
    row.style.cursor = "pointer";
    row.style.transition = "transform 0.15s ease, box-shadow 0.15s ease";

    // Make topic clickable for chat
    row.addEventListener("click", () => {
      selectTopicForChat(topic.topic, topic);
      // Highlight selected row
      document.querySelectorAll(`#${targetId} .topics-row`).forEach(r => {
        r.style.borderLeft = "none";
        r.style.background = "rgba(255, 255, 255, 0.03)";
      });
      row.style.borderLeft = "3px solid var(--accent)";
      row.style.background = "rgba(255, 106, 61, 0.08)";
    });

    row.addEventListener("mouseenter", () => {
      row.style.transform = "translateX(4px)";
      row.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
    });
    row.addEventListener("mouseleave", () => {
      row.style.transform = "translateX(0)";
      row.style.boxShadow = "none";
    });

    const title = document.createElement("div");
    const titleStrong = document.createElement("strong");
    titleStrong.textContent = topic.topic;
    const titleMeta = document.createElement("span");
    titleMeta.style.fontSize = "0.85rem";
    titleMeta.style.color = "#8892B0";
    titleMeta.textContent = `${topic.tweet_count} menciones`;
    title.appendChild(titleStrong);
    title.appendChild(document.createElement("br"));
    title.appendChild(titleMeta);
    row.appendChild(title);

    const risk = document.createElement("div");
    const riskLevel = topic.sentiment?.negative > 0.4 ? "Alto" : topic.sentiment?.negative > 0.25 ? "Medio" : "Bajo";
    const riskColor = riskLevel === "Alto" ? "#FF6A3D" : riskLevel === "Medio" ? "#F5B800" : "#42d697";
    risk.innerHTML = `<span style="padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: ${riskColor}20; color: ${riskColor};">Riesgo ${riskLevel}</span>`;
    row.appendChild(risk);

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

function buildDriversFromTopics(mediaData) {
  const topics = mediaData?.topics || [];
  return topics.slice(0, 3).map((topic) => `${topic.topic} concentra ${topic.tweet_count} menciones`);
}

function buildRiskSignals(mediaData, forecastData) {
  const risks = [];
  const signals = extractForecastSignals(forecastData);
  const topics = mediaData?.topics || [];
  topics.forEach((topic) => {
    if ((topic.sentiment?.negative || 0) > 0.4) {
      risks.push(`⚠️ ${topic.topic} con ${(topic.sentiment.negative * 100).toFixed(0)}% critico`);
    }
  });
  if (signals.momentum != null && signals.momentum < -0.02) {
    risks.push("⚠️ Momentum negativo sostenido");
  }
  if (signals.icce != null && signals.icce < 40) {
    risks.push("⚠️ Clima narrativo bajo");
  }
  return risks;
}

function buildForecastSummary(forecastData, topic) {
  if (!forecastData?.forecast?.icce_pred?.length) {
    return { text: "Sin proyeccion disponible.", range: "" };
  }
  const latest = forecastData.series.icce[forecastData.series.icce.length - 1] || 0;
  const projected = forecastData.forecast.icce_pred[forecastData.forecast.icce_pred.length - 1] || 0;
  const delta = (projected - latest) * 100;
  const text = delta >= 0
    ? `Se espera mejora en ${topic || "la narrativa"} de ${delta.toFixed(1)} pts.`
    : `Se espera caida en ${topic || "la narrativa"} de ${Math.abs(delta).toFixed(1)} pts.`;
  const low = forecastData.forecast.pred_low?.slice(-1)[0];
  const high = forecastData.forecast.pred_high?.slice(-1)[0];
  const range = low != null && high != null
    ? `Rango esperado: ${(low * 100).toFixed(0)}–${(high * 100).toFixed(0)} (confianza media)`
    : "";
  return { text, range };
}

function buildActionItems(mediaData, forecastData, topic) {
  const actions = [];
  const topics = mediaData?.topics || [];
  const riskTopic = topics.find((t) => (t.sentiment?.negative || 0) > 0.4);

  if (riskTopic) {
    actions.push({ label: `MONITOREAR ${riskTopic.topic} por picos criticos`, priority: "high" });
  }

  actions.push({
    label: `VALIDAR claims criticos en ${topic || "temas clave"}`,
    priority: "medium"
  });

  actions.push({
    label: "PREPARAR Q&A interno ante cambios de tono",
    priority: "low"
  });

  return actions.slice(0, 3);
}

function fillList(listEl, primaryItems, secondaryItems, fallback) {
  if (!listEl) return;
  listEl.innerHTML = "";
  const items = [...(primaryItems || []), ...(secondaryItems || [])].filter(Boolean);
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

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return new Date().toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
  }
  return date.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
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
    const icceDescriptor = narrativeStrengthLabel(icceNow);
    return {
      icce: icceNow,
      momentum: momentumNow,
      forecastDirection,
      momentumLabel: momentumLabel(momentumNow),
      icceLabel: `Clima ${icceDescriptor}`
    };
  }

  if (forecastData.icce) {
    const icceNow = forecastData.icce.current_icce;
    const momentumNow = forecastData.momentum?.current_momentum ?? null;
    const icceDescriptor = narrativeStrengthLabel(icceNow);
    return {
      icce: icceNow,
      momentum: momentumNow,
      forecastDirection: forecastData.forecast ? "Forecast disponible" : null,
      momentumLabel: momentumNow != null ? momentumLabel(momentumNow) : null,
      icceLabel: `Clima ${icceDescriptor}`
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
  return `Forecast ${direction} ${Math.abs(delta).toFixed(1)} pts`;
}

function extractSentiment(mediaData) {
  const sentiment = mediaData?.sentiment_overview;
  if (!sentiment) return { netLabel: null, detail: null };
  const net = sentiment.positive - sentiment.negative;
  const netLabel = `${net >= 0 ? "+" : ""}${(net * 100).toFixed(1)}%`;
  const detail = `Positivo ${(sentiment.positive * 100).toFixed(1)}% · Negativo ${(sentiment.negative * 100).toFixed(1)}%`;
  return { netLabel, detail };
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
  if (icce >= 65 && net >= 0) return "Territorio favorable";
  if (icce < 45 && net < 0) return "Territorio critico";
  return "Territorio neutral";
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
  if (icce > 65 && net > 5) {
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

// =====================================================
// MOCK DATA: Paloma Valencia Demo
// =====================================================
function generatePalomaValenciaMockData() {
  const today = new Date();
  const dates = [];
  const icceValues = [];
  const momentumValues = [];

  // Generate 30 days of historical data
  for (let i = 29; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    dates.push(date.toISOString().split("T")[0]);

    // ICCE oscillates around 58-67 with some variation
    const baseIcce = 0.62 + Math.sin(i * 0.3) * 0.05 + (Math.random() - 0.5) * 0.04;
    icceValues.push(Math.max(0.45, Math.min(0.75, baseIcce)));

    // Momentum varies between -0.02 and 0.03
    const baseMomentum = 0.008 + Math.sin(i * 0.5) * 0.015 + (Math.random() - 0.5) * 0.01;
    momentumValues.push(baseMomentum);
  }

  // Generate 14 days of forecast
  const forecastDates = [];
  const forecastIcce = [];
  const forecastLow = [];
  const forecastHigh = [];

  for (let i = 1; i <= 14; i++) {
    const date = new Date(today);
    date.setDate(date.getDate() + i);
    forecastDates.push(date.toISOString().split("T")[0]);

    // Slightly upward trend in forecast
    const projected = icceValues[icceValues.length - 1] + i * 0.003 + (Math.random() - 0.5) * 0.02;
    forecastIcce.push(Math.max(0.5, Math.min(0.8, projected)));
    forecastLow.push(projected - 0.08);
    forecastHigh.push(projected + 0.08);
  }

  const mediaData = {
    metadata: {
      tweets_analyzed: 847,
      time_window_from: dates[0],
      time_window_to: dates[dates.length - 1],
      location: "Colombia",
      candidate: "Paloma Valencia",
      geo_distribution: [
        { name: "Bogotá", weight: 0.32, x: 52, y: 45 },
        { name: "Medellín", weight: 0.18, x: 35, y: 35 },
        { name: "Cali", weight: 0.14, x: 28, y: 55 },
        { name: "Barranquilla", weight: 0.09, x: 45, y: 15 },
        { name: "Cartagena", weight: 0.07, x: 38, y: 18 },
        { name: "Bucaramanga", weight: 0.06, x: 48, y: 32 },
        { name: "Pereira", weight: 0.05, x: 32, y: 48 },
        { name: "Manizales", weight: 0.04, x: 34, y: 46 }
      ]
    },
    sentiment_overview: {
      positive: 0.42,
      neutral: 0.35,
      negative: 0.23
    },
    topics: [
      {
        topic: "Seguridad ciudadana",
        tweet_count: 234,
        sentiment: { positive: 0.48, neutral: 0.32, negative: 0.20 }
      },
      {
        topic: "Política fiscal",
        tweet_count: 187,
        sentiment: { positive: 0.35, neutral: 0.40, negative: 0.25 }
      },
      {
        topic: "Reforma pensional",
        tweet_count: 156,
        sentiment: { positive: 0.28, neutral: 0.35, negative: 0.37 }
      },
      {
        topic: "Gestión Congreso",
        tweet_count: 142,
        sentiment: { positive: 0.52, neutral: 0.30, negative: 0.18 }
      },
      {
        topic: "Oposición al gobierno",
        tweet_count: 128,
        sentiment: { positive: 0.55, neutral: 0.28, negative: 0.17 }
      }
    ],
    summary: {
      overview: "Paloma Valencia mantiene presencia narrativa estable con tono mayoritariamente favorable. Su posicionamiento en seguridad ciudadana genera tracción positiva, mientras reforma pensional presenta fricción moderada que requiere monitoreo.",
      key_findings: [
        "Seguridad ciudadana es el tema de mayor tracción positiva (48% favorable)",
        "Reforma pensional presenta la mayor fricción (37% crítico) - punto de atención",
        "Gestión en Congreso genera percepción positiva consistente",
        "Bogotá y Medellín concentran 50% de la conversación",
        "Momentum positivo en últimos 7 días (+0.012)"
      ],
      key_stats: [
        "847 menciones analizadas",
        "42% tono favorable",
        "ICCE promedio: 62.4"
      ]
    }
  };

  const forecastData = {
    series: {
      dates: dates,
      icce: icceValues,
      momentum: momentumValues
    },
    forecast: {
      dates: forecastDates,
      icce_pred: forecastIcce,
      pred_low: forecastLow,
      pred_high: forecastHigh
    },
    icce: {
      current_icce: icceValues[icceValues.length - 1] * 100,
      trend: "stable_up"
    },
    momentum: {
      current_momentum: momentumValues[momentumValues.length - 1],
      direction: "positive"
    }
  };

  const trendingData = {
    topics: [
      { topic: "Reforma pensional", mentions: 89, trend: "up" },
      { topic: "Seguridad Bogotá", mentions: 67, trend: "stable" },
      { topic: "Debate fiscal", mentions: 54, trend: "up" },
      { topic: "Elecciones 2026", mentions: 45, trend: "up" },
      { topic: "Centro Democrático", mentions: 38, trend: "stable" },
      { topic: "Oposición gobierno", mentions: 32, trend: "down" }
    ]
  };

  const campaignData = {
    executive_summary: {
      overview: "Paloma Valencia tiene una ventana favorable para posicionamiento en seguridad ciudadana. El clima narrativo es receptivo (ICCE 62.4) con momentum positivo. Reforma pensional requiere estrategia de contención por fricción elevada.",
      key_points: [
        "Clima narrativo favorable para amplificar mensaje",
        "Seguridad ciudadana como tema ancla positivo",
        "Reforma pensional como punto de riesgo a gestionar"
      ]
    },
    strategic_plan: {
      objectives: [
        "Consolidar liderazgo narrativo en seguridad ciudadana",
        "Neutralizar fricción en tema pensional con datos concretos"
      ],
      actions: [
        { action: "Amplificar contenido sobre logros en seguridad con casos específicos", priority: "high" },
        { action: "Preparar Q&A defensivo sobre reforma pensional con cifras", priority: "high" },
        { action: "Programar apariciones en medios de Bogotá y Medellín", priority: "medium" },
        { action: "Activar voceros en redes para balance de tono", priority: "medium" }
      ],
      expected_impact: "Incremento proyectado de 5-8 puntos en percepción favorable en próximas 2 semanas"
    },
    speech: {
      title: "Seguridad para todos los colombianos",
      content: "Colombianos y colombianas, hoy quiero hablarles de lo que más nos importa: la seguridad de nuestras familias. En el Congreso hemos trabajado incansablemente para fortalecer las herramientas que nuestras fuerzas del orden necesitan. No es retórica, son hechos: más recursos para la Policía, mejor tecnología para combatir el crimen, y leyes más estrictas contra quienes atentan contra nuestra tranquilidad.\n\nPero la seguridad va más allá de uniformes y patrullas. Es poder caminar tranquilos por nuestras calles, es que nuestros hijos lleguen seguros a casa, es que los comerciantes puedan trabajar sin miedo. Por eso mi compromiso es integral: prevención, acción y justicia.\n\nSé que hay quienes prefieren las excusas. Nosotros preferimos las soluciones. Colombia merece líderes que actúen, no que prometan. Y yo estoy aquí para actuar, con ustedes, por ustedes.\n\nGracias por su confianza. Juntos, vamos a construir el país seguro que merecemos.",
      duration_minutes: 4,
      key_messages: [
        "Seguridad como prioridad demostrada con hechos",
        "Enfoque integral: prevención, acción, justicia",
        "Liderazgo de acción vs. retórica"
      ]
    }
  };

  return {
    mediaData,
    forecastData,
    trendingData,
    campaignData,
    input: {
      location: "Colombia",
      topic: "Seguridad",
      candidateName: "Paloma Valencia"
    },
    runtimeMs: 2847
  };
}
