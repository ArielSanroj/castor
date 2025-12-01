#!/usr/bin/env python3
"""
Ejemplo de cómo se vería la respuesta del Forecast Dashboard
usando datos similares a los ejemplos de Medios y Campañas.
"""
import json
from datetime import datetime, timedelta

def generate_forecast_response_example():
    """Genera un ejemplo de respuesta del Forecast Dashboard."""
    
    now = datetime.utcnow()
    
    # Datos similares a los ejemplos de Medios/Campañas
    # Bogotá, Seguridad, Juan Pérez, ~50 tweets analizados
    
    # ICCE histórico (últimos 30 días)
    icce_values = []
    base_icce = 58.0  # Basado en sentimiento 30% pos, 40% neg, 30% neut
    
    for i in range(30, 0, -1):
        date = now - timedelta(days=i)
        # Simular variación basada en el sentimiento del ejemplo
        # El ejemplo muestra 40% negativo, así que ICCE estaría en rango medio-bajo
        variation = (i % 7) * 1.5 - 4.5  # Oscilación semanal
        noise = (i % 3) * 1.0 - 1.0
        value = max(0, min(100, base_icce + variation + noise))
        
        icce_values.append({
            "date": date.isoformat(),
            "value": round(value, 1),
            "volume": 45 + (i % 10) * 2,
            "sentiment_score": 0.10 + (i % 5) * 0.02 - 0.05,  # Basado en 30% pos, 40% neg
            "conversation_share": 0.35 + (i % 7) * 0.015
        })
    
    current_icce = icce_values[-1]["value"]
    
    # Momentum histórico
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
            trend = "stable"
        
        momentum_values.append({
            "date": icce_values[i]["date"],
            "momentum": round(momentum, 2),
            "change": round(icce_values[i]["value"] - icce_values[i-1]["value"], 2) if i > 0 else 0.0,
            "trend": trend
        })
    
    current_momentum = momentum_values[-1]["momentum"] if momentum_values else 0.0
    current_trend = momentum_values[-1]["trend"] if momentum_values else "stable"
    
    # Proyección (14 días)
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
    
    # Métricas narrativas basadas en los datos del ejemplo
    # Del ejemplo: 30% positivo, 40% negativo, 30% neutro
    # ~50 tweets analizados, tema Seguridad, candidato Juan Pérez
    
    # SVE: Si hay ~50 tweets sobre Seguridad y Juan Pérez está en ~42% de menciones
    sve = 0.42
    
    # SNA: Basado en sentimiento (30% pos - 40% neg) / total = -0.10, pero ajustado
    sna = (0.30 - 0.40) / 1.0  # -0.10, pero puede ser ajustado a positivo si hay más contexto
    sna = 0.12  # Ajustado para reflejar mejor la narrativa
    
    # CP: 58% de comparaciones favorables (del ejemplo anterior)
    cp = 0.58
    
    # NMI: Motivación narrativa positiva pero moderada
    nmi = 0.18
    
    # IVN
    sve_norm = sve
    sna_norm = (sna + 1.0) / 2.0  # Normalizar de -1,1 a 0,1
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
    
    response = {
        "success": True,
        "candidate_name": "Juan Pérez",
        "location": "Bogotá",
        "icce": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "current_icce": current_icce,
            "historical_values": icce_values,
            "metadata": {
                "days_back": 30,
                "data_points": len(icce_values),
                "calculated_at": now.isoformat()
            }
        },
        "momentum": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "current_momentum": current_momentum,
            "historical_momentum": momentum_values,
            "trend": current_trend,
            "metadata": {
                "days_back": 30,
                "data_points": len(momentum_values),
                "calculated_at": now.isoformat()
            }
        },
        "forecast": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "forecast_points": forecast_points,
            "model_type": "holt_winters",
            "metadata": {
                "forecast_days": 14,
                "historical_points": len(icce_values),
                "calculated_at": now.isoformat()
            }
        },
        "metadata": {
            "calculated_at": now.isoformat(),
            "narrative_metrics": {
                "sve": round(sve, 2),
                "sna": round(sna, 2),
                "cp": round(cp, 2),
                "nmi": round(nmi, 2),
                "ivn": {
                    "ivn": round(ivn_score, 3),
                    "interpretation": interpretation,
                    "risk_level": risk_level,
                    "components": {
                        "sve": round(sve_norm, 3),
                        "sna": round(sna_norm, 3),
                        "cp": round(cp_norm, 3),
                        "nmi": round(nmi_norm, 3)
                    }
                }
            }
        }
    }
    
    return response

def print_formatted_response():
    """Imprime la respuesta formateada."""
    response = generate_forecast_response_example()
    
    print("\n" + "="*80)
    print("  📊 RESPUESTA DEL FORECAST DASHBOARD")
    print("  (Basado en datos similares a Medios/Campañas)")
    print("="*80 + "\n")
    
    print("🔵 JSON Response completo:")
    print(json.dumps(response, indent=2, ensure_ascii=False, default=str))
    
    print("\n" + "="*80)
    print("  📱 CÓMO SE RENDERIZA EN EL FRONTEND")
    print("="*80 + "\n")
    
    print(f"┌─────────────────────────────────────────────────────────────┐")
    print(f"│  DASHBOARD DE FORECAST - {response['candidate_name']} ({response['location']})  │")
    print(f"└─────────────────────────────────────────────────────────────┘\n")
    
    # Tab ICCE
    print("📊 TAB: ICCE")
    print("─" * 60)
    print(f"ICCE Actual: {response['icce']['current_icce']:.1f}/100")
    print(f"Histórico: {len(response['icce']['historical_values'])} días")
    print("Gráfico: Línea temporal con valores históricos")
    print("Últimos 5 valores:")
    for val in response['icce']['historical_values'][-5:]:
        date = datetime.fromisoformat(val['date']).strftime("%Y-%m-%d")
        print(f"  • {date}: {val['value']:.1f} (vol: {val['volume']}, sent: {val['sentiment_score']:+.2f})")
    print()
    
    # Tab Momentum
    print("📈 TAB: Momentum")
    print("─" * 60)
    momentum = response['momentum']['current_momentum']
    trend = response['momentum']['trend']
    trend_emoji = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"
    print(f"Momentum Actual: {momentum:+.2f}")
    print(f"Tendencia: {trend_emoji} {trend}")
    print(f"Histórico: {len(response['momentum']['historical_momentum'])} días")
    print("Gráfico: Línea temporal con valores de momentum")
    print("Últimos 5 valores:")
    for val in response['momentum']['historical_momentum'][-5:]:
        date = datetime.fromisoformat(val['date']).strftime("%Y-%m-%d")
        print(f"  • {date}: {val['momentum']:+.2f} ({val['trend']})")
    print()
    
    # Tab Forecast
    print("🔮 TAB: Proyección")
    print("─" * 60)
    print(f"Modelo: {response['forecast']['model_type']}")
    print(f"Días proyectados: {len(response['forecast']['forecast_points'])}")
    print("Gráfico: Línea histórica + proyección con intervalos de confianza")
    print("Primeros 5 días proyectados:")
    for i, point in enumerate(response['forecast']['forecast_points'][:5], 1):
        date = datetime.fromisoformat(point['date']).strftime("%Y-%m-%d")
        print(f"  {i}. {date}: {point['projected_value']:.1f} "
              f"({point['lower_bound']:.1f} - {point['upper_bound']:.1f}, "
              f"conf: {point['confidence']*100:.0f}%)")
    print()
    
    # Tab Métricas Narrativas
    if response['metadata'].get('narrative_metrics'):
        print("⭐ TAB: Métricas Narrativas")
        print("─" * 60)
        metrics = response['metadata']['narrative_metrics']
        
        print("┌─────────────┬──────────┬─────────────────────────────┐")
        print("│ Métrica     │ Valor    │ Descripción                 │")
        print("├─────────────┼──────────┼─────────────────────────────┤")
        print(f"│ SVE         │ {metrics['sve']*100:5.1f}%  │ Share of Voice Electoral    │")
        print(f"│ SNA         │ {metrics['sna']:+.2f}    │ Sentimiento Neto Ajustado   │")
        print(f"│ CP          │ {metrics['cp']*100:5.1f}%  │ Preferencia Comparativa     │")
        print(f"│ NMI         │ {metrics['nmi']:+.2f}    │ Motivación Narrativa        │")
        print("└─────────────┴──────────┴─────────────────────────────┘")
        print()
        
        if metrics.get('ivn'):
            ivn = metrics['ivn']
            print("┌─────────────────────────────────────────────────────┐")
            print("│  IVN - INTENCIÓN DE VOTO NARRATIVA                  │")
            print("├─────────────────────────────────────────────────────┤")
            print(f"│  Valor: {ivn['ivn']*100:5.1f}%                                    │")
            print(f"│  Interpretación: {ivn['interpretation']:<30} │")
            print(f"│  Riesgo: {ivn['risk_level']:<40} │")
            print("└─────────────────────────────────────────────────────┘")
            print()
            print("Componentes:")
            comp = ivn['components']
            print(f"  • SVE: {comp['sve']*100:.1f}% (peso: 40%)")
            print(f"  • SNA: {comp['sna']*100:.1f}% (peso: 30%)")
            print(f"  • CP:  {comp['cp']*100:.1f}% (peso: 20%)")
            print(f"  • NMI: {comp['nmi']*100:.1f}% (peso: 10%)")
            print()
            print(f"Cálculo: IVN = 0.4×{comp['sve']:.2f} + 0.3×{comp['sna']:.2f} + "
                  f"0.2×{comp['cp']:.2f} + 0.1×{comp['nmi']:.2f} = {ivn['ivn']:.3f}")
    
    print("\n" + "="*80)
    print("  📊 COMPARACIÓN CON DATOS DE MEDIOS/CAMPAÑAS")
    print("="*80 + "\n")
    
    print("Datos de entrada (del ejemplo de Medios/Campañas):")
    print("  • Ubicación: Bogotá")
    print("  • Tema: Seguridad")
    print("  • Candidato: Juan Pérez")
    print("  • Tweets analizados: ~50")
    print("  • Sentimiento: 30% positivo, 40% negativo, 30% neutro")
    print()
    print("Métricas derivadas en Forecast:")
    print(f"  • ICCE actual: {response['icce']['current_icce']:.1f}/100")
    print(f"  • Momentum: {response['momentum']['current_momentum']:+.2f} ({response['momentum']['trend']})")
    print(f"  • SVE: {response['metadata']['narrative_metrics']['sve']*100:.1f}%")
    print(f"  • SNA: {response['metadata']['narrative_metrics']['sna']:+.2f}")
    print(f"  • IVN: {response['metadata']['narrative_metrics']['ivn']['ivn']*100:.1f}%")
    print()
    print("💡 El Forecast toma los mismos datos base y agrega:")
    print("   ✓ Cálculo de ICCE histórico (30 días)")
    print("   ✓ Cálculo de Momentum (tendencia)")
    print("   ✓ Proyección estadística (14 días)")
    print("   ✓ Métricas narrativas (SVE, SNA, CP, NMI, IVN)")
    
    print("\n" + "="*80)

if __name__ == "__main__":
    print_formatted_response()

