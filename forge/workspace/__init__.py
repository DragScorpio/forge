"""Workspace manager: run every attempt in an isolated copy, never on the committed task repo."""

from .manager import Workspace, checkout

__all__ = ["Workspace", "checkout"]
