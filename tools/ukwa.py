#!/usr/bin/env python
"""
UKWA Extractor :: Lost and Found
The University of Edinburgh, Heritage Collections
"""

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse

import requests

# ------------------- User Agent -------------------

HEADERS = {
  "User-Agent": "Lost and Found :: The University of Edinburgh, Heritage Collections"
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

# ------------------- URL Normaliser -------------------

def normalise_domain(domain):
  return (
    domain.lower()
    .replace("http://", "")
    .replace("https://", "")
    .strip("/")
  )


def get_host(url):
  try:
    return (urlparse(url).hostname or "").lower()
  except Exception:
    return ""

# ------------------- UKWA Seed Lists Loader -------------------

def load_source(source):
  if source.startswith(("http://", "https://")):
    response = requests.get(
      source,
      headers=HEADERS,
      timeout=180,
    )

    response.raise_for_status()

    return response.text

  path = Path(source)

  if not path.exists():
    raise FileNotFoundError(path)

  with path.open(
    encoding="utf-8"
  ) as file:
    return file.read()

# ------------------- Extraction Engine -------------------

def extract_urls(data):
  urls = set()

  try:
    records = json.loads(data)

    for record in records:
      url = record.get(
        "Primary Seed",
        ""
      )

      if url:
        urls.add(url)

  except json.JSONDecodeError:
    reader = csv.DictReader(
      data.splitlines()
    )

    for row in reader:
      url = row.get(
        "Primary Seed",
        ""
      )

      if url:
        urls.add(url)

  return sorted(urls)

# ------------------- Target Filter -------------------

def filter_urls(urls, domain):
  results = set()

  for url in urls:
    host = get_host(url)

    if not host:
      continue

    if host == domain or host.endswith("." + domain):
      results.add(url)

  return sorted(results)

# ------------------- CSV Storage -------------------

def write_results(domain, urls):
  output_dir = Path("output") / domain / "ukwa"

  output_dir.mkdir(
    parents=True,
    exist_ok=True
  )

  urls_file = output_dir / "urls.csv"
  hosts_file = output_dir / "hosts.csv"

  hosts = sorted({
    get_host(url)
    for url in urls
    if get_host(url)
  })

  with urls_file.open(
    "w",
    newline="",
    encoding="utf-8",
  ) as file:
    writer = csv.writer(file)

    writer.writerow(["url"])

    for url in urls:
      writer.writerow([url])

  with hosts_file.open(
    "w",
    newline="",
    encoding="utf-8",
  ) as file:
    writer = csv.writer(file)

    writer.writerow(["host"])

    for host in hosts:
      writer.writerow([host])

  return (
    urls_file,
    hosts_file,
    len(urls),
    len(hosts),
  )

# ------------------- Main CLI -------------------

def main():
  parser = argparse.ArgumentParser(
    description="Extract hosts and URLs from UKWA seed lists"
  )

  parser.add_argument(
    "source",
    help="UKWA seed list CSV/JSON file or URL",
  )

  parser.add_argument(
    "domain",
    help="Target to search, for example ed.ac.uk",
  )

  args = parser.parse_args()
  domain = normalise_domain(args.domain)

  UI.line()
  print("UKWA EXTRACTOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Target: {domain}")
  print(f"    ├─ Source: {args.source}")
  print("    └─ Initialisng...")

  try:
    data = load_source(args.source)

  except Exception as error:
    UI.log("error")
    return

  UI.log("ok", "UKWA seed list loaded")
  UI.log("info", "Extracting...")

  urls = extract_urls(data)

  UI.log("ok", f"Extracted {len(urls):,} URLs")
  UI.log("info", "Filtering results...")

  urls = filter_urls(urls, domain)
  urls_file, hosts_file, url_count, host_count = write_results(domain, urls)

  UI.line()
  UI.log("ok", "Extraction complete")
  UI.log("info", "Results")
  print(f"    ├─ URLs:  {url_count:,}")
  print(f"    └─ Hosts: {host_count:,}")
  UI.line()
  UI.log("info", "Output")
  print(f"    ├─ {urls_file}")
  print(f"    └─ {hosts_file}")
  UI.line()

# ------------------- Entry Point -------------------

if __name__ == "__main__":
  main()