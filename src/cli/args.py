import argparse


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parses CLI arguments: --session-id and the one-shot --ask mode."""
    parser = argparse.ArgumentParser(description="Interactive assistant!")
    parser.add_argument(
        '--session-id',
        type=str,
        default=None,
        help="ID of the session to load and continue (np. a1b2c3d4-log.json -> a1b2c3d4)"
    )
    parser.add_argument(
        '--ask', '-p',
        nargs='?',
        const='-',
        default=None,
        metavar='QUESTION',
        help="One-shot mode: print only the answer to stdout and exit. "
             "Without QUESTION (or with '-') the question is read from stdin. "
             "Nothing is saved unless --session-id is given."
    )
    parser.add_argument(
        '--stdin',
        action='store_true',
        help="With --ask: append piped stdin to the question as context (e.g. git diff | ... --ask 'review' --stdin)"
    )
    control = parser.add_mutually_exclusive_group()
    control.add_argument('--serve', action='store_true',
                         help="Load the model once and keep it in memory; --ask then uses it (see --stop)")
    control.add_argument('--stop', action='store_true', help="Stop the Smith server and release the model from memory")
    control.add_argument('--status', action='store_true', help="Tell whether the Smith server is running")
    return parser.parse_args(argv)


def get_session_id_from_cli() -> str | None:
    """Returns the value of --session-id (None when absent)."""
    return parse_args().session_id
