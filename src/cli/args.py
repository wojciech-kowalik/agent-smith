import argparse

def get_session_id_from_cli() -> str | None:
    """Parses CLI arguments in search of --session-id."""
    parser = argparse.ArgumentParser(description="Interactive assistant!")
    parser.add_argument(
        '--session-id',
        type=str,
        default=None,
        help="ID of the session to load and continue (np. a1b2c3d4-log.json -> a1b2c3d4)"
    )
    args = parser.parse_args()
    return args.session_id
