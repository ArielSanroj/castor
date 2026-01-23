#!/usr/bin/env python3
"""
Script para traer 100 tweets de Abelardo De La Espriella
"""
import sys
import os
import json
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
load_dotenv()

import tweepy
from config import Config

def fetch_espriella_tweets(max_tweets=100):
    """Buscar tweets de Abelardo De La Espriella"""

    print("=" * 60)
    print("BÚSQUEDA DE TWEETS - ABELARDO DE LA ESPRIELLA")
    print("=" * 60)

    # Crear cliente
    client = tweepy.Client(
        bearer_token=Config.TWITTER_BEARER_TOKEN,
        wait_on_rate_limit=True
    )

    # Query de búsqueda
    search_query = '("Abelardo De La Espriella" OR "Abelardo Espriella" OR "de la Espriella") lang:es -is:retweet'

    print(f"\n🔍 Query: {search_query}")
    print(f"📊 Objetivo: {max_tweets} tweets")
    print("-" * 60)

    all_tweets = []
    pagination_token = None
    request_count = 0

    while len(all_tweets) < max_tweets:
        remaining = max_tweets - len(all_tweets)
        current_max = min(remaining, 100)  # Max 100 por request

        try:
            request_count += 1
            print(f"\n📡 Request #{request_count} - Solicitando {current_max} tweets...")

            response = client.search_recent_tweets(
                query=search_query,
                max_results=current_max,
                tweet_fields=['created_at', 'author_id', 'public_metrics', 'lang', 'source'],
                user_fields=['username', 'name', 'verified', 'public_metrics', 'description', 'location'],
                expansions=['author_id'],
                next_token=pagination_token
            )

            if not response.data:
                print("   ⚠️ No más tweets disponibles")
                break

            # Build user lookup
            users_by_id = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users_by_id[user.id] = {
                        'id': str(user.id),
                        'username': user.username,
                        'name': user.name,
                        'verified': getattr(user, 'verified', False),
                        'followers_count': user.public_metrics.get('followers_count', 0) if user.public_metrics else 0,
                        'description': user.description,
                        'location': user.location
                    }

            for tweet in response.data:
                author = users_by_id.get(tweet.author_id, {})
                all_tweets.append({
                    'id': str(tweet.id),
                    'text': tweet.text,
                    'created_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'author_id': str(tweet.author_id),
                    'author_username': author.get('username', 'unknown'),
                    'author_name': author.get('name', 'unknown'),
                    'author_followers': author.get('followers_count', 0),
                    'author_verified': author.get('verified', False),
                    'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                    'retweets': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                    'replies': tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                    'source': getattr(tweet, 'source', None),
                    'lang': tweet.lang
                })

            print(f"   ✅ Recibidos: {len(response.data)} tweets (Total: {len(all_tweets)})")

            # Check for more pages
            if hasattr(response, 'meta') and response.meta.get('next_token'):
                pagination_token = response.meta['next_token']
            else:
                print("   📄 No hay más páginas")
                break

        except tweepy.errors.TooManyRequests as e:
            print(f"\n⚠️ RATE LIMIT ALCANZADO: {e}")
            print("   El plan Free tiene límites muy estrictos")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            break

    # Mostrar resultados
    print("\n" + "=" * 60)
    print(f"RESULTADOS: {len(all_tweets)} TWEETS OBTENIDOS")
    print("=" * 60)

    if all_tweets:
        # Estadísticas
        total_likes = sum(t['likes'] for t in all_tweets)
        total_rts = sum(t['retweets'] for t in all_tweets)
        total_replies = sum(t['replies'] for t in all_tweets)
        unique_authors = len(set(t['author_username'] for t in all_tweets))

        print(f"\n📊 ESTADÍSTICAS:")
        print(f"   • Total tweets: {len(all_tweets)}")
        print(f"   • Autores únicos: {unique_authors}")
        print(f"   • Total likes: {total_likes:,}")
        print(f"   • Total retweets: {total_rts:,}")
        print(f"   • Total replies: {total_replies:,}")

        # Top 10 tweets por engagement
        print(f"\n🔥 TOP 10 TWEETS POR ENGAGEMENT:")
        print("-" * 60)
        sorted_tweets = sorted(all_tweets, key=lambda x: x['likes'] + x['retweets'], reverse=True)
        for i, tweet in enumerate(sorted_tweets[:10], 1):
            engagement = tweet['likes'] + tweet['retweets']
            print(f"\n{i}. @{tweet['author_username']} ({tweet['author_followers']:,} seguidores)")
            print(f"   {tweet['text'][:200]}...")
            print(f"   ❤️ {tweet['likes']:,} | 🔄 {tweet['retweets']:,} | 💬 {tweet['replies']:,}")
            print(f"   📅 {tweet['created_at']}")

        # Guardar en archivo JSON
        output_file = 'tweets_espriella.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                'query': search_query,
                'total_tweets': len(all_tweets),
                'fetched_at': datetime.now().isoformat(),
                'stats': {
                    'total_likes': total_likes,
                    'total_retweets': total_rts,
                    'total_replies': total_replies,
                    'unique_authors': unique_authors
                },
                'tweets': all_tweets
            }, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Tweets guardados en: {output_file}")

    return all_tweets

if __name__ == "__main__":
    tweets = fetch_espriella_tweets(max_tweets=100)
    print(f"\n✅ Proceso completado. Se obtuvieron {len(tweets)} tweets.")
