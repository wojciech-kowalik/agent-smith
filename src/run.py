import sys

from cli.args import parse_args

if __name__ == "__main__":
    args = parse_args()
    if args.serve or args.stop or args.status:
        import server
        sys.exit(server.serve() if args.serve else server.stop() if args.stop else server.status())
    if args.ask is not None:
        from ask import run_ask
        sys.exit(run_ask(args.ask, args.session_id, args.stdin))
    import chat
    chat.init_chat()
    chat.main_loop()
