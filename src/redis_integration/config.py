#!/usr/bin/env python3
"""
Redis Configuration for Calendar Service

This module provides Redis configuration management for the FOGIS calendar service,
including environment variable handling and configuration validation.

Author: FOGIS System Architecture Team
Date: 2025-09-22
Issue: Redis configuration for calendar service
"""

import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class RedisSubscriptionConfig:
    """Redis subscription configuration for calendar service."""
    
    # Connection settings
    url: str = "redis://fogis-redis:6379"
    enabled: bool = True
    
    # Connection timeouts
    socket_connect_timeout: int = 5
    socket_timeout: int = 5
    retry_on_timeout: bool = True
    
    # Connection management
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_interval: int = 30
    subscription_timeout: int = 1
    
    # Channel configuration
    match_updates_channel: str = "fogis:matches:updates"
    processor_status_channel: str = "fogis:processor:status"
    system_alerts_channel: str = "fogis:system:alerts"
    
    # Subscription settings
    decode_responses: bool = True
    auto_reconnect: bool = True
    
    @classmethod
    def from_environment(cls) -> 'RedisSubscriptionConfig':
        """
        Create Redis configuration from environment variables.
        
        Returns:
            RedisSubscriptionConfig: Configuration loaded from environment
        """
        config = cls()
        
        # Load configuration from environment variables
        config.url = os.getenv('REDIS_URL', config.url)
        config.enabled = os.getenv('REDIS_PUBSUB_ENABLED', 'true').lower() == 'true'
        
        # Connection timeouts
        config.socket_connect_timeout = int(os.getenv('REDIS_CONNECTION_TIMEOUT', str(config.socket_connect_timeout)))
        config.socket_timeout = int(os.getenv('REDIS_SOCKET_TIMEOUT', str(config.socket_timeout)))
        config.retry_on_timeout = os.getenv('REDIS_RETRY_ON_TIMEOUT', 'true').lower() == 'true'
        
        # Connection management
        config.max_retries = int(os.getenv('REDIS_MAX_RETRIES', str(config.max_retries)))
        config.retry_delay = float(os.getenv('REDIS_RETRY_DELAY', str(config.retry_delay)))
        config.health_check_interval = int(os.getenv('REDIS_HEALTH_CHECK_INTERVAL', str(config.health_check_interval)))
        config.subscription_timeout = int(os.getenv('REDIS_SUBSCRIPTION_TIMEOUT', str(config.subscription_timeout)))
        
        # Channel configuration
        config.match_updates_channel = os.getenv('REDIS_MATCH_UPDATES_CHANNEL', config.match_updates_channel)
        config.processor_status_channel = os.getenv('REDIS_PROCESSOR_STATUS_CHANNEL', config.processor_status_channel)
        config.system_alerts_channel = os.getenv('REDIS_SYSTEM_ALERTS_CHANNEL', config.system_alerts_channel)
        
        # Subscription settings
        config.decode_responses = os.getenv('REDIS_DECODE_RESPONSES', 'true').lower() == 'true'
        config.auto_reconnect = os.getenv('REDIS_AUTO_RECONNECT', 'true').lower() == 'true'
        
        logger.info("🔧 Redis subscription configuration loaded from environment")
        logger.info(f"   URL: {config.url}")
        logger.info(f"   Enabled: {config.enabled}")
        logger.info(f"   Channels: {config.match_updates_channel}, {config.processor_status_channel}, {config.system_alerts_channel}")
        
        return config
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate Redis subscription configuration.
        
        Returns:
            Dict[str, Any]: Validation result with errors and warnings
        """
        errors = []
        warnings = []
        
        # Validate URL
        if not self.url:
            errors.append("Redis URL is required")
        elif not self.url.startswith(('redis://', 'rediss://')):
            warnings.append(f"Redis URL format may be invalid: {self.url}")
        
        # Validate timeouts
        if self.socket_connect_timeout <= 0:
            errors.append("Socket connect timeout must be positive")
        if self.socket_timeout <= 0:
            errors.append("Socket timeout must be positive")
        if self.subscription_timeout < 0:
            errors.append("Subscription timeout must be non-negative")
        
        # Validate retry settings
        if self.max_retries < 0:
            errors.append("Max retries must be non-negative")
        if self.retry_delay < 0:
            errors.append("Retry delay must be non-negative")
        
        # Validate health check interval
        if self.health_check_interval <= 0:
            errors.append("Health check interval must be positive")
        
        # Validate channels
        if not self.match_updates_channel:
            errors.append("Match updates channel is required")
        if not self.processor_status_channel:
            errors.append("Processor status channel is required")
        if not self.system_alerts_channel:
            errors.append("System alerts channel is required")
        
        # Check for channel conflicts
        channels = [self.match_updates_channel, self.processor_status_channel, self.system_alerts_channel]
        if len(set(channels)) != len(channels):
            errors.append("Channel names must be unique")
        
        # Performance warnings
        if self.socket_timeout > 30:
            warnings.append("Socket timeout is very high (>30s)")
        if self.max_retries > 10:
            warnings.append("Max retries is very high (>10)")
        if self.health_check_interval < 10:
            warnings.append("Health check interval is very low (<10s)")
        if self.subscription_timeout > 5:
            warnings.append("Subscription timeout is very high (>5s)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.
        
        Returns:
            Dict[str, Any]: Configuration as dictionary
        """
        return asdict(self)
    
    def get_channels(self) -> Dict[str, str]:
        """
        Get Redis channel configuration.
        
        Returns:
            Dict[str, str]: Channel name mapping
        """
        return {
            'match_updates': self.match_updates_channel,
            'processor_status': self.processor_status_channel,
            'system_alerts': self.system_alerts_channel
        }

class RedisSubscriptionConfigManager:
    """Manages Redis subscription configuration for the calendar service."""
    
    def __init__(self, config: RedisSubscriptionConfig = None):
        """
        Initialize Redis subscription configuration manager.
        
        Args:
            config: Redis configuration (optional, loads from environment if not provided)
        """
        self.config = config or RedisSubscriptionConfig.from_environment()
        self._validation_result: Optional[Dict[str, Any]] = None
        
        logger.info("🔧 Redis Subscription Configuration Manager initialized")
    
    def get_config(self) -> RedisSubscriptionConfig:
        """
        Get current Redis subscription configuration.
        
        Returns:
            RedisSubscriptionConfig: Current configuration
        """
        return self.config
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate current Redis subscription configuration.
        
        Returns:
            Dict[str, Any]: Validation result
        """
        if self._validation_result is None:
            self._validation_result = self.config.validate()
        
        return self._validation_result
    
    def is_valid(self) -> bool:
        """
        Check if current configuration is valid.
        
        Returns:
            bool: True if configuration is valid
        """
        validation = self.validate_config()
        return validation.get('valid', False)
    
    def get_connection_url(self) -> str:
        """
        Get Redis connection URL.
        
        Returns:
            str: Redis connection URL
        """
        return self.config.url
    
    def is_enabled(self) -> bool:
        """
        Check if Redis subscription is enabled.
        
        Returns:
            bool: True if Redis subscription is enabled
        """
        return self.config.enabled
    
    def get_channels(self) -> Dict[str, str]:
        """
        Get Redis channel configuration.
        
        Returns:
            Dict[str, str]: Channel name mapping
        """
        return self.config.get_channels()
    
    def reload_from_environment(self) -> None:
        """Reload configuration from environment variables."""
        logger.info("🔄 Reloading Redis subscription configuration from environment")
        self.config = RedisSubscriptionConfig.from_environment()
        self._validation_result = None  # Reset validation cache
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get configuration status summary.
        
        Returns:
            Dict[str, Any]: Configuration status summary
        """
        validation = self.validate_config()
        
        return {
            "enabled": self.config.enabled,
            "url": self.config.url,
            "valid": validation.get('valid', False),
            "errors": validation.get('errors', []),
            "warnings": validation.get('warnings', []),
            "channels": self.get_channels(),
            "timeouts": {
                "connection": self.config.socket_connect_timeout,
                "socket": self.config.socket_timeout,
                "subscription": self.config.subscription_timeout
            }
        }

# Global configuration instance
_config_manager: Optional[RedisSubscriptionConfigManager] = None

def get_redis_subscription_config() -> RedisSubscriptionConfig:
    """
    Get global Redis subscription configuration.
    
    Returns:
        RedisSubscriptionConfig: Global Redis configuration
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = RedisSubscriptionConfigManager()
    
    return _config_manager.get_config()

def get_redis_subscription_config_manager() -> RedisSubscriptionConfigManager:
    """
    Get global Redis subscription configuration manager.
    
    Returns:
        RedisSubscriptionConfigManager: Global configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = RedisSubscriptionConfigManager()
    
    return _config_manager

def reload_redis_subscription_config() -> None:
    """Reload global Redis subscription configuration from environment."""
    global _config_manager
    if _config_manager is not None:
        _config_manager.reload_from_environment()
    else:
        _config_manager = RedisSubscriptionConfigManager()

if __name__ == "__main__":
    # Test Redis subscription configuration
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🧪 Testing Redis subscription configuration...")
    
    # Test configuration loading
    config = RedisSubscriptionConfig.from_environment()
    logger.info(f"📋 Configuration loaded:")
    logger.info(f"   URL: {config.url}")
    logger.info(f"   Enabled: {config.enabled}")
    logger.info(f"   Channels: {config.get_channels()}")
    
    # Test validation
    validation = config.validate()
    if validation['valid']:
        logger.info("✅ Configuration validation successful")
    else:
        logger.error("❌ Configuration validation failed")
        for error in validation['errors']:
            logger.error(f"   - {error}")
    
    if validation['warnings']:
        for warning in validation['warnings']:
            logger.warning(f"   ⚠️ {warning}")
    
    # Test configuration manager
    manager = RedisSubscriptionConfigManager(config)
    status = manager.get_status_summary()
    
    logger.info(f"📊 Configuration Status:")
    logger.info(f"   Valid: {status['valid']}")
    logger.info(f"   Enabled: {status['enabled']}")
    logger.info(f"   Errors: {len(status['errors'])}")
    logger.info(f"   Warnings: {len(status['warnings'])}")
    
    # Test global configuration
    global_config = get_redis_subscription_config()
    logger.info(f"🌐 Global configuration URL: {global_config.url}")
