"""Host-side tools for the Elfin robot.

This package intentionally does not depend on ROS. It talks to the Flask
joint-state API over HTTP, so it can run on a laptop while the robot stack runs
inside the Docker container.
"""

from .api import (
    DEFAULT_API_URL,
    DEFAULT_TIMEOUT_SEC,
    ElfinApiError,
    ElfinClient,
    JointStateUnavailable,
)

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_API_URL",
    "DEFAULT_TIMEOUT_SEC",
    "ElfinApiError",
    "ElfinClient",
    "JointStateUnavailable",
    "__version__",
]
