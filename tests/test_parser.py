"""Tests for lib/parser.py — workout file parsing."""

import datetime
import sys
import tempfile
from pathlib import Path

# Allow imports from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from lib.parser import ExerciseSet, parse_workout_file, load_all_workouts


def _write_workout(tmp_dir: Path, name: str, content: str) -> Path:
    f = tmp_dir / name
    f.write_text(content)
    return f


# ---------------------------------------------------------------------------
# Happy-path tests: the format used in the fixed 2026-04-09 file
# ---------------------------------------------------------------------------

def test_parse_basic_workout():
    """Standard workout without dash prefixes parses correctly."""
    content = """\
Start: 10:30 PM
Group: Biceps

Preacher
35 x 6
35 x 6
35 x 6
35 x 6

Zottman
20 x 8
20 x 8
20 x 8
20 x 8

Group: Triceps

Overhead V
40 x 12
40 x 12
40 x 12
40 x 12

Rope Push
30 x 12
30 x 12
30 x 12
30 x 12

End: 11:50 PM
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_workout(Path(tmp), "2026-04-09", content)
        w = parse_workout_file(path)

    assert w.date == datetime.date(2026, 4, 9)
    assert w.duration_minutes == 80.0
    assert w.groups == ["Biceps", "Triceps"]
    assert len(w.exercises) == 4

    preacher = w.exercises[0]
    assert preacher.name == "Preacher"
    assert preacher.group == "Biceps"
    assert preacher.sets == [ExerciseSet(35.0, 6)] * 4

    zottman = w.exercises[1]
    assert zottman.name == "Zottman"
    assert zottman.group == "Biceps"
    assert zottman.sets == [ExerciseSet(20.0, 8)] * 4

    overhead = w.exercises[2]
    assert overhead.name == "Overhead V"
    assert overhead.group == "Triceps"
    assert overhead.sets == [ExerciseSet(40.0, 12)] * 4

    rope = w.exercises[3]
    assert rope.name == "Rope Push"
    assert rope.group == "Triceps"
    assert rope.sets == [ExerciseSet(30.0, 12)] * 4


def test_dash_prefix_sets_are_rejected():
    """Dash-prefixed set lines (old format) are NOT parsed as sets.

    The SET_PATTERN requires lines to start with a digit (possibly preceded by
    whitespace). A line like '- 35 x 6' does not match, so it is treated as an
    exercise name rather than a set — which is the bug that was fixed.

    This test documents that behaviour: callers must use the normalised format.
    """
    content = """\
Start: 10:30 PM
Group: Biceps

Preacher
- 35 x 6
- 35 x 6

End: 11:50 PM
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_workout(Path(tmp), "2026-04-09", content)
        w = parse_workout_file(path)

    # The two "- 35 x 6" lines are wrongly treated as exercise names, so we
    # end up with 3 "exercises" and zero sets on the first one.
    broken_exercises = [ex for ex in w.exercises if ex.name.startswith("-")]
    assert len(broken_exercises) > 0, "Dash lines must NOT parse as sets under current SET_PATTERN"


def test_fixed_workout_file_parseable():
    """The actual 2026-04-09 workout file in the repo parses without error."""
    repo_root = Path(__file__).parent.parent
    workout_path = repo_root / "workouts" / "2026-04-09"
    assert workout_path.exists(), "workouts/2026-04-09 must exist"

    w = parse_workout_file(workout_path)

    assert w.date == datetime.date(2026, 4, 9)
    assert w.groups == ["Biceps", "Triceps"]
    assert len(w.exercises) == 4
    # Every exercise must have at least one set
    for ex in w.exercises:
        assert len(ex.sets) > 0, f"Exercise '{ex.name}' has no sets"


def test_load_all_workouts_includes_april9():
    """load_all_workouts includes the fixed 2026-04-09 workout."""
    repo_root = Path(__file__).parent.parent
    workouts = load_all_workouts(repo_root / "workouts")

    dates = [w.date for w in workouts]
    assert datetime.date(2026, 4, 9) in dates


def test_all_workouts_have_sets():
    """Every workout loaded from the repo must have exercises with sets."""
    repo_root = Path(__file__).parent.parent
    workouts = load_all_workouts(repo_root / "workouts")

    assert len(workouts) > 0, "Expected at least one workout"
    for w in workouts:
        for ex in w.exercises:
            assert len(ex.sets) > 0, (
                f"{w.date}: exercise '{ex.name}' (group={ex.group}) has no sets"
            )


def test_duration_calculation():
    """Duration is computed correctly, including midnight-crossing workouts."""
    content = """\
Start: 11:00 PM
Group: Legs

Squat
100 x 5

End: 12:30 AM
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_workout(Path(tmp), "2026-04-10", content)
        w = parse_workout_file(path)

    assert w.duration_minutes == 90.0


def test_decimal_weight():
    """Weights with decimal points are parsed."""
    content = """\
Start: 8:00 AM
Group: Shoulders

Lateral Raise
12.5 x 15
12.5 x 12

End: 8:30 AM
"""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_workout(Path(tmp), "2026-04-11", content)
        w = parse_workout_file(path)

    assert w.exercises[0].sets[0].weight == 12.5


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
