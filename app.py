"""Vercel/FastAPI entrypoint.

Vercel auto-discovers a FastAPI instance named ``app`` from a supported
top-level entrypoint. The application itself stays in ``backend.main`` so the
same code continues to work with local Uvicorn and in tests.
"""

from backend.main import app

__all__ = ["app"]
