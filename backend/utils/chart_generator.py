"""
Chart.js data generator for sentiment visualization.
"""
from typing import List, Dict, Any
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../'))

from models.schemas import PNDTopicAnalysis, ChartData, SentimentData


class ChartGenerator:
    """Generate Chart.js configuration from analysis data."""
    
    @staticmethod
    def generate_sentiment_chart(topic_analyses: List[PNDTopicAnalysis]) -> ChartData:
        """
        Generate bar chart for sentiment distribution by topic.
        
        Args:
            topic_analyses: List of topic analyses
            
        Returns:
            ChartData object with Chart.js configuration
        """
        labels = [analysis.topic for analysis in topic_analyses]
        
        positive_data = [
            round(analysis.sentiment.positive * 100, 1)
            for analysis in topic_analyses
        ]
        negative_data = [
            round(analysis.sentiment.negative * 100, 1)
            for analysis in topic_analyses
        ]
        neutral_data = [
            round(analysis.sentiment.neutral * 100, 1)
            for analysis in topic_analyses
        ]
        
        datasets = [
            {
                'label': 'Positivo',
                'data': positive_data,
                'backgroundColor': '#36A2EB',
                'borderColor': '#2E8BC0',
                'borderWidth': 1
            },
            {
                'label': 'Negativo',
                'data': negative_data,
                'backgroundColor': '#FF6384',
                'borderColor': '#E63946',
                'borderWidth': 1
            },
            {
                'label': 'Neutral',
                'data': neutral_data,
                'backgroundColor': '#FFCE56',
                'borderColor': '#F4A261',
                'borderWidth': 1
            }
        ]
        
        options = {
            'responsive': True,
            'maintainAspectRatio': True,
            'scales': {
                'x': {
                    'stacked': True,
                    'title': {
                        'display': True,
                        'text': 'Temas del PND'
                    }
                },
                'y': {
                    'stacked': True,
                    'beginAtZero': True,
                    'max': 100,
                    'title': {
                        'display': True,
                        'text': 'Porcentaje (%)'
                    },
                    'ticks': {
                        'callback': "function(value) { return value + '%'; }"
                    }
                }
            },
            'plugins': {
                'title': {
                    'display': True,
                    'text': 'Distribución de Sentimientos por Tema',
                    'font': {
                        'size': 16
                    }
                },
                'legend': {
                    'display': True,
                    'position': 'top'
                },
                'tooltip': {
                    'callbacks': {
                        'label': "function(context) { return context.dataset.label + ': ' + context.parsed.y + '%'; }"
                    }
                }
            }
        }
        
        return ChartData(
            type='bar',
            labels=labels,
            datasets=datasets,
            options=options
        )
    
    @staticmethod
    def generate_pie_chart(overall_sentiment: SentimentData) -> ChartData:
        """
        Generate pie chart for overall sentiment distribution.
        
        Args:
            overall_sentiment: Aggregated sentiment data
            
        Returns:
            ChartData object
        """
        labels = ['Positivo', 'Negativo', 'Neutral']
        data = [
            round(overall_sentiment.positive * 100, 1),
            round(overall_sentiment.negative * 100, 1),
            round(overall_sentiment.neutral * 100, 1)
        ]
        
        datasets = [{
            'label': 'Sentimiento General',
            'data': data,
            'backgroundColor': ['#36A2EB', '#FF6384', '#FFCE56'],
            'borderColor': ['#2E8BC0', '#E63946', '#F4A261'],
            'borderWidth': 2
        }]
        
        options = {
            'responsive': True,
            'maintainAspectRatio': True,
            'plugins': {
                'title': {
                    'display': True,
                    'text': 'Distribución General de Sentimientos',
                    'font': {
                        'size': 16
                    }
                },
                'legend': {
                    'display': True,
                    'position': 'right'
                },
                'tooltip': {
                    'callbacks': {
                        'label': "function(context) { return context.label + ': ' + context.parsed + '%'; }"
                    }
                }
            }
        }
        
        return ChartData(
            type='pie',
            labels=labels,
            datasets=datasets,
            options=options
        )

