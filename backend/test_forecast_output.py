#!/usr/bin/env python3
"""
Script para mostrar cómo se ve un resultado ejemplo del Forecast Dashboard
con todas las métricas narrativas.
"""
import json
from datetime import datetime, timedelta
from app.schemas.forecast import (
    ICCEValue,
    MomentumValue,
    ForecastPoint,
    ICCEResponse,
    MomentumResponse,
    ForecastResponse,
    ForecastDashboardResponse,
)
from app.schemas.narrative import NarrativeIndices, IVNResult

def generate_example_dashboard_response():
    """Genera un ejemplo completo de respuesta del dashboard de Forecast."""
    
    # Generar valores históricos de ICCE (últimos 30 días)
    now = datetime.utcnow()
    icce_values = []
    base_icce = 65.0
    
    for i in range(30, 0, -1):
        date = now - timedelta(days=i)
        # Simular variación realista
        variation = (i % 7) * 2 - 6  # Oscilación semanal
        noise = (i % 3) * 1.5 - 1.5  # Ruido diario
        value = max(0, min(100, base_icce + variation + noise))
        
        icce_values.append(ICCEValue(
            date=date,
            value=value,
            volume=50 + (i % 10) * 5,
            sentiment_score=0.1 + (i % 5) * 0.05 - 0.1,
            conversation_share=0.35 + (i % 7) * 0.02
        ))
    
    current_icce = icce_values[-1].value
    
    # Generar valores de Momentum
    momentum_values = []
    for i in range(7, len(icce_values)):
        recent_avg = sum(v.value for v in icce_values[i-7:i]) / 7
        previous_avg = sum(v.value for v in icce_values[i-8:i-1]) / 7 if i > 7 else recent_avg
        momentum = recent_avg - previous_avg
        
        if momentum > 2:
            trend = "up"
        elif momentum < -2:
            trend = "down"
        else:
            trend = "stable"
        
        momentum_values.append(MomentumValue(
            date=icce_values[i].date,
            momentum=momentum,
            change=icce_values[i].value - icce_values[i-1].value if i > 0 else 0,
            trend=trend
        ))
    
    # Generar proyección
    forecast_points = []
    last_value = icce_values[-1].value
    trend = (icce_values[-1].value - icce_values[-7].value) / 7
    
    for i in range(1, 15):
        forecast_date = now + timedelta(days=i)
        projected = last_value + (trend * i)
        margin = 5.0 * (1 + i * 0.1)  # Aumenta con el tiempo
        
        forecast_points.append(ForecastPoint(
            date=forecast_date,
            projected_value=max(0, min(100, projected)),
            lower_bound=max(0, min(100, projected - margin)),
            upper_bound=max(0, min(100, projected + margin)),
            confidence=max(0.4, 1.0 - (i * 0.03))
        ))
    
    # Métricas narrativas
    narrative_metrics = {
        "sve": 0.42,  # 42% de share of voice
        "sna": 0.15,  # Sentimiento neto positivo
        "cp": 0.58,   # 58% de preferencia comparativa
        "nmi": 0.22,  # Motivación narrativa positiva
        "ivn": {
            "ivn": 0.65,
            "interpretation": "Competitivo con sesgo positivo",
            "risk_level": "medio-bajo",
            "components": {
                "sve": 0.42,
                "sna": 0.575,  # Normalizado de -1,1 a 0,1
                "cp": 0.58,
                "nmi": 0.61    # Normalizado de -1,1 a 0,1
            }
        }
    }
    
    # Construir respuestas
    icce_response = ICCEResponse(
        success=True,
        candidate_name="Juan Pérez",
        location="Bogotá",
        current_icce=current_icce,
        historical_values=icce_values,
        metadata={
            "days_back": 30,
            "data_points": len(icce_values),
            "calculated_at": now.isoformat()
        }
    )
    
    momentum_response = MomentumResponse(
        success=True,
        candidate_name="Juan Pérez",
        location="Bogotá",
        current_momentum=momentum_values[-1].momentum if momentum_values else 0.0,
        historical_momentum=momentum_values,
        trend=momentum_values[-1].trend if momentum_values else "stable",
        metadata={
            "days_back": 30,
            "data_points": len(momentum_values),
            "calculated_at": now.isoformat()
        }
    )
    
    forecast_response = ForecastResponse(
        success=True,
        candidate_name="Juan Pérez",
        location="Bogotá",
        forecast_points=forecast_points,
        model_type="holt_winters",
        metadata={
            "forecast_days": 14,
            "historical_points": len(icce_values),
            "calculated_at": now.isoformat()
        }
    )
    
    dashboard = ForecastDashboardResponse(
        success=True,
        candidate_name="Juan Pérez",
        location="Bogotá",
        icce=icce_response,
        momentum=momentum_response,
        forecast=forecast_response,
        metadata={
            "calculated_at": now.isoformat(),
            "narrative_metrics": narrative_metrics
        }
    )
    
    return dashboard

def print_formatted_response():
    """Imprime la respuesta formateada de manera legible."""
    dashboard = generate_example_dashboard_response()
    
    print("\n" + "="*80)
    print("  EJEMPLO DE RESPUESTA DEL DASHBOARD DE FORECAST")
    print("="*80 + "\n")
    
    print("📊 ESTRUCTURA COMPLETA JSON:")
    print(json.dumps(dashboard.model_dump(), indent=2, ensure_ascii=False, default=str))
    
    print("\n" + "="*80)
    print("  RESUMEN EJECUTIVO")
    print("="*80 + "\n")
    
    print(f"✅ Candidato: {dashboard.candidate_name}")
    print(f"📍 Ubicación: {dashboard.location}")
    print(f"📅 Calculado en: {dashboard.metadata['calculated_at']}\n")
    
    print("📈 ICCE (Índice Compuesto de Conversación Electoral):")
    print(f"   Valor actual: {dashboard.icce.current_icce:.1f}/100")
    print(f"   Datos históricos: {len(dashboard.icce.historical_values)} días")
    print(f"   Últimos 5 valores:")
    for val in dashboard.icce.historical_values[-5:]:
        date_str = val.date.strftime("%Y-%m-%d")
        print(f"     • {date_str}: {val.value:.1f} (volumen: {val.volume}, sentimiento: {val.sentiment_score:+.2f})")
    
    print("\n📊 MOMENTUM ELECTORAL DE CONVERSACIÓN:")
    print(f"   Momentum actual: {dashboard.momentum.current_momentum:+.2f}")
    print(f"   Tendencia: {dashboard.momentum.trend}")
    print(f"   Datos históricos: {len(dashboard.momentum.historical_momentum)} días")
    print(f"   Últimos 5 valores:")
    for val in dashboard.momentum.historical_momentum[-5:]:
        date_str = val.date.strftime("%Y-%m-%d")
        print(f"     • {date_str}: {val.momentum:+.2f} ({val.trend})")
    
    print("\n🔮 PROYECCIÓN DE CONVERSACIÓN (14 días):")
    print(f"   Modelo: {dashboard.forecast.model_type}")
    print(f"   Puntos de proyección: {len(dashboard.forecast.forecast_points)}")
    print(f"   Primeros 5 días proyectados:")
    for point in dashboard.forecast.forecast_points[:5]:
        date_str = point.date.strftime("%Y-%m-%d")
        print(f"     • {date_str}: {point.projected_value:.1f} "
              f"(intervalo: {point.lower_bound:.1f} - {point.upper_bound:.1f}, "
              f"confianza: {point.confidence*100:.0f}%)")
    
    if dashboard.metadata.get("narrative_metrics"):
        print("\n" + "="*80)
        print("  MÉTRICAS NARRATIVAS")
        print("="*80 + "\n")
        
        metrics = dashboard.metadata["narrative_metrics"]
        
        print("📊 ÍNDICES NARRATIVOS:")
        print(f"   SVE (Share of Voice Electoral): {metrics['sve']*100:.1f}%")
        print(f"      → {metrics['sve']*100:.1f}% de la conversación total")
        
        print(f"\n   SNA (Sentiment Net Adjusted): {metrics['sna']:+.2f}")
        if metrics['sna'] > 0.2:
            print(f"      → Narrativa favorable (positivo)")
        elif metrics['sna'] < -0.2:
            print(f"      → Riesgo reputacional (negativo)")
        else:
            print(f"      → Neutral")
        
        print(f"\n   CP (Comparative Preference): {metrics['cp']*100:.1f}%")
        print(f"      → {metrics['cp']*100:.1f}% de comparaciones favorables")
        
        print(f"\n   NMI (Narrative Motivation Index): {metrics['nmi']:+.2f}")
        if metrics['nmi'] > 0:
            print(f"      → Motivación positiva (esperanza/pride)")
        else:
            print(f"      → Motivación negativa (frustración/enojo)")
        
        if metrics.get("ivn"):
            ivn = metrics["ivn"]
            print("\n" + "="*60)
            print("  ⭐ IVN - INTENCIÓN DE VOTO NARRATIVA")
            print("="*60 + "\n")
            
            ivn_score = ivn.get("ivn", 0)
            print(f"   Valor IVN: {ivn_score*100:.1f}%")
            print(f"   Interpretación: {ivn.get('interpretation', 'N/A')}")
            print(f"   Nivel de riesgo: {ivn.get('risk_level', 'N/A')}")
            
            if ivn.get("components"):
                print("\n   Componentes del IVN:")
                comp = ivn["components"]
                print(f"     • SVE normalizado: {comp.get('sve', 0)*100:.1f}%")
                print(f"     • SNA normalizado: {comp.get('sna', 0)*100:.1f}%")
                print(f"     • CP normalizado: {comp.get('cp', 0)*100:.1f}%")
                print(f"     • NMI normalizado: {comp.get('nmi', 0)*100:.1f}%")
                
                print("\n   Cálculo:")
                print(f"     IVN = 0.4*{comp.get('sve', 0):.3f} + 0.3*{comp.get('sna', 0):.3f} + "
                      f"0.2*{comp.get('cp', 0):.3f} + 0.1*{comp.get('nmi', 0):.3f}")
                print(f"     IVN = {ivn_score:.3f} = {ivn_score*100:.1f}%")
    
    print("\n" + "="*80)
    print("  FIN DEL EJEMPLO")
    print("="*80 + "\n")

if __name__ == "__main__":
    print_formatted_response()

