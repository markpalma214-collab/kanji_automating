"""
async_utils.py — run blocking work (AI API calls) off the Tk main thread,
and safely marshal the result back onto the main thread.

Tkinter is not thread-safe: widgets must only be touched from the main
thread. The pattern here is the standard one — do the work in a daemon
thread, push the result into a queue, and poll the queue from the main
thread via `root.after(...)`.
"""

import queue
import threading


def run_async(root, work_fn, on_success, on_error, *args, poll_ms=80, **kwargs):
    """
    Run work_fn(*args, **kwargs) in a background thread.

    on_success(result) and on_error(exception) are both called on the main
    thread, so they are free to update Tk widgets directly.

    `root` must be any widget with `.after()` (typically the Tk root).
    """
    result_queue: "queue.Queue" = queue.Queue()

    def worker():
        try:
            result = work_fn(*args, **kwargs)
            result_queue.put(("ok", result))
        except Exception as exc:  # noqa: BLE001 - surface any error to the UI
            result_queue.put(("error", exc))

    def poll():
        try:
            status, payload = result_queue.get_nowait()
        except queue.Empty:
            root.after(poll_ms, poll)
            return
        if status == "ok":
            on_success(payload)
        else:
            on_error(payload)

    threading.Thread(target=worker, daemon=True).start()
    root.after(poll_ms, poll)
