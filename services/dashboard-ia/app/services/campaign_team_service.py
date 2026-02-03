"""
Servicio para el Dashboard de Equipo de Campaña Electoral.
Integra datos de E-14 (OCR electoral) con análisis de redes sociales.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.schemas.campaign_team import (
    ActionItem,
    ActionPlanResponse,
    ActionPriority,
    AlertResponse,
    AlertSeverity,
    AlertsListResponse,
    AlertStatus,
    CandidateVoteSummary,
    DashboardSummary,
    E14SocialCorrelation,
    E14SocialCorrelationResponse,
    ForecastVsReality,
    ForecastVsRealityResponse,
    OpportunityZone,
    OpportunityZonesResponse,
    ProcessingProgress,
    RegionalTrend,
    RegionalTrendsResponse,
    VotesByParty,
    VotesReportResponse,
    WarRoomStats,
)

logger = logging.getLogger(__name__)


class CampaignTeamService:
    """Service for Campaign Team Dashboard operations."""

    def __init__(self, db_service=None):
        """
        Initialize the service.

        Args:
            db_service: DatabaseService instance (optional, for dependency injection)
        """
        self._db_service = db_service

    def _get_session(self) -> Session:
        """Get database session."""
        if self._db_service:
            return self._db_service.get_session()
        # Fallback: create new session from current app
        from flask import current_app
        db_service = current_app.extensions.get("database_service")
        if db_service:
            return db_service.get_session()
        raise RuntimeError("No database service available")

    # ============================================================
    # WAR ROOM
    # ============================================================

    def get_war_room_stats(self, contest_id: int) -> WarRoomStats:
        """
        Get KPIs for the War Room.

        Args:
            contest_id: Contest ID to filter by

        Returns:
            WarRoomStats with all KPIs
        """
        session = self._get_session()
        try:
            query = text("""
                SELECT
                    COUNT(DISTINCT pt.id) as total_mesas,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'VALIDATED') as validated,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'NEEDS_REVIEW') as needs_review,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'PENDING') as pending,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'PROCESSING') as processing,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'FAILED') as failed,
                    COUNT(a.id) FILTER (WHERE a.status = 'OPEN' AND a.severity = 'CRITICAL') as critical_alerts,
                    COUNT(a.id) FILTER (WHERE a.status = 'OPEN' AND a.severity = 'HIGH') as high_alerts
                FROM polling_table pt
                LEFT JOIN form_instance fi ON fi.polling_table_id = pt.id
                LEFT JOIN alert a ON a.polling_table_id = pt.id
                WHERE pt.contest_id = :contest_id
            """)

            result = session.execute(query, {"contest_id": contest_id}).fetchone()

            if not result:
                return WarRoomStats()

            total = result.total_mesas or 0
            validated = result.validated or 0
            processed = validated + (result.needs_review or 0)

            validation_rate = (validated / total * 100) if total > 0 else 0.0
            processing_rate = (processed / total * 100) if total > 0 else 0.0

            return WarRoomStats(
                total_mesas=total,
                validated=validated,
                needs_review=result.needs_review or 0,
                pending=result.pending or 0,
                processing=result.processing or 0,
                failed=result.failed or 0,
                critical_alerts=result.critical_alerts or 0,
                high_alerts=result.high_alerts or 0,
                validation_rate=round(validation_rate, 2),
                processing_rate=round(processing_rate, 2)
            )

        except Exception as e:
            logger.error(f"Error getting war room stats: {e}", exc_info=True)
            return WarRoomStats()
        finally:
            session.close()

    def get_processing_progress(self, contest_id: int) -> List[ProcessingProgress]:
        """
        Get processing progress by municipality.

        Args:
            contest_id: Contest ID

        Returns:
            List of ProcessingProgress per municipality
        """
        session = self._get_session()
        try:
            query = text("""
                SELECT
                    pt.dept_code,
                    d.name as dept_name,
                    pt.muni_code,
                    m.name as muni_name,
                    COUNT(DISTINCT pt.id) as total_mesas,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'VALIDATED') as validated,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'NEEDS_REVIEW') as needs_review,
                    COUNT(DISTINCT fi.id) FILTER (WHERE fi.status = 'PENDING') as pending,
                    COUNT(a.id) FILTER (WHERE a.status = 'OPEN' AND a.severity IN ('HIGH', 'CRITICAL')) as critical_alerts
                FROM polling_table pt
                LEFT JOIN department d ON d.code = pt.dept_code
                LEFT JOIN municipality m ON m.code = pt.muni_code
                LEFT JOIN form_instance fi ON fi.polling_table_id = pt.id
                LEFT JOIN alert a ON a.polling_table_id = pt.id
                WHERE pt.contest_id = :contest_id
                GROUP BY pt.dept_code, d.name, pt.muni_code, m.name
                ORDER BY pt.dept_code, pt.muni_code
            """)

            results = session.execute(query, {"contest_id": contest_id}).fetchall()

            progress_list = []
            for row in results:
                total = row.total_mesas or 0
                validated = row.validated or 0
                validation_rate = (validated / total * 100) if total > 0 else 0.0

                progress_list.append(ProcessingProgress(
                    dept_code=row.dept_code,
                    dept_name=row.dept_name,
                    muni_code=row.muni_code,
                    muni_name=row.muni_name,
                    total_mesas=total,
                    validated=validated,
                    needs_review=row.needs_review or 0,
                    pending=row.pending or 0,
                    critical_alerts=row.critical_alerts or 0,
                    validation_rate=round(validation_rate, 2)
                ))

            return progress_list

        except Exception as e:
            logger.error(f"Error getting processing progress: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_alerts(
        self,
        contest_id: int,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50
    ) -> AlertsListResponse:
        """
        Get alerts for the contest.

        Args:
            contest_id: Contest ID
            status: Filter by status (optional)
            severity: Filter by severity (optional)
            limit: Max results

        Returns:
            AlertsListResponse with alerts list
        """
        session = self._get_session()
        try:
            # Build query with optional filters
            query_parts = ["""
                SELECT
                    a.id,
                    a.alert_type,
                    a.severity,
                    a.status,
                    a.title,
                    a.message,
                    a.evidence,
                    a.assigned_to,
                    a.assigned_at,
                    a.created_at,
                    a.updated_at,
                    pt.mesa_id,
                    pt.dept_code,
                    pt.muni_code
                FROM alert a
                LEFT JOIN polling_table pt ON pt.id = a.polling_table_id
                WHERE a.contest_id = :contest_id
            """]

            params = {"contest_id": contest_id, "limit": limit}

            if status:
                query_parts.append("AND a.status = :status")
                params["status"] = status

            if severity:
                query_parts.append("AND a.severity = :severity")
                params["severity"] = severity

            query_parts.append("ORDER BY a.severity DESC, a.created_at DESC LIMIT :limit")

            query = text(" ".join(query_parts))
            results = session.execute(query, params).fetchall()

            alerts = []
            for row in results:
                alerts.append(AlertResponse(
                    id=row.id,
                    alert_type=row.alert_type,
                    severity=AlertSeverity(row.severity) if row.severity else AlertSeverity.INFO,
                    status=AlertStatus(row.status) if row.status else AlertStatus.OPEN,
                    title=row.title,
                    message=row.message,
                    mesa_id=row.mesa_id,
                    dept_code=row.dept_code,
                    muni_code=row.muni_code,
                    assigned_to=row.assigned_to,
                    assigned_at=row.assigned_at,
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                    evidence=row.evidence
                ))

            # Count totals
            count_query = text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status = 'OPEN') as open_count,
                    COUNT(*) FILTER (WHERE status = 'OPEN' AND severity = 'CRITICAL') as critical_count
                FROM alert
                WHERE contest_id = :contest_id
            """)
            counts = session.execute(count_query, {"contest_id": contest_id}).fetchone()

            return AlertsListResponse(
                alerts=alerts,
                total=counts.total if counts else 0,
                open_count=counts.open_count if counts else 0,
                critical_count=counts.critical_count if counts else 0
            )

        except Exception as e:
            logger.error(f"Error getting alerts: {e}", exc_info=True)
            return AlertsListResponse(success=False, alerts=[], total=0, open_count=0, critical_count=0)
        finally:
            session.close()

    def assign_alert(
        self,
        alert_id: int,
        user_id: int,
        notes: Optional[str] = None
    ) -> bool:
        """
        Assign an alert to a user.

        Args:
            alert_id: Alert ID
            user_id: User ID to assign
            notes: Optional notes

        Returns:
            True if successful
        """
        session = self._get_session()
        try:
            query = text("""
                UPDATE alert
                SET assigned_to = :user_id,
                    assigned_at = NOW(),
                    status = 'ACKNOWLEDGED',
                    resolution_notes = COALESCE(resolution_notes || E'\\n', '') || :notes,
                    updated_at = NOW()
                WHERE id = :alert_id
                RETURNING id
            """)

            result = session.execute(query, {
                "alert_id": alert_id,
                "user_id": user_id,
                "notes": notes or f"Assigned to user {user_id}"
            })
            session.commit()

            return result.fetchone() is not None

        except Exception as e:
            session.rollback()
            logger.error(f"Error assigning alert: {e}", exc_info=True)
            return False
        finally:
            session.close()

    # ============================================================
    # REPORTES
    # ============================================================

    def get_votes_by_candidate(self, contest_id: int) -> VotesReportResponse:
        """
        Get votes by candidate from reconciled results.

        Args:
            contest_id: Contest ID

        Returns:
            VotesReportResponse with candidate and party breakdown
        """
        session = self._get_session()
        try:
            # Get contest info
            contest_query = text("SELECT name FROM contest WHERE id = :contest_id")
            contest_result = session.execute(contest_query, {"contest_id": contest_id}).fetchone()
            contest_name = contest_result.name if contest_result else "Unknown Contest"

            # Get votes by candidate
            query = text("""
                SELECT
                    bo.candidate_name,
                    pg.name as party_name,
                    bo.ballot_code,
                    SUM(vt.votes) as total_votes,
                    COUNT(DISTINCT r.polling_table_id) as mesas_count
                FROM reconciliation r
                JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                JOIN ballot_option bo ON bo.id = vt.ballot_option_id
                LEFT JOIN political_group pg ON pg.id = bo.political_group_id
                WHERE r.contest_id = :contest_id
                  AND bo.option_type = 'CANDIDATE'
                GROUP BY bo.candidate_name, pg.name, bo.ballot_code
                ORDER BY total_votes DESC
            """)

            results = session.execute(query, {"contest_id": contest_id}).fetchall()

            # Calculate totals
            total_votes = sum(row.total_votes or 0 for row in results)

            by_candidate = []
            for row in results:
                votes = row.total_votes or 0
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0.0

                by_candidate.append(CandidateVoteSummary(
                    candidate_name=row.candidate_name or "Unknown",
                    party_name=row.party_name,
                    ballot_code=row.ballot_code or "",
                    total_votes=votes,
                    percentage=round(percentage, 2),
                    mesas_count=row.mesas_count or 0
                ))

            # Get votes by party
            party_query = text("""
                SELECT
                    pg.name as party_name,
                    pg.code as party_code,
                    SUM(vt.votes) as total_votes,
                    COUNT(DISTINCT bo.id) as candidates_count
                FROM reconciliation r
                JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                JOIN ballot_option bo ON bo.id = vt.ballot_option_id
                JOIN political_group pg ON pg.id = bo.political_group_id
                WHERE r.contest_id = :contest_id
                GROUP BY pg.name, pg.code
                ORDER BY total_votes DESC
            """)

            party_results = session.execute(party_query, {"contest_id": contest_id}).fetchall()

            by_party = []
            for row in party_results:
                votes = row.total_votes or 0
                percentage = (votes / total_votes * 100) if total_votes > 0 else 0.0

                by_party.append(VotesByParty(
                    party_name=row.party_name or "Independent",
                    party_code=row.party_code,
                    total_votes=votes,
                    percentage=round(percentage, 2),
                    candidates_count=row.candidates_count or 1
                ))

            # Get mesa counts
            mesa_query = text("""
                SELECT
                    COUNT(DISTINCT pt.id) as total_mesas,
                    COUNT(DISTINCT r.polling_table_id) as counted_mesas
                FROM polling_table pt
                LEFT JOIN reconciliation r ON r.polling_table_id = pt.id
                WHERE pt.contest_id = :contest_id
            """)
            mesa_result = session.execute(mesa_query, {"contest_id": contest_id}).fetchone()

            total_mesas = mesa_result.total_mesas if mesa_result else 0
            counted_mesas = mesa_result.counted_mesas if mesa_result else 0
            coverage = (counted_mesas / total_mesas * 100) if total_mesas > 0 else 0.0

            return VotesReportResponse(
                contest_id=contest_id,
                contest_name=contest_name,
                total_votes=total_votes,
                total_mesas=total_mesas,
                mesas_counted=counted_mesas,
                coverage_percentage=round(coverage, 2),
                by_candidate=by_candidate,
                by_party=by_party
            )

        except Exception as e:
            logger.error(f"Error getting votes by candidate: {e}", exc_info=True)
            return VotesReportResponse(
                success=False,
                contest_id=contest_id,
                contest_name="Error",
                total_votes=0,
                total_mesas=0,
                mesas_counted=0,
                coverage_percentage=0,
                by_candidate=[],
                by_party=[]
            )
        finally:
            session.close()

    def get_regional_trends(self, contest_id: int) -> RegionalTrendsResponse:
        """
        Get regional trends by department.

        Args:
            contest_id: Contest ID

        Returns:
            RegionalTrendsResponse with department-level trends
        """
        session = self._get_session()
        try:
            query = text("""
                WITH dept_votes AS (
                    SELECT
                        pt.dept_code,
                        d.name as dept_name,
                        bo.candidate_name,
                        SUM(vt.votes) as votes,
                        COUNT(DISTINCT r.polling_table_id) as mesas
                    FROM reconciliation r
                    JOIN polling_table pt ON pt.id = r.polling_table_id
                    JOIN department d ON d.code = pt.dept_code
                    JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                    JOIN ballot_option bo ON bo.id = vt.ballot_option_id
                    WHERE r.contest_id = :contest_id AND bo.option_type = 'CANDIDATE'
                    GROUP BY pt.dept_code, d.name, bo.candidate_name
                ),
                dept_totals AS (
                    SELECT
                        dept_code,
                        dept_name,
                        SUM(votes) as total_votes,
                        MAX(mesas) as total_mesas
                    FROM dept_votes
                    GROUP BY dept_code, dept_name
                ),
                dept_leaders AS (
                    SELECT DISTINCT ON (dept_code)
                        dept_code,
                        candidate_name as leading_candidate,
                        votes as leading_votes
                    FROM dept_votes
                    ORDER BY dept_code, votes DESC
                )
                SELECT
                    t.dept_code,
                    t.dept_name,
                    t.total_votes,
                    t.total_mesas,
                    l.leading_candidate,
                    l.leading_votes
                FROM dept_totals t
                JOIN dept_leaders l ON l.dept_code = t.dept_code
                ORDER BY t.total_votes DESC
            """)

            results = session.execute(query, {"contest_id": contest_id}).fetchall()

            # Get total mesas per department
            mesas_query = text("""
                SELECT pt.dept_code, COUNT(DISTINCT pt.id) as total
                FROM polling_table pt
                WHERE pt.contest_id = :contest_id
                GROUP BY pt.dept_code
            """)
            mesas_results = session.execute(mesas_query, {"contest_id": contest_id}).fetchall()
            mesas_by_dept = {row.dept_code: row.total for row in mesas_results}

            trends = []
            for row in results:
                total_mesas_dept = mesas_by_dept.get(row.dept_code, row.total_mesas)
                coverage = (row.total_mesas / total_mesas_dept * 100) if total_mesas_dept > 0 else 0.0
                leading_pct = (row.leading_votes / row.total_votes * 100) if row.total_votes > 0 else 0.0

                trends.append(RegionalTrend(
                    dept_code=row.dept_code,
                    dept_name=row.dept_name,
                    total_votes=row.total_votes,
                    total_mesas=total_mesas_dept,
                    coverage=round(coverage, 2),
                    leading_candidate=row.leading_candidate,
                    leading_votes=row.leading_votes,
                    leading_percentage=round(leading_pct, 2)
                ))

            return RegionalTrendsResponse(
                contest_id=contest_id,
                trends=trends,
                total_departments=len(trends),
                total_municipalities=0  # Would need another query
            )

        except Exception as e:
            logger.error(f"Error getting regional trends: {e}", exc_info=True)
            return RegionalTrendsResponse(
                success=False,
                contest_id=contest_id,
                trends=[],
                total_departments=0,
                total_municipalities=0
            )
        finally:
            session.close()

    # ============================================================
    # PLAN DE ACCIÓN
    # ============================================================

    def get_prioritized_actions(self, contest_id: int) -> ActionPlanResponse:
        """
        Generate prioritized action plan based on alerts and opportunity zones.

        Args:
            contest_id: Contest ID

        Returns:
            ActionPlanResponse with categorized actions
        """
        session = self._get_session()
        try:
            actions = {
                "critical": [],
                "high": [],
                "medium": [],
                "low": []
            }

            # 1. Critical alerts -> Critical actions
            alerts_query = text("""
                SELECT
                    a.id,
                    a.title,
                    a.message,
                    a.severity,
                    pt.mesa_id,
                    pt.dept_code,
                    pt.muni_code,
                    d.name as dept_name,
                    m.name as muni_name
                FROM alert a
                JOIN polling_table pt ON pt.id = a.polling_table_id
                LEFT JOIN department d ON d.code = pt.dept_code
                LEFT JOIN municipality m ON m.code = pt.muni_code
                WHERE a.contest_id = :contest_id
                  AND a.status = 'OPEN'
                  AND a.severity IN ('CRITICAL', 'HIGH')
                ORDER BY a.severity DESC, a.created_at ASC
                LIMIT 20
            """)

            alert_results = session.execute(alerts_query, {"contest_id": contest_id}).fetchall()

            for row in alert_results:
                priority = ActionPriority.CRITICAL if row.severity == "CRITICAL" else ActionPriority.HIGH
                zone_name = f"{row.dept_name}, {row.muni_name}" if row.dept_name else row.mesa_id

                action = ActionItem(
                    id=str(uuid.uuid4())[:8],
                    action=f"Resolver alerta: {row.title}",
                    priority=priority,
                    zone=row.mesa_id or f"{row.dept_code}-{row.muni_code}",
                    zone_name=zone_name,
                    resources=["Validador electoral", "Supervisor"],
                    reason=row.message or "Alerta crítica sin resolver",
                    related_alert_id=row.id,
                    related_mesa_id=row.mesa_id,
                    estimated_impact="Alto - Validación de resultados"
                )

                if priority == ActionPriority.CRITICAL:
                    actions["critical"].append(action)
                else:
                    actions["high"].append(action)

            # 2. Low participation zones -> Medium actions
            opportunity_zones = self.get_opportunity_zones(contest_id, limit=10)

            for zone in opportunity_zones.zones[:5]:
                action = ActionItem(
                    id=str(uuid.uuid4())[:8],
                    action=f"Movilizar votantes en {zone.muni_name}",
                    priority=ActionPriority.MEDIUM,
                    zone=f"{zone.dept_code}-{zone.muni_code}",
                    zone_name=f"{zone.dept_name}, {zone.muni_name}",
                    resources=["Equipo de campo", "Transporte", "Comunicaciones"],
                    reason=f"Participación baja: {zone.participation:.1f}% - Potencial: {zone.potential_votes} votos",
                    estimated_impact=f"Potencial de {zone.potential_votes} votos adicionales"
                )
                actions["medium"].append(action)

            # 3. Pending mesas in key zones -> Low actions
            pending_query = text("""
                SELECT
                    pt.dept_code,
                    d.name as dept_name,
                    pt.muni_code,
                    m.name as muni_name,
                    COUNT(pt.id) as pending_mesas
                FROM polling_table pt
                LEFT JOIN form_instance fi ON fi.polling_table_id = pt.id
                LEFT JOIN department d ON d.code = pt.dept_code
                LEFT JOIN municipality m ON m.code = pt.muni_code
                WHERE pt.contest_id = :contest_id
                  AND (fi.id IS NULL OR fi.status = 'PENDING')
                GROUP BY pt.dept_code, d.name, pt.muni_code, m.name
                HAVING COUNT(pt.id) > 5
                ORDER BY COUNT(pt.id) DESC
                LIMIT 5
            """)

            pending_results = session.execute(pending_query, {"contest_id": contest_id}).fetchall()

            for row in pending_results:
                action = ActionItem(
                    id=str(uuid.uuid4())[:8],
                    action=f"Acelerar procesamiento en {row.muni_name}",
                    priority=ActionPriority.LOW,
                    zone=f"{row.dept_code}-{row.muni_code}",
                    zone_name=f"{row.dept_name}, {row.muni_name}",
                    resources=["Digitadores", "Coordinador regional"],
                    reason=f"{row.pending_mesas} mesas pendientes de procesar",
                    estimated_impact=f"Completar conteo de {row.pending_mesas} mesas"
                )
                actions["low"].append(action)

            total = sum(len(v) for v in actions.values())

            return ActionPlanResponse(
                contest_id=contest_id,
                total_actions=total,
                critical_actions=actions["critical"],
                high_actions=actions["high"],
                medium_actions=actions["medium"],
                low_actions=actions["low"]
            )

        except Exception as e:
            logger.error(f"Error generating action plan: {e}", exc_info=True)
            return ActionPlanResponse(
                success=False,
                contest_id=contest_id,
                total_actions=0,
                critical_actions=[],
                high_actions=[],
                medium_actions=[],
                low_actions=[]
            )
        finally:
            session.close()

    def get_opportunity_zones(self, contest_id: int, limit: int = 20) -> OpportunityZonesResponse:
        """
        Get zones with low participation (opportunity for mobilization).

        Args:
            contest_id: Contest ID
            limit: Max results

        Returns:
            OpportunityZonesResponse with low-participation zones
        """
        session = self._get_session()
        try:
            query = text("""
                SELECT
                    pt.dept_code,
                    d.name as dept_name,
                    pt.muni_code,
                    m.name as muni_name,
                    SUM(ml.total_sufragantes_e11) as habilitados,
                    SUM(ml.total_votos_urna) as votaron,
                    ROUND(SUM(ml.total_votos_urna) * 100.0 / NULLIF(SUM(ml.total_sufragantes_e11), 0), 2) as participation
                FROM polling_table pt
                JOIN form_instance fi ON fi.polling_table_id = pt.id
                JOIN mesa_leveling ml ON ml.form_id = fi.id
                LEFT JOIN department d ON d.code = pt.dept_code
                LEFT JOIN municipality m ON m.code = pt.muni_code
                WHERE pt.contest_id = :contest_id
                  AND fi.status = 'VALIDATED'
                GROUP BY pt.dept_code, d.name, pt.muni_code, m.name
                HAVING ROUND(SUM(ml.total_votos_urna) * 100.0 / NULLIF(SUM(ml.total_sufragantes_e11), 0), 2) < 50
                ORDER BY participation ASC
                LIMIT :limit
            """)

            results = session.execute(query, {"contest_id": contest_id, "limit": limit}).fetchall()

            zones = []
            total_potential = 0
            total_participation = 0

            for row in results:
                habilitados = row.habilitados or 0
                votaron = row.votaron or 0
                participation = row.participation or 0.0
                potential = habilitados - votaron

                # Priority score: lower participation + higher potential = higher priority
                priority_score = (100 - participation) * 0.6 + (potential / 1000) * 0.4

                zones.append(OpportunityZone(
                    dept_code=row.dept_code,
                    dept_name=row.dept_name or row.dept_code,
                    muni_code=row.muni_code,
                    muni_name=row.muni_name or row.muni_code,
                    habilitados=habilitados,
                    votaron=votaron,
                    participation=participation,
                    potential_votes=potential,
                    priority_score=round(priority_score, 2)
                ))

                total_potential += potential
                total_participation += participation

            avg_participation = total_participation / len(zones) if zones else 0.0

            return OpportunityZonesResponse(
                contest_id=contest_id,
                zones=zones,
                total_potential=total_potential,
                average_participation=round(avg_participation, 2)
            )

        except Exception as e:
            logger.error(f"Error getting opportunity zones: {e}", exc_info=True)
            return OpportunityZonesResponse(
                success=False,
                contest_id=contest_id,
                zones=[],
                total_potential=0,
                average_participation=0.0
            )
        finally:
            session.close()

    # ============================================================
    # CORRELACIÓN
    # ============================================================

    def get_e14_vs_social_correlation(
        self,
        contest_id: int,
        candidate_name: Optional[str] = None
    ) -> E14SocialCorrelationResponse:
        """
        Get correlation between E-14 results and social media metrics.

        Args:
            contest_id: Contest ID
            candidate_name: Filter by candidate (optional)

        Returns:
            E14SocialCorrelationResponse with correlation data
        """
        session = self._get_session()
        try:
            # Get E-14 data by department
            e14_query = text("""
                SELECT
                    pt.dept_code,
                    d.name as dept_name,
                    SUM(vt.votes) as total_votes
                FROM reconciliation r
                JOIN polling_table pt ON pt.id = r.polling_table_id
                JOIN department d ON d.code = pt.dept_code
                JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                JOIN ballot_option bo ON bo.id = vt.ballot_option_id
                WHERE r.contest_id = :contest_id
                  AND bo.option_type = 'CANDIDATE'
                  AND (:candidate_name IS NULL OR bo.candidate_name = :candidate_name)
                GROUP BY pt.dept_code, d.name
                ORDER BY total_votes DESC
            """)

            e14_results = session.execute(e14_query, {
                "contest_id": contest_id,
                "candidate_name": candidate_name
            }).fetchall()

            # Calculate total for percentages
            total_votes = sum(row.total_votes or 0 for row in e14_results)

            # Try to get social metrics from analysis_snapshot
            # (This joins with the social media analysis data if available)
            social_query = text("""
                SELECT
                    location as dept_name,
                    AVG(icce) as icce_score,
                    AVG(sov) as sov_score,
                    AVG(sentiment) as sentiment_score
                FROM analysis_snapshot
                WHERE candidate_name = :candidate_name
                GROUP BY location
            """)

            social_results = {}
            try:
                social_data = session.execute(social_query, {
                    "candidate_name": candidate_name
                }).fetchall()
                social_results = {row.dept_name.upper(): row for row in social_data}
            except Exception:
                pass  # Social data may not be available

            data_points = []
            insights = []

            for row in e14_results:
                vote_pct = (row.total_votes / total_votes * 100) if total_votes > 0 else 0.0

                # Match with social data if available
                social = social_results.get(row.dept_name.upper())
                icce = social.icce_score if social else None
                sov = social.sov_score if social else None
                sentiment = social.sentiment_score if social else None

                # Calculate expected vs actual if we have ICCE
                expected_diff = None
                if icce is not None:
                    expected_diff = vote_pct - icce
                    if abs(expected_diff) > 10:
                        insights.append(f"Discrepancia en {row.dept_name}: {expected_diff:+.1f}% vs predicción")

                data_points.append(E14SocialCorrelation(
                    dept_code=row.dept_code,
                    dept_name=row.dept_name,
                    total_votes=row.total_votes,
                    vote_percentage=round(vote_pct, 2),
                    icce_score=round(icce, 2) if icce else None,
                    sov_score=round(sov, 2) if sov else None,
                    sentiment_score=round(sentiment, 2) if sentiment else None,
                    expected_vs_actual=round(expected_diff, 2) if expected_diff else None
                ))

            # Calculate correlation if we have enough data points with both values
            r_squared = None
            points_with_icce = [p for p in data_points if p.icce_score is not None]
            if len(points_with_icce) >= 5:
                # Simple correlation calculation
                votes = [p.vote_percentage for p in points_with_icce]
                icces = [p.icce_score for p in points_with_icce]

                mean_v = sum(votes) / len(votes)
                mean_i = sum(icces) / len(icces)

                numerator = sum((v - mean_v) * (i - mean_i) for v, i in zip(votes, icces))
                denom_v = sum((v - mean_v) ** 2 for v in votes) ** 0.5
                denom_i = sum((i - mean_i) ** 2 for i in icces) ** 0.5

                if denom_v > 0 and denom_i > 0:
                    correlation = numerator / (denom_v * denom_i)
                    r_squared = correlation ** 2

            return E14SocialCorrelationResponse(
                contest_id=contest_id,
                candidate_name=candidate_name,
                data_points=data_points,
                r_squared=round(r_squared, 4) if r_squared else None,
                correlation_coefficient=round(r_squared ** 0.5, 4) if r_squared else None,
                insights=insights
            )

        except Exception as e:
            logger.error(f"Error getting E14 vs social correlation: {e}", exc_info=True)
            return E14SocialCorrelationResponse(
                success=False,
                contest_id=contest_id,
                candidate_name=candidate_name,
                data_points=[]
            )
        finally:
            session.close()

    def get_forecast_vs_reality(
        self,
        contest_id: int,
        candidate_name: Optional[str] = None
    ) -> ForecastVsRealityResponse:
        """
        Compare forecast predictions with actual E-14 results.

        Args:
            contest_id: Contest ID
            candidate_name: Filter by candidate (optional)

        Returns:
            ForecastVsRealityResponse with timeline comparison
        """
        session = self._get_session()
        try:
            # Get forecast data from forecast_snapshot
            forecast_query = text("""
                SELECT
                    DATE(created_at) as date,
                    candidate_name,
                    predicted_vote_share,
                    icce_score
                FROM forecast_snapshot
                WHERE candidate_name = :candidate_name
                ORDER BY created_at ASC
            """)

            forecasts = {}
            try:
                forecast_results = session.execute(forecast_query, {
                    "candidate_name": candidate_name
                }).fetchall()

                for row in forecast_results:
                    date_str = row.date.strftime("%Y-%m-%d") if row.date else None
                    if date_str:
                        forecasts[date_str] = {
                            "votes": row.predicted_vote_share,
                            "icce": row.icce_score
                        }
            except Exception:
                pass  # Forecast data may not be available

            # Get actual E-14 results (current state)
            actual_query = text("""
                SELECT
                    SUM(vt.votes) as total_votes
                FROM reconciliation r
                JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                JOIN ballot_option bo ON bo.id = vt.ballot_option_id
                WHERE r.contest_id = :contest_id
                  AND bo.option_type = 'CANDIDATE'
                  AND (:candidate_name IS NULL OR bo.candidate_name = :candidate_name)
            """)

            actual_result = session.execute(actual_query, {
                "contest_id": contest_id,
                "candidate_name": candidate_name
            }).fetchone()

            actual_votes = actual_result.total_votes if actual_result else 0

            # Get total votes for percentage
            total_query = text("""
                SELECT SUM(vt.votes) as total
                FROM reconciliation r
                JOIN vote_tally vt ON vt.form_id = r.chosen_form_id
                WHERE r.contest_id = :contest_id
            """)
            total_result = session.execute(total_query, {"contest_id": contest_id}).fetchone()
            total_all_votes = total_result.total if total_result else 0

            actual_pct = (actual_votes / total_all_votes * 100) if total_all_votes > 0 else 0.0

            # Build timeline
            timeline = []
            insights = []
            errors = []

            # Add forecast entries
            for date_str, forecast in sorted(forecasts.items()):
                timeline.append(ForecastVsReality(
                    date=date_str,
                    forecast_votes=None,
                    forecast_percentage=forecast.get("votes"),
                    forecast_icce=forecast.get("icce"),
                    actual_votes=None,
                    actual_percentage=None,
                    delta_votes=None,
                    delta_percentage=None,
                    accuracy=None
                ))

            # Add final actual result
            today = datetime.utcnow().strftime("%Y-%m-%d")

            # Find the closest forecast to compare
            last_forecast_pct = None
            if timeline:
                last_forecast_pct = timeline[-1].forecast_percentage

            delta_pct = None
            accuracy = None
            if last_forecast_pct is not None:
                delta_pct = actual_pct - last_forecast_pct
                accuracy = 100 - abs(delta_pct)
                errors.append(abs(delta_pct))

                if delta_pct > 5:
                    insights.append(f"Resultado {delta_pct:.1f}% mejor que el pronóstico")
                elif delta_pct < -5:
                    insights.append(f"Resultado {abs(delta_pct):.1f}% por debajo del pronóstico")
                else:
                    insights.append("Resultado cercano al pronóstico")

            timeline.append(ForecastVsReality(
                date=today,
                forecast_votes=None,
                forecast_percentage=last_forecast_pct,
                forecast_icce=None,
                actual_votes=actual_votes,
                actual_percentage=round(actual_pct, 2),
                delta_votes=None,
                delta_percentage=round(delta_pct, 2) if delta_pct else None,
                accuracy=round(accuracy, 2) if accuracy else None
            ))

            overall_accuracy = 100 - (sum(errors) / len(errors)) if errors else None
            mae = sum(errors) / len(errors) if errors else None

            return ForecastVsRealityResponse(
                contest_id=contest_id,
                candidate_name=candidate_name,
                timeline=timeline,
                overall_accuracy=round(overall_accuracy, 2) if overall_accuracy else None,
                mean_absolute_error=round(mae, 2) if mae else None,
                insights=insights
            )

        except Exception as e:
            logger.error(f"Error getting forecast vs reality: {e}", exc_info=True)
            return ForecastVsRealityResponse(
                success=False,
                contest_id=contest_id,
                candidate_name=candidate_name,
                timeline=[]
            )
        finally:
            session.close()

    # ============================================================
    # DASHBOARD SUMMARY
    # ============================================================

    def get_dashboard_summary(self, contest_id: int) -> DashboardSummary:
        """
        Get complete dashboard summary.

        Args:
            contest_id: Contest ID

        Returns:
            DashboardSummary with all key metrics
        """
        session = self._get_session()
        try:
            # Get contest info
            contest_query = text("""
                SELECT c.name, e.election_date
                FROM contest c
                JOIN election e ON e.id = c.election_id
                WHERE c.id = :contest_id
            """)
            contest_result = session.execute(contest_query, {"contest_id": contest_id}).fetchone()

            contest_name = contest_result.name if contest_result else "Unknown"
            election_date = contest_result.election_date.strftime("%Y-%m-%d") if contest_result else ""

            # Get war room stats
            war_room = self.get_war_room_stats(contest_id)

            # Get leading candidate
            votes_report = self.get_votes_by_candidate(contest_id)
            leading = votes_report.by_candidate[0] if votes_report.by_candidate else None

            # Get pending counts
            alerts = self.get_alerts(contest_id, status="OPEN")
            actions = self.get_prioritized_actions(contest_id)

            return DashboardSummary(
                contest_id=contest_id,
                contest_name=contest_name,
                election_date=election_date,
                war_room=war_room,
                total_votes_counted=votes_report.total_votes,
                leading_candidate=leading.candidate_name if leading else None,
                leading_percentage=leading.percentage if leading else 0.0,
                pending_alerts=alerts.open_count,
                pending_actions=actions.total_actions
            )

        except Exception as e:
            logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
            return DashboardSummary(
                success=False,
                contest_id=contest_id,
                contest_name="Error",
                election_date="",
                war_room=WarRoomStats()
            )
        finally:
            session.close()


# Singleton instance
_campaign_team_service: Optional[CampaignTeamService] = None


def get_campaign_team_service(db_service=None) -> CampaignTeamService:
    """Get or create CampaignTeamService singleton."""
    global _campaign_team_service
    if _campaign_team_service is None:
        _campaign_team_service = CampaignTeamService(db_service=db_service)
    return _campaign_team_service
