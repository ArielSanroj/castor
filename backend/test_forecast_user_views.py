#!/usr/bin/env python3
"""
Muestra cómo se vería el Forecast Dashboard para cada tipo de usuario
(Medios y Campañas) usando los datos de ejemplo.
"""
import json
from datetime import datetime, timedelta

def generate_forecast_data_from_example():
    """Genera datos de forecast basados en los ejemplos de Medios/Campañas."""
    
    # Datos base del ejemplo:
    # - Ubicación: Bogotá
    # - Tema: Seguridad
    # - Candidato: Juan Pérez
    # - Sentimiento: 30% positivo, 40% negativo, 30% neutro
    # - Tweets: ~50 para campañas, ~10 para medios
    
    now = datetime.utcnow()
    
    # ICCE histórico (basado en sentimiento negativo predominante)
    base_icce = 55.0  # Refleja el sentimiento mixto-negativo
    icce_values = []
    for i in range(30, 0, -1):
        date = now - timedelta(days=i)
        variation = (i % 7) * 1.5 - 4.5
        noise = (i % 3) * 1.0 - 1.0
        value = max(0, min(100, base_icce + variation + noise))
        icce_values.append({
            "date": date.isoformat(),
            "value": round(value, 1),
            "volume": 45 + (i % 10) * 2,
            "sentiment_score": 0.10 + (i % 5) * 0.02 - 0.05,
            "conversation_share": 0.35 + (i % 7) * 0.015
        })
    
    current_icce = icce_values[-1]["value"]
    
    # Momentum (ligeramente negativo por el sentimiento negativo)
    momentum_values = []
    for i in range(7, len(icce_values)):
        recent_avg = sum(v["value"] for v in icce_values[i-7:i]) / 7
        previous_avg = sum(v["value"] for v in icce_values[i-8:i-1]) / 7 if i > 7 else recent_avg
        momentum = recent_avg - previous_avg
        
        if momentum > 2:
            trend = "up"
        elif momentum < -2:
            trend = "down"
        else:
            trend = "down" if i > len(icce_values) - 5 else "stable"  # Últimos días en declive
        
        momentum_values.append({
            "date": icce_values[i]["date"],
            "momentum": round(momentum, 2),
            "change": round(icce_values[i]["value"] - icce_values[i-1]["value"], 2) if i > 0 else 0.0,
            "trend": trend
        })
    
    current_momentum = momentum_values[-1]["momentum"] if momentum_values else -0.5
    current_trend = momentum_values[-1]["trend"] if momentum_values else "stable"
    
    # Proyección (tendencia ligeramente negativa)
    forecast_points = []
    last_value = icce_values[-1]["value"]
    trend_slope = (icce_values[-1]["value"] - icce_values[-7]["value"]) / 7
    
    for i in range(1, 15):
        forecast_date = now + timedelta(days=i)
        projected = last_value + (trend_slope * i)
        margin = 4.0 * (1 + i * 0.08)
        confidence = max(0.4, 1.0 - (i * 0.03))
        
        forecast_points.append({
            "date": forecast_date.isoformat(),
            "projected_value": round(max(0, min(100, projected)), 1),
            "lower_bound": round(max(0, min(100, projected - margin)), 1),
            "upper_bound": round(max(0, min(100, projected + margin)), 1),
            "confidence": round(confidence, 2)
        })
    
    # Métricas narrativas (basadas en sentimiento 30% pos, 40% neg, 30% neutro)
    sve = 0.42
    sna = (0.30 - 0.40) / 1.0  # -0.10, pero ajustado
    sna = -0.15  # Negativo por el 40% negativo
    cp = 0.65  # Alto para mostrar oportunidad
    nmi = 0.25  # Positivo para mostrar oportunidad
    
    sve_norm = sve
    sna_norm = (sna + 1.0) / 2.0
    cp_norm = cp
    nmi_norm = (nmi + 1.0) / 2.0
    
    ivn_score = 0.4 * sve_norm + 0.3 * sna_norm + 0.2 * cp_norm + 0.1 * nmi_norm
    
    if ivn_score >= 0.80:
        interpretation = "Narrativa dominante (alta probabilidad de consolidación)"
        risk_level = "bajo"
    elif ivn_score >= 0.60:
        interpretation = "Competitivo con sesgo positivo"
        risk_level = "medio-bajo"
    elif ivn_score >= 0.40:
        interpretation = "Territorio neutral, depende de ejecución"
        risk_level = "medio"
    elif ivn_score >= 0.20:
        interpretation = "Pérdida de narrativa"
        risk_level = "medio-alto"
    else:
        interpretation = "Narrativa rota o crisis"
        risk_level = "alto"
    
    return {
        "candidate_name": "Juan Pérez",
        "location": "Bogotá",
        "topic": "Seguridad",
        "icce": {
            "current_icce": current_icce,
            "historical_values": icce_values
        },
        "momentum": {
            "current_momentum": current_momentum,
            "trend": current_trend,
            "historical_momentum": momentum_values
        },
        "forecast": {
            "forecast_points": forecast_points
        },
        "narrative_metrics": {
            "sve": sve,
            "sna": sna,
            "cp": cp,
            "nmi": nmi,
            "ivn": {
                "ivn": ivn_score,
                "interpretation": interpretation,
                "risk_level": risk_level
            }
        },
        "sentiment_overview": {
            "positive": 0.3,
            "negative": 0.4,
            "neutral": 0.3
        }
    }

def translate_to_human_language(data, user_type="medio"):
    """Traduce los datos a lenguaje humano según el tipo de usuario."""
    
    candidate_name = data["candidate_name"]
    location = data["location"]
    topic = data["topic"]
    
    # Estado Actual
    icce = data["icce"]["current_icce"]
    sentiment = data["sentiment_overview"]
    
    if icce >= 70:
        estado_actual = f"La conversación sobre {topic} en {location} está muy activa y positiva. {candidate_name} tiene una presencia narrativa fuerte."
    elif icce >= 50:
        if sentiment["negative"] > 0.4:
            estado_actual = f"La conversación sobre {topic} en {location} está activa pero con tono negativo. La narrativa requiere atención estratégica."
        else:
            estado_actual = f"La conversación sobre {topic} en {location} está moderadamente activa. La narrativa está en territorio competitivo."
    else:
        estado_actual = f"La conversación sobre {topic} en {location} está baja o con predominio negativo. La narrativa está débil."
    
    # Momentum
    momentum = data["momentum"]["current_momentum"]
    trend = data["momentum"]["trend"]
    
    if trend == "up":
        if abs(momentum) > 2:
            momentum_text = f"{candidate_name} está ganando terreno significativamente en los últimos días. La narrativa está subiendo."
        else:
            momentum_text = f"{candidate_name} está recuperando terreno gradualmente. La narrativa muestra una tendencia positiva."
    elif trend == "down":
        if abs(momentum) > 2:
            momentum_text = f"{candidate_name} está perdiendo terreno significativamente. La narrativa está cayendo y requiere atención."
        else:
            momentum_text = f"{candidate_name} muestra una ligera pérdida de terreno. La narrativa está en declive moderado."
    else:
        momentum_text = f"{candidate_name} se ha mantenido estable esta semana. La narrativa no muestra cambios significativos."
    
    # Proyección
    forecast_points = data["forecast"]["forecast_points"]
    change = forecast_points[-1]["projected_value"] - icce
    percent_change = abs((change / icce) * 100) if icce > 0 else 0
    
    if change > 3:
        proyeccion_text = f"Se proyecta un aumento del {percent_change:.1f}% en la conversación positiva sobre {candidate_name} en los próximos {len(forecast_points)} días. La narrativa está en tendencia alcista."
    elif change < -3:
        proyeccion_text = f"Se proyecta una disminución del {percent_change:.1f}% en la conversación sobre {candidate_name} en los próximos {len(forecast_points)} días. La narrativa está en riesgo de deterioro."
    else:
        proyeccion_text = f"Se proyecta que la conversación sobre {candidate_name} se mantendrá estable en los próximos {len(forecast_points)} días, con variaciones menores."
    
    # Posición Narrativa
    ivn = data["narrative_metrics"]["ivn"]["ivn"]
    ivn_interpretation = data["narrative_metrics"]["ivn"]["interpretation"]
    risk_level = data["narrative_metrics"]["ivn"]["risk_level"]
    
    if ivn >= 0.80:
        posicion_label = "Narrativa Dominante"
        posicion_text = "La narrativa del candidato es fuerte y está consolidada. Tiene una posición dominante en la conversación."
    elif ivn >= 0.60:
        posicion_label = "Narrativa Competitiva"
        posicion_text = "La narrativa es competitiva con sesgo positivo. El candidato tiene buena posición pero debe mantener el momentum."
    elif ivn >= 0.40:
        posicion_label = "Territorio Neutral"
        posicion_text = "La narrativa está en territorio neutral. El resultado depende de la ejecución estratégica en los próximos días."
    elif ivn >= 0.20:
        posicion_label = "Narrativa Débil"
        posicion_text = "La narrativa está perdiendo fuerza. Se requiere intervención estratégica para recuperar terreno."
    else:
        posicion_label = "Narrativa en Crisis"
        posicion_text = "La narrativa está rota o en crisis. Se requiere acción inmediata para evitar mayor deterioro."
    
    # Share of Voice
    sve = data["narrative_metrics"]["sve"]
    if sve >= 0.5:
        sve_text = f"{candidate_name} domina la conversación con el {sve*100:.0f}% del share of voice."
    elif sve >= 0.25:
        sve_text = f"{candidate_name} tiene una presencia competitiva con el {sve*100:.0f}% del share of voice."
    else:
        sve_text = f"{candidate_name} tiene baja presencia con solo el {sve*100:.0f}% del share of voice. Riesgo de irrelevancia narrativa."
    
    # Sentimiento
    sna = data["narrative_metrics"]["sna"]
    if sna > 0.2:
        sentiment_text = "El tono de la conversación es favorable. Predomina el sentimiento positivo sobre el negativo."
    elif sna < -0.2:
        sentiment_text = "El tono de la conversación es negativo. Las críticas y preocupaciones dominan la narrativa."
    else:
        sentiment_text = "El tono de la conversación es neutral. No hay predominio claro de sentimiento positivo o negativo."
    
    # Oportunidades y Riesgos
    opportunities = []
    risks = []
    
    # Oportunidades
    if data["narrative_metrics"]["cp"] > 0.6:
        opportunities.append({
            "title": "Ventana de Oportunidad en Comparaciones",
            "description": f"El {data['narrative_metrics']['cp']*100:.0f}% de las comparaciones son favorables. Es un buen momento para destacar propuestas frente a competidores."
        })
    
    if data["narrative_metrics"]["nmi"] > 0.2:
        opportunities.append({
            "title": "Motivación Narrativa Positiva",
            "description": "La narrativa muestra emociones positivas (esperanza, orgullo). Aprovecha este momentum para fortalecer el mensaje."
        })
    
    if trend == "up":
        opportunities.append({
            "title": "Momentum Alcista",
            "description": "La narrativa está subiendo. Es momento de capitalizar esta tendencia con acciones estratégicas."
        })
    
    # Riesgos
    if ivn < 0.4:
        risks.append({
            "title": "Narrativa Débil",
            "description": f"La posición narrativa está en {ivn*100:.0f}%. Se requiere intervención estratégica inmediata para evitar mayor deterioro.",
            "severity": risk_level
        })
    
    if sna < -0.2:
        risks.append({
            "title": "Tono Negativo Predominante",
            "description": "El sentimiento neto es negativo. La narrativa está siendo dominada por críticas y preocupaciones.",
            "severity": "alto"
        })
    
    if trend == "down":
        risks.append({
            "title": "Pérdida de Momentum",
            "description": "La narrativa está perdiendo terreno. Se requiere acción para revertir la tendencia.",
            "severity": "medio-alto"
        })
    
    if sve < 0.25:
        risks.append({
            "title": "Bajo Share of Voice",
            "description": f"Solo el {sve*100:.0f}% de la conversación. Riesgo de perder relevancia narrativa frente a competidores.",
            "severity": "medio"
        })
    
    return {
        "estado_actual": estado_actual,
        "momentum": momentum_text,
        "proyeccion": proyeccion_text,
        "posicion": {
            "valor": ivn * 100,
            "label": posicion_label,
            "interpretation": posicion_text,
            "risk_level": risk_level
        },
        "share_of_voice": sve_text,
        "sentiment": sentiment_text,
        "opportunities": opportunities,
        "risks": risks
    }

def print_user_view(data, user_type, human_data):
    """Imprime la vista para un tipo de usuario específico."""
    
    print("\n" + "="*80)
    print(f"  📊 VISTA PARA: {'MEDIOS' if user_type == 'medio' else 'CAMPAÑAS'}")
    print("="*80 + "\n")
    
    print(f"📍 Ubicación: {data['location']}")
    print(f"🎯 Tema: {data['topic']}")
    if user_type == "campaña":
        print(f"👤 Candidato: {data['candidate_name']}")
    print()
    
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  RESUMEN EJECUTIVO                                         │")
    print("└─────────────────────────────────────────────────────────────┘\n")
    
    print("🔵 ESTADO ACTUAL:")
    print(f"   {human_data['estado_actual']}\n")
    
    print("🟠 MOMENTUM:")
    print(f"   {human_data['momentum']}\n")
    
    print("🟣 PROYECCIÓN:")
    print(f"   {human_data['proyeccion']}\n")
    
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  ⭐ POSICIÓN NARRATIVA                                      │")
    print("└─────────────────────────────────────────────────────────────┘\n")
    
    posicion = human_data['posicion']
    print(f"   Valor: {posicion['valor']:.1f}%")
    print(f"   Etiqueta: {posicion['label']}")
    print(f"   Interpretación: {posicion['interpretation']}")
    print(f"   Riesgo: {posicion['risk_level']}\n")
    
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  ANÁLISIS DETALLADO                                         │")
    print("└─────────────────────────────────────────────────────────────┘\n")
    
    print("📊 DOMINIO NARRATIVO:")
    print(f"   {human_data['share_of_voice']}\n")
    
    print("💬 TONO DE LA CONVERSACIÓN:")
    print(f"   {human_data['sentiment']}\n")
    
    if user_type == "campaña":
        print("┌─────────────────────────────────────────────────────────────┐")
        print("│  🟢 OPORTUNIDADES                                          │")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        if human_data['opportunities']:
            for i, opp in enumerate(human_data['opportunities'], 1):
                print(f"   {i}. {opp['title']}")
                print(f"      {opp['description']}\n")
        else:
            print("   No se identificaron oportunidades específicas en este momento.\n")
        
        print("┌─────────────────────────────────────────────────────────────┐")
        print("│  🔴 RIESGOS                                                 │")
        print("└─────────────────────────────────────────────────────────────┘\n")
        
        if human_data['risks']:
            for i, risk in enumerate(human_data['risks'], 1):
                print(f"   {i}. {risk['title']} [{risk['severity']}]")
                print(f"      {risk['description']}\n")
        else:
            print("   No se identificaron riesgos significativos en este momento.\n")
    
    print("="*80 + "\n")

def main():
    # Generar datos de ejemplo
    data = generate_forecast_data_from_example()
    
    # Vista para MEDIOS
    human_data_medio = translate_to_human_language(data, "medio")
    print_user_view(data, "medio", human_data_medio)
    
    # Vista para CAMPAÑAS
    human_data_campaña = translate_to_human_language(data, "campaña")
    print_user_view(data, "campaña", human_data_campaña)
    
    print("\n💡 DIFERENCIAS CLAVE:")
    print("   • MEDIOS: Enfoque descriptivo, sin recomendaciones estratégicas")
    print("   • CAMPAÑAS: Incluye oportunidades y riesgos para acción estratégica")
    print("   • Ambos comparten el mismo motor de datos, pero la presentación difiere\n")

if __name__ == "__main__":
    main()

