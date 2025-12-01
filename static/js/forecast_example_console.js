// Ejemplo de cómo se vería en la consola del navegador
// cuando se ejecuta el código de forecast.js

console.log("=".repeat(80));
console.log("  📊 EJEMPLO: RESPUESTA DEL ENDPOINT /api/forecast/dashboard");
console.log("=".repeat(80));

// Simulación de la respuesta que llegaría del servidor
const exampleResponse = {
    success: true,
    candidate_name: "Juan Pérez",
    location: "Bogotá",
    icce: {
        success: true,
        candidate_name: "Juan Pérez",
        location: "Bogotá",
        current_icce: 65.3,
        historical_values: [
            { date: "2025-11-25T10:00:00Z", value: 62.1, volume: 45, sentiment_score: 0.12, conversation_share: 0.38 },
            { date: "2025-11-26T10:00:00Z", value: 63.5, volume: 52, sentiment_score: 0.15, conversation_share: 0.40 },
            { date: "2025-11-27T10:00:00Z", value: 64.2, volume: 48, sentiment_score: 0.18, conversation_share: 0.39 },
            { date: "2025-11-28T10:00:00Z", value: 65.8, volume: 55, sentiment_score: 0.20, conversation_share: 0.42 },
            { date: "2025-11-29T10:00:00Z", value: 64.9, volume: 50, sentiment_score: 0.16, conversation_share: 0.41 },
            { date: "2025-11-30T10:00:00Z", value: 65.3, volume: 53, sentiment_score: 0.19, conversation_share: 0.43 }
        ],
        metadata: { days_back: 30, data_points: 30 }
    },
    momentum: {
        success: true,
        candidate_name: "Juan Pérez",
        location: "Bogotá",
        current_momentum: 1.2,
        historical_momentum: [
            { date: "2025-11-25T10:00:00Z", momentum: 0.5, change: 1.4, trend: "stable" },
            { date: "2025-11-26T10:00:00Z", momentum: 0.8, change: 1.4, trend: "stable" },
            { date: "2025-11-27T10:00:00Z", momentum: 1.0, change: 0.7, trend: "stable" },
            { date: "2025-11-28T10:00:00Z", momentum: 1.5, change: 1.6, trend: "up" },
            { date: "2025-11-29T10:00:00Z", momentum: 1.1, change: -0.9, trend: "stable" },
            { date: "2025-11-30T10:00:00Z", momentum: 1.2, change: 0.4, trend: "stable" }
        ],
        trend: "stable",
        metadata: { days_back: 30, data_points: 23 }
    },
    forecast: {
        success: true,
        candidate_name: "Juan Pérez",
        location: "Bogotá",
        forecast_points: [
            { date: "2025-12-01T10:00:00Z", projected_value: 65.8, lower_bound: 60.3, upper_bound: 71.3, confidence: 0.97 },
            { date: "2025-12-02T10:00:00Z", projected_value: 66.2, lower_bound: 60.1, upper_bound: 72.3, confidence: 0.94 },
            { date: "2025-12-03T10:00:00Z", projected_value: 66.5, lower_bound: 59.8, upper_bound: 73.2, confidence: 0.91 },
            { date: "2025-12-04T10:00:00Z", projected_value: 66.9, lower_bound: 59.5, upper_bound: 74.3, confidence: 0.88 },
            { date: "2025-12-05T10:00:00Z", projected_value: 67.2, lower_bound: 59.2, upper_bound: 75.2, confidence: 0.85 }
        ],
        model_type: "holt_winters",
        metadata: { forecast_days: 14, historical_points: 30 }
    },
    metadata: {
        calculated_at: "2025-12-01T16:30:00Z",
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

console.log("\n📦 Objeto completo recibido:");
console.log(exampleResponse);

console.log("\n" + "=".repeat(80));
console.log("  🔍 DESGLOSE DE LA RESPUESTA");
console.log("=".repeat(80));

console.log("\n1️⃣ ICCE (Índice Compuesto de Conversación Electoral):");
console.log(`   • Valor actual: ${exampleResponse.icce.current_icce}/100`);
console.log(`   • Datos históricos: ${exampleResponse.icce.historical_values.length} días`);
console.log(`   • Últimos 3 valores:`);
exampleResponse.icce.historical_values.slice(-3).forEach((val, i) => {
    const date = new Date(val.date).toLocaleDateString('es-ES');
    console.log(`     ${i+1}. ${date}: ${val.value.toFixed(1)} (vol: ${val.volume}, sent: ${val.sentiment_score.toFixed(2)})`);
});

console.log("\n2️⃣ MOMENTUM (Momentum Electoral de Conversación):");
console.log(`   • Momentum actual: ${exampleResponse.momentum.current_momentum > 0 ? '+' : ''}${exampleResponse.momentum.current_momentum.toFixed(2)}`);
console.log(`   • Tendencia: ${exampleResponse.momentum.trend}`);
console.log(`   • Datos históricos: ${exampleResponse.momentum.historical_momentum.length} días`);

console.log("\n3️⃣ FORECAST (Proyección):");
console.log(`   • Modelo: ${exampleResponse.forecast.model_type}`);
console.log(`   • Días proyectados: ${exampleResponse.forecast.forecast_points.length}`);
console.log(`   • Primeros 3 días:`);
exampleResponse.forecast.forecast_points.slice(0, 3).forEach((point, i) => {
    const date = new Date(point.date).toLocaleDateString('es-ES');
    console.log(`     ${i+1}. ${date}: ${point.projected_value.toFixed(1)} ` +
                `(${point.lower_bound.toFixed(1)} - ${point.upper_bound.toFixed(1)}, ` +
                `conf: ${(point.confidence*100).toFixed(0)}%)`);
});

console.log("\n4️⃣ MÉTRICAS NARRATIVAS:");
if (exampleResponse.metadata.narrative_metrics) {
    const metrics = exampleResponse.metadata.narrative_metrics;
    console.log(`   • SVE (Share of Voice): ${(metrics.sve * 100).toFixed(1)}%`);
    console.log(`   • SNA (Sentiment Net): ${metrics.sna > 0 ? '+' : ''}${metrics.sna.toFixed(2)}`);
    console.log(`   • CP (Comparative Preference): ${(metrics.cp * 100).toFixed(1)}%`);
    console.log(`   • NMI (Narrative Motivation): ${metrics.nmi > 0 ? '+' : ''}${metrics.nmi.toFixed(2)}`);
    
    if (metrics.ivn) {
        console.log(`\n   ⭐ IVN (Intención de Voto Narrativa):`);
        console.log(`      • Valor: ${(metrics.ivn.ivn * 100).toFixed(1)}%`);
        console.log(`      • Interpretación: ${metrics.ivn.interpretation}`);
        console.log(`      • Riesgo: ${metrics.ivn.risk_level}`);
        console.log(`      • Componentes:`);
        const comp = metrics.ivn.components;
        console.log(`        - SVE: ${(comp.sve * 100).toFixed(1)}% (peso 40%)`);
        console.log(`        - SNA: ${(comp.sna * 100).toFixed(1)}% (peso 30%)`);
        console.log(`        - CP:  ${(comp.cp * 100).toFixed(1)}% (peso 20%)`);
        console.log(`        - NMI: ${(comp.nmi * 100).toFixed(1)}% (peso 10%)`);
    }
}

console.log("\n" + "=".repeat(80));
console.log("  ✅ CÓMO SE USA EN EL FRONTEND");
console.log("=".repeat(80));

console.log("\n📊 renderForecastDashboard(data) ejecuta:");
console.log("   ✓ renderICCE(data.icce)");
console.log("   ✓ renderMomentum(data.momentum)");
console.log("   ✓ renderForecast(data.forecast, data.icce)");
console.log("   ✓ renderNarrativeMetrics(data.metadata.narrative_metrics)");

console.log("\n🎨 Visualizaciones generadas:");
console.log("   • Gráfico ICCE: Línea temporal con valores históricos");
console.log("   • Gráfico Momentum: Línea temporal con valores de momentum");
console.log("   • Gráfico Forecast: Histórico + proyección con intervalos");
console.log("   • Cards de métricas: SVE, SNA, CP, NMI con valores");
console.log("   • Card IVN: Valor destacado con interpretación y riesgo");

console.log("\n" + "=".repeat(80));

