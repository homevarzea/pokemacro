import os
import sys
import threading

port = 5000

def start_flask():
    from modules import app
    app.run(port=port)

if __name__ == '__main__':
    # The same portable executable runs its elevated worker without a GUI.
    if sys.argv[1:2] == ['--game-bridge-worker']:
        from bridge_entry import run_worker
        run_worker(sys.argv[2:])
        sys.exit(0)
    if sys.argv[1:2] == ['--bridge-self-test']:
        from bridge_entry import self_test
        sys.exit(self_test(sys.argv[2]))
    import multiprocessing
    multiprocessing.freeze_support()
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
    import webview
    from modules import app
    window = webview.create_window(
        'Pokemacro', 
        f'http://127.0.0.1:{port}',
        width=1200,
        height=800
    )

    flask_thread = threading.Thread(target=start_flask)
    flask_thread.daemon = True
    flask_thread.start()

    debug_mode = os.environ.get('DEBUG_MODE', 'False').lower().strip() in ['true', '1', 'yes']
    webview.start(debug=debug_mode)
