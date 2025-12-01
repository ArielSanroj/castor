// Forecast Human Language Translation Functions

/**
 * Traduce el IVN a lenguaje humano
 */
function translateIVNToHumanLanguage(ivnScore, interpretation, riskLevel) {
    let positionLabel = "";
    let humanInterpretation = "";
    
    if (ivnScore >= 0.80) {
        positionLabel = "Narrativa Dominante";
        humanInterpretation = "La narrativa del candidato es fuerte y está consolidada. Tiene una posición dominante en la conversación.";
    } else if (ivnScore >= 0.60) {
        positionLabel = "Narrativa Competitiva";
        humanInterpretation = "La narrativa es competitiva con sesgo positivo. El candidato tiene buena posición pero debe mantener el momentum.";
    } else if (ivnScore >= 0.40) {
        positionLabel = "Territorio Neutral";
        humanInterpretation = "La narrativa está en territorio neutral. El resultado depende de la ejecución estratégica en los próximos días.";
    } else if (ivnScore >= 0.20) {
        positionLabel = "Narrativa Débil";
        humanInterpretation = "La narrativa está perdiendo fuerza. Se requiere intervención estratégica para recuperar terreno.";
    } else {
        positionLabel = "Narrativa en Crisis";
        humanInterpretation = "La narrativa está rota o en crisis. Se requiere acción inmediata para evitar mayor deterioro.";
    }
    
    return {
        label: positionLabel,
        interpretation: humanInterpretation,
        riskLevel: riskLevel
    };
}

/**
 * Traduce el momentum a lenguaje humano
 */
function translateMomentumToHumanLanguage(momentum, trend, candidateName) {
    const absMomentum = Math.abs(momentum);
    
    if (trend === "up") {
        if (absMomentum > 2) {
            return `${candidateName || "El candidato"} está ganando terreno significativamente en los últimos días. La narrativa está subiendo.`;
        } else {
            return `${candidateName || "El candidato"} está recuperando terreno gradualmente. La narrativa muestra una tendencia positiva.`;
        }
    } else if (trend === "down") {
        if (absMomentum > 2) {
            return `${candidateName || "El candidato"} está perdiendo terreno significativamente. La narrativa está cayendo y requiere atención.`;
        } else {
            return `${candidateName || "El candidato"} muestra una ligera pérdida de terreno. La narrativa está en declive moderado.`;
        }
    } else {
        return `${candidateName || "El candidato"} se ha mantenido estable esta semana. La narrativa no muestra cambios significativos.`;
    }
}

/**
 * Traduce el estado actual (ICCE) a lenguaje humano
 */
function translateCurrentStatusToHumanLanguage(icce, sentimentOverview, location, topic) {
    let statusText = "";
    
    if (icce >= 70) {
        statusText = `La conversación sobre ${topic || "el tema"} en ${location} está muy activa y positiva. El candidato tiene una presencia narrativa fuerte.`;
    } else if (icce >= 50) {
        if (sentimentOverview && sentimentOverview.negative > 0.4) {
            statusText = `La conversación sobre ${topic || "el tema"} en ${location} está activa pero con tono negativo. La narrativa requiere atención estratégica.`;
        } else {
            statusText = `La conversación sobre ${topic || "el tema"} en ${location} está moderadamente activa. La narrativa está en territorio competitivo.`;
        }
    } else {
        statusText = `La conversación sobre ${topic || "el tema"} en ${location} está baja o con predominio negativo. La narrativa está débil.`;
    }
    
    return statusText;
}

/**
 * Traduce la proyección a lenguaje humano
 */
function translateProjectionToHumanLanguage(forecastPoints, currentICCE, candidateName) {
    if (!forecastPoints || forecastPoints.length === 0) {
        return "No hay proyección disponible en este momento.";
    }
    
    const firstProjection = forecastPoints[0];
    const lastProjection = forecastPoints[forecastPoints.length - 1];
    const change = lastProjection.projected_value - currentICCE;
    const percentChange = ((change / currentICCE) * 100).toFixed(1);
    
    if (change > 3) {
        return `Se proyecta un aumento del ${Math.abs(percentChange)}% en la conversación positiva sobre ${candidateName || "el candidato"} en los próximos ${forecastPoints.length} días. La narrativa está en tendencia alcista.`;
    } else if (change < -3) {
        return `Se proyecta una disminución del ${Math.abs(percentChange)}% en la conversación sobre ${candidateName || "el candidato"} en los próximos ${forecastPoints.length} días. La narrativa está en riesgo de deterioro.`;
    } else {
        return `Se proyecta que la conversación sobre ${candidateName || "el candidato"} se mantendrá estable en los próximos ${forecastPoints.length} días, con variaciones menores.`;
    }
}

/**
 * Genera oportunidades basadas en los datos
 */
function generateOpportunities(data) {
    const opportunities = [];
    const metrics = data.metadata?.narrative_metrics;
    
    if (!metrics) return opportunities;
    
    // Oportunidad basada en CP alto
    if (metrics.cp > 0.6) {
        opportunities.push({
            title: "Ventana de Oportunidad en Comparaciones",
            description: `El ${(metrics.cp * 100).toFixed(0)}% de las comparaciones son favorables. Es un buen momento para destacar propuestas frente a competidores.`,
            icon: "🟢"
        });
    }
    
    // Oportunidad basada en NMI positivo
    if (metrics.nmi > 0.2) {
        opportunities.push({
            title: "Motivación Narrativa Positiva",
            description: "La narrativa muestra emociones positivas (esperanza, orgullo). Aprovecha este momentum para fortalecer el mensaje.",
            icon: "📈"
        });
    }
    
    // Oportunidad basada en momentum positivo
    if (data.momentum && data.momentum.trend === "up") {
        opportunities.push({
            title: "Momentum Alcista",
            description: "La narrativa está subiendo. Es momento de capitalizar esta tendencia con acciones estratégicas.",
            icon: "🚀"
        });
    }
    
    // Oportunidad basada en proyección positiva
    if (data.forecast) {
        const avgProjection = data.forecast.forecast_points.reduce((sum, p) => sum + p.projected_value, 0) / data.forecast.forecast_points.length;
        if (avgProjection > data.icce.current_icce + 2) {
            opportunities.push({
                title: "Proyección Positiva",
                description: `Se proyecta un aumento en la conversación positiva. Prepara contenido y estrategias para capitalizar esta tendencia.`,
                icon: "🔮"
            });
        }
    }
    
    return opportunities;
}

/**
 * Genera riesgos basados en los datos
 */
function generateRisks(data) {
    const risks = [];
    const metrics = data.metadata?.narrative_metrics;
    
    if (!metrics) return risks;
    
    // Riesgo basado en IVN bajo
    if (metrics.ivn && metrics.ivn.ivn < 0.4) {
        risks.push({
            title: "Narrativa Débil",
            description: `La posición narrativa está en ${(metrics.ivn.ivn * 100).toFixed(0)}%. Se requiere intervención estratégica inmediata para evitar mayor deterioro.`,
            severity: metrics.ivn.risk_level,
            icon: "🔴"
        });
    }
    
    // Riesgo basado en SNA negativo
    if (metrics.sna < -0.2) {
        risks.push({
            title: "Tono Negativo Predominante",
            description: "El sentimiento neto es negativo. La narrativa está siendo dominada por críticas y preocupaciones.",
            severity: "alto",
            icon: "⚠️"
        });
    }
    
    // Riesgo basado en momentum negativo
    if (data.momentum && data.momentum.trend === "down") {
        risks.push({
            title: "Pérdida de Momentum",
            description: "La narrativa está perdiendo terreno. Se requiere acción para revertir la tendencia.",
            severity: "medio-alto",
            icon: "📉"
        });
    }
    
    // Riesgo basado en proyección negativa
    if (data.forecast) {
        const avgProjection = data.forecast.forecast_points.reduce((sum, p) => sum + p.projected_value, 0) / data.forecast.forecast_points.length;
        if (avgProjection < data.icce.current_icce - 2) {
            risks.push({
                title: "Proyección Negativa",
                description: `Se proyecta una disminución en la conversación. Prepara estrategias de contención y recuperación.`,
                severity: "medio",
                icon: "🔻"
            });
        }
    }
    
    // Riesgo basado en SVE bajo
    if (metrics.sve < 0.25) {
        risks.push({
            title: "Bajo Share of Voice",
            description: `Solo el ${(metrics.sve * 100).toFixed(0)}% de la conversación. Riesgo de perder relevancia narrativa frente a competidores.`,
            severity: "medio",
            icon: "📊"
        });
    }
    
    return risks;
}

/**
 * Traduce Share of Voice a lenguaje humano
 */
function translateShareOfVoice(sve, candidateName) {
    if (sve >= 0.5) {
        return `${candidateName || "El candidato"} domina la conversación con el ${(sve * 100).toFixed(0)}% del share of voice.`;
    } else if (sve >= 0.25) {
        return `${candidateName || "El candidato"} tiene una presencia competitiva con el ${(sve * 100).toFixed(0)}% del share of voice.`;
    } else {
        return `${candidateName || "El candidato"} tiene baja presencia con solo el ${(sve * 100).toFixed(0)}% del share of voice. Riesgo de irrelevancia narrativa.`;
    }
}

/**
 * Traduce sentimiento a lenguaje humano
 */
function translateSentiment(sna, sentimentOverview) {
    if (sna > 0.2) {
        return `El tono de la conversación es favorable. Predomina el sentimiento positivo sobre el negativo.`;
    } else if (sna < -0.2) {
        return `El tono de la conversación es negativo. Las críticas y preocupaciones dominan la narrativa.`;
    } else {
        return `El tono de la conversación es neutral. No hay predominio claro de sentimiento positivo o negativo.`;
    }
}

