"""Agent Failure Lab application package.

Re-export the ASGI app so that ``uvicorn app:app`` works: uvicorn imports the
package ``app`` and then looks for an attribute named ``app`` inside it.
Without this export, ``app:app`` resolves to this (otherwise empty) package and
fails with ``Attribute "app" not found in module "app"``.
"""
# Day 17 - 避免包初始化时触发 FastAPI 应用导入
#from app.app import app

__all__ = ["app"]
