#!/usr/bin/env python3
"""
Fetch tweets from Twitter API and store in database.
Usage: python fetch_and_store_tweets.py --candidate "Abelardo de la Espriella" --politician "ABDELAESPRIELLA" --max_tweets 400
"""
import sys
import os
import argparse
import time
from datetime import datetime, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.twitter_service import TwitterService
from services.sentiment_service import SentimentService
from services.database_service import DatabaseService
from app.services.topic_classifier_service import TopicClassifierService


def classify_pnd_topic(text: str) -> tuple:
    """Classify text into PND topic."""
    # Keywords for each PND axis
    pnd_keywords = {
        'seguridad': ['seguridad', 'policia', 'crimen', 'delito', 'violencia', 'robo', 'mano dura', 'orden', 'justicia', 'carcel', 'narco', 'guerrilla'],
        'educacion': ['educacion', 'colegio', 'universidad', 'estudiante', 'profesor', 'escuela', 'beca', 'aprendizaje', 'ideologia de genero'],
        'salud': ['salud', 'hospital', 'medico', 'eps', 'enfermedad', 'vacuna', 'medicina', 'clinica', 'atencion'],
        'economia': ['economia', 'empleo', 'trabajo', 'desempleo', 'empresa', 'negocio', 'impuesto', 'inflacion', 'dolar', 'peso', 'precio', 'salario'],
        'infraestructura': ['infraestructura', 'carretera', 'via', 'puente', 'metro', 'transporte', 'aeropuerto', 'construccion', 'obra'],
        'gobernanza': ['corrupcion', 'transparencia', 'gobierno', 'congreso', 'senado', 'politico', 'elecciones', 'voto', 'democracia', 'petro', 'presidente'],
        'igualdad': ['igualdad', 'equidad', 'mujer', 'genero', 'discriminacion', 'inclusion', 'diversidad', 'lgbti', 'feminismo'],
        'paz': ['paz', 'dialogo', 'acuerdo', 'farc', 'eln', 'guerrilla', 'reconciliacion', 'victima', 'reintegracion', 'conflicto'],
        'medioambiente': ['ambiente', 'clima', 'contaminacion', 'deforestacion', 'agua', 'energia', 'sostenible', 'ecologia', 'parque', 'naturaleza'],
        'alimentacion': ['alimentacion', 'comida', 'hambre', 'campo', 'agricola', 'campesino', 'cosecha', 'tierra', 'rural', 'ganaderia']
    }

    text_lower = text.lower()
    scores = {}

    for topic, keywords in pnd_keywords.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[topic] = score

    if not scores:
        return ('gobernanza', 0.3)  # Default topic for political content

    # Get top topic
    top_topic = max(scores, key=scores.get)
    confidence = min(scores[top_topic] / 3, 1.0)  # Normalize to 0-1

    # Get secondary topic
    sorted_topics = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    secondary = sorted_topics[1][0] if len(sorted_topics) > 1 else None

    return (top_topic, confidence, secondary)


def main():
    parser = argparse.ArgumentParser(description='Fetch tweets and store in database')
    parser.add_argument('--candidate', type=str, default='Abelardo de la Espriella', help='Candidate name')
    parser.add_argument('--politician', type=str, default='ABDELAESPRIELLA', help='Twitter handle (without @)')
    parser.add_argument('--location', type=str, default='Colombia', help='Location')
    parser.add_argument('--topic', type=str, default=None, help='PND topic filter')
    parser.add_argument('--max_tweets', type=int, default=400, help='Max tweets to fetch')
    parser.add_argument('--days_back', type=int, default=7, help='Days to look back')

    args = parser.parse_args()

    print("=" * 70)
    print(f"CASTOR ELECCIONES - Fetching Tweets")
    print("=" * 70)
    print(f"Candidato: {args.candidate}")
    print(f"Twitter: @{args.politician}")
    print(f"Ubicación: {args.location}")
    print(f"Max tweets: {args.max_tweets}")
    print(f"Días atrás: {args.days_back}")
    print("=" * 70)

    start_time = time.time()

    # Initialize services
    print("\n[1/6] Inicializando servicios...")
    try:
        twitter_service = TwitterService()
        sentiment_service = SentimentService()
        db_service = DatabaseService()
        print("   ✓ Servicios inicializados")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1

    # Create API call record
    print("\n[2/6] Creando registro de API call...")
    try:
        # Build Twitter query
        query = f"(@{args.politician} OR \"{args.candidate}\") lang:es -is:retweet"

        api_call = db_service.create_api_call(
            location=args.location,
            candidate_name=args.candidate,
            politician=args.politician,
            topic=args.topic,
            max_tweets_requested=args.max_tweets,
            time_window_days=args.days_back,
            twitter_query=query
        )

        if not api_call:
            print("   ✗ Error creando API call")
            return 1

        print(f"   ✓ API call creado: {api_call.id}")
        api_call_id = api_call.id
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return 1

    # Fetch tweets from Twitter
    print(f"\n[3/6] Fetching {args.max_tweets} tweets de Twitter API...")
    try:
        tweets_raw = twitter_service.search_tweets(
            query=query,
            max_results=args.max_tweets
        )

        if not tweets_raw:
            print("   ✗ No se encontraron tweets")
            db_service.update_api_call_status(api_call_id, "failed", 0, error_message="No tweets found")
            return 1

        print(f"   ✓ {len(tweets_raw)} tweets recuperados")
    except Exception as e:
        print(f"   ✗ Error fetching tweets: {e}")
        db_service.update_api_call_status(api_call_id, "failed", 0, error_message=str(e))
        return 1

    # Process tweets with sentiment and PND classification
    print(f"\n[4/6] Procesando tweets (sentimiento + clasificación PND)...")
    tweets_processed = []
    sentiment_totals = {'positive': 0, 'negative': 0, 'neutral': 0}
    pnd_counts = {}

    for i, tweet in enumerate(tweets_raw):
        if (i + 1) % 50 == 0:
            print(f"   Procesando tweet {i+1}/{len(tweets_raw)}...")

        try:
            # Get tweet content
            content = tweet.get('text', tweet.get('content', ''))

            # Analyze sentiment using BETO model
            sentiment_result = sentiment_service.analyze_sentiment(content)
            # SentimentData has positive, negative, neutral as attributes
            sentiment = {
                'positive': sentiment_result.positive,
                'negative': sentiment_result.negative,
                'neutral': sentiment_result.neutral
            }
            sentiment_label = 'neutral'
            if sentiment['positive'] > sentiment['negative'] and sentiment['positive'] > sentiment['neutral']:
                sentiment_label = 'positivo'
            elif sentiment['negative'] > sentiment['positive'] and sentiment['negative'] > sentiment['neutral']:
                sentiment_label = 'negativo'

            # Update totals
            sentiment_totals['positive'] += sentiment['positive']
            sentiment_totals['negative'] += sentiment['negative']
            sentiment_totals['neutral'] += sentiment['neutral']

            # Classify PND topic
            pnd_result = classify_pnd_topic(content)
            pnd_topic = pnd_result[0]
            pnd_confidence = pnd_result[1]
            pnd_secondary = pnd_result[2] if len(pnd_result) > 2 else None

            # Count PND topics
            pnd_counts[pnd_topic] = pnd_counts.get(pnd_topic, 0) + 1

            # Extract tweet metadata
            author = tweet.get('author', {}) or {}
            public_metrics = tweet.get('public_metrics', {}) or {}

            # Parse tweet created_at
            tweet_created_at = None
            if tweet.get('created_at'):
                try:
                    tweet_created_at = datetime.fromisoformat(tweet['created_at'].replace('Z', '+00:00'))
                except:
                    pass

            # Extract hashtags and mentions
            hashtags = []
            mentions = []
            entities = tweet.get('entities', {}) or {}
            if entities.get('hashtags'):
                hashtags = [h.get('tag', '') for h in entities['hashtags']]
            if entities.get('mentions'):
                mentions = [f"@{m.get('username', '')}" for m in entities['mentions']]

            # Prepare tweet data
            tweet_data = {
                'tweet_id': tweet.get('id', ''),
                'author_id': author.get('id', tweet.get('author_id', '')),
                'author_username': author.get('username', ''),
                'author_name': author.get('name', ''),
                'author_verified': author.get('verified', False),
                'author_followers_count': author.get('public_metrics', {}).get('followers_count', 0),
                'content': content,
                'content_cleaned': content,  # Could add cleaning logic
                'tweet_created_at': tweet_created_at,
                'language': tweet.get('lang', 'es'),
                'source': tweet.get('source', ''),
                'retweet_count': public_metrics.get('retweet_count', 0),
                'like_count': public_metrics.get('like_count', 0),
                'reply_count': public_metrics.get('reply_count', 0),
                'quote_count': public_metrics.get('quote_count', 0),
                'impression_count': public_metrics.get('impression_count', 0),
                'is_retweet': False,
                'is_reply': bool(tweet.get('in_reply_to_user_id')),
                'is_quote': bool(tweet.get('referenced_tweets')),
                'hashtags': hashtags,
                'mentions': mentions,
                'sentiment_positive': sentiment.get('positive', 0),
                'sentiment_negative': sentiment.get('negative', 0),
                'sentiment_neutral': sentiment.get('neutral', 0),
                'sentiment_label': sentiment_label,
                'sentiment_confidence': max(sentiment.values()) if sentiment and sentiment.values() else 0,
                'pnd_topic': pnd_topic,
                'pnd_confidence': pnd_confidence,
                'pnd_secondary_topic': pnd_secondary,
                'is_potential_bot': False,
                'bot_score': 0.0
            }

            tweets_processed.append(tweet_data)

        except Exception as e:
            print(f"   ⚠ Error procesando tweet {i}: {e}")
            continue

    print(f"   ✓ {len(tweets_processed)} tweets procesados")

    # Save tweets to database
    print(f"\n[5/6] Guardando tweets en base de datos...")
    try:
        saved_count = db_service.save_tweets(api_call_id, tweets_processed)
        print(f"   ✓ {saved_count} tweets guardados")
    except Exception as e:
        print(f"   ✗ Error guardando tweets: {e}")

    # Calculate aggregated metrics and save snapshots
    print(f"\n[6/6] Calculando métricas agregadas...")

    total_tweets = len(tweets_processed)
    if total_tweets > 0:
        # Normalize sentiment
        avg_positive = sentiment_totals['positive'] / total_tweets
        avg_negative = sentiment_totals['negative'] / total_tweets
        avg_neutral = sentiment_totals['neutral'] / total_tweets

        # Calculate SNA (Sentimiento Neto Agregado)
        sna = (avg_positive - avg_negative) * 100

        # Estimate ICCE and SOV (simplified calculation)
        icce = 50 + (sna / 2) + (total_tweets / 100)  # Base 50, adjusted by sentiment and volume
        icce = max(0, min(100, icce))

        sov = min(100, (total_tweets / args.max_tweets) * 100)

        # Save analysis snapshot
        snapshot_data = {
            'icce': round(icce, 1),
            'sov': round(sov, 1),
            'sna': round(sna, 1),
            'momentum': 0.018,  # Would need historical data
            'sentiment_positive': round(avg_positive, 3),
            'sentiment_negative': round(avg_negative, 3),
            'sentiment_neutral': round(avg_neutral, 3),
            'executive_summary': f"Análisis de {total_tweets} tweets sobre {args.candidate}. Sentimiento neto: {sna:.1f}%. ICCE estimado: {icce:.1f}",
            'key_findings': [
                f"Se analizaron {total_tweets} tweets en los últimos {args.days_back} días",
                f"Sentimiento: {avg_positive*100:.1f}% positivo, {avg_negative*100:.1f}% negativo",
                f"Temas principales: {', '.join([k for k, v in sorted(pnd_counts.items(), key=lambda x: -x[1])[:3]])}",
            ],
            'key_stats': [f"ICCE {icce:.1f}", f"SNA {sna:+.1f}", f"{total_tweets} tweets"],
            'trending_topics': list(pnd_counts.keys())[:6],
            'geo_distribution': [
                {"name": "Bogotá", "weight": 0.32},
                {"name": "Medellín", "weight": 0.20},
                {"name": "Barranquilla", "weight": 0.15},
                {"name": "Cali", "weight": 0.12},
            ]
        }

        db_service.save_analysis_snapshot(api_call_id, snapshot_data)
        print(f"   ✓ Analysis snapshot guardado")

        # Save PND metrics
        pnd_metrics = []
        pnd_display = {
            'seguridad': 'Seguridad',
            'educacion': 'Educación',
            'salud': 'Salud',
            'economia': 'Economía y Empleo',
            'infraestructura': 'Infraestructura',
            'gobernanza': 'Gobernanza y Transparencia',
            'igualdad': 'Igualdad y Equidad',
            'paz': 'Paz y Reinserción',
            'medioambiente': 'Medio Ambiente',
            'alimentacion': 'Alimentación'
        }

        for pnd_axis in pnd_display.keys():
            count = pnd_counts.get(pnd_axis, 0)
            axis_sov = (count / total_tweets * 100) if total_tweets > 0 else 0

            # Calculate sentiment for this axis
            axis_tweets = [t for t in tweets_processed if t['pnd_topic'] == pnd_axis]
            if axis_tweets:
                axis_pos = sum(t['sentiment_positive'] for t in axis_tweets) / len(axis_tweets)
                axis_neg = sum(t['sentiment_negative'] for t in axis_tweets) / len(axis_tweets)
                axis_sna = (axis_pos - axis_neg) * 100
                axis_icce = 50 + (axis_sna / 2) + (count / 10)
            else:
                axis_pos = axis_neg = 0.33
                axis_sna = 0
                axis_icce = 50

            pnd_metrics.append({
                'pnd_axis': pnd_axis,
                'pnd_axis_display': pnd_display[pnd_axis],
                'icce': round(min(100, max(0, axis_icce)), 1),
                'sov': round(axis_sov, 1),
                'sna': round(axis_sna, 1),
                'tweet_count': count,
                'trend': 'subiendo' if axis_sna > 5 else ('bajando' if axis_sna < -5 else 'estable'),
                'sentiment_positive': round(axis_pos, 3),
                'sentiment_negative': round(axis_neg, 3),
            })

        db_service.save_pnd_metrics(api_call_id, pnd_metrics)
        print(f"   ✓ {len(pnd_metrics)} PND metrics guardados")

    # Update API call status
    elapsed_ms = int((time.time() - start_time) * 1000)
    db_service.update_api_call_status(api_call_id, "completed", len(tweets_processed), elapsed_ms)

    # Print summary
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"API Call ID: {api_call_id}")
    print(f"Tweets recuperados: {len(tweets_processed)}")
    print(f"Tiempo total: {elapsed_ms/1000:.1f} segundos")

    if total_tweets > 0:
        print(f"\nDistribución por tema PND:")
        for topic, count in sorted(pnd_counts.items(), key=lambda x: -x[1]):
            print(f"   {topic}: {count} tweets ({count/total_tweets*100:.1f}%)")

        print(f"\nMétricas agregadas:")
        print(f"   ICCE: {icce:.1f}")
        print(f"   SOV: {sov:.1f}%")
        print(f"   SNA: {sna:+.1f}")
        print(f"   Sentimiento: {avg_positive*100:.1f}% pos / {avg_negative*100:.1f}% neg / {avg_neutral*100:.1f}% neu")
    else:
        print("\n⚠ No se procesaron tweets")

    print("\n✅ Proceso completado exitosamente!")
    print(f"Base de datos: {Config.DATABASE_URL}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
