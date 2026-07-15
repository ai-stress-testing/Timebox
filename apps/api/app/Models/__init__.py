"""Import all models so Base.metadata sees every table at create_all time."""
from app.Models.ai import AiSession, PurgeAudit
from app.Models.base import Base
from app.Models.calendar import Calendar
from app.Models.chore import ChoreDefinition
from app.Models.event import Event
from app.Models.llm_settings import LlmSettings
from app.Models.pomodoro import PomodoroSession, ResidualPrompt, TaskResidual
from app.Models.schedule import ChoreOccurrence, ScheduleRun
from app.Models.vault import VaultIdentity

__all__ = [
    "AiSession",
    "Base",
    "Calendar",
    "ChoreDefinition",
    "ChoreOccurrence",
    "Event",
    "LlmSettings",
    "PomodoroSession",
    "PurgeAudit",
    "ResidualPrompt",
    "ScheduleRun",
    "TaskResidual",
    "VaultIdentity",
]
