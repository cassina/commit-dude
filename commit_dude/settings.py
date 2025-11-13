import logging
import os


class CommitDudeFormatter(logging.Formatter):
    """CommitDude colored formatter"""

    COLORS = {
        "DEBUG": "\033[38;2;110;246;223m",  # Light teal (#6ef6df)
        "INFO": "\033[38;2;118;245;249m",  # Bright cyan (#76f5f9)
        "WARNING": "\033[38;2;193;255;185m",  # Light green (#c1ffb9)
        "ERROR": "\033[38;2;229;136;224m",  # Pink (#e588e0)
        "CRITICAL": "\033[38;2;165;142;238m",  # Purple (#a58eee)
        "RESET": "\033[0m",  # Reset color
        "BOLD": "\033[1m",  # Bold text
        "DIM": "\033[2m",  # Dim text
    }

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        formatted = super().format(record)

        if record.levelname == "DEBUG":
            return (
                f"{self.COLORS['DIM']}{color}[DEBUG] {formatted}{self.COLORS['RESET']}"
            )
        elif record.levelname == "INFO":
            return f"{color}[INFO] {formatted}{self.COLORS['RESET']}"
        elif record.levelname == "WARNING":
            return f"{self.COLORS['BOLD']}{color}[WARNING] {formatted}{self.COLORS['RESET']}"
        elif record.levelname == "ERROR":
            return (
                f"{self.COLORS['BOLD']}{color}[ERROR] {formatted}{self.COLORS['RESET']}"
            )
        elif record.levelname == "CRITICAL":
            return f"{self.COLORS['BOLD']}{color}[CRITICAL] {formatted}{self.COLORS['RESET']}"
        else:
            return f"{color}{formatted}{self.COLORS['RESET']}"


# Configure logger
def commit_dude_logger(name: str):
    """Create a preconfigured logger with colors and dynamic log levels."""
    logger = logging.getLogger(name)

    if not logger.handlers:  # Prevent adding multiple handlers
        level = os.getenv("COMMIT_DUDE_LOG_LEVEL", "INFO").upper()

        logger.setLevel(level)

        handler = logging.StreamHandler()
        handler.setLevel(level)
        handler.setFormatter(
            CommitDudeFormatter("%(message)s")
        )

        logger.addHandler(handler)

    return logger
# def commit_dude_logger(file_name):
#     return logging.getLogger(file_name)
