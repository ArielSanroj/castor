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
 * Traduce momentum a "Tendencia Semanal" con interpretación estratégica
 */
function translateWeeklyTrend(momentum, trend, candidateName, momentumHistory = []) {
    let direction = "";
    let change = "";
    let explanation = "";
    
    // Analizar patrón histórico si está disponible
    const hasRecentDrop = momentumHistory.length >= 3 && 
        momentumHistory.slice(-3).some(m => m < -0.01);
    const hasRecentRecovery = momentumHistory.length >= 2 && 
        momentumHistory[momentumHistory.length - 1] > 0.01 &&
        momentumHistory[momentumHistory.length - 2] < -0.01;
    
    if (trend === "up" || momentum > 0.01) {
        direction = "subiendo";
        if (hasRecentRecovery) {
            change = "recuperación tras caída";
            explanation = `${candidateName || "El candidato"} está recuperando terreno tras una caída reciente. La narrativa muestra signos de recuperación.`;
        } else {
            change = "crecimiento sostenido";
            explanation = `${candidateName || "El candidato"} está ganando terreno de forma sostenida. La narrativa está en tendencia positiva.`;
        }
    } else if (trend === "down" || momentum < -0.01) {
        direction = "bajando fuerte";
        change = "pérdida de terreno";
        if (hasRecentDrop) {
            explanation = `${candidateName || "El candidato"} está perdiendo terreno significativamente. La narrativa está cayendo y requiere atención inmediata.`;
        } else {
            explanation = `${candidateName || "El candidato"} muestra una pérdida de terreno. La narrativa está en declive.`;
        }
    } else {
        direction = "estable";
        if (hasRecentDrop) {
            change = "estabilidad tras caída";
            explanation = `${candidateName || "El candidato"} se ha estabilizado tras una caída a mitad de semana. La narrativa requiere monitoreo constante.`;
        } else {
            change = "sin cambios relevantes";
            explanation = `${candidateName || "El candidato"} se ha mantenido estable esta semana. La narrativa no muestra cambios significativos.`;
        }
    }
    
    return {
        direction: direction,
        change: change,
        explanation: explanation
    };
}

/**
 * Traduce el momentum a lenguaje humano (compatibilidad)
 */
function translateMomentumToHumanLanguage(momentum, trend, candidateName) {
    const trendData = translateWeeklyTrend(momentum, trend, candidateName);
    return trendData.explanation;
}

/**
 * Traduce ICCE a "Fuerza Narrativa" con interpretación estratégica
 */
function translateNarrativeStrength(icce, candidateName, location) {
    let score = Math.round(icce);
    let label = "";
    let interpretation = "";
    
    if (icce >= 70) {
        label = "dominante";
        interpretation = `${candidateName || "El candidato"} tiene una narrativa fuerte y dominante. La conversación es mayoritariamente positiva, con crecimiento sostenido y proyección favorable.`;
    } else if (icce >= 50) {
        label = "competitiva";
        interpretation = `${candidateName || "El candidato"} tiene una narrativa competitiva. La conversación está mezclada pero con potencial de crecimiento.`;
    } else if (icce >= 30) {
        label = "débil";
        interpretation = `${candidateName || "El candidato"} tiene una narrativa débil. La conversación está marcada por críticas y requiere atención estratégica.`;
    } else {
        label = "crisis severa";
        interpretation = `${candidateName || "El candidato"} está en crisis narrativa severa. La conversación está casi completamente dominada por críticas y alarma pública.`;
    }
    
    return {
        score: score,
        label: label,
        interpretation: interpretation
    };
}

/**
 * Traduce el estado actual (ICCE) a lenguaje humano
 */
function translateCurrentStatusToHumanLanguage(icce, sentimentOverview, location, topic) {
    const narrativeStrength = translateNarrativeStrength(icce, null, location);
    return narrativeStrength.interpretation;
}

/**
 * Traduce forecast a "Pronóstico de Conversación" con interpretación estratégica
 */
function translateConversationForecast(forecastPoints, currentICCE, candidateName) {
    if (!forecastPoints || forecastPoints.length === 0) {
        return {
            outlook: "no disponible",
            trend_next_days: "sin datos",
            explanation: "No hay proyección disponible en este momento."
        };
    }
    
    const firstProjection = forecastPoints[0];
    const lastProjection = forecastPoints[forecastPoints.length - 1];
    const change = lastProjection.projected_value - currentICCE;
    const avgProjection = forecastPoints.reduce((sum, p) => sum + p.projected_value, 0) / forecastPoints.length;
    
    let outlook = "";
    let trend_next_days = "";
    let explanation = "";
    
    if (change > 5) {
        outlook = "crecimiento moderado";
        trend_next_days = "aumento sostenido";
        explanation = `La conversación seguirá subiendo y se mantendrá positiva en los próximos ${forecastPoints.length} días. La narrativa está en tendencia alcista.`;
    } else if (change > 2) {
        outlook = "recuperación leve";
        trend_next_days = "mejora gradual";
        explanation = `Se proyecta una recuperación lenta pero sostenida en los próximos ${forecastPoints.length} días. No se proyecta una crisis inmediata, pero tampoco un crecimiento fuerte.`;
    } else if (change < -5) {
        outlook = "caída continua";
        trend_next_days = "deterioro";
        explanation = `Se proyecta una caída continua en la conversación. El impacto se sostendrá al menos ${forecastPoints.length} días más. Se requiere acción inmediata.`;
    } else if (change < -2) {
        outlook = "riesgo de deterioro";
        trend_next_days = "disminución";
        explanation = `Se proyecta una disminución en la conversación sobre ${candidateName || "el candidato"} en los próximos ${forecastPoints.length} días. La narrativa está en riesgo de deterioro.`;
    } else {
        outlook = "estable";
        trend_next_days = "sin cambios significativos";
        explanation = `La conversación se mantendrá estable en los próximos ${forecastPoints.length} días, con variaciones menores. Se espera una recuperación gradual si se mantienen mensajes claros.`;
    }
    
    return {
        outlook: outlook,
        trend_next_days: trend_next_days,
        explanation: explanation
    };
}

/**
 * Traduce la proyección a lenguaje humano (compatibilidad)
 */
function translateProjectionToHumanLanguage(forecastPoints, currentICCE, candidateName) {
    const forecastData = translateConversationForecast(forecastPoints, currentICCE, candidateName);
    return forecastData.explanation;
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

