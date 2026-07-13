#!/usr/bin/env python
"""
Activity Validator :: Lost and Found
"""

import argparse
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ------------------- User Agent -------------------

HEADERS = {
  "User-Agent": "Lost and Found :: The University of Edinburgh"
}

# ------------------- Terminal UI -------------------

class UI:
  SYMBOLS = {
    "info":  "[▪]",
    "ok":    "[✓]",
    "error": "[✕]",
    "issue": "[-]"
  }

  COLORS = {
    "cyan":   "\033[36m",
    "green":  "\033[32m",
    "red":    "\033[31m",
    "yellow": "\033[33m",
    "reset":  "\033[0m",
  }

  @classmethod
  def paint(cls, text, colour):
    return f"{cls.COLORS[colour]}{text}{cls.COLORS['reset']}"

  @classmethod
  def log(cls, kind, message):
    mapping = {
      "info":  ("info", "cyan"),
      "ok":    ("ok", "green"),
      "error": ("error", "red"),
      "issue": ("issue", "yellow"),
    }

    sym, col = mapping[kind]
    print(f"{cls.paint(cls.SYMBOLS[sym], col)} {message}")

  @staticmethod
  def line():
    print()

# ------------------- Source Helpers -------------------

def get_source_name(path):
  return path.stem


def get_domain(path):
  if path.parent.parent.name:
    return path.parent.parent.name

  return "unknown"

# ------------------- URL Loader -------------------

def load_urls(path):
  urls = []

  with path.open(
    newline="",
    encoding="utf-8"
  ) as file:

    reader = csv.reader(file)

    for row in reader:
      if not row:
        continue

      url = row[0].strip()

      if url.lower() in (
        "url",
        "domain",
        "host"
      ):
        continue

      if not url.startswith("http"):
        url = "https://" + url

      urls.append(url)

  return urls

# ------------------- URL Validator -------------------

def check_url(url):
  try:
    response = requests.get(
      url,
      headers=HEADERS,
      timeout=180,
      allow_redirects=True
    )

    return (
      url,
      response.status_code
    )

  except requests.exceptions.SSLError:
    return (
      url,
      "ssl_error"
    )

  except requests.exceptions.Timeout:
    return (
      url,
      "timeout"
    )

  except requests.exceptions.ConnectionError:
    return (
      url,
      "connection_error"
    )

  except Exception:
    return (
      url,
      "error"
    )


def is_live(status):
  return (
    isinstance(status, int)
    and 200 <= status < 400
  )

# ------------------- CSV Storage -------------------

def write_results(domain, source, results):
  output_dir = (
    Path("output")
    / domain
    / "__live"
  )

  output_dir.mkdir(
    parents=True,
    exist_ok=True
  )

  output_file = (
    output_dir
    / f"{source}__live.csv"
  )

  with output_file.open(
    "w",
    newline="",
    encoding="utf-8"
  ) as file:

    writer = csv.writer(file)

    writer.writerow([
      "url",
      "status"
    ])

    for row in results:
      writer.writerow(row)

  return output_file, len(results)

# ------------------- Main CLI -------------------

def main():
  parser = argparse.ArgumentParser(
    description="Check whether discovered hosts and URLs are still active"
  )

  parser.add_argument(
    "source",
    help="CSV file containing URLs"
  )

  args = parser.parse_args()
  source_file = Path(args.source)
  source_name = get_source_name(source_file)
  domain = get_domain(source_file)

  UI.line()
  print("ACTIVITY VALIDATOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Source: {source_file}")
  print("    └─ Initialising...")
  UI.line()

  try:
    urls = load_urls(source_file)

  except Exception as error:
    UI.log("error", str(error))
    return

  UI.log("ok", f"Loaded URLs: {len(urls):,}")
  UI.log("info", "Validating...")

  live = []

  with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
      executor.submit(check_url, url)
      for url in urls
    ]

    for index, future in enumerate(
      as_completed(futures),
      1
    ):
      url, status = future.result()

      live.append(
        (url, status)
      ) if is_live(status) else None

      branch = "└─" if index == len(urls) else "├─"

      print(
        f"    {branch} {index}/{len(urls)}: {status} {url}"
      )

  output_file, count = write_results(
    domain,
    source_name,
    live
  )

  UI.line()
  UI.log("ok", "Validation complete")
  UI.log("info", "Results")
  print(f"    ├─ Checked: {len(urls):,}")
  print(f"    └─ Active:  {count:,}")
  UI.line()
  UI.log("info", "Output")
  print(f"    └─ {output_file}")
  UI.line()

# ------------------- Entry Point -------------------

if __name__ == "__main__":
  main()