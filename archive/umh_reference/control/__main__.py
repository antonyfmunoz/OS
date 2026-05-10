"""Entry point for python3 -m umh.control."""

import sys

sys.path.insert(0, "/opt/OS")

from umh.control.api import app

if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("UMH_API_PORT", "8000"))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
