# Workout Tracker

A workout tracker built **entirely on GitHub** -- no servers, no databases, no frontend frameworks.

| Layer      | Technology              |
|------------|-------------------------|
| UI         | GitHub Mobile           |
| Backend    | GitHub Actions          |
| Database   | Git + GitHub            |
| Hosting    | GitHub (repo itself)    |

## The Vision

Every part of this app runs on GitHub:

- **Recording workouts** = creating a file via GitHub Mobile
- **Processing data** = GitHub Actions triggered on push
- **Storing history** = Git commits are the database
- **Viewing stats** = reading markdown files on GitHub Mobile
- **Visualizations** = SVG files rendered inline by GitHub

No external services. No deployments. No infrastructure to maintain. Just GitHub.

## How It Works

1. Open GitHub Mobile, navigate to `workouts/`, create a new file named `YYYY-MM-DD`
2. Write your workout in the format below and commit
3. A GitHub Action automatically runs to regenerate your stats
4. View your updated insights and trends right in the repo:
   - [`insights/INSIGHTS.md`](insights/INSIGHTS.md) -- Personal records, frequency stats, time analysis
   - [`trends/TRENDS.md`](trends/TRENDS.md) -- Exercise progression, week-over-week comparison, consistency heatmap

## Workout File Format

Create a file like `workouts/2026-03-31`:

```
Start: 07:30 AM
Group: Chest

Bench Press
135 x 10
185 x 8
225 x 6

Incline Dumbbell Press
50 x 12
60 x 10

Group: Triceps

Tricep Pushdown
40 x 15
50 x 12

End: 08:45 AM
```

**Rules:**
- First line: `Start: hh:mm AM/PM`
- `Group: <muscle group>` before exercises (multiple groups per workout allowed)
- Exercise name on its own line, followed by `weight x reps` lines
- Empty line between exercises
- Last line: `End: hh:mm AM/PM`

## Generated Reports

| Report | What's Inside |
|--------|---------------|
| [INSIGHTS.md](insights/INSIGHTS.md) | Workout time stats, personal records with badges, workout frequency, per-body-part breakdown, exercise details |
| [TRENDS.md](trends/TRENDS.md) | Exercise weight progression, week-over-week volume comparison, GitHub-style consistency heatmap |
