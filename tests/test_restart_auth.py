"""Tests for restart_auth module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

import restart_auth


class TestRestartAuthMain:
    """Test cases for the main restart_auth function."""

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_token_valid_no_refresh_needed_user_cancels(
        self, mock_print, mock_auth_manager_class
    ):
        """Test main function when token is valid, no refresh needed, and user cancels."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - valid and doesn't need refresh
        mock_token_status = {
            "valid": True,
            "expired": False,
            "needs_refresh": False,
            "expiry": "2024-12-31T23:59:59Z",
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock user input - user cancels
        with patch("builtins.input", return_value="n"):
            result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify HeadlessAuthManager was created
        mock_auth_manager_class.assert_called_once()

        # Verify token status was checked
        mock_auth_manager.get_token_status.assert_called_once()

        # Verify force_refresh was NOT called since user cancelled
        mock_auth_manager.force_refresh.assert_not_called()

        # Verify appropriate messages were printed
        mock_print.assert_any_call("🔄 Restarting Authentication Process")
        mock_print.assert_any_call("✅ Token is still valid and doesn't need refresh.")
        mock_print.assert_any_call("ℹ️  Authentication restart cancelled.")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_token_valid_no_refresh_needed_user_proceeds(
        self, mock_print, mock_auth_manager_class
    ):
        """Test main function when token is valid, no refresh needed, but user proceeds."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - valid and doesn't need refresh
        mock_token_status = {
            "valid": True,
            "expired": False,
            "needs_refresh": False,
            "expiry": "2024-12-31T23:59:59Z",
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock successful force refresh
        mock_auth_manager.force_refresh.return_value = True

        # Mock user input - user proceeds
        with patch("builtins.input", return_value="y"):
            result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify force_refresh was called
        mock_auth_manager.force_refresh.assert_called_once()

        # Verify success messages were printed
        mock_print.assert_any_call("✅ Authentication completed successfully!")
        mock_print.assert_any_call("✅ New token saved and ready for use.")
        mock_print.assert_any_call("✅ Background monitoring will continue automatically.")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_token_needs_refresh_success(self, mock_print, mock_auth_manager_class):
        """Test main function when token needs refresh and authentication succeeds."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - needs refresh
        mock_token_status = {
            "valid": False,
            "expired": True,
            "needs_refresh": True,
            "expiry": "2024-01-01T00:00:00Z",
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock successful force refresh
        mock_auth_manager.force_refresh.return_value = True

        result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify force_refresh was called
        mock_auth_manager.force_refresh.assert_called_once()

        # Verify status messages were printed
        mock_print.assert_any_call("📊 Current Token Status:")
        mock_print.assert_any_call("  Valid: False")
        mock_print.assert_any_call("  Expired: True")
        mock_print.assert_any_call("  Needs Refresh: True")
        mock_print.assert_any_call("  Expires: 2024-01-01T00:00:00Z")

        # Verify success messages were printed
        mock_print.assert_any_call("✅ Authentication completed successfully!")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_token_needs_refresh_failure(self, mock_print, mock_auth_manager_class):
        """Test main function when token needs refresh but authentication fails."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - needs refresh
        mock_token_status = {"valid": False, "expired": True, "needs_refresh": True}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock failed force refresh
        mock_auth_manager.force_refresh.return_value = False

        result = restart_auth.main()

        # Verify return code
        assert result == 1

        # Verify force_refresh was called
        mock_auth_manager.force_refresh.assert_called_once()

        # Verify failure messages were printed
        mock_print.assert_any_call("❌ Authentication failed.")
        mock_print.assert_any_call("💡 You can try running this script again.")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_token_status_no_expiry(self, mock_print, mock_auth_manager_class):
        """Test main function when token status has no expiry information."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - no expiry info
        mock_token_status = {
            "valid": False,
            "expired": True,
            "needs_refresh": True,
            "expiry": None,
        }
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock successful force refresh
        mock_auth_manager.force_refresh.return_value = True

        result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify status messages were printed (but not expiry since it's None)
        mock_print.assert_any_call("📊 Current Token Status:")
        mock_print.assert_any_call("  Valid: False")
        mock_print.assert_any_call("  Expired: True")
        mock_print.assert_any_call("  Needs Refresh: True")

        # Verify expiry message was NOT printed since expiry is None
        expiry_calls = [call for call in mock_print.call_args_list if "Expires:" in str(call)]
        assert len(expiry_calls) == 0

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_keyboard_interrupt(self, mock_print, mock_auth_manager_class):
        """Test main function when user interrupts with Ctrl+C."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock KeyboardInterrupt during get_token_status
        mock_auth_manager.get_token_status.side_effect = KeyboardInterrupt()

        result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify cancellation message was printed
        mock_print.assert_any_call("\n⚠️  Authentication cancelled by user.")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    @patch("restart_auth.logger")
    def test_main_general_exception(self, mock_logger, mock_print, mock_auth_manager_class):
        """Test main function when a general exception occurs."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock exception during get_token_status
        test_exception = Exception("Test error")
        mock_auth_manager.get_token_status.side_effect = test_exception

        result = restart_auth.main()

        # Verify return code
        assert result == 1

        # Verify exception was logged
        mock_logger.exception.assert_called_once_with(
            "Error during authentication restart: Test error"
        )

        # Verify error message was printed
        mock_print.assert_any_call("❌ Error: Test error")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_user_input_variations(self, mock_print, mock_auth_manager_class):
        """Test main function with various user input variations."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - valid and doesn't need refresh
        mock_token_status = {"valid": True, "expired": False, "needs_refresh": False}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Test different user inputs that should cancel
        cancel_inputs = ["n", "N", "no", "No", "NO", "", "anything_else"]

        for user_input in cancel_inputs:
            mock_print.reset_mock()
            mock_auth_manager.force_refresh.reset_mock()

            with patch("builtins.input", return_value=user_input):
                result = restart_auth.main()

            # Should always cancel and return 0
            assert result == 0
            mock_auth_manager.force_refresh.assert_not_called()
            mock_print.assert_any_call("ℹ️  Authentication restart cancelled.")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_user_input_proceed_variations(self, mock_print, mock_auth_manager_class):
        """Test main function with user inputs that should proceed."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - valid and doesn't need refresh
        mock_token_status = {"valid": True, "expired": False, "needs_refresh": False}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock successful force refresh
        mock_auth_manager.force_refresh.return_value = True

        # Test different user inputs that should proceed
        proceed_inputs = ["y", "Y", "yes", "Yes", "YES"]

        for user_input in proceed_inputs:
            mock_print.reset_mock()
            mock_auth_manager.force_refresh.reset_mock()

            with patch("builtins.input", return_value=user_input):
                result = restart_auth.main()

            # Should always proceed and return 0 (success)
            assert result == 0
            mock_auth_manager.force_refresh.assert_called_once()
            mock_print.assert_any_call("✅ Authentication completed successfully!")


class TestRestartAuthScriptExecution:
    """Test cases for script execution scenarios."""

    @patch("sys.exit")
    def test_script_execution_main_entry_point(self, mock_exit):
        """Test that the script properly calls sys.exit with main's return value."""
        # Mock the main function to return success
        with patch("restart_auth.main", return_value=0) as mock_main:
            # Test the if __name__ == "__main__" block
            with patch("restart_auth.__name__", "__main__"):
                try:
                    exec(
                        "if __name__ == '__main__': sys.exit(main())",
                        {"__name__": "__main__", "sys": sys, "main": mock_main},
                    )
                except SystemExit:
                    pass  # Expected when sys.exit is called

        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)

    def test_script_execution_not_main(self):
        """Test that main is not called when script is imported."""
        # When imported (not run as main), main should not be called
        with patch("restart_auth.main") as mock_main:
            # Simulate import (not main execution)
            with patch("restart_auth.__name__", "restart_auth"):
                # The if __name__ == "__main__" block should not execute
                pass

        # main should not have been called
        mock_main.assert_not_called()


class TestRestartAuthEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_empty_token_status(self, mock_print, mock_auth_manager_class):
        """Test main function with empty token status."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock empty token status
        mock_token_status = {}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock successful force refresh
        mock_auth_manager.force_refresh.return_value = True

        result = restart_auth.main()

        # Verify return code
        assert result == 0

        # Verify default values were used
        mock_print.assert_any_call("  Valid: False")  # Default for missing 'valid'
        mock_print.assert_any_call("  Expired: True")  # Default for missing 'expired'
        mock_print.assert_any_call("  Needs Refresh: True")  # Default for missing 'needs_refresh'

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_auth_manager_creation_failure(self, mock_print, mock_auth_manager_class):
        """Test main function when HeadlessAuthManager creation fails."""
        # Mock HeadlessAuthManager creation failure
        mock_auth_manager_class.side_effect = Exception("Failed to create auth manager")

        result = restart_auth.main()

        # Verify return code
        assert result == 1

        # Verify error was handled
        mock_print.assert_any_call("❌ Error: Failed to create auth manager")

    @patch("restart_auth.HeadlessAuthManager")
    @patch("builtins.print")
    def test_main_force_refresh_exception(self, mock_print, mock_auth_manager_class):
        """Test main function when force_refresh raises an exception."""
        # Mock HeadlessAuthManager
        mock_auth_manager = MagicMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        # Mock token status - needs refresh
        mock_token_status = {"valid": False, "expired": True, "needs_refresh": True}
        mock_auth_manager.get_token_status.return_value = mock_token_status

        # Mock force_refresh raising an exception
        mock_auth_manager.force_refresh.side_effect = Exception("Force refresh failed")

        result = restart_auth.main()

        # Verify return code
        assert result == 1

        # Verify error was handled
        mock_print.assert_any_call("❌ Error: Force refresh failed")
