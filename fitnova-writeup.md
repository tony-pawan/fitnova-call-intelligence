# FitNova – Design Write-up

## Problem Statement

The objective of this project was to design and implement an end-to-end AI-powered Sales Call Intelligence platform capable of transforming raw sales call recordings into structured, actionable insights. Beyond simply transcribing conversations, the system evaluates sales quality, identifies compliance risks, surfaces coaching opportunities, and enables human reviewers to validate AI-generated findings.

A key requirement of the assignment was to design the system as a **source-agnostic platform**. Instead of building for a single telephony provider, I focused on creating a modular architecture where new data sources, AI models, and storage backends can be integrated without affecting the overall processing pipeline.

Rather than optimizing for production scale, I prioritized clean architecture, extensibility, explainability, and clear separation of responsibilities across components.

---

# High-Level Architecture

The system follows a sequential processing pipeline:

```
Ingestion
      ↓
Transcription
      ↓
Speaker Diarization
      ↓
AI Quality Analysis
      ↓
Storage
      ↓
Dashboard & Analytics
      ↓
Human Feedback
```

Each stage is isolated behind well-defined interfaces, making it possible to evolve or replace individual components independently.

For example, changing the transcription engine does not require modifications to the analysis engine or dashboard because every stage communicates through structured intermediate data.

This separation of concerns keeps the system maintainable while making future integrations significantly easier.

---

# Major Design Decisions

## 1. Source-Agnostic Ingestion

One of the primary goals was ensuring that the processing pipeline never depends on where the recording originated.

To achieve this, I introduced a connector-based ingestion layer. Every supported source—manual upload, telephony systems, CRM exports, REST APIs, or folder watchers—implements the same interface and converts incoming data into a common `CallInput` object.

This abstraction allows new integrations to be added without modifying downstream processing logic.

Although the prototype currently demonstrates the Manual Upload connector, the architecture supports plugging in additional connectors with minimal effort.

---

## 2. Modular AI Pipeline

Instead of building one large processing function, the workflow is divided into independent stages:

- Speech Transcription
- Speaker Diarization
- AI Quality Analysis
- Storage
- Dashboard Aggregation

Each stage produces structured outputs consumed by the next stage.

This modularity provides several advantages:

- easier debugging
- independent testing
- component replacement
- clearer responsibility boundaries

For example, Faster Whisper could be replaced with another speech recognition model without changing the analysis or dashboard layers.

Similarly, Gemini could later be replaced by another LLM while preserving the same orchestration logic.

---

## 3. Explainable AI

One important design decision was ensuring that AI recommendations are transparent rather than opaque.

Instead of returning only a quality score, the system generates:

- overall score
- category scores
- strengths
- weaknesses
- coaching recommendations
- compliance issues
- transcript evidence with timestamps

Providing supporting evidence allows reviewers to understand why a particular issue was flagged and reduces blind trust in AI-generated decisions.

---

## 4. Human Feedback Loop

Rather than treating AI outputs as final, the platform incorporates a human review stage.

Reviewers can:

- approve findings
- dismiss findings
- mark false positives
- add reviewer comments

This acknowledges that LLM outputs are probabilistic rather than deterministic.

Although the current implementation stores reviewer decisions without retraining the AI models, the stored feedback provides a clear foundation for future prompt optimization or supervised fine-tuning.

---

## 5. Storage Strategy

The application intentionally separates structured relational data from large AI-generated artifacts.

### PostgreSQL

Stores:

- Organizations
- Teams
- Advisors
- Calls
- Analyses
- Issue Tags
- Human Feedback
- Ingestion Sources

These entities benefit from relational queries, filtering, and dashboard aggregations.

### Filesystem Storage

Stores:

- Original audio
- Transcript JSON
- Conversation JSON
- Analysis JSON
- Processing timelines

Large artifacts are stored separately because they are rarely queried relationally but are valuable for auditing and debugging.

This hybrid storage strategy keeps the database lightweight while preserving complete processing history.

---

# Dashboard Philosophy

The dashboard was designed to answer business questions rather than simply display metrics.

Examples include:

- Which advisors consistently perform well?
- Which teams require additional coaching?
- Which compliance issues occur most frequently?
- Which sales competencies are weakest?
- How often do reviewers agree with AI findings?

Instead of overwhelming users with dozens of charts, the dashboard focuses on actionable visualizations such as advisor leaderboards, team comparisons, radar charts, compliance heatmaps, and reviewer analytics.

---

# Engineering Trade-offs

Several deliberate trade-offs were made to balance functionality with implementation complexity.

### Manual Upload

Only the Manual Upload connector is fully implemented.

The connector architecture, however, allows telephony systems, CRM exports, APIs, and folder watchers to be added without modifying the processing pipeline.

### Local Storage

Filesystem storage was chosen instead of cloud object storage (e.g., Amazon S3 or Azure Blob Storage) to simplify deployment while maintaining a clear storage abstraction.

### Asynchronous Processing

Calls are processed asynchronously after upload rather than streamed in real time.

This keeps the architecture simpler while matching the assignment's focus on post-call analytics.

### Human Feedback

Reviewer decisions are stored and surfaced in dashboards but are not currently used to retrain AI models automatically.

This avoids introducing unnecessary machine learning infrastructure while preserving future extensibility.

---

# Edge Cases Considered

During development, several realistic scenarios were considered:

- mixed Hindi-English conversations
- noisy recordings
- low-volume speech
- overlapping speakers
- missing API credentials
- Gemini API quota exhaustion
- Pyannote model loading failures
- duplicate uploads
- corrupted audio files
- human disagreement with AI findings

Fallback mechanisms and deterministic mock responses were implemented where appropriate to ensure the application remains functional even when external services are unavailable.

---

# Limitations

Although the platform demonstrates a complete conversational intelligence workflow, several limitations remain.

Speaker diarization accuracy decreases when multiple speakers interrupt each other frequently.

The quality of AI analysis ultimately depends on the capabilities and consistency of the underlying language model.

The prototype currently relies on local filesystem storage, which would not be suitable for large-scale production deployments.

Similarly, asynchronous background threads would eventually need to be replaced by a distributed task queue such as Celery or RabbitMQ for improved scalability and fault tolerance.

---

# Future Improvements

Several enhancements would move the platform closer to production readiness:

- Live telephony integrations
- CRM synchronization
- Cloud object storage
- Distributed task queues
- Real-time streaming transcription
- Automatic model improvement using reviewer feedback
- Support for multiple LLM providers
- Role-based authentication
- Real-time coaching during live calls

---

# Conclusion

This project was designed with a strong emphasis on modularity, extensibility, and explainability.

Instead of optimizing for a single use case, the architecture separates ingestion, AI processing, storage, analytics, and human review into independent components that can evolve over time.

The result is a complete end-to-end conversational intelligence platform that satisfies the assignment requirements while providing a solid foundation for future production-scale enhancements.
