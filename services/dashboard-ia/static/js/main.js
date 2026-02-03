// static/js/main.js

let currentMode = null;
let lastResponse = null;
let mainChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  currentMode = body.dataset.mode || "media";

  const form = document.getElementById("analysis-form");
  const submitBtn = document.getElementById("submit-btn");
  const resultsSection = document.getElementById("results-section");
  const errorBox = document.getElementById("form-error");

  if (!form) return;

  setupTabs();
  
  // Initialize first tab styles
  setTimeout(() => {
    const firstTab = document.querySelector(".tab.active");
    if (firstTab) {
      firstTab.style.borderBottom = "2px solid var(--accent)";
      firstTab.style.color = "var(--accent)";
    }
  }, 100);

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.style.display = "none";
    errorBox.textContent = "";

    const formData = new FormData(form);

    submitBtn.disabled = true;
    submitBtn.textContent = "Analizando...";

    try {
      let payload;
      let url;
      if (currentMode === "media") {
        url = (window.API_CONFIG?.apiUrl("/api/media/analyze")) || "/api/media/analyze";
        payload = {
          location: formData.get("location"),
          topic: emptyToNull(formData.get("topic")),
          candidate_name: emptyToNull(formData.get("candidate_name")),
          politician: emptyToNull(formData.get("politician")),
          max_tweets: Number(formData.get("max_tweets") || 15),
          time_window_days: Number(formData.get("time_window_days") || 7),
          language: "es",
        };
      } else {
        url = (window.API_CONFIG?.apiUrl("/api/campaign/analyze")) || "/api/campaign/analyze";
        payload = {
          location: formData.get("location"),
          theme: formData.get("theme"),
          candidate_name: emptyToNull(formData.get("candidate_name")),
          politician: emptyToNull(formData.get("politician")),
          max_tweets: Number(formData.get("max_tweets") || 120),
          language: "es",
        };
      }

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Error HTTP ${res.status}: ${text}`);
      }

      const data = await res.json();
      if (!data.success) {
        throw new Error(data.error || "Error desconocido en el análisis");
      }

      lastResponse = data;
      resultsSection.style.display = "block";

      if (currentMode === "media") {
        renderMediaResults(data);
      } else {
        renderCampaignResults(data);
      }
    } catch (err) {
      console.error(err);
      errorBox.textContent = err.message || "Error al procesar el análisis.";
      errorBox.style.display = "block";
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Generar análisis";
    }
  });

  if (currentMode === "campaign") {
    const copyBtn = document.getElementById("copy-speech-btn");
    const copyStatus = document.getElementById("copy-speech-status");
    if (copyBtn) {
      copyBtn.addEventListener("click", async () => {
        const textarea = document.getElementById("speech-content");
        if (!textarea || !textarea.value) return;

        try {
          await navigator.clipboard.writeText(textarea.value);
          copyStatus.textContent = "Copiado ✔";
          setTimeout(() => (copyStatus.textContent = ""), 2000);
        } catch {
          copyStatus.textContent = "No se pudo copiar";
          setTimeout(() => (copyStatus.textContent = ""), 2000);
        }
      });
    }
  }
});

function emptyToNull(value) {
  if (value == null) return null;
  const trimmed = String(value).trim();
  return trimmed === "" ? null : trimmed;
}

// Helper functions for topic rendering
function getTopicEmoji(topic) {
  const emojiMap = {
    'Seguridad': '🔒',
    'Salud': '🏥',
    'Educación': '📚',
    'Infraestructura': '🏗️',
    'Alimentación': '🍽️',
    'Gobernanza': '⚖️',
    'Igualdad': '⚖️',
    'Paz': '🕊️',
    'Economía': '💰',
    'Empleo': '💼',
    'Medio Ambiente': '🌱'
  };
  return emojiMap[topic] || '📊';
}

function getTopicInsight(topic) {
  const insightMap = {
    'Seguridad': '¡Tu seguridad es lo primero!',
    'Salud': 'Salud para todos',
    'Educación': 'Educación de calidad',
    'Infraestructura': 'Infraestructura que conecta',
    'Alimentación': 'Alimentación para todos',
    'Gobernanza': 'Gobernanza transparente',
    'Igualdad': 'Igualdad de oportunidades',
    'Paz': 'Construyendo paz',
    'Economía': 'Economía para el desarrollo',
    'Empleo': 'Empleo digno',
    'Medio Ambiente': 'Cuidando nuestro planeta'
  };
  return insightMap[topic] || '';
}

function setupTabs() {
  const tabs = document.querySelectorAll(".tab");
  const contents = document.querySelectorAll(".tab-content");
  if (!tabs.length) return;

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      // Update tab styles
      tabs.forEach((t) => {
        t.classList.remove("active");
        t.style.borderBottom = "2px solid transparent";
        t.style.color = "var(--muted)";
      });
      tab.classList.add("active");
      tab.style.borderBottom = "2px solid var(--accent)";
      tab.style.color = "var(--accent)";

      // Update content visibility
      contents.forEach((c) => {
        const isActive = c.id === `tab-${target}`;
        c.style.display = isActive ? "block" : "none";
        c.classList.toggle("active", isActive);
      });

      if (target === "charts" || target === "chart") {
        if (lastResponse) {
          if (currentMode === "media") renderMediaChart(lastResponse);
          else renderCampaignChart(lastResponse);
        }
      }
    });
  });
}

function renderMediaResults(data) {
  const overviewEl = document.getElementById("summary-overview");
  const statsEl = document.getElementById("summary-stats");
  const findingsEl = document.getElementById("summary-findings");
  const topicsContainer = document.getElementById("topics-container");

  if (!data.summary || !data.metadata) return;

  overviewEl.textContent = data.summary.overview || "";

  statsEl.innerHTML = "";
  (data.summary.key_stats || []).forEach((s) => {
    const li = document.createElement("li");
    li.textContent = s;
    statsEl.appendChild(li);
  });

  findingsEl.innerHTML = "";
  (data.summary.key_findings || []).forEach((f) => {
    const li = document.createElement("li");
    li.textContent = f;
    findingsEl.appendChild(li);
  });

  topicsContainer.innerHTML = "";
  (data.topics || []).forEach((topic) => {
    const card = document.createElement("div");
    card.style.marginBottom = "0.75rem";

    const title = document.createElement("strong");
    title.textContent = `${topic.topic} (${topic.tweet_count} mensajes)`;
    card.appendChild(title);

    // Temperatura narrativa en lugar de sentimiento técnico
    const narrative = document.createElement("div");
    narrative.className = "muted";
    narrative.innerHTML = `
      Narrativa favorable: ${(topic.sentiment.positive * 100).toFixed(1)}% ·
      Narrativa neutra: ${(topic.sentiment.neutral * 100).toFixed(1)}% ·
      Narrativa crítica: ${(topic.sentiment.negative * 100).toFixed(1)}%
    `;
    card.appendChild(narrative);

    topicsContainer.appendChild(card);
  });

  renderMediaChart(data);
}

function renderMediaChart(data) {
  const ctx = document.getElementById("main-chart");
  if (!ctx) return;

  const chartDataCfg = data.chart_data?.by_topic_sentiment;
  if (!chartDataCfg) return;

  if (mainChartInstance) {
    mainChartInstance.destroy();
  }

      // Ajustar etiquetas de la leyenda para temperatura narrativa
      if (chartDataCfg?.data?.datasets) {
        chartDataCfg.data.datasets.forEach((ds) => {
          if (ds.label === "Positivo") ds.label = "Narrativa favorable";
          if (ds.label === "Negativo") ds.label = "Narrativa crítica";
          if (ds.label === "Neutral") ds.label = "Narrativa neutra";
        });
      }

      mainChartInstance = new Chart(ctx, chartDataCfg);
}

function renderCampaignResults(data) {
  const overviewEl = document.getElementById("campaign-overview");
  const findingsEl = document.getElementById("campaign-findings");
  const recsEl = document.getElementById("campaign-recommendations");
  const topicsContainer = document.getElementById("campaign-topics-container");
  const planContainer = document.getElementById("campaign-plan-container");
  const speechTitle = document.getElementById("speech-title");
  const speechKeypoints = document.getElementById("speech-keypoints");
  const speechMeta = document.getElementById("speech-meta");
  const speechContent = document.getElementById("speech-content");

  // Render Executive Summary
  if (data.executive_summary) {
    if (overviewEl) {
      overviewEl.textContent = data.executive_summary.overview || "";
    }

    // Show findings section if there are findings
    if (data.executive_summary.key_findings && data.executive_summary.key_findings.length > 0) {
      const findingsSection = document.getElementById("campaign-findings-section");
      if (findingsSection) findingsSection.style.display = "block";
      
      findingsEl.innerHTML = "";
      data.executive_summary.key_findings.forEach((f) => {
        const li = document.createElement("li");
        li.textContent = f;
        findingsEl.appendChild(li);
      });
    }

    // Show recommendations section if there are recommendations
    if (data.executive_summary.recommendations && data.executive_summary.recommendations.length > 0) {
      const recsSection = document.getElementById("campaign-recommendations-section");
      if (recsSection) recsSection.style.display = "block";
      
      recsEl.innerHTML = "";
      data.executive_summary.recommendations.forEach((r) => {
        const li = document.createElement("li");
        li.textContent = r;
        recsEl.appendChild(li);
      });
    }
  }

  // Render Data Analysis (Topics)
  topicsContainer.innerHTML = "";
  (data.topic_analyses || data.topics || []).forEach((topic) => {
    const topicCard = document.createElement("div");
    topicCard.style.cssText = "background: var(--panel-alt); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem;";

    // Topic header with emoji
    const topicEmoji = getTopicEmoji(topic.topic);
    const header = document.createElement("div");
    header.style.cssText = "margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);";
    
    const title = document.createElement("strong");
    title.style.cssText = "font-size: 1.1rem; color: var(--text); display: block; margin-bottom: 0.5rem;";
    title.textContent = `${topic.topic} (${topic.tweet_count} tweets, Temperatura narrativa: favorable ${Math.round(topic.sentiment.positive * topic.tweet_count)}, crítica ${Math.round(topic.sentiment.negative * topic.tweet_count)}, neutra ${Math.round(topic.sentiment.neutral * topic.tweet_count)}):`;
    header.appendChild(title);

    // Emoji and key insight
    if (topicEmoji) {
      const emojiDiv = document.createElement("div");
      emojiDiv.style.cssText = "font-size: 1.2rem; margin-top: 0.5rem;";
      emojiDiv.textContent = `${topicEmoji} ${getTopicInsight(topic.topic)}`;
      header.appendChild(emojiDiv);
    }
    
    topicCard.appendChild(header);

    // Sentiment breakdown
    const sentimentDiv = document.createElement("div");
    sentimentDiv.style.cssText = "color: var(--muted); font-size: 0.9rem; margin-bottom: 1rem;";
    const posPct = (topic.sentiment.positive * 100).toFixed(1);
    const negPct = (topic.sentiment.negative * 100).toFixed(1);
    const neuPct = (topic.sentiment.neutral * 100).toFixed(1);
    sentimentDiv.innerHTML = `Narrativa favorable ${posPct}%, crítica ${negPct}%, neutra ${neuPct}% ${parseFloat(negPct) > 50 ? `(${negPct}% crítica)` : ''}`;
    topicCard.appendChild(sentimentDiv);

    // Sample tweets if available
    if (topic.sample_tweets && topic.sample_tweets.length > 0) {
      topic.sample_tweets.slice(0, 3).forEach((tweet) => {
        const tweetDiv = document.createElement("div");
        tweetDiv.style.cssText = "margin-bottom: 0.75rem; padding: 0.75rem; background: var(--panel); border-radius: 8px; border-left: 3px solid var(--border);";
        
        const tweetLink = document.createElement("a");
        tweetLink.href = tweet.url || "#";
        tweetLink.target = "_blank";
        tweetLink.style.cssText = "color: var(--muted); font-size: 0.85rem; text-decoration: none; display: block; margin-bottom: 0.25rem;";
        tweetLink.textContent = tweet.url || "";
        tweetDiv.appendChild(tweetLink);

        const tweetText = document.createElement("div");
        tweetText.style.cssText = "color: var(--text); font-size: 0.9rem; line-height: 1.5;";
        tweetText.textContent = `- "${tweet.text || tweet.content || ''}"`;
        tweetDiv.appendChild(tweetText);

        const sentimentBadge = document.createElement("span");
        sentimentBadge.style.cssText = "display: inline-block; margin-top: 0.5rem; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem; background: var(--panel-alt); color: var(--muted);";
        sentimentBadge.textContent = tweet.sentiment === 'positive' ? 'Narrativa favorable' : tweet.sentiment === 'negative' ? 'Narrativa crítica' : 'Narrativa neutra';
        tweetDiv.appendChild(sentimentBadge);

        topicCard.appendChild(tweetDiv);
      });
    }

    topicsContainer.appendChild(topicCard);
  });

  // Render Strategic Plan
  planContainer.innerHTML = "";
  if (data.strategic_plan && Array.isArray(data.strategic_plan.objectives)) {
    data.strategic_plan.objectives.forEach((obj) => {
      const planCard = document.createElement("div");
      planCard.style.cssText = "background: var(--panel-alt); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; margin-bottom: 1.5rem;";

      // Topic title
      const title = document.createElement("h4");
      title.style.cssText = "font-size: 1.3rem; font-weight: 700; margin-bottom: 1.5rem; color: var(--text); border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem;";
      title.textContent = obj.name || obj.topic || "Objetivo estratégico";
      planCard.appendChild(title);

      // Necesidad section
      if (obj.need || obj.description) {
        const necesidadDiv = document.createElement("div");
        necesidadDiv.style.cssText = "margin-bottom: 1.5rem;";
        
        const necesidadTitle = document.createElement("strong");
        necesidadTitle.style.cssText = "display: block; font-size: 1rem; color: var(--accent); margin-bottom: 0.5rem;";
        necesidadTitle.textContent = "Necesidad:";
        necesidadDiv.appendChild(necesidadTitle);

        const necesidadText = document.createElement("div");
        necesidadText.style.cssText = "color: var(--muted); line-height: 1.7; font-size: 0.95rem;";
        necesidadText.textContent = obj.need || obj.description || "";
        necesidadDiv.appendChild(necesidadText);

        planCard.appendChild(necesidadDiv);
      }

      // Sentimientos section (from topic data)
      const topicData = (data.topic_analyses || data.topics || []).find(t => 
        t.topic === obj.name || t.topic === obj.topic
      );
      if (topicData) {
        const sentimientosDiv = document.createElement("div");
        sentimientosDiv.style.cssText = "margin-bottom: 1.5rem;";
        
        const sentimientosTitle = document.createElement("strong");
        sentimientosTitle.style.cssText = "display: block; font-size: 1rem; color: var(--accent); margin-bottom: 0.5rem;";
        sentimientosTitle.textContent = "Temperatura narrativa:";
        sentimientosDiv.appendChild(sentimientosTitle);

        const sentimientosText = document.createElement("div");
        sentimientosText.style.cssText = "color: var(--muted); line-height: 1.7; font-size: 0.95rem;";
        const pos = Math.round(topicData.sentiment.positive * topicData.tweet_count);
        const neg = Math.round(topicData.sentiment.negative * topicData.tweet_count);
        const neu = Math.round(topicData.sentiment.neutral * topicData.tweet_count);
        const posPct = (topicData.sentiment.positive * 100).toFixed(1);
        const negPct = (topicData.sentiment.negative * 100).toFixed(1);
        const neuPct = (topicData.sentiment.neutral * 100).toFixed(1);
        sentimientosText.textContent = `Narrativa favorable ${pos} (${posPct}%), crítica ${neg} (${negPct}%), neutra ${neu} (${neuPct}%) ${parseFloat(negPct) > 50 ? `(${negPct}% crítica)` : ''}`;
        sentimientosDiv.appendChild(sentimientosText);

        planCard.appendChild(sentimientosDiv);
      }

      // Propuesta section
      if (obj.proposal || obj.actions) {
        const propuestaDiv = document.createElement("div");
        propuestaDiv.style.cssText = "margin-bottom: 1.5rem;";
        
        const propuestaTitle = document.createElement("strong");
        propuestaTitle.style.cssText = "display: block; font-size: 1rem; color: var(--accent); margin-bottom: 0.5rem;";
        propuestaTitle.textContent = "Propuesta:";
        propuestaDiv.appendChild(propuestaTitle);

        if (obj.proposal) {
          const propuestaText = document.createElement("div");
          propuestaText.style.cssText = "color: var(--muted); line-height: 1.7; font-size: 0.95rem;";
          propuestaText.textContent = obj.proposal;
          propuestaDiv.appendChild(propuestaText);
        } else if (Array.isArray(obj.actions) && obj.actions.length > 0) {
          const propuestaList = document.createElement("ul");
          propuestaList.style.cssText = "color: var(--muted); line-height: 1.7; font-size: 0.95rem; padding-left: 1.5rem; margin: 0;";
          obj.actions.forEach((act) => {
            const li = document.createElement("li");
            li.style.cssText = "margin-bottom: 0.5rem;";
            li.innerHTML = `<span style="background: var(--accent); color: white; padding: 0.2rem 0.5rem; border-radius: 4px; font-size: 0.75rem; margin-right: 0.5rem;">${act.priority || 'Alta'}</span>${act.description}`;
            propuestaList.appendChild(li);
          });
          propuestaDiv.appendChild(propuestaList);
        }

        planCard.appendChild(propuestaDiv);
      }

      // Impacto section
      if (obj.impact || obj.expected_outcome) {
        const impactoDiv = document.createElement("div");
        
        const impactoTitle = document.createElement("strong");
        impactoTitle.style.cssText = "display: block; font-size: 1rem; color: var(--accent); margin-bottom: 0.5rem;";
        impactoTitle.textContent = "Impacto:";
        impactoDiv.appendChild(impactoTitle);

        const impactoText = document.createElement("div");
        impactoText.style.cssText = "color: var(--muted); line-height: 1.7; font-size: 0.95rem;";
        impactoText.textContent = obj.impact || obj.expected_outcome || "";
        impactoDiv.appendChild(impactoText);

        planCard.appendChild(impactoDiv);
      }

      planContainer.appendChild(planCard);
    });
  }

  // Render Speech
  if (data.speech) {
    const speechTitleContainer = document.getElementById("speech-title-container");
    const speechKeypointsContainer = document.getElementById("speech-keypoints-container");
    
    if (data.speech.title) {
      if (speechTitleContainer) speechTitleContainer.style.display = "block";
      if (speechTitle) speechTitle.textContent = data.speech.title;
    }

    if (data.speech.key_points && data.speech.key_points.length > 0) {
      if (speechKeypointsContainer) speechKeypointsContainer.style.display = "block";
      speechKeypoints.innerHTML = "";
      data.speech.key_points.forEach((kp) => {
        const li = document.createElement("li");
        li.textContent = kp;
        speechKeypoints.appendChild(li);
      });
    }

    const metaParts = [];
    if (data.speech.duration_minutes) {
      metaParts.push(`Duración aprox.: ${data.speech.duration_minutes} min`);
    }
    if (data.speech.trending_topic) {
      metaParts.push(`Incorpora tema tendencia: ${data.speech.trending_topic}`);
    }
    if (metaParts.length > 0) {
      if (speechMeta) {
        speechMeta.style.display = "block";
        speechMeta.textContent = metaParts.join(" · ");
      }
    }

    if (speechContent) {
      speechContent.value = data.speech.content || "";
    }
  }

  renderCampaignChart(data);
}

function renderCampaignChart(data) {
  const ctx = document.getElementById("main-chart");
  if (!ctx) return;

  const chartDataCfg = data.chart_data?.by_topic_sentiment;
  if (!chartDataCfg) return;

  if (mainChartInstance) {
    mainChartInstance.destroy();
  }

  mainChartInstance = new Chart(ctx, chartDataCfg);
}

// ====================
// MOCKUP DATA FOR TESTING
// ====================
function generateMediaMockupData() {
  return {
    success: true,
    summary: {
      overview: "Un análisis de tweets recientes en Bogotá sobre el tema de Seguridad revela preocupaciones ciudadanas significativas. Se analizaron aproximadamente 15 tweets en español, excluyendo retweets, relacionados con temas de seguridad ciudadana, delincuencia y políticas públicas de seguridad. El análisis muestra un panorama mixto donde predominan las preocupaciones sobre seguridad en barrios específicos, aunque también se observan menciones positivas hacia operativos policiales recientes.",
      key_stats: [
        "15 tweets analizados en los últimos 7 días",
        "Distribución de sentimiento: 33% positivo, 40% negativo, 27% neutro",
        "Tema principal identificado: Seguridad ciudadana",
        "Ubicación geográfica: Bogotá, Colombia"
      ],
      key_findings: [
        "La mayoría de los tweets muestran preocupación por la seguridad en barrios específicos de Bogotá",
        "Se identifican menciones frecuentes a la necesidad de mayor presencia policial en zonas críticas",
        "Los ciudadanos expresan frustración con la respuesta de las autoridades ante incidentes de seguridad",
        "Existe un sentimiento positivo hacia operativos policiales recientes en algunas zonas",
        "Los temas más mencionados incluyen robos, asaltos y necesidad de iluminación pública"
      ]
    },
    sentiment_overview: {
      positive: 0.33,
      negative: 0.40,
      neutral: 0.27,
      total_tweets: 15
    },
    topics: [
      {
        topic: "Seguridad",
        tweet_count: 15,
        sentiment: {
          positive: 0.33,
          negative: 0.40,
          neutral: 0.27
        }
      }
    ],
    peaks: [],
    chart_data: {
      by_topic_sentiment: {
        type: "bar",
        data: {
          labels: ["Seguridad"],
          datasets: [
            {
              label: "Positivo",
              data: [5],
              backgroundColor: "rgba(66, 214, 151, 0.8)"
            },
            {
              label: "Neutral",
              data: [4],
              backgroundColor: "rgba(136, 146, 176, 0.8)"
            },
            {
              label: "Negativo",
              data: [6],
              backgroundColor: "rgba(255, 107, 129, 0.8)"
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              position: "top"
            },
            title: {
              display: true,
              text: "Sentimiento por tema"
            }
          },
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      }
    },
    metadata: {
      tweets_analyzed: 15,
      location: "Bogotá",
      topic: "Seguridad",
      time_window_from: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      time_window_to: new Date().toISOString(),
      trending_topic: null,
      raw_query: "Bogotá AND Seguridad"
    }
  };
}

function generateMockupData() {
  return {
    success: true,
    executive_summary: {
      overview: "Un análisis de tweets recientes en Cartagena revela preocupaciones ciudadanas alineadas con conceptos clave del Plan Nacional de Desarrollo (PND 2022-2026). Se recolectaron y clasificaron aproximadamente 94 tweets en español (excluyendo retweets), relacionados con temas como seguridad, alimentación, infraestructura, gobernanza, igualdad, paz, economía, medio ambiente, educación y salud.",
      key_findings: [
        "La mayoría de los tweets muestran un tono mixto, con predominio de neutral (24.5%), seguido de negativo (42.6%) y positivo (33.0%).",
        "Los temas más críticos incluyen gobernanza y transparencia (9 menciones negativas), mientras que salud destaca por positividad (5 menciones positivas).",
        "Esto sugiere oportunidades para campañas enfocadas en soluciones prácticas."
      ],
      recommendations: [
        "Priorizar temas críticos en la estrategia de campaña, especialmente gobernanza y transparencia.",
        "Enfocarse en soluciones prácticas para temas con sentimiento negativo predominante.",
        "Aprovechar el sentimiento positivo en salud para construir narrativas exitosas."
      ]
    },
    topic_analyses: [
      {
        topic: "Seguridad",
        tweet_count: 15,
        sentiment: {
          positive: 0.467,
          negative: 0.267,
          neutral: 0.267
        },
        sample_tweets: [
          {
            text: "Operativos intensivos del DATT mejoran seguridad vial en carril exclusivo de Transcaribe",
            url: "https://t.co/a3VRh1SaJn",
            sentiment: "neutral"
          },
          {
            text: "El director de la Policía, general Carlos Triana, informó la captura en Cartagena de Javier Fernández Morales, alias 'Choki', ciudadano español requerido por el delito de abuso sexual de un menor de 16 años.",
            url: "https://t.co/uJ71rrgLs6",
            sentiment: "positive"
          },
          {
            text: "Más de 100 motocicletas fueron inmovilizadas por invadir carril exclusivo de Transcaribe en Cartagena",
            url: "https://t.co/NOSXyXVDLn",
            sentiment: "neutral"
          }
        ]
      },
      {
        topic: "Alimentación",
        tweet_count: 5,
        sentiment: {
          positive: 0.2,
          negative: 0.6,
          neutral: 0.2
        },
        sample_tweets: [
          {
            text: "La situación de alimentación en Cartagena es crítica. Necesitamos mejores políticas para garantizar que ningún niño pase hambre.",
            url: "https://t.co/example1",
            sentiment: "negative"
          },
          {
            text: "El gobierno debe priorizar la alimentación de las familias más vulnerables en Cartagena",
            url: "https://t.co/example2",
            sentiment: "negative"
          }
        ]
      },
      {
        topic: "Infraestructura",
        tweet_count: 10,
        sentiment: {
          positive: 0.5,
          negative: 0.3,
          neutral: 0.2
        },
        sample_tweets: [
          {
            text: "Cartagena impulsa la movilidad empresarial con nuevas vías de conexión",
            url: "https://t.co/infra1",
            sentiment: "positive"
          },
          {
            text: "Hace 18 años la ley ordenó que Cartagena adopte mejores sistemas de transporte",
            url: "https://t.co/infra2",
            sentiment: "neutral"
          }
        ]
      },
      {
        topic: "Gobernanza y Transparencia",
        tweet_count: 9,
        sentiment: {
          positive: 0.0,
          negative: 1.0,
          neutral: 0.0
        },
        sample_tweets: [
          {
            text: "Aquí se revela quien es el contratista de @distris...",
            url: "https://t.co/gobernanza1",
            sentiment: "negative"
          },
          {
            text: "@JavierC87190538 @berniemoreno José Justiniano Moreno es el contratista principal",
            url: "https://t.co/gobernanza2",
            sentiment: "negative"
          }
        ]
      }
    ],
    strategic_plan: {
      objectives: [
        {
          name: "Seguridad",
          topic: "Seguridad",
          need: "Los votantes de Cartagena expresan preocupaciones sobre seguridad. 🔒 ¡Tu seguridad es lo primero!",
          proposal: "Implementar un plan integral de seguridad ciudadana en Cartagena, incluyendo más policía comunitaria, cámaras de vigilancia y programas de prevención del delito.",
          impact: "Reducción del 30% en índices de criminalidad y mayor sensación de seguridad ciudadana"
        },
        {
          name: "Alimentación",
          topic: "Alimentación",
          need: "Los votantes de Cartagena están preocupados por la alimentación. La situación de 'cartagena' (alimentación OR hambr...); Necesitamos mejores políticas para 'cartagena' (al...); El gobierno debe priorizar 'cartagena' (alimentaci...",
          proposal: "Crear programas de seguridad alimentaria en Cartagena con apoyo a productores locales y comedores comunitarios.",
          impact: "Reducción del 25% en desnutrición infantil y fortalecimiento de la economía local"
        },
        {
          name: "Infraestructura",
          topic: "Infraestructura",
          need: "Los votantes de Cartagena están preocupados por infraestructura. Cartagena impulsa la movilidad empresarial con la ...; Hace 18 años la ley ordenó que Cartagena adopta...; Las ciudades capitales lideran la transformaci...",
          proposal: "Mejorar la infraestructura vial y de transporte en Cartagena con nuevas carreteras, puentes y sistemas de movilidad sostenible.",
          impact: "Reducción del 40% en tiempos de desplazamiento y mayor conectividad regional"
        },
        {
          name: "Gobernanza y Transparencia",
          topic: "Gobernanza y Transparencia",
          need: "Los votantes de Cartagena expresan preocupaciones sobre gobernanza y transparencia. Aquí se revela quien es el contratista de @distris...; @JavierC87190538 @berniemoreno José Justiniano Mor...; @Joaquin162025 @berniemoreno José Justiniano Moren...",
          proposal: "Fortalecer la transparencia y participación ciudadana en Cartagena con portales de información pública y organismos de veeduría ciudadana.",
          impact: "Aumento del 50% en la confianza ciudadana y reducción de la corrupción"
        }
      ]
    },
    speech: {
      title: "Discurso para Cartagena",
      content: `Queridos ciudadanos de Cartagena, soy Ariel, un candidato comprometido con nuestra comunidad.

Respecto a seguridad: La seguridad en Cartagena es nuestra prioridad. Trabajaremos con la comunidad para crear espacios seguros donde nuestras familias puedan vivir en paz.

Respecto a alimentación: Ningún niño en Cartagena debe irse a la cama con hambre. Garantizaremos alimentación nutritiva para todas las familias.

Respecto a infraestructura: Cartagena merece carreteras decentes que conecten nuestras comunidades y faciliten el desarrollo económico.

Respecto a gobernanza y transparencia: El gobierno de Cartagena será transparente y participativo. Cada peso público se invertirá con honestidad.

Respecto a igualdad y equidad: En Cartagena todas las personas tienen los mismos derechos y oportunidades, sin distinción de género, raza o condición.`,
      key_points: [
        "Seguridad como prioridad",
        "Alimentación para todos",
        "Infraestructura que conecta",
        "Transparencia y participación"
      ],
      duration_minutes: 5,
      trending_topic: "Seguridad"
    },
    chart_data: {
      by_topic_sentiment: {
        type: "bar",
        data: {
          labels: ["Seguridad", "Alimentación", "Infraestructura", "Gobernanza"],
          datasets: [
            {
              label: "Positivo",
              data: [7, 1, 5, 0],
              backgroundColor: "rgba(66, 214, 151, 0.8)"
            },
            {
              label: "Neutral",
              data: [4, 1, 2, 0],
              backgroundColor: "rgba(136, 146, 176, 0.8)"
            },
            {
              label: "Negativo",
              data: [4, 3, 3, 9],
              backgroundColor: "rgba(255, 107, 129, 0.8)"
            }
          ]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              position: "top"
            },
            title: {
              display: true,
              text: "Sentimiento por tema"
            }
          },
          scales: {
            y: {
              beginAtZero: true
            }
          }
        }
      }
    },
    metadata: {
      tweets_analyzed: 94,
      location: "Cartagena",
      theme: "General",
      candidate_name: "Ariel",
      generated_at: new Date().toISOString()
    }
  };
}

// Function to test with mockup data
window.testWithMockup = function() {
  const resultsSection = document.getElementById("results-section");
  if (!resultsSection) {
    console.error("Results section not found");
    return;
  }
  
  resultsSection.style.display = "block";
  const mockupData = generateMockupData();
  lastResponse = mockupData;
  
  if (currentMode === "campaign") {
    renderCampaignResults(mockupData);
  } else {
    renderMediaResults(mockupData);
  }
  
  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
};

// Function to test media with mockup data
window.testMediaWithMockup = function() {
  const resultsSection = document.getElementById("results-section");
  if (!resultsSection) {
    console.error("Results section not found");
    return;
  }
  
  resultsSection.style.display = "block";
  const mockupData = generateMediaMockupData();
  lastResponse = mockupData;
  
  renderMediaResults(mockupData);
  
  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
};
