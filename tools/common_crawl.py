#!/usr/bin/env python
"""
Common Crawl Extractor :: Lost and Found
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
  return domain.lower().replace("http://", "").replace("https://", "").strip("/")


def get_host(url):
  try:
    return (urlparse(url).hostname or "").lower()
  except Exception:
    return ""

# ------------------- Common Crawl CDX URL Index -------------------

def load_indexes(latest=False):
  r = requests.get(
    "https://index.commoncrawl.org/collinfo.json",
    headers=HEADERS,
    timeout=30,
  )
  r.raise_for_status()

  indexes = [
    i["cdx-api"]
    for i in r.json()
    if i.get("id", "").startswith("CC-MAIN") and i.get("cdx-api")
  ]

  return indexes[:1] if latest else indexes

# ------------------- CSV Storage -------------------

def load_existing(path):
  if not path.exists():
    return set()

  with path.open(newline="", encoding="utf-8") as f:
    reader = csv.reader(f)
    next(reader, None)
    return {row[0] for row in reader if row}

# ------------------- Extraction Engine -------------------

def crawl(endpoint, domain, seen_hosts, seen_urls, hosts_writer, urls_writer):
  params = {
    "url": f"*.{domain}/*",
    "output": "json",
    "pageSize": 2000,
  }

  try:
    r = requests.get(
      endpoint,
      headers=HEADERS,
      params=params,
      stream=True,
      timeout=180,
    )

    if r.status_code != 200:
      UI.log("error", f"HTTP {r.status_code}")
      return

    for line in r.iter_lines():
      if not line:
        continue

      try:
        data = json.loads(line)
        url = data.get("url")

        if not url:
          continue

        host = get_host(url)

        if not host.endswith(domain):
          continue

        if url not in seen_urls:
          seen_urls.add(url)
          urls_writer.writerow([url])

        if host not in seen_hosts:
          seen_hosts.add(host)
          hosts_writer.writerow([host])

      except Exception:
        continue

  except requests.RequestException as e:
    UI.log("error", str(e))

def main():
  parser = argparse.ArgumentParser(
    description="Extract hosts and URLs from Common Crawl CDX URL Index"
  )

  parser.add_argument(
    "domain",
    help="Target to search, for example ed.ac.uk",
  )

  parser.add_argument(
    "--latest",
    action="store_true",
    help="Only use the latest Common Crawl CDX URL Index",
  )

  args = parser.parse_args()
  domain = normalise_domain(args.domain)

  outdir = Path("output") / domain / "common_crawl"
  outdir.mkdir(parents=True, exist_ok=True)

  hosts_file = outdir / "hosts.csv"
  urls_file = outdir / "urls.csv"

  UI.line()
  print("COMMON CRAWL EXTRACTOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Target: {domain}")
  print(f"    ├─ Mode:   {'Latest index' if args.latest else 'All indexes'}")
  print("    └─ Initialising...")
  UI.line()

  indexes = load_indexes(args.latest)

  UI.log("ok", f"Loaded indexes: {len(indexes):,}")
  UI.log("info", "Extracting...")
  UI.line()

  seen_hosts = load_existing(hosts_file)
  seen_urls = load_existing(urls_file)

  with (
    hosts_file.open("a", newline="", encoding="utf-8") as hh,
    urls_file.open("a", newline="", encoding="utf-8") as uh,
  ):
    hw = csv.writer(hh)
    uw = csv.writer(uh)

    if not seen_hosts:
      hw.writerow(["host"])

    if not seen_urls:
      uw.writerow(["url"])

    for i, endpoint in enumerate(indexes, 1):
      print(f"    Searching index: {i}/{len(indexes)}...")
      print(f"    ├─ Endpoint: {endpoint}")

      crawl(endpoint, domain, seen_hosts, seen_urls, hw, uw)

      UI.log("ok",f"└─ Extracted: Hosts: {len(seen_hosts):,} :: URLs: {len(seen_urls):,}",)
      UI.line()

  UI.log("ok", "Extraction complete")
  UI.log("info", "Results")
  print(f"    ├─ Hosts: {len(seen_hosts):,}")
  print(f"    └─ URLs:  {len(seen_urls):,}")
  UI.line()
  UI.log("info", "Output")
  print(f"    ├─ {hosts_file}")
  print(f"    └─ {urls_file}")
  UI.line()

# ------------------- Entry Point -------------------

if __name__ == "__main__":
  main()