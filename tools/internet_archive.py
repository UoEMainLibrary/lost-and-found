#!/usr/bin/env python
"""
Internet Archive Extractor :: Lost and Found
"""

import argparse
import csv
import time
from pathlib import Path
from urllib.parse import urlparse

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

# ------------------- Internet Archive CDX API -------------------

def get_pages(domain):
  endpoint = "https://web.archive.org/cdx/search/cdx"

  params = {
    "url": f"{domain}/",
    "matchType": "domain",
    "showNumPages": "true",
    "pageSize": 50,
  }

  response = requests.get(
    endpoint,
    params=params,
    headers=HEADERS,
    timeout=180,
  )

  response.raise_for_status()

  try:
    return int(response.text.strip())

  except ValueError:
    return 1


def load_internet_archive(domain):
  endpoint = "https://web.archive.org/cdx/search/cdx"
  urls = set()

  pages = get_pages(domain)

  UI.log("ok", f"Found {pages:,} pages")
  UI.log("info", "Extracting...")

  for page in range(pages):

    params = {
      "url": f"{domain}/",
      "matchType": "domain",
      "output": "txt",
      "fl": "original",
      "page": page,
      "pageSize": 50,
    }

    for attempt in range(1, 6):
      try:
        print(f"    {'└─' if page == pages - 1 else '├─'} "f"Page {page + 1}/{pages} "f"(Attempt: {attempt}/5)")

        response = requests.get(
          endpoint,
          params=params,
          headers=HEADERS,
          timeout=180,
        )

        response.raise_for_status()

        urls.update(
          line.strip()
          for line in response.text.splitlines()
          if line.strip()
        )

        break

      except requests.RequestException as error:
        UI.log("issue", str(error))
        time.sleep(attempt * 5)

  return sorted(urls)

# ------------------- URL Filtering -------------------

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

  outdir = Path("output") / domain / "internet_archive"

  outdir.mkdir(
    parents=True,
    exist_ok=True
  )

  urls_file = outdir / "urls.csv"
  hosts_file = outdir / "hosts.csv"

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
    description="Extract hosts and URLs from the Internet Archive's Wayback CDX Server API"
  )

  parser.add_argument(
    "domain",
    help="Target domain to search, for example ed.ac.uk",
  )

  args = parser.parse_args()
  domain = normalise_domain(args.domain)

  UI.line()
  print("INTERNET ARCHIVE EXTRACTOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Target: {domain}")
  print(f"    ├─ Source: Wayback CDX Server API")
  print("    └─ Initialising...")
  UI.line()

  urls = load_internet_archive(domain)

  UI.log("ok", f"Downloaded URLs: {len(urls):,}")
  UI.log("info", "Extracting...")
  UI.line()

  urls = filter_urls(urls, domain)
  urls_file, hosts_file, url_count, host_count = write_results(domain, urls)

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