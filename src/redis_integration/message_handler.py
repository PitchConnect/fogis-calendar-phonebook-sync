#!/usr/bin/env python3
"""
Message Handlers for Calendar Service Redis Integration

This module provides message handling capabilities for processing Redis pub/sub messages
in the FOGIS calendar service, including match updates and processing status notifications.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis message handling for calendar service
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MessageProcessingResult:
    """Result of message processing operation."""

    success: bool
    message_type: str
    message_id: Optional[str] = None
    matches_processed: int = 0
    error: Optional[str] = None
    processing_time_ms: float = 0
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class MatchUpdateHandler:
    """Handles match update messages from Redis pub/sub."""

    def __init__(self, calendar_sync_callback: Callable[[List[Dict]], bool] = None):
       """Initialize the instance."""
        """
        Initialize match update handler.

        Args:
            calendar_sync_callback: Function to call for calendar synchronization
        """
        self.calendar_sync_callback = calendar_sync_callback
        self.processing_stats = {
            "total_messages": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "last_processed": None,
            "last_error": None,
        }
        self.processing_lock = threading.Lock()

        logger.info("🔧 Match Update Handler initialized")

    def handle_message(self, message: Dict[str, Any]) -> MessageProcessingResult:
        """
        Handle match update message from Redis.

        Args:
            message: Redis message containing match updates

        Returns:
            MessageProcessingResult: Result of message processing
        """
        start_time = datetime.now()

        with self.processing_lock:
            self.processing_stats["total_messages"] += 1

        try:
            # Validate message structure
            validation_result = self._validate_message(message)
            if not validation_result.success:
                return validation_result

            # Extract message details
            message_id = message.get("message_id")
            message_type = message.get("type")
            payload = message.get("payload", {})

            logger.info(f"📨 Processing match update message: {message_id}")
            logger.info(f"   Type: {message_type}")
            logger.info(f"   Source: {message.get('source', 'unknown')}")

            # Process based on message type
            if message_type == "match_updates":
                result = self._handle_match_updates(message_id, payload)
            elif message_type == "processing_status":
                result = self._handle_processing_status(message_id, payload)
            elif message_type == "system_alert":
                result = self._handle_system_alert(message_id, payload)
            else:
                logger.warning(f"⚠️ Unknown message type: {message_type}")
                result = MessageProcessingResult(
                    success=False,
                    message_type=message_type,
                    message_id=message_id,
                    error=f"Unknown message type: {message_type}",
                )

            # Update processing time
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            result.processing_time_ms = processing_time

            # Update statistics
            with self.processing_lock:
                if result.success:
                    self.processing_stats["successful_messages"] += 1
                    self.processing_stats["last_processed"] = datetime.now().isoformat()
                else:
                    self.processing_stats["failed_messages"] += 1
                    self.processing_stats["last_error"] = result.error

            logger.info(f"✅ Message processing completed in {processing_time:.2f}ms")
            return result

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Failed to process message: {e}"

            logger.error(f"❌ {error_msg}")

            with self.processing_lock:
                self.processing_stats["failed_messages"] += 1
                self.processing_stats["last_error"] = error_msg

            return MessageProcessingResult(
                success=False,
                message_type=message.get("type", "unknown"),
                message_id=message.get("message_id"),
                error=error_msg,
                processing_time_ms=processing_time,
            )

    def _validate_message(self, message: Dict[str, Any]) -> MessageProcessingResult:
        """
        Validate message structure and required fields.

        Args:
            message: Message to validate

        Returns:
            MessageProcessingResult: Validation result
        """
        required_fields = ["message_id", "timestamp", "source", "version", "type", "payload"]

        for field in required_fields:
            if field not in message:
                error_msg = f"Missing required field: {field}"
                logger.error(f"❌ Message validation failed: {error_msg}")
                return MessageProcessingResult(
                    success=False,
                    message_type=message.get("type", "unknown"),
                    message_id=message.get("message_id"),
                    error=error_msg,
                )

        # Validate message version
        if message.get("version") != "1.0":
            error_msg = f"Unsupported message version: {message.get('version')}"
            logger.warning(f"⚠️ {error_msg}")

        return MessageProcessingResult(
            success=True, message_type=message.get("type"), message_id=message.get("message_id")
        )

    def _handle_match_updates(
        self, message_id: str, payload: Dict[str, Any]
    ) -> MessageProcessingResult:
        """
        Handle match updates payload.

        Args:
            message_id: Message identifier
            payload: Match updates payload

        Returns:
            MessageProcessingResult: Processing result
        """
        try:
            matches = payload.get("matches", [])
            metadata = payload.get("metadata", {})

            logger.info(f"📊 Processing {len(matches)} matches")
            logger.info(f"   Has Changes: {metadata.get('has_changes', False)}")
            logger.info(f"   Change Summary: {metadata.get('change_summary', {})}")

            # Check if there are actual changes to process
            if not metadata.get("has_changes", False):
                logger.info("📋 No changes detected - skipping calendar sync")
                return MessageProcessingResult(
                    success=True,
                    message_type="match_updates",
                    message_id=message_id,
                    matches_processed=len(matches),
                )

            # Process matches through calendar sync callback
            if self.calendar_sync_callback:
                logger.info("🗓️ Triggering calendar synchronization...")

                try:
                    sync_success = self.calendar_sync_callback(matches)

                    if sync_success:
                        logger.info("✅ Calendar synchronization completed successfully")
                        return MessageProcessingResult(
                            success=True,
                            message_type="match_updates",
                            message_id=message_id,
                            matches_processed=len(matches),
                        )
                    else:
                        error_msg = "Calendar synchronization failed"
                        logger.error(f"❌ {error_msg}")
                        return MessageProcessingResult(
                            success=False,
                            message_type="match_updates",
                            message_id=message_id,
                            matches_processed=0,
                            error=error_msg,
                        )

                except Exception as e:
                    error_msg = f"Calendar sync callback failed: {e}"
                    logger.error(f"❌ {error_msg}")
                    return MessageProcessingResult(
                        success=False,
                        message_type="match_updates",
                        message_id=message_id,
                        matches_processed=0,
                        error=error_msg,
                    )
            else:
                logger.warning(
                    "⚠️ No calendar sync callback configured - matches processed but not synced"
                )
                return MessageProcessingResult(
                    success=True,
                    message_type="match_updates",
                    message_id=message_id,
                    matches_processed=len(matches),
                )

        except Exception as e:
            error_msg = f"Failed to process match updates: {e}"
            logger.error(f"❌ {error_msg}")
            return MessageProcessingResult(
                success=False, message_type="match_updates", message_id=message_id, error=error_msg
            )

    def _handle_processing_status(
        self, message_id: str, payload: Dict[str, Any]
    ) -> MessageProcessingResult:
        """
        Handle processing status payload.

        Args:
            message_id: Message identifier
            payload: Processing status payload

        Returns:
            MessageProcessingResult: Processing result
        """
        try:
            status = payload.get("status", "unknown")
            cycle_number = payload.get("cycle_number", 0)
            matches_processed = payload.get("matches_processed", 0)

            logger.info(f"📊 Processing status update: {status}")
            logger.info(f"   Cycle: {cycle_number}")
            logger.info(f"   Matches Processed: {matches_processed}")

            # Log processing status for monitoring
            if status == "completed":
                logger.info("✅ Match processor completed successfully")
            elif status == "failed":
                errors = payload.get("errors", [])
                logger.warning(f"⚠️ Match processor failed: {errors}")
            elif status == "started":
                logger.info("🚀 Match processor started")

            return MessageProcessingResult(
                success=True,
                message_type="processing_status",
                message_id=message_id,
                matches_processed=matches_processed,
            )

        except Exception as e:
            error_msg = f"Failed to process status update: {e}"
            logger.error(f"❌ {error_msg}")
            return MessageProcessingResult(
                success=False,
                message_type="processing_status",
                message_id=message_id,
                error=error_msg,
            )

    def _handle_system_alert(
        self, message_id: str, payload: Dict[str, Any]
    ) -> MessageProcessingResult:
        """
        Handle system alert payload.

        Args:
            message_id: Message identifier
            payload: System alert payload

        Returns:
            MessageProcessingResult: Processing result
        """
        try:
            alert_type = payload.get("alert_type", "unknown")
            severity = payload.get("severity", "info")
            message_text = payload.get("message", "")

            logger.info(f"🚨 System alert received: {alert_type}")
            logger.info(f"   Severity: {severity}")
            logger.info(f"   Message: {message_text}")

            # Log alert based on severity
            if severity == "error":
                logger.error(f"🚨 SYSTEM ERROR: {message_text}")
            elif severity == "warning":
                logger.warning(f"⚠️ SYSTEM WARNING: {message_text}")
            else:
                logger.info(f"ℹ️ SYSTEM INFO: {message_text}")

            return MessageProcessingResult(
                success=True, message_type="system_alert", message_id=message_id
            )

        except Exception as e:
            error_msg = f"Failed to process system alert: {e}"
            logger.error(f"❌ {error_msg}")
            return MessageProcessingResult(
                success=False, message_type="system_alert", message_id=message_id, error=error_msg
            )

    def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get message processing statistics.

        Returns:
            Dict[str, Any]: Processing statistics
        """
        with self.processing_lock:
            return self.processing_stats.copy()

    def reset_stats(self) -> None:
        """Reset processing statistics."""
        with self.processing_lock:
            self.processing_stats = {
                "total_messages": 0,
                "successful_messages": 0,
                "failed_messages": 0,
                "last_processed": None,
                "last_error": None,
            }
        logger.info("📊 Processing statistics reset")


class ProcessingStatusHandler:
    """Handles processing status messages for monitoring and logging."""

    def __init__(self):
       """Initialize the instance."""
        """Initialize processing status handler."""
        self.status_history = []
        self.max_history = 100  # Keep last 100 status updates

        logger.info("🔧 Processing Status Handler initialized")

    def handle_status_update(self, message: Dict[str, Any]) -> bool:
        """
        Handle processing status update message.

        Args:
            message: Status update message

        Returns:
            bool: True if handled successfully
        """
        try:
            payload = message.get("payload", {})
            status = payload.get("status", "unknown")
            timestamp = message.get("timestamp", datetime.now().isoformat())

            # Add to history
            status_entry = {
                "timestamp": timestamp,
                "status": status,
                "cycle_number": payload.get("cycle_number", 0),
                "matches_processed": payload.get("matches_processed", 0),
                "processing_duration_ms": payload.get("processing_duration_ms", 0),
            }

            self.status_history.append(status_entry)

            # Trim history if needed
            if len(self.status_history) > self.max_history:
                self.status_history = self.status_history[-self.max_history :]

            logger.info(f"📊 Status update recorded: {status}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to handle status update: {e}")
            return False

    def get_status_history(self) -> List[Dict[str, Any]]:
        """
        Get processing status history.

        Returns:
            List[Dict[str, Any]]: Status history
        """
        return self.status_history.copy()

    def get_latest_status(self) -> Optional[Dict[str, Any]]:
        """
        Get latest processing status.

        Returns:
            Optional[Dict[str, Any]]: Latest status or None if no history
        """
        return self.status_history[-1] if self.status_history else None


# Convenience functions for external use
def create_match_update_handler(
    calendar_sync_callback: Callable[[List[Dict]], bool] = None
) -> MatchUpdateHandler:
    """
    Create match update handler with optional calendar sync callback.

    Args:
        calendar_sync_callback: Function to call for calendar synchronization

    Returns:
        MatchUpdateHandler: Configured message handler
    """
    return MatchUpdateHandler(calendar_sync_callback)


def create_processing_status_handler() -> ProcessingStatusHandler:
    """
    Create processing status handler.

    Returns:
        ProcessingStatusHandler: Configured status handler
    """
    return ProcessingStatusHandler()


if __name__ == "__main__":
    # Test message handlers
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    logger.info("🧪 Testing message handlers...")

    # Test match update handler
    def test_calendar_sync(matches):
        logger.info(f"📅 Test calendar sync called with {len(matches)} matches")
        return True

    handler = create_match_update_handler(test_calendar_sync)

    # Test message
    test_message = {
        "message_id": "test-123",
        "timestamp": datetime.now().isoformat(),
        "source": "match-list-processor",
        "version": "1.0",
        "type": "match_updates",
        "payload": {
            "matches": [{"matchid": 123456, "hemmalag": "Team A", "bortalag": "Team B"}],
            "metadata": {
                "has_changes": True,
                "change_summary": {"new_matches": 1, "updated_matches": 0, "cancelled_matches": 0},
            },
        },
    }

    result = handler.handle_message(test_message)

    if result.success:
        logger.info("✅ Message handler test successful")
        logger.info(f"📊 Processing time: {result.processing_time_ms:.2f}ms")
    else:
        logger.error("❌ Message handler test failed")
        logger.error(f"   Error: {result.error}")

    # Get statistics
    stats = handler.get_processing_stats()
    logger.info("📊 Processing Statistics:")
    logger.info(f"   Total Messages: {stats['total_messages']}")
    logger.info(f"   Successful: {stats['successful_messages']}")
    logger.info(f"   Failed: {stats['failed_messages']}")
