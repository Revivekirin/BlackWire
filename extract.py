import os
from pathlib import Path
import pandas as pd
import ast

from extract.merge_csv import merge_and_update_shodan_csv
from extract.extract_url import process_html_files_and_extract_urls
from extract.extract_shodan import enrich_ips_with_shodan_data
from extract.extract_cvedb import update_cvedb_from_shodan, match_cves_to_mitre
from extract.extract_geolocation import add_coordinates_to_shodan_data
from settings import settings

BASE_DOWNLOAD_DIR = settings.BASE_DOWNLOAD_DIR
TOR_PROXY_ADDRESS = settings.TOR_PROXY_ADDRESS
ONION_JSON_PATH = settings.ONION_LIST_PATH
SHODAN_API_KEY = settings.SHODAN_API_KEY
MITRE_XLSX_PATH = settings.MITRE_XLSX_PATH
CVEDB_PATH = settings.CVEDB_PATH
BASE_NEWS_DIR = settings.BASE_NEWS_DIR
OUTPUT_DIR = settings.OUTPUT_DIR


def run():
    if not BASE_NEWS_DIR:
        print("ERROR: Please set os.getenv('BASE_NEWS_DIR')")
        return
    if not OUTPUT_DIR:
        print("ERROR: Please set os.getenv('OUTPUT_DIR')")
        return
    if not SHODAN_API_KEY:
        print("ERROR: Please set os.getenv('SHODAN_API_KEY')")
        return

    output_dir_path = Path(OUTPUT_DIR)
    try:
        output_dir_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"ERROR: Failed to create '{output_dir_path}': {e}")
        return

    print("\n--- Step 1: Extract URLs ---")
    process_html_files_and_extract_urls(BASE_NEWS_DIR, OUTPUT_DIR)

    print("\n--- Step 2: Merge CSV Files ---")
    merge_and_update_shodan_csv(OUTPUT_DIR)

    print("\n--- Step 3: Enrich with Shodan Data ---")
    shodan_data_csv_file = output_dir_path / "shodan_data.csv"

    if shodan_data_csv_file.exists():
        enrich_success = enrich_ips_with_shodan_data(str(shodan_data_csv_file), SHODAN_API_KEY)
        if enrich_success:
            print("Shodan enrichment completed successfully.")
        else:
            print("Shodan enrichment encountered issues or no updates were needed.")
    else:
        print(f"ERROR: Could not find '{shodan_data_csv_file}' for Shodan enrichment.")
        print("Please ensure the CSV merge step completed successfully.")

    print("\n--- Step 4: Generate Combined CVE List ---")
    if shodan_data_csv_file.exists():
        try:
            df = pd.read_csv(shodan_data_csv_file)

            def combine_vulns(row):
                vulns_str = row.get('vulns', '')
                shodan_vulns_str = row.get('shodan_vulns', '')

                vulns = []
                if pd.notna(vulns_str) and isinstance(vulns_str, str):
                    vulns = [v.strip() for v in vulns_str.split(',') if v.strip().startswith("CVE-")]

                shodan_vulns = []
                if pd.notna(shodan_vulns_str) and isinstance(shodan_vulns_str, str):
                    try:
                        parsed = ast.literal_eval(shodan_vulns_str)
                        if isinstance(parsed, list):
                            shodan_vulns = [v.strip() for v in parsed if isinstance(v, str) and v.startswith("CVE-")]
                    except Exception as e:
                        print(f"[Warning] Failed to parse shodan_vulns: {e} -> {shodan_vulns_str}")

                return list(set(vulns + shodan_vulns))

            df['cve_list'] = df.apply(combine_vulns, axis=1)
            df.to_csv(shodan_data_csv_file, index=False)
            print(f"File with 'cve_list' column saved: {shodan_data_csv_file}")
        except Exception as e:
            print(f"[Error] Exception occurred while generating cve_list: {e}")
    else:
        print(f"[Error] '{shodan_data_csv_file}' does not exist; cannot generate cve_list.")

    print("\n--- Step 5: Update CVE Database with Shodan Info ---")
    update_cvedb_from_shodan(str(shodan_data_csv_file), CVEDB_PATH)

    print("\n--- Step 6: Map CVEs to MITRE TTPs ---")
    match_cves_to_mitre(CVEDB_PATH, MITRE_XLSX_PATH)

    print("\n--- Step 7: Add Geolocation Coordinates ---")
    if shodan_data_csv_file.exists():
        try:
            add_coordinates_to_shodan_data(str(shodan_data_csv_file), save=True, sleep_sec=1)
        except Exception as e:
            print(f"[Error] Exception occurred while adding coordinates: {e}")
    else:
        print(f"[Error] '{shodan_data_csv_file}' does not exist; cannot add coordinates.")

    print("\nAll tasks completed successfully.")

if __name__ == "__main__":
    run()
