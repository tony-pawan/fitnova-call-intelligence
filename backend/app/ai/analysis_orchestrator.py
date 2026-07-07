import time
from datetime import datetime
from backend.app.ai.analyzers import DiscoveryAnalyzer, ComplianceAnalyzer, SalesQualityAnalyzer
from backend.app.ai.dto.analysis import AnalysisResult, AnalysisMetadata
from backend.app.ai.dto.conversation import ConversationResult
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.utils.timeline import log_pipeline_event

logger = get_logger("ANALYSIS")

class AnalysisOrchestrator:
    """
    Orchestration agent responsible for executing Discovery, Compliance, 
    and Sales Quality agents, handling partial failures, and aggregating score outputs.
    """
    def __init__(self, client = None) -> None:
        self.discovery = DiscoveryAnalyzer(client)
        self.compliance = ComplianceAnalyzer(client)
        self.sales_quality = SalesQualityAnalyzer(client)

    def analyze(self, call_id: int, conversation: ConversationResult) -> AnalysisResult:
        logger.info(f"Starting multi-agent analysis for Call ID {call_id}")
        start_time = time.time()

        completed_analyzers = []
        failed_analyzers = []

        discovery_res = None
        compliance_res = None
        sales_quality_res = None

        # 1. Execute Needs Discovery analysis
        try:
            logger.info("Executing discovery analyzer agent check")
            discovery_res = self.discovery.analyze(conversation)
            if "Analysis Failure" in getattr(discovery_res, "issue_tags", []):
                failed_analyzers.append("discovery")
                log_pipeline_event(call_id, "Analyzer Failed")
            else:
                completed_analyzers.append("discovery")
                log_pipeline_event(call_id, "Discovery Analysis Completed")
        except Exception as e:
            logger.error(f"Discovery analyzer agent threw an exception: {e}")
            failed_analyzers.append("discovery")
            log_pipeline_event(call_id, "Analyzer Failed")

        # 2. Execute Compliance auditing analysis
        try:
            logger.info("Executing compliance analyzer agent check")
            compliance_res = self.compliance.analyze(conversation)
            if "Analysis Failure" in getattr(compliance_res, "issue_tags", []):
                failed_analyzers.append("compliance")
                log_pipeline_event(call_id, "Analyzer Failed")
            else:
                completed_analyzers.append("compliance")
                log_pipeline_event(call_id, "Compliance Analysis Completed")
        except Exception as e:
            logger.error(f"Compliance analyzer agent threw an exception: {e}")
            failed_analyzers.append("compliance")
            log_pipeline_event(call_id, "Analyzer Failed")

        # 3. Execute Sales Pitch Quality analysis
        try:
            logger.info("Executing sales quality analyzer agent check")
            sales_quality_res = self.sales_quality.analyze(conversation)
            if "Analysis Failure" in getattr(sales_quality_res, "issue_tags", []):
                failed_analyzers.append("sales_quality")
                log_pipeline_event(call_id, "Analyzer Failed")
            else:
                completed_analyzers.append("sales_quality")
                log_pipeline_event(call_id, "Sales Quality Analysis Completed")
        except Exception as e:
            logger.error(f"Sales Quality analyzer agent threw an exception: {e}")
            failed_analyzers.append("sales_quality")
            log_pipeline_event(call_id, "Analyzer Failed")

        # 4. Handle Complete Failure (Fail pipeline only if ALL analyzers fail)
        if not completed_analyzers:
            logger.error(f"All multi-agent analysis agents failed execution for Call ID {call_id}")
            log_pipeline_event(call_id, "All Analyzers Failed")
            raise RuntimeError("All configured generative analyzers failed execution.")

        # Helper method to deduplicate lists while preserving order
        def deduplicate(items: list) -> list:
            seen = set()
            return [x for x in items if not (x in seen or seen.add(x))]

        # 5. Merge Outputs & Calculate Overall Score
        scores = []
        summaries = []
        strengths = []
        weaknesses = []
        recommendations = []
        issue_tags = []

        if "discovery" in completed_analyzers and discovery_res:
            scores.append(discovery_res.score)
            summaries.append(f"Discovery: {discovery_res.summary}")
            strengths.extend(discovery_res.strengths)
            weaknesses.extend(discovery_res.weaknesses)
            recommendations.extend(discovery_res.recommendations)
            issue_tags.extend(discovery_res.issue_tags)

        if "compliance" in completed_analyzers and compliance_res:
            scores.append(compliance_res.score)
            summaries.append(f"Compliance: {compliance_res.summary}")
            strengths.extend(compliance_res.strengths)
            weaknesses.extend(compliance_res.weaknesses)
            recommendations.extend(compliance_res.recommendations)
            issue_tags.extend(compliance_res.issue_tags)

        if "sales_quality" in completed_analyzers and sales_quality_res:
            scores.append(sales_quality_res.score)
            summaries.append(f"Sales Quality: {sales_quality_res.summary}")
            strengths.extend(sales_quality_res.strengths)
            weaknesses.extend(sales_quality_res.weaknesses)
            recommendations.extend(sales_quality_res.recommendations)
            issue_tags.extend(sales_quality_res.issue_tags)

        # Mathematical average of analyzer scores
        overall_score = round(sum(scores) / len(scores), 2)
        consolidated_summary = " | ".join(summaries)

        processing_time = round(time.time() - start_time, 2)
        logger.info(f"Aggregation completed in {processing_time}s. Overall score: {overall_score}")
        log_pipeline_event(call_id, "Aggregation Completed")

        # Telemetry metadata mapping
        metadata = AnalysisMetadata(
            model=settings.GEMINI_MODEL,
            processing_time=processing_time,
            analysis_timestamp=datetime.now().isoformat(),
            completed_analyzers=completed_analyzers,
            failed_analyzers=failed_analyzers
        )

        return AnalysisResult(
            overall_score=overall_score,
            summary=consolidated_summary,
            strengths=deduplicate(strengths),
            weaknesses=deduplicate(weaknesses),
            recommendations=deduplicate(recommendations),
            issue_tags=deduplicate(issue_tags),
            analysis_metadata=metadata
        )
