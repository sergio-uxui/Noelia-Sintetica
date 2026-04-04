"""Noelia Sintética — Agente de monitorización semanal de ofertas de empleo."""

__version__ = "0.1.0"
__author__ = "Noelia Sintética"

from .agent import NoeliAgent
from .storage import Database

__all__ = ["NoeliAgent", "Database"]
