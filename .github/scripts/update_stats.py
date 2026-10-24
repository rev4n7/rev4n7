"""Refresh the stats on the profile cards from the GitHub API.

Run every day by .github/workflows/update-stats.yml. Only the text inside <g id="info"> in each card is
rewritten; the animated symbol is left alone.
"""
import datetime
import json
import os
import pathlib
import re
import urllib.request

USER = "rev4n7"
ROOT = pathlib.Path(__file__).resolve().parents[2]
WIDTH = 54  # characters per info line, so the dot leaders line up in any monospace font
CARDS = {
    "dark_mode.svg": dict(rule="#2c2932", title="#e5383b", label="#ff6a3d", dots="#3b3741", value="#ece6da"),
    "light_mode.svg": dict(rule="#d3ccc0", title="#b3001b", label="#c0451f", dots="#b9b2a6", value="#17161a"),
}


def api(path):
    request = urllib.request.Request(f"https://api.github.com/{path}",
                                     headers={"Accept": "application/vnd.github+json"})
    if os.environ.get("GH_TOKEN"):
        request.add_header("Authorization", f"Bearer {os.environ['GH_TOKEN']}")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def owned_repos():
    repos, page = [], 1
    while True:
        batch = api(f"users/{USER}/repos?type=owner&per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            return repos
        page += 1


def age(start, end):
    years, months, days = end.year - start.year, end.month - start.month, end.day - start.day
    if days < 0:
        months -= 1
        days += (end.replace(day=1) - datetime.timedelta(days=1)).day
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def stats():
    user, repos = api(f"users/{USER}"), owned_repos()
    counts = {}
    for repo in repos:
        if not repo["fork"] and repo["language"]:
            counts[repo["language"]] = counts.get(repo["language"], 0) + 1
    return dict(
        uptime=age(datetime.date.fromisoformat(user["created_at"][:10]), datetime.datetime.now(datetime.UTC).date()),
        languages=", ".join(sorted(counts, key=lambda name: (-counts[name], name))[:2]),
        repos=str(user["public_repos"]),
        stars=str(sum(repo["stargazers_count"] for repo in repos)),
        commits=str(api(f"search/commits?q=author:{USER}&per_page=1")["total_count"]),
        followers=str(user["followers"]),
    )


def header(title):
    return [("rule", "─ "), ("title", title), ("rule", " " + "─" * (WIDTH - len(title) - 3))]


def field(label, value, width=WIDTH):
    return [("label", f". {label}: "), ("dots", "." * (width - len(label) - len(value) - 5)), ("value", " " + value)]


def pair(left, right):
    return field(*left, width=25) + [("rule", " | ")] + field(*right, width=26)


def info(colors, s):
    lines = [
        (92, header(f"{USER}@github")),
        (116, field("Uptime", s["uptime"])),
        (140, field("Languages", s["languages"])),
        (180, header("Contact")),
        (204, field("GitHub", f"github.com/{USER}")),
        (244, header("GitHub Stats")),
        (268, pair(("Repos", s["repos"]), ("Stars", s["stars"]))),
        (292, pair(("Commits", s["commits"]), ("Followers", s["followers"]))),
    ]
    return "".join(f'<text x="480" y="{y}" class="t" xml:space="preserve">'
                   + "".join(f'<tspan fill="{colors[part]}">{chunk}</tspan>' for part, chunk in parts) + "</text>"
                   for y, parts in lines)


def main():
    s = stats()
    print(s)
    for name, colors in CARDS.items():
        path = ROOT / name
        svg = path.read_text(encoding="utf-8")
        if '<g id="info">' not in svg:
            raise SystemExit(f'{name} has no <g id="info"> to update')
        updated = re.sub(r'(<g id="info">).*?(</g>)', lambda m: m.group(1) + info(colors, s) + m.group(2), svg,
                         count=1, flags=re.S)
        path.write_text(updated, encoding="utf-8", newline="\n")
        print(name, "updated" if updated != svg else "unchanged")


if __name__ == "__main__":
    main()
