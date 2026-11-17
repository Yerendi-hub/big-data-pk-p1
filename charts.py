import os

import matplotlib
matplotlib.use("Agg")   # render to files only, no window
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
from pymongo import MongoClient

import config

CHARTS_DIR = "charts"

WHITE_COLOR = "#2a78d6"
DRAW_COLOR = "#b5b4ad"
BLACK_COLOR = "#eb6834"
TEXT_COLOR = "#52514e"
GRID_COLOR = "#e5e4e0"

MIN_GAMES = 1000
TOP_OPENINGS = 15
SPEED_ORDER = ["ultrabullet", "bullet", "blitz", "rapid", "classical", "correspondence"]


def load_rows(db, name):
    doc = db.results.find_one({"_id": name})
    if doc is None:
        raise SystemExit(f"No results for '{name}'. Run run_analyses.py first.")
    return doc["rows"]


def format_count(n):
    """613922 -> '613 922' (Polish thousands separator)."""
    return f"{n:,}".replace(",", " ")


def style_axes(ax, grid_axis):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.tick_params(colors=TEXT_COLOR)
    ax.grid(axis=grid_axis, color=GRID_COLOR, linewidth=0.8)
    ax.set_axisbelow(True)   # grid behind the bars


def outcome_shares(rows):
    """Percentages of white wins, draws and black wins for each row."""
    white = [100 * r["white_wins"] / r["games"] for r in rows]
    draws = [100 * r["draws"] / r["games"] for r in rows]
    black = [100 * r["black_wins"] / r["games"] for r in rows]
    return white, draws, black


def save(fig, filename):
    path = os.path.join(CHARTS_DIR, filename)
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  saved:", path)


def chart_elo_results(db):
    rows = [r for r in load_rows(db, "elo_results") if r["games"] >= MIN_GAMES]
    labels = [f"{r['elo_bucket']}–{r['elo_bucket'] + 199}" for r in rows]
    white, draws, black = outcome_shares(rows)
    white_plus_draws = [w + d for w, d in zip(white, draws)]

    fig, ax = plt.subplots(figsize=(10, 5))
    bar = {"width": 0.7, "edgecolor": "white", "linewidth": 1}
    ax.bar(labels, white, color=WHITE_COLOR, label="Wygrane białych", **bar)
    ax.bar(labels, draws, bottom=white, color=DRAW_COLOR, label="Remisy", **bar)
    ax.bar(labels, black, bottom=white_plus_draws, color=BLACK_COLOR, label="Wygrane czarnych", **bar)

    ax.set_title(f"Wynik partii a średni ranking graczy (przedziały z ≥ {format_count(MIN_GAMES)} partii)")
    ax.set_xlabel("Średni ranking obu graczy")
    ax.yaxis.set_major_formatter(PercentFormatter())
    ax.set_ylim(0, 100)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=3, frameon=False)
    style_axes(ax, "y")
    save(fig, "elo_results.png")


def chart_opening_results(db):
    rows = sorted(load_rows(db, "opening_results"), key=lambda r: r["games"], reverse=True)
    rows = rows[:TOP_OPENINGS][::-1]   # barh draws bottom-up, so reverse to put #1 on top
    labels = [f"{r['opening_family']} ({format_count(r['games'])})" for r in rows]
    white, draws, black = outcome_shares(rows)
    white_plus_draws = [w + d for w, d in zip(white, draws)]

    fig, ax = plt.subplots(figsize=(10, 7))
    bar = {"height": 0.7, "edgecolor": "white", "linewidth": 1}
    ax.barh(labels, white, color=WHITE_COLOR, label="Wygrane białych", **bar)
    ax.barh(labels, draws, left=white, color=DRAW_COLOR, label="Remisy", **bar)
    ax.barh(labels, black, left=white_plus_draws, color=BLACK_COLOR, label="Wygrane czarnych", **bar)

    ax.set_title(f"Wyniki w {TOP_OPENINGS} najpopularniejszych rodzinach debiutów (w nawiasie liczba partii)")
    ax.xaxis.set_major_formatter(PercentFormatter())
    ax.set_xlim(0, 100)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=False)
    style_axes(ax, "x")
    save(fig, "opening_results.png")


def chart_speed_length(db):
    by_speed = {r["speed"]: r for r in load_rows(db, "speed_length")}
    rows = [by_speed[s] for s in SPEED_ORDER if s in by_speed]
    labels = [f"{r['speed']}\n({format_count(r['games'])} partii)" for r in rows]
    averages = [r["avg_moves"] for r in rows]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, averages, width=0.6, color=WHITE_COLOR)
    ax.bar_label(bars, fmt="%.1f", color=TEXT_COLOR, padding=3)

    ax.set_title("Średnia liczba ruchów w partii według tempa gry")
    ax.set_ylabel("Średnia liczba ruchów")
    style_axes(ax, "y")
    save(fig, "speed_length.png")


def main():
    os.makedirs(CHARTS_DIR, exist_ok=True)
    db = MongoClient(config.MONGO_URI_LOCAL)[config.DB_NAME]

    chart_elo_results(db)
    chart_opening_results(db)
    chart_speed_length(db)


if __name__ == "__main__":
    main()