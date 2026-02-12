"""metrics.py

Centralized metrics tracking for the AURA processing pipeline.
Tracks scraping, LLM processing, database operations, errors, and timing.

Jan 2026
"""
import time
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


# Error categories for structured error tracking
class ErrorCategory:
    SCRAPING_ERROR = "SCRAPING_ERROR"
    LLM_ERROR = "LLM_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PIPELINE_ERROR = "PIPELINE_ERROR"


@dataclass
class ErrorRecord:
    """Structured error record with context"""
    category: str
    message: str
    context: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PipelineMetrics:
    """
    Centralized metrics tracking for the entire AURA pipeline.

    Usage:
        metrics = PipelineMetrics(run_date="2026-01-30")

        metrics.start_stage("scraping")
        metrics.increment("scraping.pdfs_downloaded")
        metrics.end_stage("scraping")

        metrics.record_error(ErrorCategory.SCRAPING_ERROR, "Download failed", {"arxiv_id": "123"})

        summary = metrics.get_summary()
        json_data = metrics.to_json()
    """

    def __init__(self, run_date: str):
        self.run_date = run_date
        self.start_time = time.time()

        # Scraping metrics
        self.scraping = {
            "papers_requested": 0,
            "metadata_fetched": 0,
            "pdfs_attempted": 0,
            "pdfs_downloaded": 0,
            "pdfs_failed": 0,
            "text_extraction_attempted": 0,
            "text_extraction_succeeded": 0,
            "text_extraction_failed": 0,
        }

        # LLM processing metrics
        self.llm = {
            "papers_processed": 0,
            "papers_skipped_no_text": 0,
            "keywords_extraction_success": 0,
            "keywords_extraction_failed": 0,
            "definitions_extraction_success": 0,
            "definitions_extraction_failed": 0,
            "total_keywords_extracted": 0,
            "total_definitions_extracted": 0,
            "keywords_without_definitions": 0,
        }

        # Database metrics
        self.database = {
            "papers_attempted": 0,
            "papers_inserted": 0,
            "papers_duplicate": 0,
            "papers_no_definitions": 0,
            "papers_error": 0,
            "keywords_new": 0,
            "keywords_existing": 0,
            "keywords_total": 0,
        }

        # Timing metrics (stage_name -> duration in seconds)
        self.timing = {}
        self._stage_start_times = {}

        # Error log
        self.errors: List[ErrorRecord] = []

    def increment(self, metric_path: str, amount: int = 1) -> None:
        """
        Increment a metric by path notation.

        Args:
            metric_path: Dot-separated path like "scraping.pdfs_downloaded"
            amount: Amount to increment by (default: 1)

        Example:
            metrics.increment("scraping.pdfs_downloaded")
            metrics.increment("llm.total_keywords_extracted", 3)
        """
        parts = metric_path.split(".")
        if len(parts) != 2:
            raise ValueError(f"Metric path must be in format 'category.metric', got: {metric_path}")

        category, metric = parts

        if category == "scraping":
            if metric not in self.scraping:
                raise ValueError(f"Unknown scraping metric: {metric}")
            self.scraping[metric] += amount
        elif category == "llm":
            if metric not in self.llm:
                raise ValueError(f"Unknown LLM metric: {metric}")
            self.llm[metric] += amount
        elif category == "database":
            if metric not in self.database:
                raise ValueError(f"Unknown database metric: {metric}")
            self.database[metric] += amount
        else:
            raise ValueError(f"Unknown metric category: {category}")

    def get(self, metric_path: str) -> int:
        """
        Get a metric value by path notation.

        Args:
            metric_path: Dot-separated path like "scraping.pdfs_downloaded"

        Returns:
            Current value of the metric
        """
        parts = metric_path.split(".")
        if len(parts) != 2:
            raise ValueError(f"Metric path must be in format 'category.metric', got: {metric_path}")

        category, metric = parts

        if category == "scraping":
            return self.scraping.get(metric, 0)
        elif category == "llm":
            return self.llm.get(metric, 0)
        elif category == "database":
            return self.database.get(metric, 0)
        elif category == "timing":
            return self.timing.get(metric, 0.0)
        else:
            raise ValueError(f"Unknown metric category: {category}")

    def start_stage(self, stage_name: str) -> None:
        """
        Start timing a pipeline stage.

        Args:
            stage_name: Name of the stage (e.g., "scraping", "llm_processing", "database")
        """
        self._stage_start_times[stage_name] = time.time()

    def end_stage(self, stage_name: str) -> float:
        """
        End timing a pipeline stage and record duration.

        Args:
            stage_name: Name of the stage

        Returns:
            Duration in seconds

        Raises:
            ValueError: If stage was not started
        """
        if stage_name not in self._stage_start_times:
            raise ValueError(f"Stage '{stage_name}' was not started")

        duration = time.time() - self._stage_start_times[stage_name]
        self.timing[stage_name] = duration
        del self._stage_start_times[stage_name]
        return duration

    def record_error(self, category: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a structured error with context.

        Args:
            category: Error category (use ErrorCategory constants)
            message: Human-readable error message
            context: Additional context dict (paper_id, arxiv_id, etc.)
        """
        error = ErrorRecord(
            category=category,
            message=message,
            context=context or {}
        )
        self.errors.append(error)

    def get_summary(self) -> str:
        """
        Generate a human-readable summary report.

        Returns:
            Multi-line string with formatted metrics
        """
        total_time = time.time() - self.start_time

        lines = []
        lines.append("=" * 80)
        lines.append(f"AURA Pipeline Summary - {self.run_date}")
        lines.append("=" * 80)
        lines.append("")

        # Scraping metrics
        lines.append("SCRAPING METRICS:")
        lines.append(f"  Papers requested:        {self.scraping['papers_requested']}")
        lines.append(f"  Metadata fetched:        {self.scraping['metadata_fetched']} ({self._percent(self.scraping['metadata_fetched'], self.scraping['papers_requested'])})")
        lines.append(f"  PDFs downloaded:         {self.scraping['pdfs_downloaded']} ({self._percent(self.scraping['pdfs_downloaded'], self.scraping['pdfs_attempted'])})")
        lines.append(f"  PDFs failed:             {self.scraping['pdfs_failed']}")
        lines.append(f"  Text extracted:          {self.scraping['text_extraction_succeeded']} ({self._percent(self.scraping['text_extraction_succeeded'], self.scraping['text_extraction_attempted'])})")
        if "scraping" in self.timing:
            lines.append(f"  Duration:                {self.timing['scraping']:.1f}s")
        lines.append("")

        # LLM metrics
        lines.append("LLM PROCESSING METRICS:")
        lines.append(f"  Papers processed:        {self.llm['papers_processed']}")
        lines.append(f"  Papers skipped (no text): {self.llm['papers_skipped_no_text']}")
        lines.append(f"  Keyword extraction:      {self.llm['keywords_extraction_success']} succeeded, {self.llm['keywords_extraction_failed']} failed ({self._percent(self.llm['keywords_extraction_success'], self.llm['papers_processed'])})")
        lines.append(f"  Definition extraction:   {self.llm['definitions_extraction_success']} succeeded, {self.llm['definitions_extraction_failed']} failed ({self._percent(self.llm['definitions_extraction_success'], self.llm['papers_processed'])})")
        lines.append(f"  Total keywords:          {self.llm['total_keywords_extracted']}")
        lines.append(f"  Valid definitions:       {self.llm['total_definitions_extracted']} ({self._percent(self.llm['total_definitions_extracted'], self.llm['total_keywords_extracted'])})")
        lines.append(f"  Keywords w/o definitions: {self.llm['keywords_without_definitions']}")
        if "llm_processing" in self.timing:
            avg_time = self.timing['llm_processing'] / max(self.llm['papers_processed'], 1)
            lines.append(f"  Duration:                {self.timing['llm_processing']:.1f}s (avg {avg_time:.1f}s per paper)")
        lines.append("")

        # Database metrics
        lines.append("DATABASE METRICS:")
        lines.append(f"  Papers attempted:        {self.database['papers_attempted']}")
        lines.append(f"  Papers inserted:         {self.database['papers_inserted']} ({self._percent(self.database['papers_inserted'], self.database['papers_attempted'])})")
        lines.append(f"  Papers duplicate:        {self.database['papers_duplicate']}")
        lines.append(f"  Papers no definitions:   {self.database['papers_no_definitions']} ({self._percent(self.database['papers_no_definitions'], self.database['papers_attempted'])})")
        lines.append(f"  Papers error:            {self.database['papers_error']}")
        lines.append(f"  New keywords:            {self.database['keywords_new']}")
        lines.append(f"  Existing keywords:       {self.database['keywords_existing']}")
        lines.append(f"  Total keywords:          {self.database['keywords_total']}")
        if "database" in self.timing:
            lines.append(f"  Duration:                {self.timing['database']:.1f}s")
        lines.append("")

        # Errors
        if self.errors:
            lines.append(f"ERRORS ({len(self.errors)} total):")
            for error in self.errors:
                lines.append(f"  [{error.category}] {error.message}")
                if error.context:
                    context_str = ", ".join(f"{k}={v}" for k, v in error.context.items())
                    lines.append(f"    Context: {context_str}")
            lines.append("")

        # Timing breakdown
        if self.timing:
            lines.append("TIMING BREAKDOWN:")
            for stage, duration in sorted(self.timing.items()):
                percentage = (duration / total_time * 100) if total_time > 0 else 0
                lines.append(f"  {stage:20s} {duration:6.1f}s ({percentage:5.1f}%)")
            lines.append(f"  {'TOTAL':20s} {total_time:6.1f}s")

        lines.append("=" * 80)

        return "\n".join(lines)

    def to_json(self) -> str:
        """
        Export all metrics as JSON.

        Returns:
            JSON string with all metrics, timing, and errors
        """
        data = {
            "run_date": self.run_date,
            "total_duration": time.time() - self.start_time,
            "scraping": self.scraping,
            "llm": self.llm,
            "database": self.database,
            "timing": self.timing,
            "errors": [error.to_dict() for error in self.errors]
        }
        return json.dumps(data, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export all metrics as a dictionary.

        Returns:
            Dictionary with all metrics, timing, and errors
        """
        return {
            "run_date": self.run_date,
            "total_duration": time.time() - self.start_time,
            "scraping": self.scraping.copy(),
            "llm": self.llm.copy(),
            "database": self.database.copy(),
            "timing": self.timing.copy(),
            "errors": [error.to_dict() for error in self.errors]
        }

    @staticmethod
    def _percent(numerator: int, denominator: int) -> str:
        """Helper to format percentage strings"""
        if denominator == 0:
            return "N/A"
        return f"{(numerator / denominator * 100):.1f}%"


if __name__ == "__main__":
    # Example usage
    metrics = PipelineMetrics(run_date="2026-01-30")

    # Simulate scraping
    metrics.start_stage("scraping")
    metrics.increment("scraping.papers_requested", 10)
    metrics.increment("scraping.metadata_fetched", 10)
    metrics.increment("scraping.pdfs_attempted", 10)
    metrics.increment("scraping.pdfs_downloaded", 8)
    metrics.increment("scraping.pdfs_failed", 2)
    metrics.increment("scraping.text_extraction_attempted", 8)
    metrics.increment("scraping.text_extraction_succeeded", 8)
    time.sleep(0.1)  # Simulate work
    metrics.end_stage("scraping")

    # Simulate LLM processing
    metrics.start_stage("llm_processing")
    metrics.increment("llm.papers_processed", 8)
    metrics.increment("llm.keywords_extraction_success", 8)
    metrics.increment("llm.total_keywords_extracted", 24)
    metrics.increment("llm.definitions_extraction_success", 6)
    metrics.increment("llm.definitions_extraction_failed", 2)
    metrics.increment("llm.total_definitions_extracted", 18)
    metrics.increment("llm.keywords_without_definitions", 6)
    time.sleep(0.1)  # Simulate work
    metrics.end_stage("llm_processing")

    # Record some errors
    metrics.record_error(
        ErrorCategory.SCRAPING_ERROR,
        "Failed to download PDF: Connection timeout",
        {"arxiv_id": "2401.12345", "url": "https://arxiv.org/pdf/2401.12345"}
    )

    # Print summary
    print(metrics.get_summary())
    print("\nJSON Export:")
    print(metrics.to_json())
