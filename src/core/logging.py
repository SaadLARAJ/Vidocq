"""
ShadowMap Entreprise v4.0 - Configuration de la journalisation structurée

ZÉRO instruction print() autorisée dans le code de production.
Toute la journalisation utilise structlog avec sérialisation JSON pour l'analyse automatique.

Utilisation :
    import structlog
    logger = structlog.get_logger()
    logger.info("entity_extracted", entity_id=entity.id, confidence=0.85)
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger

from src.config import settings


def add_app_context(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Ajoute un contexte au niveau de l'application à toutes les entrées de journal.

    Args:
        logger: Instance du logger enveloppé.
        method_name: Nom de la méthode de journalisation appelée.
        event_dict: Dictionnaire d'événements à journaliser.

    Returns:
        Dictionnaire d'événements modifié avec le contexte de l'application.
    """
    event_dict["environment"] = settings.ENVIRONMENT
    event_dict["app"] = "shadowmap-enterprise"
    event_dict["version"] = "4.0.0"
    return event_dict


def drop_color_message_key(
    logger: WrappedLogger, method_name: str, event_dict: EventDict
) -> EventDict:
    """
    Supprime les clés de formatage de couleur ajoutées par ConsoleRenderer en production.

    Args:
        logger: Instance du logger enveloppé.
        method_name: Nom de la méthode de journalisation appelée.
        event_dict: Dictionnaire d'événements à journaliser.

    Returns:
        Dictionnaire d'événements avec les clés de couleur supprimées.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog pour une journalisation JSON de qualité production.

    - Sortie JSON en production/staging pour les systèmes d'agrégation de logs.
    - Sortie console avec couleurs en développement.
    - Tous les logs incluent l'horodatage, le niveau, le contexte de l'application.
    - Aucune instruction print() autorisée - les logs sont structurés.
    """
    # Détermine si l'exécution est en mode développement
    is_development = settings.ENVIRONMENT == "development"

    # Configure la journalisation de la bibliothèque standard
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )

    # Processeurs partagés pour tous les environnements
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
    ]

    # Processeurs spécifiques à l'environnement
    if is_development:
        # Développement : sortie console lisible par l'homme avec des couleurs
        processors = shared_processors + [
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production/Staging : JSON analysable par une machine
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            drop_color_message_key,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,  # type: ignore
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """
    Obtient une instance de logger structlog configurée.

    Args:
        name: Nom optionnel du logger (par défaut le nom du module).

    Returns:
        Logger structlog configuré.

    Exemple :
        >>> logger = get_logger(__name__)
        >>> logger.info("task_started", task_id="123", priority="high")
    """
    return structlog.get_logger(name)


# Initialise la journalisation à l'importation du module
configure_logging()

