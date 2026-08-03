"""Import all models so Base.metadata sees every table at create_all time."""
from app.Models.ai import AiSession, PurgeAudit
from app.Models.attention_class import AttentionClass
from app.Models.base import Base
from app.Models.calendar import Calendar
from app.Models.canvas import CanvasAlarm, CanvasItem, CanvasPositionHistory
from app.Models.chore import ChoreDefinition
from app.Models.chore_entropy import ChoreCompletion, ChoreEntropy
from app.Models.chore_healing import ChoreNHistory, ScheduleHealingLog
from app.Models.duration_profile import DurationProfile
from app.Models.event import Event
from app.Models.event_exception import EventException
from app.Models.event_type import EventType
from app.Models.llm_settings import LlmSettings
from app.Models.pomodoro import PomodoroSession, ResidualPrompt, TaskResidual
from app.Models.routine import Routine, RoutineRun, RoutineStep, RoutineStepRun
from app.Models.schedule import ChoreOccurrence, ScheduleRun
from app.Models.todo import Todo
from app.Models.vault import VaultIdentity

__all__ = [
    "AiSession",
    "AttentionClass",
    "Base",
    "Calendar",
    "CanvasAlarm",
    "CanvasItem",
    "CanvasPositionHistory",
    "ChoreCompletion",
    "ChoreDefinition",
    "ChoreEntropy",
    "ChoreNHistory",
    "ChoreOccurrence",
    "DurationProfile",
    "Event",
    "EventException",
    "EventType",
    "LlmSettings",
    "PomodoroSession",
    "PurgeAudit",
    "ResidualPrompt",
    "Routine",
    "RoutineRun",
    "RoutineStep",
    "RoutineStepRun",
    "ScheduleHealingLog",
    "ScheduleRun",
    "TaskResidual",
    "Todo",
    "VaultIdentity",
]
