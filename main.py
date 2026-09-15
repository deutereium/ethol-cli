#!/usr/bin/env python3

"""Entry point for the Simple Et‑Hol Notifier.
Runs the scheduler defined in ``ethol_notifier.scheduler``.
"""

from ethol_notifier.scheduler import run

if __name__ == "__main__":
    run()
