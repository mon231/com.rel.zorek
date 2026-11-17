"""PC entry: python desktop/app.py [shares.json]  (default ./shares.json). Needs: pip install -r backend/requirements.txt"""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from zorek_backend import Zorek  # noqa: E402

z = Zorek(sys.argv[1] if len(sys.argv) > 1 else "shares.json")
threading.Thread(target=z.run_forever, daemon=True).start()
last = None
try:
    while True:
        st = z.status()
        if st != last:
            print(st, flush=True)
            last = st
        time.sleep(1)
except KeyboardInterrupt:
    pass
