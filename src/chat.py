import atexit
import files.config as config
import cli.args
from session import get_session_manager
import command_handler
from cli import console
from cli.prompt import get_user_input

def init_chat():
    """Initializes a new session or loads an existing one."""
    manager = get_session_manager()
    
    # Initialize session based on CLI args
    cli_session_id = cli.args.get_session_id_from_cli()
    session = manager.initialize_from_cli(cli_session_id)
    
    # Register cleanup handler
    atexit.register(lambda: manager.cleanup_and_save())

def main_loop():
    """Main loop of the interactive chat."""
    manager = get_session_manager()

    while True:
        try:
            user_input = get_user_input()

            if not user_input:
                continue

            if user_input.startswith('/'):
                should_exit = command_handler.handle_command(user_input)
                if should_exit:
                    break 
                continue
            
            # Conversation with the model
            session = manager.get_current_session()
            
            # Send message (handles WAL logging internally)
            # The answer is printed token by token; the progress bar is replaced by the first token.
            streamed = False

            def on_token(piece):
                nonlocal streamed
                if not streamed:
                    bar.stop()
                    console.stream_start(f"\n{session.assistant_name}: ")
                    streamed = True
                console.stream_write(piece)

            with console.ProgressBar() as bar:
                try:
                    response = session.send_message(user_input, on_token=on_token)
                finally:
                    if streamed:
                        console.stream_end()
            
            # Get token information
            total_tokens, remaining_tokens, max_tokens = session.get_token_info()

            # Display response (already printed while streaming; only an empty answer is not)
            if not streamed:
                console.print_assistant(f"\n{session.assistant_name}: {response.text}")
            console.print_info(f"Tokens: {total_tokens} (Remaining: {remaining_tokens} / {max_tokens})")

            # Save session
            success, error = session.save_to_file()
            if not success and error:
                console.print_error(f"Error saving session: {error}")

        except KeyboardInterrupt:
            console.print_info("\nInterrupted by user (Ctrl+C). Running the final save procedure...")
            break
        except EOFError:
            console.print_info("\nExit (Ctrl+D).")
            break
        except Exception as e:
            # Keep the chat alive: a failed request does not add anything to the history,
            # so the user can simply try again (or /exit).
            console.print_error(f"\nAn unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
