# Copyright (c) 2024 Sansible Contributors
# MIT License

"""
Sansible: Minimal Ansible-compatible playbook runner.

A lightweight, pure-Python alternative to Ansible for running simple playbooks
on Windows and Linux hosts via SSH and WinRM.

Features:
    - Pure Python wheel (py3-none-any) — no compiled extensions
    - Windows-native control node — no WSL required
    - SSH (asyncssh) and WinRM (pypsrp) connections
    - Subset of Ansible module and feature support

This package exposes the main CLI entry point and release metadata.
"""

from __future__ import annotations

from sansible.release import __version__, __author__, __codename__

__all__ = [
    "__version__",
    "__author__",
    "__codename__",
]
