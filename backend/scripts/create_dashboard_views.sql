-- Dashboard Views for CASTOR ELECCIONES
-- Run this after the migration script

-- ============================================
-- VIEW: Resumen por ubicación
-- ============================================
CREATE OR REPLACE VIEW v_location_summary AS
SELECT
    a.location,
    COUNT(DISTINCT a.id) as total_analyses,
    COUNT(DISTINCT a.candidate_name) as candidates_analyzed,
    AVG(a.sentiment_positive) as avg_positive,
    AVG(a.sentiment_negative) as avg_negative,
    AVG(a.sentiment_neutral) as avg_neutral,
    SUM(a.tweets_analyzed) as total_tweets,
    MAX(a.created_at) as last_analysis
FROM analyses a
GROUP BY a.location
ORDER BY total_analyses DESC;

-- ============================================
-- VIEW: Topics más críticos (negativos)
-- ============================================
CREATE OR REPLACE VIEW v_critical_topics AS
SELECT
    t.topic_name,
    a.location,
    AVG(t.sentiment_negative) as avg_negative,
    AVG(t.sentiment_positive) as avg_positive,
    SUM(t.tweet_count) as total_mentions,
    COUNT(DISTINCT a.id) as analyses_count
FROM analysis_topics t
JOIN analyses a ON t.analysis_id = a.id
GROUP BY t.topic_name, a.location
HAVING AVG(t.sentiment_negative) > 0.3
ORDER BY avg_negative DESC;

-- ============================================
-- VIEW: Evolución de sentimiento por ubicación
-- ============================================
CREATE OR REPLACE VIEW v_sentiment_evolution AS
SELECT
    a.location,
    DATE(a.created_at) as analysis_date,
    AVG(a.sentiment_positive) as avg_positive,
    AVG(a.sentiment_negative) as avg_negative,
    COUNT(*) as analyses_count
FROM analyses a
WHERE a.created_at >= NOW() - INTERVAL '90 days'
GROUP BY a.location, DATE(a.created_at)
ORDER BY a.location, analysis_date;

-- ============================================
-- VIEW: Comparación de candidatos
-- ============================================
CREATE OR REPLACE VIEW v_candidate_comparison AS
SELECT
    a.candidate_name,
    a.location,
    COUNT(*) as total_analyses,
    AVG(a.sentiment_positive) as avg_positive,
    AVG(a.sentiment_negative) as avg_negative,
    AVG(a.tweets_analyzed) as avg_tweets,
    MAX(a.created_at) as last_analysis
FROM analyses a
WHERE a.candidate_name IS NOT NULL
GROUP BY a.candidate_name, a.location
ORDER BY avg_positive DESC;

-- ============================================
-- VIEW: Recomendaciones prioritarias
-- ============================================
CREATE OR REPLACE VIEW v_priority_recommendations AS
SELECT
    r.recommendation_type,
    r.priority,
    r.content,
    r.topic_related,
    a.location,
    a.candidate_name,
    a.created_at
FROM analysis_recommendations r
JOIN analyses a ON r.analysis_id = a.id
WHERE r.priority = 'alta'
ORDER BY a.created_at DESC;

-- ============================================
-- VIEW: Trending topics por ubicación
-- ============================================
CREATE OR REPLACE VIEW v_trending_by_location AS
SELECT
    a.location,
    a.trending_topic,
    COUNT(*) as appearances,
    AVG(a.sentiment_positive) as sentiment_when_trending,
    MAX(a.created_at) as last_seen
FROM analyses a
WHERE a.trending_topic IS NOT NULL
GROUP BY a.location, a.trending_topic
ORDER BY appearances DESC;

-- ============================================
-- VIEW: Dashboard de usuario
-- ============================================
CREATE OR REPLACE VIEW v_user_dashboard AS
SELECT
    u.id as user_id,
    u.email,
    u.first_name,
    u.last_name,
    m.total_analyses,
    m.avg_sentiment_positive,
    m.avg_sentiment_negative,
    m.most_analyzed_location,
    m.most_analyzed_topic,
    m.last_analysis_at,
    (
        SELECT COUNT(*)
        FROM analysis_recommendations r
        JOIN analyses a ON r.analysis_id = a.id
        WHERE a.user_id = u.id AND r.priority = 'alta'
    ) as pending_high_priority_actions
FROM users u
LEFT JOIN user_metrics m ON u.id = m.user_id
WHERE u.is_active = true;

-- ============================================
-- VIEW: Alertas de caída de sentimiento
-- ============================================
CREATE OR REPLACE VIEW v_sentiment_alerts AS
WITH sentiment_changes AS (
    SELECT
        a.location,
        a.theme,
        a.sentiment_positive,
        a.created_at,
        LAG(a.sentiment_positive) OVER (
            PARTITION BY a.location, a.theme
            ORDER BY a.created_at
        ) as prev_sentiment
    FROM analyses a
)
SELECT
    location,
    theme,
    sentiment_positive as current_sentiment,
    prev_sentiment,
    (sentiment_positive - prev_sentiment) as change,
    created_at
FROM sentiment_changes
WHERE prev_sentiment IS NOT NULL
  AND (sentiment_positive - prev_sentiment) < -0.15
ORDER BY created_at DESC;

-- ============================================
-- VIEW: Resumen ejecutivo rápido
-- ============================================
CREATE OR REPLACE VIEW v_executive_summary AS
SELECT
    'Total Análisis' as metric,
    COUNT(*)::text as value
FROM analyses
UNION ALL
SELECT
    'Ubicaciones Analizadas',
    COUNT(DISTINCT location)::text
FROM analyses
UNION ALL
SELECT
    'Sentimiento Promedio Positivo',
    ROUND(AVG(sentiment_positive)::numeric * 100, 1)::text || '%'
FROM analyses
UNION ALL
SELECT
    'Tema Más Crítico',
    (SELECT topic_name FROM analysis_topics GROUP BY topic_name ORDER BY AVG(sentiment_negative) DESC LIMIT 1)
UNION ALL
SELECT
    'Ubicación Más Activa',
    (SELECT location FROM analyses GROUP BY location ORDER BY COUNT(*) DESC LIMIT 1);
