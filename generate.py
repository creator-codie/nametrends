#!/usr/bin/env python3
"""
Site generator for the NameTrends programmatic SEO site.

This script downloads the U.S. Social Security Administration (SSA) baby
names dataset (which is in the public domain) and builds a static website
highlighting the fastest‑rising names. The dataset contains name, sex and
count for each year from 1880 onward. Each run produces an `index.html`
listing the top trending names along with individual pages for every
featured name. The output is placed into a `site` directory.

To keep dependencies to a minimum this script relies only on Python's
standard library. It can run as part of a GitHub Actions workflow or
locally.
"""

import csv
import io
import json
import os
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime

# Constants for the SSA names dataset
NAMES_ZIP_URL = "https://www.ssa.gov/oact/babynames/names.zip"


def download_names_zip() -> bytes:
    """Download the SSA names ZIP and return its binary content.

    Some servers block requests without a User‑Agent header, so we send a
    browser‑like header to improve reliability. If the request fails, an
    exception will be raised.
    """
    req = urllib.request.Request(
        NAMES_ZIP_URL,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0 Safari/537.36"},
    )
    with urllib.request.urlopen(req) as response:
        return response.read()


def parse_names(zip_bytes: bytes):
    """Parse the zipped SSA dataset and return a nested dictionary.

    Returns a mapping of the form:
      years[year][sex][name] = count
    """
    years: dict[int, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(dict))
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for filename in zf.namelist():
            if not filename.startswith("yob") or not filename.endswith(".txt"):
                continue
            year = int(filename[3:7])
            with zf.open(filename) as fh:
                reader = csv.reader(io.TextIOWrapper(fh, encoding="utf-8"))
                for row in reader:
                    name, sex, count = row
                    years[year][sex][name] = int(count)
    return years


def compute_ranks(years_data):
    """Compute rank for each name per year and sex.

    Returns a mapping:
      ranks[sex][name][year] = rank (1 = most common).
    If a name does not appear for a given year/sex it is omitted.
    """
    ranks: dict[str, dict[str, dict[int, int]]] = {"M": defaultdict(dict), "F": defaultdict(dict)}
    for year, sex_data in years_data.items():
        for sex, names_counts in sex_data.items():
            # Sort names by count descending
            sorted_names = sorted(names_counts.items(), key=lambda kv: (-kv[1], kv[0]))
            for rank, (name, _) in enumerate(sorted_names, start=1):
                ranks[sex][name][year] = rank
    return ranks


def calculate_trending(ranks, top_n=100):
    """Calculate the top N names with the biggest rank improvement in the last year.

    Improvement is measured as previous_rank - current_rank; a positive value
    means the name rose in popularity. Names must appear in both years to
    qualify.
    """
    # Determine the two most recent years common to both genders
    all_years = set()
    for sex in ranks:
        for name in ranks[sex]:
            all_years.update(ranks[sex][name].keys())
    if len(all_years) < 2:
        return []
    last_year = max(all_years)
    prev_year = max(y for y in all_years if y < last_year)

    trending_list = []
    for sex in ["M", "F"]:
        for name, year_ranks in ranks[sex].items():
            if last_year in year_ranks and prev_year in year_ranks:
                prev_rank = year_ranks[prev_year]
                current_rank = year_ranks[last_year]
                improvement = prev_rank - current_rank
                trending_list.append((name, sex, current_rank, prev_rank, improvement))
    # Sort by improvement descending, then by current rank ascending
    trending_list.sort(key=lambda tup: (-(tup[4]), tup[2], tup[0]))
    return trending_list[:top_n]


def render_index(trending_list, config):
    """Render the index.html page listing trending names."""
    site_name = config.get("site_name", "NameTrends")
    description = config.get("description", "")
    rows = []
    for name, sex, current_rank, prev_rank, improvement in trending_list:
        # Link to individual page for the name/sex pair
        link = f"names/{name}-{sex}.html"
        rows.append(
            f"<tr><td><a href=\"{link}\">{name}</a></td><td>{sex}</td>"
            f"<td>{current_rank}</td><td>{prev_rank}</td><td>{improvement:+}</td></tr>"
        )
    rows_html = "\n".join(rows)
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{site_name}</title>
  <link rel=\"stylesheet\" href=\"assets/style.css\">
  <meta name=\"description\" content=\"{description}\">
</head>
<body>
  <header>
    <h1>{site_name}</h1>
    <p>{description}</p>
  </header>
  <h2>Top Trending Names</h2>
  <table>
    <thead>
      <tr><th>Name</th><th>Gender</th><th>Rank (latest)</th><th>Rank (prev)</th><th>Improvement</th></tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <footer>
    <p>Data from the U.S. Social Security Administration (public domain). Generated on {datetime.utcnow().date()}</p>
  </footer>
</body>
</html>"""
    return html


def render_name_page(name, sex, year_ranks, config):
    """Render an individual name page."""
    site_name = config.get("site_name", "NameTrends")
    # Sort years ascending
    years = sorted(year_ranks.keys())
    rows_html = "\n".join(
        f"<tr><td>{year}</td><td>{year_ranks[year]}</td></tr>" for year in years
    )
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
  <title>{name} ({sex}) - {site_name}</title>
  <link rel=\"stylesheet\" href=\"../assets/style.css\">
</head>
<body>
  <header>
    <h1>{name} ({sex})</h1>
    <p><a href=\"../index.html\">&larr; Back to index</a></p>
  </header>
  <h2>Rank by Year</h2>
  <table>
    <thead><tr><th>Year</th><th>Rank</th></tr></thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <footer>
    <p>Data source: U.S. Social Security Administration (public domain)</p>
  </footer>
</body>
</html>"""
    return html


def write_assets(output_dir):
    """Write static assets such as CSS to the output directory."""
    assets_path = os.path.join(output_dir, "assets")
    os.makedirs(assets_path, exist_ok=True)
    css = """
body { font-family: Arial, sans-serif; line-height: 1.5; margin: 0; padding: 0; background: #f9f9f9; }
header, footer { background: #004080; color: white; padding: 1rem; }
header h1 { margin: 0; font-size: 2rem; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
th, td { padding: 0.5rem; border-bottom: 1px solid #ddd; text-align: left; }
th { background: #f2f2f2; }
a { color: #004080; text-decoration: none; }
a:hover { text-decoration: underline; }
"""
    with open(os.path.join(assets_path, "style.css"), "w", encoding="utf-8") as f:
        f.write(css)


def build_site():
    """Main entry point: build the site under the `site` directory."""
    # Load configuration
    # Load the config.json from the same directory as this script. The
    # repository layout puts generate.py in the top level, so use __file__'s
    # directory directly rather than going up a directory.
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, encoding="utf-8") as cf:
        config = json.load(cf)

    # Download and parse data
    zip_bytes = download_names_zip()
    years_data = parse_names(zip_bytes)
    ranks = compute_ranks(years_data)
    trending = calculate_trending(ranks, top_n=100)

    # Prepare output directory
    # Write all generated pages into a "site" subdirectory that sits
    # alongside this script. Using exist_ok=True avoids errors on
    # subsequent runs.
    output_dir = os.path.join(os.path.dirname(__file__), "site")
    os.makedirs(output_dir, exist_ok=True)

    # Write CSS
    write_assets(output_dir)

    # Write index.html
    index_html = render_index(trending, config)
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    # Write individual name pages
    names_dir = os.path.join(output_dir, "names")
    os.makedirs(names_dir, exist_ok=True)
    for name, sex, current_rank, prev_rank, improvement in trending:
        year_ranks = ranks[sex][name]
        page_html = render_name_page(name, sex, year_ranks, config)
        filename = f"{name}-{sex}.html"
        with open(os.path.join(names_dir, filename), "w", encoding="utf-8") as f:
            f.write(page_html)


if __name__ == "__main__":
    build_site()