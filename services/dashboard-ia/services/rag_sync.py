"""
RAG Database Sync for CASTOR ELECCIONES.
Handles synchronization of historical data from database to vector store.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class RAGDatabaseSync:
    """Handles syncing historical data from database to RAG vector store."""

    def __init__(self, db_service, indexer):
        """
        Initialize sync handler.

        Args:
            db_service: DatabaseService instance
            indexer: RAGIndexer instance
        """
        self.db_service = db_service
        self.indexer = indexer

    def sync_all(self, limit: int = 100) -> int:
        """Sync all historical data from database."""
        if not self.db_service:
            logger.warning("No database service configured for RAG sync")
            return 0

        try:
            indexed_count = self._sync_api_calls(limit)
            indexed_count += self._sync_legacy_analyses(limit)

            logger.info(f"Synced {indexed_count} documents from database")
            return indexed_count

        except Exception as e:
            logger.error(f"Error syncing from database: {e}", exc_info=True)
            return 0

    def _sync_api_calls(self, limit: int) -> int:
        """Sync API calls from new model."""
        indexed_count = 0
        api_calls = self.db_service.get_api_calls(limit=limit)

        for api_call in api_calls:
            try:
                count = self._sync_single_api_call(api_call)
                indexed_count += count
            except Exception as e:
                logger.warning(f"Error syncing API call {api_call.get('id')}: {e}")

        return indexed_count

    def _sync_single_api_call(self, api_call: Dict) -> int:
        """Sync a single API call with all its data."""
        api_call_id = api_call.get('id')
        if not api_call_id:
            return 0

        full_data = self.db_service.get_api_call_with_data(api_call_id)
        if not full_data:
            return 0

        metadata = self._build_api_call_metadata(api_call)
        indexed = 0

        indexed += self._index_snapshot(api_call_id, full_data, metadata)
        indexed += self._index_tweets(api_call_id, metadata)
        indexed += self._index_pnd_metrics(api_call_id, full_data, metadata)

        logger.info(f"Synced API call {api_call_id}")
        return indexed

    def _build_api_call_metadata(self, api_call: Dict) -> Dict[str, Any]:
        """Build metadata from API call."""
        return {
            "location": api_call.get('location', 'Colombia'),
            "candidate_name": api_call.get('candidate_name', ''),
            "politician": api_call.get('politician', ''),
            "topic": api_call.get('topic', ''),
            "created_at": api_call.get('fetched_at', '')
        }

    def _index_snapshot(self, api_call_id: str, full_data: Dict, metadata: Dict) -> int:
        """Index analysis snapshot from full data."""
        snapshot = full_data.get('analysis_snapshot')
        if not snapshot:
            return 0

        snapshot_data = {
            'icce': getattr(snapshot, 'icce', 50),
            'sov': getattr(snapshot, 'sov', 0),
            'sna': getattr(snapshot, 'sna', 0),
            'momentum': getattr(snapshot, 'momentum', 0),
            'sentiment_positive': getattr(snapshot, 'sentiment_positive', 0.33),
            'sentiment_negative': getattr(snapshot, 'sentiment_negative', 0.33),
            'sentiment_neutral': getattr(snapshot, 'sentiment_neutral', 0.34),
            'executive_summary': getattr(snapshot, 'executive_summary', ''),
            'key_findings': getattr(snapshot, 'key_findings', []),
            'trending_topics': getattr(snapshot, 'trending_topics', [])
        }
        return self.indexer.index_analysis_snapshot(api_call_id, snapshot_data, metadata)

    def _index_tweets(self, api_call_id: str, metadata: Dict) -> int:
        """Index tweets from database."""
        tweets = self.db_service.get_tweets_by_api_call(api_call_id, limit=200)
        if tweets:
            return self.indexer.index_tweets(api_call_id, tweets, metadata)
        return 0

    def _index_pnd_metrics(self, api_call_id: str, full_data: Dict, metadata: Dict) -> int:
        """Index PND metrics from full data."""
        pnd_metrics = full_data.get('pnd_metrics', [])
        if not pnd_metrics:
            return 0

        pnd_data = [self._extract_pnd_metric(m) for m in pnd_metrics]
        return self.indexer.index_pnd_metrics(api_call_id, pnd_data, metadata)

    def _extract_pnd_metric(self, m) -> Dict[str, Any]:
        """Extract PND metric data from model."""
        return {
            'pnd_axis': getattr(m, 'pnd_axis', ''),
            'pnd_axis_display': getattr(m, 'pnd_axis_display', ''),
            'icce': getattr(m, 'icce', 0),
            'sov': getattr(m, 'sov', 0),
            'sna': getattr(m, 'sna', 0),
            'tweet_count': getattr(m, 'tweet_count', 0),
            'trend': getattr(m, 'trend', 'stable'),
            'sample_tweets': getattr(m, 'sample_tweets', [])
        }

    def _sync_legacy_analyses(self, limit: int) -> int:
        """Sync legacy analyses if they exist."""
        try:
            analyses = self.db_service.get_all_analyses(limit=limit)
            indexed = 0

            for analysis in analyses:
                try:
                    indexed += self._sync_legacy_analysis(analysis)
                except Exception as e:
                    logger.warning(f"Error syncing legacy analysis: {e}")

            return indexed
        except Exception as e:
            logger.debug(f"No legacy analyses to sync: {e}")
            return 0

    def _sync_legacy_analysis(self, analysis: Dict) -> int:
        """Sync a single legacy analysis."""
        analysis_id = analysis.get('id') or str(analysis.get('created_at', ''))
        analysis_data = analysis.get('analysis_data', {})

        if not analysis_data:
            return 0

        doc_ids = self.indexer.index_analysis(
            analysis_id=analysis_id,
            analysis_data=analysis_data,
            metadata={
                "location": analysis.get('location'),
                "theme": analysis.get('theme'),
                "candidate": analysis.get('candidate_name'),
                "created_at": str(analysis.get('created_at', '')),
                "user_id": analysis.get('user_id')
            }
        )
        return len(doc_ids)
