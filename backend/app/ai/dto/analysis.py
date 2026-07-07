from typing import List
from pydantic import BaseModel, Field  # pyrefly: ignore [missing-import]

class DiscoveryAnalysis(BaseModel):
    """
    Structured response model for Needs Discovery analyzer checks.
    """
    score: float = Field(..., ge=0.0, le=100.0, description="Needs discovery performance score")
    summary: str = Field(..., description="High-level needs discovery performance summary")
    strengths: List[str] = Field(default_factory=list, description="List of needs discovery strengths identified")
    weaknesses: List[str] = Field(default_factory=list, description="List of needs discovery weaknesses identified")
    recommendations: List[str] = Field(default_factory=list, description="Needs discovery improvements recommendations")
    issue_tags: List[str] = Field(default_factory=list, description="Associated compliance/discovery risk labels")

class ComplianceAnalysis(BaseModel):
    """
    Structured response model for Script Compliance analyzer checks.
    """
    score: float = Field(..., ge=0.0, le=100.0, description="Compliance audit performance score")
    summary: str = Field(..., description="High-level compliance performance audit summary")
    strengths: List[str] = Field(default_factory=list, description="Compliance strengths observed")
    weaknesses: List[str] = Field(default_factory=list, description="Compliance failures/risks observed")
    recommendations: List[str] = Field(default_factory=list, description="Compliance compliance improvements recommendations")
    issue_tags: List[str] = Field(default_factory=list, description="Associated regulatory risk/compliance labels")

class SalesQualityAnalysis(BaseModel):
    """
    Structured response model for Sales Pitch Quality analyzer checks.
    """
    score: float = Field(..., ge=0.0, le=100.0, description="Sales pitch quality score")
    summary: str = Field(..., description="High-level sales pitch quality summary")
    strengths: List[str] = Field(default_factory=list, description="Sales quality techniques strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Sales quality techniques weaknesses")
    recommendations: List[str] = Field(default_factory=list, description="Objection/pacing technique improvements")
    issue_tags: List[str] = Field(default_factory=list, description="Associated sales technique labels")

class AnalysisMetadata(BaseModel):
    """
    Telemetry and audit metadata for the completed run.
    """
    model: str = Field(..., description="Model identifier used (e.g. gemini-1.5-flash)")
    processing_time: float = Field(..., description="Total execution duration in seconds")
    analysis_timestamp: str = Field(..., description="ISO 8601 timestamp of analysis completion")
    completed_analyzers: List[str] = Field(..., description="Names of analyzers that completed successfully")
    failed_analyzers: List[str] = Field(..., description="Names of analyzers that failed execution")

class AnalysisResult(BaseModel):
    """
    Aggregated final output payload representing the complete call analysis scorecards.
    """
    overall_score: float = Field(..., ge=0.0, le=100.0, description="Aggregated average performance score")
    summary: str = Field(..., description="Consolidated summaries of discovery, compliance, and sales quality checks")
    strengths: List[str] = Field(..., description="Combined deduplicated strengths lists")
    weaknesses: List[str] = Field(..., description="Combined deduplicated weaknesses lists")
    recommendations: List[str] = Field(..., description="Combined deduplicated training recommendations")
    issue_tags: List[str] = Field(..., description="Deduplicated compliance risk or compliance failure tags")
    analysis_metadata: AnalysisMetadata = Field(..., description="Run metadata and analyzer success/failure tracking details")
