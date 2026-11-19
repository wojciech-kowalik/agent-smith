"""
Console output utilities for the chatbot.
Centralizes colorama usage for consistent terminal output.
"""
import sys
import threading
import time
from colorama import init, Fore, Style
from files.config import LOG_DIR

init(autoreset=True)


class ProgressBar:
    """Animated indeterminate progress bar with elapsed time.

    Use as a context manager around a blocking call of unknown duration
    (e.g. waiting for the model). Does nothing when stdout is not a terminal.
    """

    _WIDTH = 20
    _BLOCK = 5
    _INTERVAL = 0.1
    _active = None  # bar currently drawn, so other output can clear its line first

    def __init__(self, label: str = "Waiting for response"):
        self._label = label
        self._enabled = sys.stdout.isatty()
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.Lock()

    def _frame(self, tick: int, elapsed: float) -> str:
        # A block bouncing left and right inside the bar
        span = self._WIDTH - self._BLOCK
        pos = tick % (2 * span)
        pos = pos if pos <= span else 2 * span - pos
        bar = "░" * pos + "█" * self._BLOCK + "░" * (span - pos)
        return f"{Fore.YELLOW}{self._label} [{bar}] {elapsed:4.1f}s{Style.RESET_ALL}"

    def _run(self):
        start = time.monotonic()
        tick = 0
        while not self._stop.is_set():
            with self._lock:
                sys.stdout.write("\r\033[K" + self._frame(tick, time.monotonic() - start))
                sys.stdout.flush()
            tick += 1
            self._stop.wait(self._INTERVAL)

    def clear_line(self):
        """Erase the bar line so other output can be printed cleanly."""
        with self._lock:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

    def __enter__(self):
        if self._enabled:
            ProgressBar._active = self
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
        return self

    def stop(self):
        """Stop and erase the bar. Safe to call more than once."""
        if self._thread:
            self._stop.set()
            self._thread.join()
            self.clear_line()
            ProgressBar._active = None
            self._thread = None

    def __exit__(self, exc_type, exc, tb):
        self.stop()
        return False


def _clear_progress():
    if ProgressBar._active:
        ProgressBar._active.clear_line()


def print_error(message: str):
    """Print an error message in red color.
    
    Args:
        message: The error message to display
    """
    print(Fore.RED + message + Style.RESET_ALL)


def print_assistant(message: str):
    """Print an assistant message in cyan color.
    
    Args:
        message: The assistant message to display
    """
    print(Fore.CYAN + message + Style.RESET_ALL)


def stream_start(prefix: str):
    """Begin a streamed assistant answer: prints the prefix in cyan, no newline."""
    sys.stdout.write(Fore.CYAN + prefix)
    sys.stdout.flush()


def stream_write(piece: str):
    """Print one piece of a streamed answer immediately."""
    sys.stdout.write(piece)
    sys.stdout.flush()


def stream_end():
    """Finish a streamed answer: reset the color and end the line."""
    sys.stdout.write(Style.RESET_ALL + "\n")
    sys.stdout.flush()


def print_user(message: str):
    """Print a user message in blue color.
    
    Args:
        message: The user message to display
    """
    print(Fore.BLUE + message + Style.RESET_ALL)


def print_info(message: str):
    """Print an informational message in yellow color.
    
    Args:
        message: The informational message to display
    """
    _clear_progress()
    print(message)

def print_warning(message: str):
    """Print a warning message in yellow color.
    
    Args:
        message: The warning message to display
    """
    _clear_progress()
    print(Fore.YELLOW + message + Style.RESET_ALL)


def print_help(message: str):
    """Print an informational message in yellow color.
    
    Args:
        message: The informational message to display
    """
    print(Fore.YELLOW + message + Style.RESET_ALL)


def display_help(session_id: str):
    """Displays a short help message."""
    print_info(f"Current session (ID): {session_id}")
    print_info(f"Session files are saved continuously in: {LOG_DIR}")
    print_help("Available commands (slash commands):")
    print_help("  /switch <ID>      - Switches to an existing session.")
    print_help("  /help             - Shows this help.")
    print_help("  /exit, /quit      - Ends the chat.")
    print_help("\n  /session list     - Lists available sessions.")
    print_help("  /session display  - Shows the whole session history.")
    print_help("  /session pop      - Removes the last pair of entries (YOU and assistant).")
    print_help("  /session clear    - Clears the current session history.")
    print_help("  /session new      - Starts a new session.")
    print_help("  /session remove   - Deletes the current session file and starts a new session.")
    print_help("\n  /pdf              - Exports the current session to a PDF file.")


def display_final_instructions(session_id: str):
    """Displays instructions for continuing the session."""
    print_info("\n--- Session Continuation Instructions ---")
    print_info(f"To continue this session (ID: {session_id}) later, use the command:")
    print(Fore.WHITE + Style.BRIGHT + f"\n    python {sys.argv[0]} --session-id={session_id}\n" + Style.RESET_ALL)
    print("--------------------------------------\n")

