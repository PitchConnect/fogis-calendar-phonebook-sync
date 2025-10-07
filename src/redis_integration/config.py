#!/usr/bin/env python3
"""
Redis Configuration for Calendar Service

Configuration management for Redis pub/sub integration.
"""

import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

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

    # Schema version settings
    schema_version: str = "2.0"
    fallback_schemas: List[str] = None

    def __post_init__(self):
        """Initialize default channels and settings."""
        if self.channels is None:
            self.channels = {
                # Enhanced Schema v2.0 channels (preferred)
                "match_updates_v2": "fogis:matches:updates:v2",
                # Fallback channels for backward compatibility
                "match_updates_v1": "fogis:matches:updates:v1",
                "match_updates": "fogis:matches:updates",
                # Other channels
                "processor_status": "fogis:processor:status",
                "system_alerts": "fogis:system:alerts",
            }

        if self.fallback_schemas is None:
            self.fallback_schemas = ["1.5", "1.0"]

    @classmethod
    def from_environment(cls) -> "RedisConfig":
        """Create Redis configuration from environment variables."""
        config = cls()

        # Load essential configuration
        config.url = os.getenv("REDIS_URL", config.url)
        config.enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"
        config.timeout = int(os.getenv("REDIS_TIMEOUT", str(config.timeout)))

        # Load schema version configuration
        config.schema_version = os.getenv("REDIS_SCHEMA_VERSION", config.schema_version)

        # Load fallback schemas
        fallback_env = os.getenv("REDIS_FALLBACK_SCHEMAS")
        if fallback_env:
            config.fallback_schemas = [s.strip() for s in fallback_env.split(",")]

        logger.info(
            f"Redis config: URL={config.url}, Enabled={config.enabled}, "
            f"Schema={config.schema_version}"
        )
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
