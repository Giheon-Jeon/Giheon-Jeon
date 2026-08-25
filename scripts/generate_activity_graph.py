"""Generate a weekly commit activity line graph from a GitHub user's public
contribution calendar and save it as an SVG.

Uses the public, unauthenticated https://github.com/users/<user>/contributions
endpoint (no token required) instead of a third-party hosted renderer, since
those have repeatedly gone down (payment-required / deployment-disabled).
"""

import os
import re
import sys
import urllib.request
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

USERNAME = os.environ.get("GITHUB_USERNAME", "Giheon-Jeon")
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "assets/activity-line-graph.svg")
COLOR = "#6DB33F"

TD_RE = re.compile(
    r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"\s+id="(?P<id>contribution-day-component-\d+-\d+)"'
)
TOOLTIP_RE = re.compile(
    r'for="(?P<id>contribution-day-component-\d+-\d+)"[^>]*>(?P<text>[^<]*)'
)
COUNT_RE = re.compile(r"^(\d+)")


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_daily_counts(html: str) -> list[tuple[datetime, int]]:
    dates_by_id = {m.group("id"): m.group("date") for m in TD_RE.finditer(html)}
    counts_by_id = {}
    for m in TOOLTIP_RE.finditer(html):
        text = m.group("text").strip()
        match = COUNT_RE.match(text)
        counts_by_id[m.group("id")] = int(match.group(1)) if match else 0

    daily = []
    for id_, date_str in dates_by_id.items():
        if id_ not in counts_by_id:
            continue
        daily.append((datetime.strptime(date_str, "%Y-%m-%d"), counts_by_id[id_]))
    daily.sort(key=lambda x: x[0])
    return daily


def aggregate_weekly(daily: list[tuple[datetime, int]]) -> list[tuple[datetime, int]]:
    weekly = []
    for i in range(0, len(daily), 7):
        chunk = daily[i : i + 7]
        week_start = chunk[0][0]
        total = sum(c for _, c in chunk)
        weekly.append((week_start, total))
    return weekly


def plot(weekly: list[tuple[datetime, int]], output_path: str) -> None:
    dates = [d for d, _ in weekly]
    counts = [c for _, c in weekly]

    fig, ax = plt.subplots(figsize=(11, 3.2), dpi=150)
    ax.plot(dates, counts, color=COLOR, linewidth=2)
    ax.fill_between(dates, counts, color=COLOR, alpha=0.25)

    ax.set_ylim(bottom=0)
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))

    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.spines["bottom"].set_color("#999999")
    ax.tick_params(colors="#999999", labelsize=9)
    ax.set_ylabel("commits / week", color="#999999", fontsize=9)
    ax.grid(axis="y", color="#999999", alpha=0.2)

    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    fig.tight_layout()

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, format="svg", transparent=True)


def main() -> int:
    html = fetch_html(USERNAME)
    daily = parse_daily_counts(html)
    if not daily:
        print("No contribution data parsed; keeping previous SVG.", file=sys.stderr)
        return 1
    weekly = aggregate_weekly(daily)
    plot(weekly, OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} ({len(weekly)} weeks, {sum(c for _, c in weekly)} commits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
