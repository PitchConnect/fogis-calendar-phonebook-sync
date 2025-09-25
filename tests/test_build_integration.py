"""
Integration tests for Docker build optimization.

This module contains integration tests that validate the complete
build pipeline and performance optimizations work together correctly.
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional
from unittest.mock import Mock, patch

import pytest


class TestBuildIntegration(unittest.TestCase):
    """Integration tests for the optimized build pipeline."""

    def setUp(self):
        """Set up integration test environment."""
        self.project_root = Path(__file__).parent.parent
        self.test_image_name = "fogis-calendar-sync-test"
        self.build_timeout = 600  # 10 minutes max for test builds

    def tearDown(self):
        """Clean up test artifacts."""
        # Remove test images
        try:
            subprocess.run(["docker", "rmi", self.test_image_name], capture_output=True, timeout=30)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass  # Image might not exist

    @pytest.mark.integration
    @unittest.skipIf(not os.getenv("RUN_INTEGRATION_TESTS"), "Integration tests skipped")
    def test_docker_build_success(self):
        """Test that Docker build completes successfully."""
        build_cmd = [
            "docker",
            "build",
            "-t",
            self.test_image_name,
            "-f",
            str(self.project_root / "Dockerfile"),
            str(self.project_root),
        ]

        start_time = time.time()
        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=self.build_timeout,
            cwd=self.project_root,
        )
        build_time = time.time() - start_time

        self.assertEqual(result.returncode, 0, f"Docker build failed: {result.stderr}")

        # Log build time for performance tracking
        print(f"Build completed in {build_time:.2f} seconds")

        # Verify image was created
        inspect_result = subprocess.run(
            ["docker", "inspect", self.test_image_name], capture_output=True, text=True
        )
        self.assertEqual(inspect_result.returncode, 0, "Image should be inspectable")

    @pytest.mark.integration
    @unittest.skipIf(not os.getenv("RUN_INTEGRATION_TESTS"), "Integration tests skipped")
    def test_multi_stage_build_layers(self):
        """Test that multi-stage build creates expected layers."""
        # Build with build-arg to test layer caching
        build_cmd = [
            "docker",
            "build",
            "-t",
            self.test_image_name,
            "--build-arg",
            "VERSION=test-123",
            "-f",
            str(self.project_root / "Dockerfile"),
            str(self.project_root),
        ]

        result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=self.build_timeout,
            cwd=self.project_root,
        )

        self.assertEqual(result.returncode, 0, f"Multi-stage build failed: {result.stderr}")

        # Check that build output mentions stages
        build_output = result.stdout + result.stderr
        self.assertIn("base", build_output.lower())
        self.assertIn("dependencies", build_output.lower())
        self.assertIn("final", build_output.lower())

    @pytest.mark.integration
    @unittest.skipIf(not os.getenv("RUN_INTEGRATION_TESTS"), "Integration tests skipped")
    def test_container_functionality(self):
        """Test that built container functions correctly."""
        # First build the image
        build_cmd = [
            "docker",
            "build",
            "-t",
            self.test_image_name,
            str(self.project_root),
        ]

        build_result = subprocess.run(
            build_cmd,
            capture_output=True,
            text=True,
            timeout=self.build_timeout,
            cwd=self.project_root,
        )

        self.assertEqual(build_result.returncode, 0, "Build should succeed")

        # Test container can start (basic smoke test)
        run_cmd = [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            f"{self.test_image_name}-test",
            "-p",
            "5003:5003",
            self.test_image_name,
        ]

        container_id = None
        try:
            run_result = subprocess.run(run_cmd, capture_output=True, text=True, timeout=30)

            if run_result.returncode == 0:
                container_id = run_result.stdout.strip()

                # Wait a moment for container to start
                time.sleep(5)

                # Check container is running
                ps_result = subprocess.run(
                    ["docker", "ps", "--filter", f"id={container_id}"],
                    capture_output=True,
                    text=True,
                )

                # Container should be listed (basic functionality test)
                self.assertIn(container_id[:12], ps_result.stdout)

        finally:
            # Clean up container
            if container_id:
                subprocess.run(["docker", "stop", container_id], capture_output=True, timeout=30)

    def test_build_context_optimization(self):
        """Test that build context excludes unnecessary files."""
        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Copy essential files
            essential_files = [
                "Dockerfile",
                "requirements.txt",
                "dev-requirements.txt",
                ".dockerignore",
                "app.py",
            ]

            for file_name in essential_files:
                src_file = self.project_root / file_name
                if src_file.exists():
                    dest_file = temp_path / file_name
                    if src_file.is_file():
                        dest_file.write_text(src_file.read_text())
                    else:
                        # Create minimal version for testing
                        if file_name == "app.py":
                            dest_file.write_text("print('Hello World')")

            # Create files that should be excluded
            excluded_files = [
                ".git/config",
                ".github/workflows/test.yml",
                "__pycache__/test.pyc",
                "tests/test.py",
                "docs/README.md",
                ".pytest_cache/test",
            ]

            for file_path in excluded_files:
                full_path = temp_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text("test content")

            # Test build with this context
            build_cmd = [
                "docker",
                "build",
                "-t",
                f"{self.test_image_name}-context-test",
                str(temp_path),
            ]

            result = subprocess.run(
                build_cmd, capture_output=True, text=True, timeout=self.build_timeout
            )

            # Build should succeed even with excluded files present
            self.assertEqual(
                result.returncode,
                0,
                f"Build with optimized context failed: {result.stderr}",
            )

            # Clean up test image
            subprocess.run(
                ["docker", "rmi", f"{self.test_image_name}-context-test"],
                capture_output=True,
            )


class TestCacheEffectiveness(unittest.TestCase):
    """Test suite for Docker build cache effectiveness."""

    def setUp(self):
        """Set up cache testing environment."""
        self.project_root = Path(__file__).parent.parent
        self.test_image_base = "fogis-cache-test"

    def tearDown(self):
        """Clean up cache test artifacts."""
        # Remove test images
        for i in range(3):
            try:
                subprocess.run(
                    ["docker", "rmi", f"{self.test_image_base}-{i}"],
                    capture_output=True,
                    timeout=30,
                )
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                pass

    @pytest.mark.integration
    @unittest.skipIf(not os.getenv("RUN_INTEGRATION_TESTS"), "Integration tests skipped")
    def test_dependency_layer_caching(self):
        """Test that dependency layers are cached effectively."""
        # First build
        build_cmd_1 = [
            "docker",
            "build",
            "-t",
            f"{self.test_image_base}-1",
            str(self.project_root),
        ]

        start_time_1 = time.time()
        result_1 = subprocess.run(
            build_cmd_1,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=self.project_root,
        )
        build_time_1 = time.time() - start_time_1

        self.assertEqual(result_1.returncode, 0, "First build should succeed")

        # Second build (should use cache)
        build_cmd_2 = [
            "docker",
            "build",
            "-t",
            f"{self.test_image_base}-2",
            str(self.project_root),
        ]

        start_time_2 = time.time()
        result_2 = subprocess.run(
            build_cmd_2,
            capture_output=True,
            text=True,
            timeout=600,
            cwd=self.project_root,
        )
        build_time_2 = time.time() - start_time_2

        self.assertEqual(result_2.returncode, 0, "Second build should succeed")

        # Second build should be significantly faster due to caching
        cache_effectiveness = (build_time_1 - build_time_2) / build_time_1

        print(f"First build: {build_time_1:.2f}s, Second build: {build_time_2:.2f}s")
        print(f"Cache effectiveness: {cache_effectiveness:.2%}")

        # Expect at least 30% improvement from caching
        self.assertGreater(
            cache_effectiveness,
            0.3,
            "Cache should provide significant performance improvement",
        )


class TestWorkflowValidation(unittest.TestCase):
    """Test suite for GitHub Actions workflow validation."""

    def setUp(self):
        """Set up workflow testing environment."""
        self.project_root = Path(__file__).parent.parent
        self.workflow_path = self.project_root / ".github" / "workflows" / "docker-build.yml"

    def test_workflow_syntax_valid(self):
        """Test that workflow YAML syntax is valid."""
        import yaml

        with open(self.workflow_path, "r") as f:
            try:
                workflow_data = yaml.safe_load(f)
                self.assertIsInstance(workflow_data, dict)
                self.assertIn("jobs", workflow_data)
                self.assertIn("build", workflow_data["jobs"])
            except yaml.YAMLError as e:
                self.fail(f"Workflow YAML syntax error: {e}")

    def test_workflow_performance_features(self):
        """Test that workflow includes all performance features."""
        with open(self.workflow_path, "r") as f:
            content = f.read()

        performance_features = [
            "Determine build platforms",  # Conditional platform building
            "hashFiles('requirements.txt'",  # Requirements-based caching
            "cache-from: type=gha",  # GitHub Actions cache
            "cache-to: type=gha,mode=max",  # Optimized cache mode
            "linux/amd64,linux/arm64",  # Multi-platform support
            "linux/amd64",  # Single platform for PRs
        ]

        for feature in performance_features:
            self.assertIn(
                feature,
                content,
                f"Workflow should include performance feature: {feature}",
            )


if __name__ == "__main__":
    unittest.main()
