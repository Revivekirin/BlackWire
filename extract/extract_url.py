import os
import csv
import json
import re
import subprocess
from bs4 import BeautifulSoup
from pathlib import Path
from datetime import datetime
from settings import settings

today_str = datetime.now().strftime("%Y%m%d")

def extract_domain(raw_url):
    """Extracts the domain name from a URL."""
    url = re.sub(r"https?://", "", raw_url, flags=re.IGNORECASE)
    url = re.sub(r"^www\.", "", url, flags=re.IGNORECASE)
    return url.strip().split('/')[0].split(':')[0]

def get_ip_from_dig(domain):
    """Resolves an IP address using the `dig` command."""
    if not domain:
        return "INVALID_DOMAIN"
    try:
        dig_result = subprocess.check_output(
            ["dig", "+short", "A", domain],
            encoding='utf-8',
            timeout=5
        )
        for line in dig_result.strip().split("\n"):
            line = line.strip()
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", line):
                return line
        return "NO_IP_FOUND"
    except subprocess.CalledProcessError:
        return "DIG_ERROR_OR_NO_DOMAIN"
    except subprocess.TimeoutExpired:
        return "DIG_TIMEOUT"
    except Exception as e:
        print(f"Error during dig for {domain}: {e}")
        return "DIG_UNEXPECTED_ERROR"

def process_html_files_and_extract_urls(base_dir_path_str: str, output_dir_path_str: str) -> bool:
    """
    Extracts URLs from HTML files, resolves their IP addresses, and saves them to a CSV file.

    Args:
        base_dir_path_str (str): Base directory containing HTML files.
        output_dir_path_str (str): Directory to save the resulting CSV file.

    Returns:
        bool: True if successful, False otherwise.
    """
    html_dir = Path(base_dir_path_str)
    output_dir = Path(output_dir_path_str)
    today_str = datetime.now().strftime("%Y%m%d")
    output_csv_path = output_dir / f"{today_str}.csv"
    all_entries = []

    print(f"Starting HTML scan in: {html_dir}")

    if not html_dir.exists() or not html_dir.is_dir():
        print(f"Error: HTML directory '{html_dir}' not found or not a directory.")
        return False

    html_files_found = list(html_dir.rglob("*.html"))
    if not html_files_found:
        print(f"No HTML files found in '{html_dir}' or subdirectories.")
    else:
        print(f"Found {len(html_files_found)} HTML files.")

    for html_file in html_files_found:
        group_name = html_file.parent.name
        if html_file.parent == html_dir:
            group_name = "unknown_group_at_root"
            print(f"Notice: File '{html_file.name}' is in the root directory. Group name set to '{group_name}'.")

        print(f"\n--- Processing file: {html_file} (group: {group_name}) ---")
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                content = f.read()
                if len(content) < 50:
                    print(f"File content too short, skipping: {html_file}")
                    continue
                soup = BeautifulSoup(content, "html.parser")
        except FileNotFoundError:
            print(f"File not found (possibly deleted): {html_file}")
            continue
        except Exception as e:
            print(f"Error reading or parsing file ({html_file}): {e}")
            continue

        text_content = soup.get_text(separator=" ")
        url_pattern = re.compile(
            r'\b(?:https?://|s?ftps?://)?'
            r'(?:www\.)?'
            r'([a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'
            r'([a-zA-Z]{2,24})'
            r'(?:[/?#]\S*)?\b',
            re.IGNORECASE
        )
        
        extracted_urls_in_file = set()

        for match in url_pattern.finditer(text_content):
            raw_url = match.group(0).strip()

            if "." not in raw_url or len(raw_url) < 7 or raw_url.count('.') < 1:
                continue
            if ".onion" in raw_url:
                continue

            domain = extract_domain(raw_url)
            if not domain:
                continue

            if raw_url in extracted_urls_in_file:
                continue
            extracted_urls_in_file.add(raw_url)

            ip = get_ip_from_dig(domain)
            print(f"[+] URL: {raw_url} (Domain: {domain}) → IP: {ip}")
            all_entries.append((str(html_file.name), group_name, raw_url, domain, ip))

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Error: Failed to create output directory '{output_dir}': {e}")
        return False

    try:
        with open(output_csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["html_file", "group", "url", "domain", "ip_address"])
            writer.writerows(all_entries)
        print(f"\nCompleted. {len(all_entries)} URL entries saved to {output_csv_path}")
        return True
    except IOError as e:
        print(f"Error writing CSV file '{output_csv_path}': {e}")
        return False
    except Exception as e:
        print(f"Unexpected error saving CSV file '{output_csv_path}': {e}")
        return False

if __name__ == "__main__":
    BASE_NEWS_DIR = settings.BASE_NEWS_DIR
    OUTPUT_DIR = settings.OUTPUT_DIR
    process_html_files_and_extract_urls(BASE_NEWS_DIR, OUTPUT_DIR)
