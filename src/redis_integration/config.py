#!/usr/bin/env python3
"""
Simplified Redis Configuration for Calendar Service

Consolidated configuration management for Redis pub/sub integration.
Reduces complexity from 385 lines to ~60 lines.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Simplified Redis configuration for calendar service."""

    # Essential settings only
    url: str = "redis://fogis-redis:6379"
    enabled: bool = True
    timeout: int = 5

    # Channel configuration
    channels: Dict[str, str] = None

    def __post_init__(self):
        """Initialize default channels."""
        if self.channels is None:
            self.channels = {
                "match_updates": "fogis:matches:updates",
                "processor_status": "fogis:processor:status",
                "system_alerts": "fogis:system:alerts",
            }

    @classmethod
    def from_environment(cls) -> "RedisConfig":
        """Create Redis configuration from environment variables."""
        config = cls()

        # Load essential configuration only
        config.url = os.getenv("REDIS_URL", config.url)
        config.enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        config.timeout = int(os.getenv("REDIS_TIMEOUT", str(config.timeout)))

        logger.info(f"Redis config: URL={config.url}, Enabled={config.enabled}")
        return config


# Global configuration instance
_config: Optional[RedisConfig] = None


def get_redis_config() -> RedisConfig:
    """Get Redis configuration instance."""
    global _config
    if _config is None:
        _config = RedisConfig.from_environment()
    return _config


def reload_redis_config() -> None:
    """Reload Redis configuration from environment."""
    global _config
    _config = None
