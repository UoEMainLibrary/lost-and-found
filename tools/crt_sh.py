#!/usr/bin/env python
"""
CRT.sh Extractor :: Lost and Found
"""

import argparse
import csv
import time
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

# ------------------- URL Normaliser -------------------

def normalise_domain(domain):
  return (
    domain.lower()
    .replace("http://", "")
    .replace("https://", "")
    .strip("/")
  )

# ------------------- CRT.sh API -------------------

def fetch_json(url, retries=5):
  for attempt in range(1, retries + 1):
    try:
      UI.log("info",f"Request attempt: {attempt}/{retries}")

      response = requests.get(
        url,
        headers=HEADERS,
        timeout=180,
      )

      response.raise_for_status()

      return response.json()

    except requests.RequestException as error:
      UI.log("issue", str(error))

      if attempt < retries:
        time.sleep(attempt * 3)

  raise RuntimeError(
    "Failed to fetch data from crt.sh"
  )

# ------------------- Host Extraction -------------------

def extract_hosts(records, domain):
  hosts = set()

  for record in records or []:
    names = record.get(
      "name_value",
      ""
    )

    for name in names.splitlines():
      name = name.strip().lower()

      if not name:
        continue

      if name.startswith("*."):
        name = name[2:]

      if name == domain or name.endswith("." + domain):
        hosts.add(name)

  return sorted(hosts)

# ------------------- CSV Storage -------------------

def load_existing(path):
  if not path.exists():
    return set()

  with path.open(
    newline="",
    encoding="utf-8",
  ) as file:
    reader = csv.reader(file)
    next(reader, None)

    return {
      row[0]
      for row in reader
      if row
    }

def save_results(path, hosts):
  existing = load_existing(path)

  with path.open(
    "a",
    newline="",
    encoding="utf-8",
  ) as file:
    writer = csv.writer(file)

    if not existing:
      writer.writerow(["host"])

    for host in hosts:
      if host not in existing:
        writer.writerow([host])

# ------------------- Main CLI -------------------

def main():
  parser = argparse.ArgumentParser(
    description="Extract hosts from CRT.sh certificate transparency logs"
  )

  parser.add_argument(
    "domain",
    help="Target to search, for example ed.ac.uk",
  )

  args = parser.parse_args()
  domain = normalise_domain(args.domain)

  outdir = Path("output") / domain / "crt_sh"

  outdir.mkdir(
    parents=True,
    exist_ok=True
  )

  hosts_file = outdir / "hosts.csv"

  url = (
    f"https://crt.sh/"
    f"?q=%.{domain}"
    f"&output=json"
  )

  UI.line()
  print("CRT.SH EXTRACTOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Target: {domain}")
  print(f"    ├─ Source: CRT.sh certificate transparency logs")
  print("    └─ Initialising...")
  UI.line()

  try:
    records = fetch_json(url)

  except Exception as error:
    UI.log("error", str(error))
    return

  UI.log("ok", "Certificate logs downloaded")
  UI.log("info", "Extracting...")
  UI.line()

  hosts = extract_hosts(records, domain)

  UI.log("ok", f"Extracted {len(hosts):,} hosts")

  save_results(hosts_file, hosts)

  UI.line()
  UI.log("ok", "Extraction complete")
  UI.log("info", "Results")
  print(f"    └─ Hosts: {len(hosts):,}")
  UI.line()
  UI.log("info", "Output")
  print(f"    └─ {hosts_file}")
  UI.line()

# ------------------- Entry Point -------------------

if __name__ == "__main__":
  main()