"""Agent Failure Lab application package.

Re-export the ASGI app so that ``uvicorn app:app`` works: uvicorn imports the
package ``app`` and then looks for an attribute named ``app`` inside it.
Without this export, ``app:app`` resolves to this (otherwise empty) package and
fails with ``Attribute "app" not found in module "app"``.
"""

from app.app import app

__all__ = ["app"]
