"""Refresh the contribution graph + info-card stats from your REAL public GitHub activity.

Uses only the Python standard library. Run by .github/workflows/update-profile.yml
every day; you can also run it by hand:  python scripts/update_contributions.py
"""
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import make_heatmap as hm       # noqa: E402
import make_info_card as ic     # noqa: E402
from config import load         # noqa: E402


def fetch_days(user):
    req = urllib.request.Request(
        f"https://github.com/users/{user}/contributions",
        headers={"User-Agent": "Mozilla/5.0 (profile-updater)"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    date_of = {i: d for d, i in re.findall(r'data-date="([\d-]+)" id="(contribution-day-component-[\d-]+)"', page)}
    days = {}
    for fid, txt in re.findall(r'for="(contribution-day-component-[\d-]+)"[^>]*>\s*([^<]*)', page):
        m = re.match(r"(\d+|No) contribution", html.unescape(txt).strip())
        if m and fid in date_of:
            days[date_of[fid]] = 0 if m.group(1) == "No" else int(m.group(1))
    data = sorted((dt.date.fromisoformat(d), c) for d, c in days.items())
    if len(data) < 300:
        raise SystemExit(f"Only found {len(data)} days of data - GitHub's page may have changed; keeping old files.")
    return data


def main():
    user = load()["github_username"]
    data = fetch_days(user)
    st = hm.stats(data)

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    cjson = os.path.join(ROOT, "data", "contributions.json")
    json.dump({"stats": st, "days": [[d.isoformat(), c] for d, c in data]}, open(cjson, "w"), indent=1)
    os.environ["CONTRIB_JSON"] = cjson
    open(os.path.join(ROOT, "assets", "contrib-heatmap.svg"), "w").write(hm.svg(data, st))

    # keep the info card the same height as the existing portrait window
    card_path = os.path.join(ROOT, "assets", "info-card.svg")
    m = re.search(r'viewBox="0 0 \d+ (\d+)"', open(card_path).read())
    height = int(m.group(1)) if m else 500
    os.environ["MIN_H"] = str(height)
    open(card_path, "w").write(ic.card(height)[0])
    print(f"updated for {user}: {st}")


if __name__ == "__main__":
    main()
