"""
Planificador de ejecución semanal de Noelia Sintética.
Usa la biblioteca `schedule` para lanzar la monitorización cada lunes a las 9:00.
"""

import logging
import signal
import sys
import time
from datetime import datetime

import schedule

logger = logging.getLogger(__name__)


class WeeklyScheduler:
    """Gestiona la ejecución periódica del agente de monitorización."""

    def __init__(self, run_callback, day: str = "monday", run_time: str = "09:00"):
        """
        Args:
            run_callback: Función a ejecutar (sin argumentos).
            day: Día de la semana (monday-sunday).
            run_time: Hora en formato HH:MM.
        """
        self.run_callback = run_callback
        self.day = day.lower()
        self.run_time = run_time
        self._setup_schedule()
        self._setup_signals()

    def _setup_schedule(self) -> None:
        """Registra la tarea en el planificador."""
        day_methods = {
            "monday": schedule.every().monday,
            "tuesday": schedule.every().tuesday,
            "wednesday": schedule.every().wednesday,
            "thursday": schedule.every().thursday,
            "friday": schedule.every().friday,
            "saturday": schedule.every().saturday,
            "sunday": schedule.every().sunday,
        }
        if self.day not in day_methods:
            raise ValueError(f"Día inválido: {self.day}. Usa: {list(day_methods.keys())}")

        day_methods[self.day].at(self.run_time).do(self._execute)
        logger.info(
            "Tarea programada: cada %s a las %s", self.day.capitalize(), self.run_time
        )

    def _execute(self) -> None:
        """Wrapper que ejecuta el callback con manejo de errores."""
        logger.info("=== Iniciando monitorización programada [%s] ===", datetime.now().isoformat())
        try:
            self.run_callback()
            logger.info("=== Monitorización completada ===")
        except Exception as exc:
            logger.exception("Error durante la monitorización: %s", exc)

    def _setup_signals(self) -> None:
        """Configura cierre limpio con Ctrl+C o SIGTERM."""
        def _shutdown(signum, frame):
            logger.info("Señal %d recibida. Cerrando planificador…", signum)
            schedule.clear()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

    def run_now(self) -> None:
        """Ejecuta la tarea inmediatamente (útil para pruebas)."""
        logger.info("Ejecución manual iniciada…")
        self._execute()

    def start(self) -> None:
        """Inicia el loop de espera (bloqueante)."""
        next_run = schedule.next_run()
        logger.info(
            "Planificador activo. Próxima ejecución: %s",
            next_run.strftime("%Y-%m-%d %H:%M") if next_run else "desconocida",
        )
        while True:
            schedule.run_pending()
            time.sleep(30)  # Comprobar cada 30 segundos

    def get_next_run(self) -> str:
        """Devuelve la fecha/hora de la próxima ejecución programada."""
        next_run = schedule.next_run()
        if next_run:
            return next_run.strftime("%Y-%m-%d %H:%M")
        return "no programada"
