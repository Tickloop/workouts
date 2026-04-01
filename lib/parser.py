"""Shared workout file parser for the GitHub-only workout tracker."""

import datetime
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExerciseSet:
    weight: float
    reps: int


@dataclass
class Exercise:
    name: str
    group: str
    sets: list[ExerciseSet] = field(default_factory=list)


@dataclass
class Workout:
    date: datetime.date
    start_time: datetime.time
    end_time: datetime.time
    duration_minutes: float
    exercises: list[Exercise] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)


SET_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*x\s*(\d+)\s*$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_time(s: str) -> datetime.time:
    return datetime.datetime.strptime(s.strip(), "%I:%M %p").time()


def parse_workout_file(filepath: Path) -> Workout:
    date = datetime.date.fromisoformat(filepath.name)
    lines = filepath.read_text().splitlines()

    # Strip trailing whitespace, find non-empty lines
    lines = [line.rstrip() for line in lines]

    start_time = None
    end_time = None
    current_group = "Uncategorized"
    exercises: list[Exercise] = []
    groups_seen: list[str] = []
    current_exercise: Exercise | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.lower().startswith("start:"):
            start_time = parse_time(stripped.split(":", 1)[1])
        elif stripped.lower().startswith("end:"):
            end_time = parse_time(stripped.split(":", 1)[1])
        elif stripped.lower().startswith("group:"):
            current_group = stripped.split(":", 1)[1].strip()
            if current_group not in groups_seen:
                groups_seen.append(current_group)
        else:
            set_match = SET_PATTERN.match(stripped)
            if set_match:
                if current_exercise is None:
                    raise ValueError(f"Set found before any exercise name in {filepath}")
                current_exercise.sets.append(
                    ExerciseSet(weight=float(set_match.group(1)), reps=int(set_match.group(2)))
                )
            else:
                # This is an exercise name
                current_exercise = Exercise(name=stripped, group=current_group)
                exercises.append(current_exercise)

    if start_time is None or end_time is None:
        raise ValueError(f"Missing Start or End time in {filepath}")

    # Calculate duration, handling midnight crossing
    start_dt = datetime.datetime.combine(date, start_time)
    end_dt = datetime.datetime.combine(date, end_time)
    if end_dt < start_dt:
        end_dt += datetime.timedelta(days=1)
    duration_minutes = (end_dt - start_dt).total_seconds() / 60

    return Workout(
        date=date,
        start_time=start_time,
        end_time=end_time,
        duration_minutes=duration_minutes,
        exercises=exercises,
        groups=groups_seen if groups_seen else ["Uncategorized"],
    )


def load_all_workouts(workouts_dir: Path) -> list[Workout]:
    workouts: list[Workout] = []
    if not workouts_dir.is_dir():
        return workouts

    for f in sorted(workouts_dir.iterdir()):
        if not f.is_file():
            continue
        if not DATE_PATTERN.match(f.name):
            continue
        try:
            workouts.append(parse_workout_file(f))
        except Exception as e:
            print(f"Warning: skipping {f.name}: {e}", file=sys.stderr)

    workouts.sort(key=lambda w: w.date)
    return workouts
