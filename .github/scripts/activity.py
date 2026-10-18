"""Draw a GitHub-style "Activity overview" chart (commits, pull requests,
issues, code review) for the last 12 months, in light and dark variants.

Usage: python activity.py <username> <output-dir>
Reads a token from the GITHUB_TOKEN environment variable. With a token that
can read private repositories, private activity is counted too.
"""

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = "https://api.github.com/search/"


def search_count(kind, query, token):
    url = API + kind + "?per_page=1&q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)["total_count"]


def fetch_counts(user, token):
    since = (date.today() - timedelta(days=365)).isoformat()
    return {
        "commits": search_count("commits", f"author:{user} author-date:>={since}", token),
        "prs": search_count("issues", f"type:pr author:{user} created:>={since}", token),
        "issues": search_count("issues", f"type:issue author:{user} created:>={since}", token),
        "reviews": search_count("issues", f"type:pr reviewed-by:{user} -author:{user} created:>={since}", token),
    }


THEMES = {
    "light": {"line": "#2da44e", "fill": "#2da44e", "text": "#57606a"},
    "dark": {"line": "#3fb950", "fill": "#2ea043", "text": "#8b949e"},
}

W, H = 380, 262
CX, CY = 195, 128
REACH = {"left": 95, "right": 95, "up": 80, "down": 80}


def percentages(counts):
    total = sum(counts.values())
    if total == 0:
        return {k: 0 for k in counts}
    return {k: round(v * 100 / total) for k, v in counts.items()}


def label(text_lines, x, y, anchor, color):
    out = []
    for i, line in enumerate(text_lines):
        out.append(
            f'<text x="{x}" y="{y + i * 20}" text-anchor="{anchor}" fill="{color}" '
            f'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif" '
            f'font-size="17">{line}</text>'
        )
    return "".join(out)


def lines_for(name, pct):
    return [f"{pct}%", name] if pct > 0 else [name]


def render(counts, theme):
    c = THEMES[theme]
    p = percentages(counts)

    # Axes: code review up, issues right, pull requests down, commits left.
    pts = [
        (CX, CY - REACH["up"] * p["reviews"] / 100),
        (CX + REACH["right"] * p["issues"] / 100, CY),
        (CX, CY + REACH["down"] * p["prs"] / 100),
        (CX - REACH["left"] * p["commits"] / 100, CY),
    ]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    # Axes
    svg.append(f'<g stroke="{c["line"]}" stroke-width="2.5" stroke-linecap="round">'
               f'<line x1="{CX}" y1="{CY - REACH["up"]}" x2="{CX}" y2="{CY + REACH["down"]}"/>'
               f'<line x1="{CX - REACH["left"]}" y1="{CY}" x2="{CX + REACH["right"]}" y2="{CY}"/></g>')
    # Shape
    svg.append(f'<polygon points="{poly}" fill="{c["fill"]}" fill-opacity="0.55" '
               f'stroke="{c["line"]}" stroke-width="2.5" stroke-linejoin="round"/>')
    # Points (skip ones sitting on the centre)
    for x, y in pts:
        if (x, y) != (CX, CY):
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#ffffff" '
                       f'stroke="{c["line"]}" stroke-width="2.5"/>')
    svg.append(f'<circle cx="{CX}" cy="{CY}" r="4" fill="#ffffff" stroke="{c["line"]}" stroke-width="2.5"/>')

    # Labels
    up = lines_for("Code review", p["reviews"])
    svg.append(label(up, CX, CY - REACH["up"] - 12 - 20 * (len(up) - 1), "middle", c["text"]))
    down = lines_for("Pull requests", p["prs"])
    svg.append(label(down, CX, CY + REACH["down"] + 24, "middle", c["text"]))
    left = lines_for("Commits", p["commits"])
    svg.append(label(left, CX - REACH["left"] - 40, CY - 10 * (len(left) - 1) + 6, "middle", c["text"]))
    right = lines_for("Issues", p["issues"])
    svg.append(label(right, CX + REACH["right"] + 12, CY - 10 * (len(right) - 1) + 6, "start", c["text"]))

    svg.append("</svg>")
    return "".join(svg)


def main():
    user, out_dir = sys.argv[1], sys.argv[2]
    counts = fetch_counts(user, os.environ["GITHUB_TOKEN"])
    print("counts:", counts, "percent:", percentages(counts))
    os.makedirs(out_dir, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(out_dir, f"activity-{theme}.svg"), "w", encoding="utf-8") as f:
            f.write(render(counts, theme))


if __name__ == "__main__":
    main()
