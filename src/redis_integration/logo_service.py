#!/usr/bin/env python3
"""
Logo Service Integration for Calendar Service

Provides integration with team-logo-combiner service for generating
combined team logos using Organization IDs.
"""

import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# Check if requests is available
try:
    import requests

    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests library not available - logo service integration disabled")


class LogoServiceClient:
    """Client for team-logo-combiner service integration."""

    def __init__(self, service_url: Optional[str] = None, timeout: int = 10):
        """
        Initialize logo service client.

        Args:
            service_url: URL of the team-logo-combiner service
            timeout: Request timeout in seconds
        """
        self.service_url = service_url or os.getenv(
            "LOGO_COMBINER_URL", "http://team-logo-combiner:5002"
        )
        self.timeout = timeout
        self.enabled = REQUESTS_AVAILABLE and bool(self.service_url)
        self.cache = {}  # Simple in-memory cache for generated logos

        if self.enabled:
            logger.info(f"✅ Logo service client initialized: {self.service_url}")
        else:
            logger.warning("⚠️ Logo service client disabled")

    def generate_combined_logo(
        self, home_org_id: int, away_org_id: int, save_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate combined team logo using Organization IDs.

        Args:
            home_org_id: Home team Organization ID (logo_id)
            away_org_id: Away team Organization ID (logo_id)
            save_path: Optional path to save the logo (default: /tmp/combined_logo_{home}_{away}.png)

        Returns:
            Path to saved logo file, or None if generation failed
        """
        if not self.enabled:
            logger.debug("Logo service disabled, skipping logo generation")
            return None

        # Check cache first
        cache_key = f"{home_org_id}_{away_org_id}"
        if cache_key in self.cache:
            logger.debug(f"Using cached logo for {cache_key}")
            return self.cache[cache_key]

        try:
            # Prepare request
            url = f"{self.service_url}/create_avatar"
            payload = {
                "team1_id": str(home_org_id),
                "team2_id": str(away_org_id),
            }

            logger.debug(f"Requesting combined logo: {home_org_id} vs {away_org_id}")

            # Make request
            response = requests.post(url, json=payload, timeout=self.timeout)

            if response.status_code == 200:
                # Determine save path
                if save_path is None:
                    # Use system temp directory for security  # nosec B108
                    temp_dir = tempfile.gettempdir()
                    save_path = os.path.join(
                        temp_dir, f"combined_logo_{home_org_id}_{away_org_id}.png"
                    )

                # Ensure directory exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)

                # Save logo
                with open(save_path, "wb") as f:
                    f.write(response.content)

                # Cache the path
                self.cache[cache_key] = save_path

                logger.info(f"✅ Generated combined logo: {save_path}")
                return save_path
            else:
                logger.warning(
                    f"⚠️ Logo generation failed: HTTP {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.warning(f"⚠️ Logo generation timeout for {home_org_id} vs {away_org_id}")
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Logo service connection failed: {self.service_url}")
            return None
        except Exception as e:
            logger.error(f"❌ Logo generation error: {e}")
            return None

    def clear_cache(self):
        """Clear the logo cache."""
        self.cache.clear()
        logger.info("🗑️ Logo cache cleared")

    def get_cache_size(self) -> int:
        """Get the number of cached logos."""
        return len(self.cache)


def create_logo_service_client(service_url: Optional[str] = None) -> LogoServiceClient:
    """
    Create logo service client instance.

    Args:
        service_url: Optional URL of the team-logo-combiner service

    Returns:
        LogoServiceClient instance
    """
    return LogoServiceClient(service_url)
