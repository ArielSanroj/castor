#!/usr/bin/env python3
"""
Script para mostrar cómo se ve la respuesta del Forecast Dashboard
como se mostraría en la consola del navegador.
"""
import json
from datetime import datetime, timedelta

def print_console_example():
    """Muestra cómo se vería la respuesta en la consola del navegador."""
    
    # Ejemplo de respuesta JSON que llegaría del endpoint
    example_response = {
        "success": True,
        "candidate_name": "Juan Pérez",
        "location": "Bogotá",
        "icce": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "current_icce": 65.3,
            "historical_values": [
                {"date": "2025-11-25T10:00:00Z", "value": 62.1, "volume": 45, "sentiment_score": 0.12, "conversation_share": 0.38},
                {"date": "2025-11-26T10:00:00Z", "value": 63.5, "volume": 52, "sentiment_score": 0.15, "conversation_share": 0.40},
                {"date": "2025-11-27T10:00:00Z", "value": 64.2, "volume": 48, "sentiment_score": 0.18, "conversation_share": 0.39},
                {"date": "2025-11-28T10:00:00Z", "value": 65.8, "volume": 55, "sentiment_score": 0.20, "conversation_share": 0.42},
                {"date": "2025-11-29T10:00:00Z", "value": 64.9, "volume": 50, "sentiment_score": 0.16, "conversation_share": 0.41},
                {"date": "2025-11-30T10:00:00Z", "value": 65.3, "volume": 53, "sentiment_score": 0.19, "conversation_share": 0.43}
            ],
            "metadata": {"days_back": 30, "data_points": 30}
        },
        "momentum": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "current_momentum": 1.2,
            "historical_momentum": [
                {"date": "2025-11-25T10:00:00Z", "momentum": 0.5, "change": 1.4, "trend": "stable"},
                {"date": "2025-11-26T10:00:00Z", "momentum": 0.8, "change": 1.4, "trend": "stable"},
                {"date": "2025-11-27T10:00:00Z", "momentum": 1.0, "change": 0.7, "trend": "stable"},
                {"date": "2025-11-28T10:00:00Z", "momentum": 1.5, "change": 1.6, "trend": "up"},
                {"date": "2025-11-29T10:00:00Z", "momentum": 1.1, "change": -0.9, "trend": "stable"},
                {"date": "2025-11-30T10:00:00Z", "momentum": 1.2, "change": 0.4, "trend": "stable"}
            ],
            "trend": "stable",
            "metadata": {"days_back": 30, "data_points": 23}
        },
        "forecast": {
            "success": True,
            "candidate_name": "Juan Pérez",
            "location": "Bogotá",
            "forecast_points": [
                {"date": "2025-12-01T10:00:00Z", "projected_value": 65.8, "lower_bound": 60.3, "upper_bound": 71.3, "confidence": 0.97},
                {"date": "2025-12-02T10:00:00Z", "projected_value": 66.2, "lower_bound": 60.1, "upper_bound": 72.3, "confidence": 0.94},
                {"date": "2025-12-03T10:00:00Z", "projected_value": 66.5, "lower_bound": 59.8, "upper_bound": 73.2, "confidence": 0.91},
                {"date": "2025-12-04T10:00:00Z", "projected_value": 66.9, "lower_bound": 59.5, "upper_bound": 74.3, "confidence": 0.88},
                {"date": "2025-12-05T10:00:00Z", "projected_value": 67.2, "lower_bound": 59.2, "upper_bound": 75.2, "confidence": 0.85}
            ],
            "model_type": "holt_winters",
            "metadata": {"forecast_days": 14, "historical_points": 30}
        },
        "metadata": {
            "calculated_at": "2025-12-01T16:30:00Z",
            "narrative_metrics": {
                "sve": 0.42,
                "sna": 0.15,
                "cp": 0.58,
                "nmi": 0.22,
                "ivn": {
                    "ivn": 0.65,
                    "interpretation": "Competitivo con sesgo positivo",
                    "risk_level": "medio-bajo",
                    "components": {
                        "sve": 0.42,
                        "sna": 0.575,
                        "cp": 0.58,
                        "nmi": 0.61
                    }
                }
            }
        }
    }
    
    print("\n" + "="*80)
    print("  📊 RESPUESTA DEL ENDPOINT: POST /api/forecast/dashboard")
    print("="*80 + "\n")
    
    print("🔵 JSON Response (como se recibe en el frontend):")
    print(json.dumps(example_response, indent=2, ensure_ascii=False, default=str))
    
    print("\n" + "="*80)
    print("  📱 CÓMO SE RENDERIZA EN EL FRONTEND")
    print("="*80 + "\n")
    
    print("┌─────────────────────────────────────────────────────────────┐")
    print("│  DASHBOARD DE FORECAST - Juan Pérez (Bogotá)               │")
    print("└─────────────────────────────────────────────────────────────┘\n")
    
    # Tab ICCE
    print("📊 TAB: ICCE")
    print("─" * 60)
    print(f"ICCE Actual: {example_response['icce']['current_icce']:.1f}/100")
    print(f"Histórico: {len(example_response['icce']['historical_values'])} días")
    print("Gráfico: Línea temporal con valores históricos")
    print()
    
    # Tab Momentum
    print("📈 TAB: Momentum")
    print("─" * 60)
    momentum = example_response['momentum']['current_momentum']
    trend = example_response['momentum']['trend']
    trend_emoji = "📈" if trend == "up" else "📉" if trend == "down" else "➡️"
    print(f"Momentum Actual: {momentum:+.2f}")
    print(f"Tendencia: {trend_emoji} {trend}")
    print(f"Histórico: {len(example_response['momentum']['historical_momentum'])} días")
    print("Gráfico: Línea temporal con valores de momentum")
    print()
    
    # Tab Forecast
    print("🔮 TAB: Proyección")
    print("─" * 60)
    print(f"Modelo: {example_response['forecast']['model_type']}")
    print(f"Días proyectados: {len(example_response['forecast']['forecast_points'])}")
    print("Gráfico: Línea histórica + proyección con intervalos de confianza")
    print("Primeros 3 días:")
    for i, point in enumerate(example_response['forecast']['forecast_points'][:3], 1):
        date = point['date'][:10]
        print(f"  {i}. {date}: {point['projected_value']:.1f} "
              f"({point['lower_bound']:.1f} - {point['upper_bound']:.1f})")
    print()
    
    # Tab Métricas Narrativas
    if example_response['metadata'].get('narrative_metrics'):
        print("⭐ TAB: Métricas Narrativas")
        print("─" * 60)
        metrics = example_response['metadata']['narrative_metrics']
        
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
    print("  ✅ RESPUESTA COMPLETA - LISTA PARA RENDERIZAR")
    print("="*80 + "\n")
    
    print("💡 El frontend usa estos datos para:")
    print("   1. Renderizar gráficos Chart.js (ICCE, Momentum, Forecast)")
    print("   2. Mostrar valores actuales en cards destacadas")
    print("   3. Mostrar métricas narrativas con colores según valores")
    print("   4. Mostrar IVN con interpretación y nivel de riesgo")
    print()

if __name__ == "__main__":
    print_console_example()

