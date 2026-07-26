"""Import all models so Base.metadata sees every table at create_all time."""
from app.Models.ai import AiSession, PurgeAudit
from app.Models.base import Base
from app.Models.calendar import Calendar
from app.Models.chore import ChoreDefinition
from app.Models.chore_entropy import ChoreCompletion, ChoreEntropy
from app.Models.event import Event
from app.Models.event_exception import EventException
from app.Models.event_type import EventType
from app.Models.llm_settings import LlmSettings
from app.Models.pomodoro import PomodoroSession, ResidualPrompt, TaskResidual
from app.Models.schedule import ChoreOccurrence, ScheduleRun
from app.Models.todo import Todo
from app.Models.vault import VaultIdentity

__all__ = [
    "AiSession",
    "Base",
    "Calendar",
    "ChoreCompletion",
    "ChoreDefinition",
    "ChoreEntropy",
    "ChoreOccurrence",
    "Event",
    "EventException",
    "EventType",
    "LlmSettings",
    "PomodoroSession",
    "PurgeAudit",
    "ResidualPrompt",
    "ScheduleRun",
    "TaskResidual",
    "Todo",
    "VaultIdentity",
]
