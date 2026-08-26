#!/usr/bin/env python
"""
Registry Comparator :: Lost and Found
The University of Edinburgh, Heritage Collections
"""

import argparse
import csv
from pathlib import Path
from urllib.parse import urlparse

csv.field_size_limit(2**31 - 1) # Increase CSV field size limit

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

# ------------------- Domain Normaliser -------------------

def normalise_domain(domain):
  return (
    domain.lower()
    .replace("http://", "")
    .replace("https://", "")
    .strip("/")
  )

def extract_domain(value):
  value = value.strip()

  if "://" in value:
    parsed = urlparse(value)

    return (
      parsed.hostname
      or ""
    )

  return value.split(
    ":",
    1
  )[0]

# ------------------- Domain Loader -------------------

def load_domains(path):
  domains = set()

  if not path.exists():
    raise FileNotFoundError(path)

  with path.open(
    encoding="utf-8",
    errors="replace"
  ) as file:

    first_line = file.readline()
    file.seek(0)

    header = [
      column.strip().lower()
      for column in first_line.split(",")
    ]

    is_csv = any(
      column in {
        "url",
        "domain",
        "host"
      }
      for column in header
    )

    if is_csv:
      reader = csv.DictReader(file)

      for row in reader:
        value = (
          row.get("url")
          or row.get("domain")
          or row.get("host")
          or ""
        )

        if not value:
          continue

        domain = normalise_domain(
          extract_domain(value)
        )

        if domain:
          domains.add(domain)

    else:
      for line in file:
        line = line.strip()

        if (
          not line
          or line.startswith("#")
        ):
          continue

        domain = normalise_domain(
          extract_domain(line)
        )

        if domain:
          domains.add(domain)

  return domains

# ------------------- Output Helpers -------------------

def get_source_name(path):
  if path.parent.name:
    return path.parent.name

  return path.stem


def save_results(path, domains):
  with path.open(
    "w",
    newline="",
    encoding="utf-8",
  ) as file:

    writer = csv.writer(file)

    writer.writerow(["domain"])

    for domain in sorted(domains):
      writer.writerow([domain])

# ------------------- Main CLI -------------------

def main():
  parser = argparse.ArgumentParser(
    description="Compare two registries to identify new hosts and URLs"
  )

  parser.add_argument(
    "input",
    help="Input registry",
  )

  parser.add_argument(
    "comparison",
    help="Comparison registry",
  )

  args = parser.parse_args()
  input_file = Path(args.input)
  comparison_file = Path(args.comparison)

  try:
    domain = normalise_domain(
      comparison_file.parents[1].name
    )

  except IndexError:
    domain = normalise_domain(
      comparison_file.parent.name
      or comparison_file.stem
    )

  output_dir = (
    Path("output")
    / domain
    / "__comparisons"
  )

  output_dir.mkdir(
    parents=True,
    exist_ok=True
  )

  input_name = get_source_name(
    input_file
  )

  comparison_name = get_source_name(
    comparison_file
  )

  output_file = (
    output_dir
    / f"{input_name}__{comparison_name}.csv"
  )

  UI.line()
  print("REGISTRY COMPARATOR :: LOST AND FOUND")
  print("────────────────────────────────────────────────────────────")
  UI.log("info", "Query")
  print(f"    ├─ Target: {domain}")
  print(f"    ├─ Registries:")
  print(f"    │  ├─ Input:      {input_name}")
  print(f"    │  └─ Comparison: {comparison_name}")
  print("    └─ Initialising...")
  UI.line()

  try:
    UI.log("info", "Loading input registry...")

    input_domains = load_domains(input_file)

    UI.log("info", "Loading comparison registry...")

    comparison_domains = load_domains(comparison_file)

  except (
    FileNotFoundError,
    PermissionError,
    UnicodeError,
    csv.Error,
    OSError,
  ) as error:
    UI.log("error", str(error))
    return

  new_domains = (comparison_domains - input_domains)
  common_domains = (comparison_domains & input_domains)

  UI.log("ok", "Analysis complete")
  UI.log("info", "Results")
  print(f"    ├─ Common: {len(common_domains):,}")
  print(f"    └─ New:    {len(new_domains):,}")
  UI.line()

  save_results(output_file, new_domains)

  UI.log("info", "Output")
  print(f"    └─ {output_file}")
  UI.line()

# ------------------- Entry Point -------------------

if __name__ == "__main__":
  main()