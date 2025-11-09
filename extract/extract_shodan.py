import os
import pandas as pd
import subprocess
import json
import time
from settings import settings

def extract_shodan_features_from_api_response(data):
    """Extract selected features from a merged Shodan API response dict."""
    def get_nested(d, *keys):
        # Returns None if the final resolved value is an empty dict.
        for key in keys:
            d = d.get(key, {})
        return d if d else None

    features = {
        "product": data.get("product", []),
        "version": data.get("version", []),
        "cpe": data.get("cpe", []),
        "cpe23": data.get("cpe23", []),
        "components": list(get_nested(data, "http", "components").keys()) if get_nested(data, "http", "components") else [],
        "ssh_key": get_nested(data, "ssh", "key"),
        "ssh_kex": get_nested(data, "ssh", "kex", "kex_algorithms"),
        "ssh_mac": get_nested(data, "ssh", "kex", "mac_algorithms"),
        "ssh_cipher": get_nested(data, "ssh", "cipher"),
        "ssl_ja3s": get_nested(data, "ssl", "ja3s"),
        "ssl_jarm": get_nested(data, "ssl", "jarm"),
        "ssl_fingerprint": get_nested(data, "ssl", "cert", "fingerprint", "sha256"),
        "hostnames": data.get("hostnames"),
        "domains": data.get("domains"),
        "vulns": data.get("vulns"),
        "tags": data.get("tags"),
        "server": get_nested(data, "http", "server"),
        "asn": data.get("asn"),
        "org": data.get("org"),
        "isp": data.get("isp"),
        "country_code": data.get("country_code") or data.get("location", {}).get("country_code"),
        "region_code": data.get("region_code") or data.get("location", {}).get("region_code"),
        "ssl_issuer": get_nested(data, "ssl", "cert", "issuer"),
        "ssl_subject": get_nested(data, "ssl", "cert", "subject"),
    }

    for k, v in features.items():
        if isinstance(v, list):
            features[k] = ", ".join(map(str, v))
        elif isinstance(v, dict):
            features[k] = json.dumps(v)

    return features


def enrich_ips_with_shodan_data(csv_filepath: str, api_key: str):
    """
    Read 'ip_address' values from a CSV, query the Shodan API,
    and update the CSV with extracted features.
    Only rows with empty key fields (asn/product/vulns/ssl_fingerprint) are queried.

    Args:
        csv_filepath (str): Path to the CSV file to update with Shodan data.
        api_key (str): Shodan API key.
    """
    if not api_key:
        print("Error: Shodan API key is not provided.")
        return False

    if not os.path.exists(csv_filepath):
        print(f"Error: CSV file not found - {csv_filepath}")
        return False

    try:
        df = pd.read_csv(csv_filepath)
    except Exception as e:
        print(f"Error: Failed to load CSV '{csv_filepath}': {e}")
        return False

    if 'ip_address' not in df.columns:
        print("Error: Column 'ip_address' not found in CSV.")
        return False

    shodan_feature_columns = [
        "product", "version", "cpe", "cpe23", "components", "ssh_key",
        "ssh_kex", "ssh_mac", "ssh_cipher", "ssl_ja3s", "ssl_jarm",
        "ssl_fingerprint", "hostnames", "domains", "vulns", "tags",
        "server", "asn", "org", "isp", "country_code", "region_code",
        "ssl_issuer", "ssl_subject"
    ]

    made_changes = False
    for col in shodan_feature_columns:
        if col not in df.columns:
            df[col] = pd.NA
            made_changes = True

    print(f"Starting Shodan enrichment for file: '{csv_filepath}'")
    enriched_count = 0
    processed_ips_in_batch = 0

    for index, row in df.iterrows():
        shodan_ip = row['ip_address']

        if pd.isna(shodan_ip) or shodan_ip == "NO_IP_FOUND":
            continue

        shodan_check_columns = ["asn", "product", "vulns", "ssl_fingerprint"]
        is_all_empty = all(
            pd.isna(row.get(col)) or str(row.get(col)).strip() == "" or str(row.get(col)).lower() == 'nan'
            for col in shodan_check_columns
        )
        if not is_all_empty:
            continue

        try:
            shodan_ip_str = str(shodan_ip)
            cmd = f'curl -s "https://api.shodan.io/shodan/host/{shodan_ip_str}?key={api_key}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                print(f"Error running curl for {shodan_ip_str}: {result.stderr}")
                time.sleep(1)
                continue

            if not result.stdout:
                print(f"No data returned from Shodan for {shodan_ip_str}.")
                time.sleep(1)
                continue

            api_response_data = json.loads(result.stdout)

            if api_response_data.get("error"):
                print(f"Shodan API error for {shodan_ip_str}: {api_response_data['error']}")
                if "request limit reached" in api_response_data['error'].lower():
                    print("Shodan API request limit reached. Stopping.")
                    if made_changes or enriched_count > 0:
                        try:
                            df.to_csv(csv_filepath, index=False)
                            print(f"Progress saved: {csv_filepath} ({enriched_count} IPs updated)")
                        except Exception as e_save:
                            print(f"Error saving CSV '{csv_filepath}': {e_save}")
                    return False
                time.sleep(5)
                continue

            # Merge all 'data' entries into one dict and overlay top-level fields.
            merged_data = {}
            for item in api_response_data.get("data", []):
                merged_data.update(item)
            merged_data.update({k: v for k, v in api_response_data.items() if k != "data"})

            features = extract_shodan_features_from_api_response(merged_data)

            for col_name, value in features.items():
                if col_name in df.columns:
                    df.loc[index, col_name] = value

            made_changes = True
            enriched_count += 1
            processed_ips_in_batch += 1
            print(f"{shodan_ip_str} processed. Total enriched so far: {enriched_count}")

            time.sleep(1.1)

        except json.JSONDecodeError:
            print(f"{shodan_ip_str} failed: Shodan response is not valid JSON. Response: {result.stdout[:200]}...")
            time.sleep(1)
        except subprocess.TimeoutExpired:
            print(f"{shodan_ip_str} failed: Shodan API request timed out.")
            time.sleep(1)
        except Exception as e:
            print(f"{shodan_ip_str} failed due to an unexpected error: {e}")
            time.sleep(1)

    if made_changes or processed_ips_in_batch > 0:
        try:
            df.to_csv(csv_filepath, index=False)
            print(f"Success: CSV updated - {csv_filepath}")
            print(f"Updated/added IPs in this run: {processed_ips_in_batch}")
        except Exception as e:
            print(f"Error saving CSV '{csv_filepath}': {e}")
            return False
    else:
        print("No changes detected. CSV not saved.")

    return True


if __name__ == '__main__':
    SHODAN_API_KEY = settings.SHODAN_API_KEY
    OUTPUT_DIR = settings.OUTPUT_DIR
    enrich_ips_with_shodan_data(OUTPUT_DIR, SHODAN_API_KEY)
