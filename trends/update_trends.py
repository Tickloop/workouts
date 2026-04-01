"""Generate TRENDS.md and consistency.svg from all workout files."""

import datetime
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lib.parser import Workout, load_all_workouts


def epley_1rm(weight: float, reps: int) -> float:
    """Estimate 1RM using the Epley formula."""
    if reps == 1:
        return weight
    if weight == 0:
        return 0
    return weight * (1 + reps / 30)


def exercise_trends(workouts: list[Workout]) -> str:
    # Collect per-exercise session data: (date, top_weight, top_reps, best_1rm_weight, best_1rm_reps)
    exercise_sessions: dict[str, list[dict]] = defaultdict(list)
    exercise_group: dict[str, str] = {}

    for w in workouts:
        # Group exercises by name within this workout
        workout_exercises: dict[str, list] = defaultdict(list)
        for ex in w.exercises:
            exercise_group[ex.name] = ex.group
            workout_exercises[ex.name].extend(ex.sets)

        for name, sets in workout_exercises.items():
            if not sets:
                continue
            top_weight_set = max(sets, key=lambda s: (s.weight, s.reps))
            best_1rm_set = max(sets, key=lambda s: epley_1rm(s.weight, s.reps))
            exercise_sessions[name].append({
                "date": w.date,
                "top_weight": top_weight_set.weight,
                "top_reps": top_weight_set.reps,
                "best_1rm_weight": best_1rm_set.weight,
                "best_1rm_reps": best_1rm_set.reps,
            })

    lines = ["## Exercise Trends"]

    for name in sorted(exercise_sessions, key=lambda n: (exercise_group.get(n, ""), n)):
        sessions = exercise_sessions[name]
        grp = exercise_group.get(name, "Uncategorized")
        # Show last 10 sessions, most recent first
        recent = sessions[-10:]
        recent.reverse()

        lines += [
            "",
            f"### {name} ({grp})",
            "",
            "| Date | Top Weight | Est. 1RM | Trend |",
            "|------|-----------|----------|-------|",
        ]

        for i, sess in enumerate(recent):
            tw = sess["top_weight"]
            tr = sess["top_reps"]
            tw_str = f"{int(tw) if tw == int(tw) else tw} x {tr}"

            e1rm = epley_1rm(sess["best_1rm_weight"], sess["best_1rm_reps"])
            e1rm_str = f"{e1rm:.0f}"

            # Trend: compare to next entry (which is the previous session chronologically)
            if i < len(recent) - 1:
                prev = recent[i + 1]
                delta = sess["top_weight"] - prev["top_weight"]
                if delta > 0:
                    trend = f"\U0001f7e2 +{int(delta) if delta == int(delta) else delta}"
                elif delta < 0:
                    trend = f"\U0001f534 {int(delta) if delta == int(delta) else delta}"
                else:
                    trend = "\U0001f7e1 +0"
            else:
                trend = "--"

            lines.append(f"| {sess['date']} | {tw_str} | {e1rm_str} | {trend} |")

    return "\n".join(lines)


def week_comparison(workouts: list[Workout]) -> str:
    # Group workouts by ISO week
    weekly: dict[tuple[int, int], list[Workout]] = defaultdict(list)
    for w in workouts:
        iso = w.date.isocalendar()
        weekly[(iso[0], iso[1])].append(w)

    weeks_sorted = sorted(weekly.keys(), reverse=True)

    lines = [
        "## Week-over-Week Comparison",
        "",
        "| Week | Workouts | Total Volume | Avg Duration | vs Prev Week |",
        "|------|----------|-------------|-------------|--------------|",
    ]

    for i, week_key in enumerate(weeks_sorted):
        wks = weekly[week_key]
        num_workouts = len(wks)

        # Total volume = sum of weight * reps across all sets
        volume = sum(
            s.weight * s.reps
            for w in wks
            for ex in w.exercises
            for s in ex.sets
        )

        avg_dur = sum(w.duration_minutes for w in wks) / num_workouts

        # Week label
        monday = datetime.date.fromisocalendar(week_key[0], week_key[1], 1)
        sunday = monday + datetime.timedelta(days=6)
        week_label = f"{monday.strftime('%b %d')}-{sunday.strftime('%d')}"

        # Trend vs previous week
        if i < len(weeks_sorted) - 1:
            prev_key = weeks_sorted[i + 1]
            prev_wks = weekly[prev_key]
            prev_volume = sum(
                s.weight * s.reps
                for w in prev_wks
                for ex in w.exercises
                for s in ex.sets
            )
            if prev_volume > 0:
                pct_change = (volume - prev_volume) / prev_volume * 100
                if pct_change > 5:
                    trend = "\U0001f7e2"
                elif pct_change < -5:
                    trend = "\U0001f534"
                else:
                    trend = "\U0001f7e1"
            else:
                trend = "\U0001f7e2"
        else:
            trend = "--"

        volume_str = f"{volume:,.0f} lbs"
        lines.append(
            f"| {week_label} | {num_workouts} | {volume_str} | {avg_dur:.0f} min | {trend} |"
        )

    return "\n".join(lines)


COLORS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]


def duration_to_level(minutes: float) -> int:
    if minutes <= 0:
        return 0
    if minutes < 45:
        return 1
    if minutes < 60:
        return 2
    if minutes < 90:
        return 3
    return 4


def generate_consistency_svg(workouts: list[Workout]) -> str:
    # Build date -> duration map
    workout_map: dict[datetime.date, float] = {}
    for w in workouts:
        workout_map[w.date] = workout_map.get(w.date, 0) + w.duration_minutes

    today = datetime.date.today()

    # GitHub-style: weeks run Sunday to Saturday
    # Find the most recent Saturday (or today if Saturday)
    days_until_sat = (5 - today.weekday()) % 7
    end_date = today + datetime.timedelta(days=days_until_sat)
    # 52 weeks back, starting from Sunday
    start_date = end_date - datetime.timedelta(weeks=52) + datetime.timedelta(days=1)
    # Adjust to start on a Sunday
    start_date -= datetime.timedelta(days=start_date.weekday() + 1 if start_date.weekday() != 6 else 0)

    cell_size = 13
    cell_gap = 3
    margin_left = 40
    margin_top = 25
    total_step = cell_size + cell_gap

    # Count weeks
    num_weeks = ((end_date - start_date).days + 1 + 6) // 7

    width = margin_left + num_weeks * total_step + 10
    height = margin_top + 7 * total_step + 10

    parts = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
        f'  <style>',
        f'    text {{ fill: #767676; font-size: 11px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}',
        f'  </style>',
    ]

    # Day labels (Mon, Wed, Fri) at rows 1, 3, 5
    day_labels = {1: "Mon", 3: "Wed", 5: "Fri"}
    for row, label in day_labels.items():
        y = margin_top + row * total_step + cell_size - 2
        parts.append(f'  <text x="0" y="{y}" text-anchor="start">{label}</text>')

    # Month labels
    current_date = start_date
    last_month_label = ""
    for week_col in range(num_weeks):
        week_start = start_date + datetime.timedelta(weeks=week_col)
        month_label = week_start.strftime("%b")
        if month_label != last_month_label:
            x = margin_left + week_col * total_step
            parts.append(f'  <text x="{x}" y="{margin_top - 8}">{month_label}</text>')
            last_month_label = month_label

    # Draw cells
    current_date = start_date
    for week_col in range(num_weeks):
        for day_row in range(7):
            if current_date > today:
                current_date += datetime.timedelta(days=1)
                continue

            x = margin_left + week_col * total_step
            y = margin_top + day_row * total_step
            duration = workout_map.get(current_date, 0)
            level = duration_to_level(duration)
            color = COLORS[level]

            tooltip = f"{current_date}"
            if duration > 0:
                tooltip += f" - {int(duration)} min workout"

            parts.append(
                f'  <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'rx="2" ry="2" fill="{color}">'
                f'<title>{tooltip}</title></rect>'
            )

            current_date += datetime.timedelta(days=1)

    # Legend
    legend_x = width - 120
    legend_y = height - 5
    parts.append(f'  <text x="{legend_x - 30}" y="{legend_y}" font-size="10">Less</text>')
    for i, c in enumerate(COLORS):
        lx = legend_x + i * (cell_size + 2)
        parts.append(
            f'  <rect x="{lx}" y="{legend_y - cell_size + 2}" '
            f'width="{cell_size}" height="{cell_size}" rx="2" ry="2" fill="{c}" />'
        )
    parts.append(
        f'  <text x="{legend_x + 5 * (cell_size + 2)}" y="{legend_y}" font-size="10">More</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)


def generate_trends(workouts: list[Workout]) -> str:
    today = datetime.date.today()
    sections = [
        "# Workout Trends",
        "",
        f"> Last updated: {today} (auto-generated -- do not edit)",
    ]

    if not workouts:
        sections.append("\n*No workouts logged yet. Create a file in `workouts/` to get started!*")
        return "\n".join(sections) + "\n"

    sections.append("")
    sections.append("## Consistency")
    sections.append("")
    sections.append("![Workout Consistency](consistency.svg)")
    sections.append("")
    sections.append(week_comparison(workouts))
    sections.append("")
    sections.append(exercise_trends(workouts))

    return "\n".join(sections) + "\n"


def main():
    repo_root = Path(__file__).resolve().parent.parent
    workouts = load_all_workouts(repo_root / "workouts")

    md = generate_trends(workouts)
    (repo_root / "trends" / "TRENDS.md").write_text(md)

    svg = generate_consistency_svg(workouts)
    (repo_root / "trends" / "consistency.svg").write_text(svg)

    print(f"TRENDS.md and consistency.svg updated ({len(workouts)} workouts processed)")


if __name__ == "__main__":
    main()
