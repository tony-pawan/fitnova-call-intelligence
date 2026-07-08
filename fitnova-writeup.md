# FitNova Sales Call Intelligence System

## Overview

The objective of this project was to build an end-to-end AI-powered Sales Call Intelligence System that automatically processes sales conversations and converts them into actionable insights. The system ingests call recordings, transcribes speech, identifies speakers, evaluates sales quality using AI, stores structured results, and presents them through interactive dashboards. A human feedback loop allows reviewers to validate AI-generated findings and improve decision quality.

The architecture was designed to be modular, extensible, and source-agnostic so that additional call sources or AI models can be integrated with minimal changes.

---

# System Architecture

The application follows a pipeline-based architecture:

1. Source-Agnostic Ingestion
2. Speech Transcription
3. Speaker Diarization
4. AI Quality Analysis
5. Storage
6. Analytics Dashboard
7. Human Feedback Loop

Each stage is isolated, allowing components to evolve independently while keeping the overall workflow simple and scalable.

---

# Design Decisions

## Source-Agnostic Ingestion

Rather than coupling the application to a specific telephony provider, I designed the ingestion layer around connector abstractions. The current prototype demonstrates manual file upload, but the same pipeline can support telephony systems, CRM exports, APIs, and folder-based imports without changing downstream processing.

## Modular AI Pipeline

The processing pipeline is divided into independent stages:

- Faster Whisper for speech transcription
- Pyannote for speaker diarization
- Gemini multi-agent analysis for call evaluation

Each stage produces structured outputs that are consumed by the next stage.

## Storage Strategy

Structured metadata such as calls, teams, advisors, scores, issue tags, and reviewer feedback are stored in PostgreSQL.

Large artifacts including transcripts, conversations, AI analyses, and processing timelines are stored as JSON files on the filesystem.

This separation keeps database queries efficient while preserving complete audit information.

## Human Feedback Loop

Instead of treating AI decisions as final, reviewers can approve, dismiss, or mark flagged issues as false positives. This provides explainability and establishes a foundation for future model improvement.

---

# Trade-offs

To keep the project focused within the assignment scope, I made several trade-offs:

- Implemented the manual upload connector while designing the ingestion layer to support additional sources.
- Used local filesystem storage instead of cloud object storage such as Amazon S3.
- Used asynchronous background processing instead of real-time streaming.
- Stored reviewer feedback without implementing automatic model retraining.

These choices reduced implementation complexity while keeping the architecture extensible.

---

# Edge Cases Considered

The system accounts for several realistic scenarios:

- Mixed Hindi-English conversations
- Poor audio quality
- Mono recordings
- Speaker diarization failures
- Duplicate processing prevention
- API failures with retry/fallback mechanisms
- Human review of incorrect AI flags

---

# Limitations

The current implementation has several known limitations:

- Speaker diarization accuracy decreases for overlapping conversations.
- AI quality depends on the underlying language model.
- Manual upload is the only fully implemented connector, although the architecture supports additional ingestion sources.
- Filesystem storage should be replaced with cloud object storage for production-scale deployments.

---

# Conclusion

The final system demonstrates a complete conversational intelligence pipeline from ingestion through AI analysis, storage, dashboard visualization, and human review. While simplified for the assignment, the architecture is modular and designed to scale with additional connectors, storage backends, and AI models.
