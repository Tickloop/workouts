"""Generate INSIGHTS.md from all workout files."""

import datetime
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.parser import Workout, load_all_workouts


def format_duration(minutes: float) -> str:
    h = int(minutes) // 60
    m = int(minutes) % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def time_statistics(workouts: list[Workout]) -> str:
    total = sum(w.duration_minutes for w in workouts)
    avg = total / len(workouts)
    longest = max(workouts, key=lambda w: w.duration_minutes)
    shortest = min(workouts, key=lambda w: w.duration_minutes)

    lines = [
        "## Time Statistics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Workouts | {len(workouts)} |",
        f"| Total Time | {format_duration(total)} |",
        f"| Average Duration | {format_duration(avg)} |",
        f"| Longest Workout | {format_duration(longest.duration_minutes)} ({longest.date}) |",
        f"| Shortest Workout | {format_duration(shortest.duration_minutes)} ({shortest.date}) |",
    ]

    # Time per body part (proportional split)
    group_time: dict[str, float] = defaultdict(float)
    group_sessions: dict[str, int] = defaultdict(int)

    for w in workouts:
        # Count exercises per group in this workout
        group_ex_count: dict[str, int] = defaultdict(int)
        for ex in w.exercises:
            group_ex_count[ex.group] += 1
        total_ex = sum(group_ex_count.values())
        if total_ex == 0:
            continue
        for grp, count in group_ex_count.items():
            group_time[grp] += w.duration_minutes * count / total_ex
            group_sessions[grp] += 1

    if group_time:
        lines += [
            "",
            "### Time per Body Part",
            "",
            "| Body Part | Total Time | Avg per Session | Sessions |",
            "|-----------|-----------|-----------------|----------|",
        ]
        for grp in sorted(group_time, key=lambda g: group_time[g], reverse=True):
            t = group_time[grp]
            s = group_sessions[grp]
            lines.append(f"| {grp} | {format_duration(t)} | {format_duration(t / s)} | {s} |")

    return "\n".join(lines)


def personal_records(workouts: list[Workout]) -> str:
    # Track per-exercise: max weight, reps at that weight, date, group
    # Also track the most recent session date per exercise
    exercise_data: dict[str, dict] = {}

    for w in workouts:
        for ex in w.exercises:
            key = ex.name
            if key not in exercise_data:
                exercise_data[key] = {
                    "group": ex.group,
                    "pr_weight": 0.0,
                    "pr_reps": 0,
                    "pr_date": w.date,
                    "last_session_date": w.date,
                    "is_bodyweight": True,
                }

            data = exercise_data[key]
            data["last_session_date"] = w.date

            for s in ex.sets:
                if s.weight > 0:
                    data["is_bodyweight"] = False

                if data["is_bodyweight"]:
                    # For bodyweight exercises, PR = max reps
                    if s.reps > data["pr_reps"]:
                        data["pr_reps"] = s.reps
                        data["pr_weight"] = s.weight
                        data["pr_date"] = w.date
                elif s.weight > data["pr_weight"] or (
                    s.weight == data["pr_weight"] and s.reps > data["pr_reps"]
                ):
                    data["pr_weight"] = s.weight
                    data["pr_reps"] = s.reps
                    data["pr_date"] = w.date

    # Group by body part
    by_group: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for name, data in exercise_data.items():
        by_group[data["group"]].append((name, data))

    lines = ["## Personal Records"]

    for grp in sorted(by_group):
        lines += [
            "",
            f"### {grp}",
            "",
            "| Exercise | PR Weight | Reps @ PR | Date | Badge |",
            "|----------|-----------|-----------|------|-------|",
        ]
        for name, data in sorted(by_group[grp], key=lambda x: x[0]):
            badges = "\U0001f451"  # crown
            if data["pr_date"] == data["last_session_date"]:
                badges += " \U0001f195"  # NEW PR

            if data["is_bodyweight"]:
                weight_str = "BW"
            else:
                w = data["pr_weight"]
                weight_str = f"{int(w)}" if w == int(w) else f"{w}"

            lines.append(
                f"| {name} | {weight_str} | {data['pr_reps']} reps | {data['pr_date']} | {badges} |"
            )

    return "\n".join(lines)


def frequency_stats(workouts: list[Workout]) -> str:
    first_date = workouts[0].date
    last_date = workouts[-1].date
    total_days = (last_date - first_date).days + 1
    total_weeks = max(total_days / 7, 1)

    # Weekly streak calculation
    def get_iso_week(d: datetime.date) -> tuple[int, int]:
        iso = d.isocalendar()
        return (iso[0], iso[1])

    workout_weeks = set(get_iso_week(w.date) for w in workouts)

    # Calculate current and longest streak of consecutive weeks
    all_weeks = sorted(workout_weeks)
    longest_streak = 0
    current_streak = 0

    if all_weeks:
        streak = 1
        for i in range(1, len(all_weeks)):
            prev_year, prev_week = all_weeks[i - 1]
            curr_year, curr_week = all_weeks[i]
            # Check if consecutive (simple heuristic)
            prev_date = datetime.date.fromisocalendar(prev_year, prev_week, 1)
            curr_date = datetime.date.fromisocalendar(curr_year, curr_week, 1)
            if (curr_date - prev_date).days == 7:
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

        # Current streak: count backwards from most recent week
        today_week = get_iso_week(datetime.date.today())
        # Include current week or most recent workout week
        last_workout_week = all_weeks[-1]
        last_workout_date = datetime.date.fromisocalendar(last_workout_week[0], last_workout_week[1], 1)
        today_date = datetime.date.fromisocalendar(today_week[0], today_week[1], 1)
        if (today_date - last_workout_date).days > 13:
            current_streak = 0
        else:
            current_streak = 1
            for i in range(len(all_weeks) - 2, -1, -1):
                prev_date = datetime.date.fromisocalendar(all_weeks[i][0], all_weeks[i][1], 1)
                curr_date = datetime.date.fromisocalendar(all_weeks[i + 1][0], all_weeks[i + 1][1], 1)
                if (curr_date - prev_date).days == 7:
                    current_streak += 1
                else:
                    break

    lines = [
        "## Workout Frequency",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Workouts | {len(workouts)} |",
        f"| Avg per Week | {len(workouts) / total_weeks:.1f} |",
        f"| Current Streak | {current_streak} weeks |",
        f"| Longest Streak | {longest_streak} weeks |",
    ]

    # Monthly breakdown
    monthly: dict[str, int] = defaultdict(int)
    for w in workouts:
        key = w.date.strftime("%Y-%m")
        monthly[key] += 1

    lines += [
        "",
        "### Monthly Breakdown",
        "",
        "| Month | Workouts |",
        "|-------|----------|",
    ]
    for month in sorted(monthly, reverse=True):
        lines.append(f"| {month} | {monthly[month]} |")

    return "\n".join(lines)


def frequency_per_body_part(workouts: list[Workout]) -> str:
    group_count: dict[str, int] = defaultdict(int)
    for w in workouts:
        seen = set()
        for ex in w.exercises:
            if ex.group not in seen:
                group_count[ex.group] += 1
                seen.add(ex.group)

    total = len(workouts)
    lines = [
        "### Frequency per Body Part",
        "",
        "| Body Part | Sessions | % of Workouts |",
        "|-----------|----------|---------------|",
    ]
    for grp in sorted(group_count, key=lambda g: group_count[g], reverse=True):
        c = group_count[grp]
        pct = c / total * 100
        lines.append(f"| {grp} | {c} | {pct:.0f}% |")

    return "\n".join(lines)


def exercise_details(workouts: list[Workout]) -> str:
    # Per exercise: sessions, total sets, avg reps, max reps, avg weight, max weight
    stats: dict[str, dict] = {}

    for w in workouts:
        for ex in w.exercises:
            key = ex.name
            if key not in stats:
                stats[key] = {
                    "group": ex.group,
                    "sessions": 0,
                    "total_sets": 0,
                    "total_reps": 0,
                    "max_reps": 0,
                    "total_weight": 0.0,
                    "max_weight": 0.0,
                    "session_dates": set(),
                }
            s = stats[key]
            if w.date not in s["session_dates"]:
                s["sessions"] += 1
                s["session_dates"].add(w.date)
            for st in ex.sets:
                s["total_sets"] += 1
                s["total_reps"] += st.reps
                s["max_reps"] = max(s["max_reps"], st.reps)
                s["total_weight"] += st.weight
                s["max_weight"] = max(s["max_weight"], st.weight)

    by_group: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    for name, data in stats.items():
        by_group[data["group"]].append((name, data))

    lines = ["### Exercise Details"]

    for grp in sorted(by_group):
        lines += [
            "",
            f"#### {grp}",
            "",
            "| Exercise | Sessions | Total Sets | Avg Reps | Max Reps | Avg Weight | Max Weight |",
            "|----------|----------|-----------|----------|----------|------------|------------|",
        ]
        for name, data in sorted(by_group[grp], key=lambda x: x[0]):
            avg_reps = data["total_reps"] / data["total_sets"] if data["total_sets"] else 0
            avg_weight = data["total_weight"] / data["total_sets"] if data["total_sets"] else 0
            max_w = data["max_weight"]
            lines.append(
                f"| {name} | {data['sessions']} | {data['total_sets']} "
                f"| {avg_reps:.1f} | {data['max_reps']} "
                f"| {avg_weight:.1f} | {int(max_w) if max_w == int(max_w) else max_w} |"
            )

    return "\n".join(lines)


def generate_insights(workouts: list[Workout]) -> str:
    today = datetime.date.today()
    sections = [
        f"# Workout Insights",
        f"",
        f"> Last updated: {today} (auto-generated -- do not edit)",
    ]

    if not workouts:
        sections.append("\n*No workouts logged yet. Create a file in `workouts/` to get started!*")
        return "\n".join(sections) + "\n"

    sections.append("")
    sections.append(time_statistics(workouts))
    sections.append("")
    sections.append(personal_records(workouts))
    sections.append("")
    sections.append(frequency_stats(workouts))
    sections.append("")
    sections.append(frequency_per_body_part(workouts))
    sections.append("")
    sections.append(exercise_details(workouts))

    return "\n".join(sections) + "\n"


def main():
    repo_root = Path(__file__).resolve().parent.parent
    workouts = load_all_workouts(repo_root / "workouts")
    output = generate_insights(workouts)
    (repo_root / "insights" / "INSIGHTS.md").write_text(output)
    print(f"INSIGHTS.md updated ({len(workouts)} workouts processed)")


if __name__ == "__main__":
    main()
