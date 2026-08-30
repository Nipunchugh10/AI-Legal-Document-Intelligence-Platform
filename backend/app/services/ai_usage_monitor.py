"""
Google Gemini AI Usage Monitor & Quota Telemetry Service
--------------------------------------------------------
Tracks daily Google Gemini free-tier API request counts, rate limit events, and
triggers early warnings at 80% quota consumption to prevent disruptions.

Day 44 — Free AI Stack Resilience and Rate Limit Monitoring (Pure Gemini Architecture)
"""

import time
import threading
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class AIUsageEvent:
    """Individual recorded Gemini LLM invocation event."""

    def __init__(self, provider: str, model: str, status: str = "success", error: Optional[str] = None):
        self.timestamp = time.time()
        self.provider = provider.lower()
        self.model = model
        self.status = status  # 'success', 'rate_limited', 'error'
        self.error = error


class AIUsageMonitor:
    """Thread-safe rolling 24-hour Gemini API request monitor and quota alert system."""

    def __init__(self):
        self._events: List[AIUsageEvent] = []
        self._lock = threading.Lock()
        self.gemini_daily_limit = 1500  # Google AI Studio Free Tier RPD
        self.warning_threshold_ratio = 0.80  # 80% = 1,200 requests/day

    def record_call(self, provider: str, model: str, status: str = "success", error: Optional[str] = None) -> None:
        """Records an API invocation event and evaluates warning threshold."""
        event = AIUsageEvent(provider=provider, model=model, status=status, error=error)
        with self._lock:
            self._events.append(event)
            self._prune_expired_events()

        # Check threshold and log warning if 80% capacity is reached
        metrics = self.get_usage_metrics()
        gemini_metrics = metrics["gemini"]
        if gemini_metrics["is_warning_threshold_exceeded"]:
            logger.warning(
                "⚠️ AI USAGE ALERT: Google Gemini has reached %d / %d daily requests (%.1f%% of free tier quota). Multi-model failover buffer active.",
                gemini_metrics["calls_24h"],
                gemini_metrics["daily_limit"],
                gemini_metrics["usage_percent"],
            )

    def _prune_expired_events(self) -> None:
        """Removes events older than 24 hours."""
        cutoff = time.time() - 86400  # 24 hours
        self._events = [e for e in self._events if e.timestamp >= cutoff]

    def get_usage_metrics(self) -> Dict[str, Any]:
        """Calculates 24-hour rolling call metrics for Google Gemini."""
        with self._lock:
            self._prune_expired_events()
            events_snapshot = list(self._events)

        gemini_calls = [e for e in events_snapshot if "gemini" in e.provider or "google" in e.provider]
        gemini_count = len(gemini_calls)

        gemini_percent = round((gemini_count / self.gemini_daily_limit) * 100, 2)
        gemini_warning = gemini_count >= int(self.gemini_daily_limit * self.warning_threshold_ratio)

        # Per-model breakdown
        model_counts: Dict[str, int] = {}
        for e in gemini_calls:
            model_counts[e.model] = model_counts.get(e.model, 0) + 1

        if gemini_warning:
            health_status = "warning_quota_high"
            alert_msg = f"Gemini usage is at {gemini_percent}% of free daily limit."
        else:
            health_status = "healthy"
            alert_msg = None

        return {
            "window_hours": 24,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "gemini": {
                "provider": "Google Gemini (Free Tier)",
                "calls_24h": gemini_count,
                "daily_limit": self.gemini_daily_limit,
                "warning_threshold": int(self.gemini_daily_limit * self.warning_threshold_ratio),
                "usage_percent": gemini_percent,
                "is_warning_threshold_exceeded": gemini_warning,
                "success_count": len([e for e in gemini_calls if e.status == "success"]),
                "rate_limited_count": len([e for e in gemini_calls if e.status == "rate_limited"]),
                "error_count": len([e for e in gemini_calls if e.status == "error"]),
                "model_breakdown": model_counts,
            },
            "summary": {
                "status": health_status,
                "total_calls_24h": gemini_count,
                "gemini_operational": True,
                "alert_message": alert_msg,
            },
        }

    def clear(self) -> None:
        """Resets all recorded telemetry events."""
        with self._lock:
            self._events.clear()


# Global Singleton Instance
ai_usage_monitor = AIUsageMonitor()
