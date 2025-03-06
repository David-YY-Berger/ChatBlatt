import os
import logging
from datetime import datetime
import inspect


class Logger:
    _instance = None

    def __new__(cls, print_to_console=True):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance.__init__(print_to_console)
        return cls._instance

    def __init__(self, print_to_console=True):
        if not hasattr(self, 'initialized'):  # Ensuring the initialization happens only once
            self.print_to_console = print_to_console

            log_dir = 'logs'  # Paths.LOGS_DIR can be substituted here
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # Generate log file name with current date
            log_file = os.path.join(log_dir, f"{datetime.now().strftime('%Y-%m-%d')}_log.log")

            # Configure logging
            logging.basicConfig(
                filename=log_file,
                level=logging.DEBUG,
                format='%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

            self.logger = logging.getLogger()

            self.initialized = True  # Mark initialization as complete

    def _get_caller_info(self):
        stack = inspect.stack()
        caller_frame = stack[2]
        module = inspect.getmodule(caller_frame[0])
        module_name = module.__name__ if module else "Unknown"
        function_name = caller_frame.function
        return f"{module_name}.{function_name}"

    def _log_message(self, level, message):
        caller_info = self._get_caller_info()
        formatted_message = f"[{caller_info}] {message}"

        if level == "info":
            self.logger.info(formatted_message)
        elif level == "error":
            self.logger.error(formatted_message)
        elif level == "warning":
            self.logger.warning(formatted_message)
        elif level == "debug":
            self.logger.debug(formatted_message)

        if self.print_to_console:
            print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {level.upper()} - {formatted_message}")

    def log(self, message):
        self._log_message("info", message)

    def error(self, message):
        self._log_message("error", message)

    def warning(self, message):
        self._log_message("warning", message)

    def debug(self, message):
        self._log_message("debug", message)
