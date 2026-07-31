from unittest.mock import Mock, patch

from src.tools.log_print import log_print


def test_log_print_uses_requested_level_and_prints():
    logger = Mock()

    with patch("builtins.print") as mocked_print:
        log_print(logger, "hola", level="warning")

    mocked_print.assert_called_once_with("hola")
    logger.warning.assert_called_once_with("hola")


def test_log_print_falls_back_to_info_when_level_missing():
    class LoggerWithoutLevel:
        def __init__(self):
            self.messages = []

        def info(self, message):
            self.messages.append(message)

    logger = LoggerWithoutLevel()

    with patch("builtins.print") as mocked_print:
        log_print(logger, "mensaje", level="non_existing_level")

    mocked_print.assert_called_once_with("mensaje")
    assert logger.messages == ["mensaje"]
