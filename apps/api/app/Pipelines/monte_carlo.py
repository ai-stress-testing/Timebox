"""Monte Carlo chore scheduler — pure function pipeline (NASA rule 3).

No I/O, no DB, no clock reads: everything arrives as a frozen snapshot and the
run is fully reproducible from (inputs, seed). Iterations are hard-bounded.
The service layer snapshots the DB, calls run_monte_carlo, and persists results.
"""
import random
from dataclasses import dataclass
from datetime import datetime, timedelta

MAX_MC_ITERATIONS = 10_000
_SLOT_GRID_MINUTES = 15
_DAY_JITTERS = (-1, 0, 1)
_MAX_JITTER_TRIES = 4
_DEFAULT_START_MINUTE = 8 * 60
_DEFAULT_END_MINUTE = 20 * 60
_MAX_REBALANCE_PASSES = 200


@dataclass(frozen=True)
class ChoreSpec:
    chore_id: str
    estimated_minutes: int
    priority: int
    n_current: int
    first_due_offset: int
    preferred_days: frozenset[int]
    avoid_days: frozenset[int]
    preferred_start_minute: int | None
    preferred_end_minute: int | None
    weight: float


@dataclass(frozen=True)
class BusyInterval:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True)
class ScheduleInput:
    window_start: datetime  # midnight, day 0
    window_days: int
    chores: tuple[ChoreSpec, ...]
    busy: tuple[BusyInterval, ...]
    iterations: int
    seed: int


@dataclass(frozen=True)
class ScheduledSlot:
    chore_id: str
    start_at: datetime
    end_at: datetime
    confidence_score: float
    load_score: float


@dataclass(frozen=True)
class RunMetrics:
    score: float
    chores_scheduled: int
    mean_daily_load: float
    load_variance: float
    overloaded_days: int
    underloaded_days: int


@dataclass(frozen=True)
class ScheduleResult:
    slots: tuple[ScheduledSlot, ...]
    metrics: RunMetrics


def _due_offsets(chore: ChoreSpec, window_days: int) -> tuple[int, ...]:
    offsets = range(chore.first_due_offset, window_days, chore.n_current)
    return tuple(offsets)


def _clamp(value: int, lo: int, hi: int) -> int:
    return min(max(value, lo), hi)


def _weekday_sun0(day: datetime) -> int:
    return (day.weekday() + 1) % 7


def _sample_day(rng: random.Random, base_offset: int, chore: ChoreSpec, inp: ScheduleInput) -> int:
    for _ in range(_MAX_JITTER_TRIES):
        jitter = rng.choice(_DAY_JITTERS)
        candidate = _clamp(base_offset + jitter, 0, inp.window_days - 1)
        day = inp.window_start + timedelta(days=candidate)
        if _weekday_sun0(day) not in chore.avoid_days:
            return candidate
    return _clamp(base_offset, 0, inp.window_days - 1)


def _sample_start_minute(rng: random.Random, chore: ChoreSpec) -> int:
    lo = chore.preferred_start_minute or _DEFAULT_START_MINUTE
    hi = chore.preferred_end_minute or _DEFAULT_END_MINUTE
    hi_bound = max(lo, hi - chore.estimated_minutes)
    grid_steps = max(1, (hi_bound - lo) // _SLOT_GRID_MINUTES + 1)
    return lo + rng.randrange(grid_steps) * _SLOT_GRID_MINUTES


def _conflicts(start_at: datetime, end_at: datetime, busy: tuple[BusyInterval, ...]) -> bool:
    return any(start_at < b.end_at and end_at > b.start_at for b in busy)


@dataclass(frozen=True)
class _Placement:
    chore: ChoreSpec
    day_offset: int
    start_at: datetime
    end_at: datetime
    slot_score: float


def _score_placement(
    chore: ChoreSpec,
    day: datetime,
    start_at: datetime,
    end_at: datetime,
    inp: ScheduleInput,
    taken: tuple[_Placement, ...],
) -> float:
    weekday = _weekday_sun0(day)
    preference_bonus = 2.0 if weekday in chore.preferred_days else 0.0
    busy_penalty = -5.0 if _conflicts(start_at, end_at, inp.busy) else 0.0
    peer_busy = tuple(BusyInterval(p.start_at, p.end_at) for p in taken)
    peer_penalty = -5.0 if _conflicts(start_at, end_at, peer_busy) else 0.0
    priority_bonus = chore.priority * 0.2
    return (preference_bonus + busy_penalty + peer_penalty + priority_bonus) * chore.weight


def _place_occurrence(
    rng: random.Random,
    chore: ChoreSpec,
    base_offset: int,
    inp: ScheduleInput,
    taken: tuple[_Placement, ...],
) -> _Placement:
    day_offset = _sample_day(rng, base_offset, chore, inp)
    day = inp.window_start + timedelta(days=day_offset)
    start_minute = _sample_start_minute(rng, chore)
    start_at = day + timedelta(minutes=start_minute)
    end_at = start_at + timedelta(minutes=chore.estimated_minutes)
    slot_score = _score_placement(chore, day, start_at, end_at, inp, taken)
    return _Placement(chore, day_offset, start_at, end_at, slot_score)


def _daily_loads(placements: tuple[_Placement, ...], window_days: int) -> tuple[int, ...]:
    counts = [0] * window_days
    for placement in placements:
        counts[placement.day_offset] += 1
    return tuple(counts)


def _variance(values: tuple[int, ...]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _run_iteration(rng: random.Random, inp: ScheduleInput) -> tuple[tuple[_Placement, ...], float]:
    placements: tuple[_Placement, ...] = ()
    for chore in inp.chores:
        for base_offset in _due_offsets(chore, inp.window_days):
            placements = (*placements, _place_occurrence(rng, chore, base_offset, inp, placements))
    load_penalty = _variance(_daily_loads(placements, inp.window_days)) * 0.5
    total = sum(p.slot_score for p in placements) - load_penalty
    return placements, total


def _shift_day(placement: _Placement, new_offset: int, inp: ScheduleInput) -> _Placement:
    delta = timedelta(days=new_offset - placement.day_offset)
    return _Placement(
        placement.chore,
        new_offset,
        placement.start_at + delta,
        placement.end_at + delta,
        placement.slot_score,
    )


def _find_move(
    placements: tuple[_Placement, ...], loads: tuple[int, ...], mean: float, inp: ScheduleInput
) -> tuple[int, int] | None:
    """Return (placement_index, target_day) for one rebalancing move, or None."""
    overloaded = [d for d, load in enumerate(loads) if load > mean + 1]
    underloaded = sorted(d for d, load in enumerate(loads) if load < mean)
    for day in overloaded:
        candidates = [i for i, p in enumerate(placements) if p.day_offset == day]
        by_priority = sorted(candidates, key=lambda i: placements[i].chore.priority)
        for index in by_priority:
            chore = placements[index].chore
            for target in underloaded:
                near_enough = abs(target - day) <= 1
                target_day = inp.window_start + timedelta(days=target)
                allowed = _weekday_sun0(target_day) not in chore.avoid_days
                if near_enough and allowed:
                    return index, target
    return None


def _rebalance(placements: tuple[_Placement, ...], inp: ScheduleInput) -> tuple[_Placement, ...]:
    """Batch rebalance: shift low-priority occurrences off overloaded days (bounded)."""
    current = placements
    for _ in range(min(_MAX_REBALANCE_PASSES, len(placements) + 1)):
        loads = _daily_loads(current, inp.window_days)
        mean = sum(loads) / len(loads) if loads else 0.0
        move = _find_move(current, loads, mean, inp)
        if move is None:
            return current
        index, target = move
        shifted = _shift_day(current[index], target, inp)
        current = (*current[:index], shifted, *current[index + 1 :])
    return current


def _confidence(slot_score: float) -> float:
    return max(0.0, min(1.0, 0.5 + slot_score / 10.0))


def _to_slots(placements: tuple[_Placement, ...], loads: tuple[int, ...]) -> tuple[ScheduledSlot, ...]:
    max_load = max(loads) if loads else 1
    slots = tuple(
        ScheduledSlot(
            chore_id=p.chore.chore_id,
            start_at=p.start_at,
            end_at=p.end_at,
            confidence_score=round(_confidence(p.slot_score), 4),
            load_score=round(1.0 - loads[p.day_offset] / max(max_load, 1), 4),
        )
        for p in placements
    )
    return tuple(sorted(slots, key=lambda s: s.start_at))


def _metrics(placements: tuple[_Placement, ...], score: float, inp: ScheduleInput) -> RunMetrics:
    loads = _daily_loads(placements, inp.window_days)
    mean = sum(loads) / len(loads) if loads else 0.0
    return RunMetrics(
        score=round(score, 4),
        chores_scheduled=len(placements),
        mean_daily_load=round(mean, 2),
        load_variance=round(_variance(loads), 4),
        overloaded_days=sum(1 for load in loads if load > mean + 1),
        underloaded_days=sum(1 for load in loads if load < mean - 1),
    )


def run_monte_carlo(inp: ScheduleInput) -> ScheduleResult:
    iterations = min(inp.iterations, MAX_MC_ITERATIONS)
    rng = random.Random(inp.seed)
    best_placements: tuple[_Placement, ...] = ()
    best_score = float("-inf")
    for _ in range(iterations):
        placements, score = _run_iteration(rng, inp)
        if score > best_score:
            best_placements, best_score = placements, score
    balanced = _rebalance(best_placements, inp)
    if not balanced:
        empty = RunMetrics(0.0, 0, 0.0, 0.0, 0, 0)
        return ScheduleResult(slots=(), metrics=empty)
    loads = _daily_loads(balanced, inp.window_days)
    return ScheduleResult(
        slots=_to_slots(balanced, loads),
        metrics=_metrics(balanced, best_score, inp),
    )
