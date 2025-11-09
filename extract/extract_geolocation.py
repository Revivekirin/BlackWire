import pandas as pd
from geopy.geocoders import Nominatim
import time

def add_coordinates_to_shodan_data(csv_path, save=True, sleep_sec=1):
    """
    Adds geographic coordinates (latitude, longitude) to Shodan data based on region and country codes.
    If coordinates already exist in the CSV, they are retained.

    Args:
        csv_path (str): Path to the CSV file to update.
        save (bool): Whether to overwrite the CSV file with the new data.
        sleep_sec (int): Delay between geocoding requests to avoid rate limiting.

    Returns:
        pd.DataFrame: Updated DataFrame with latitude and longitude columns.
    """
    df = pd.read_csv(csv_path)
    geolocator = Nominatim(user_agent="geoapi")

    def get_lat_lon(row):
        if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude")):
            return pd.Series([row["latitude"], row["longitude"]])
        try:
            location = geolocator.geocode(f"{row['region_code']}, {row['country_code']}", timeout=10)
            if location:
                print(f"Geocoding {row['group']}, {row['domain']} -> {location.latitude}, {location.longitude}")
                time.sleep(sleep_sec)
                return pd.Series([location.latitude, location.longitude])
        except Exception as e:
            print(f"Geocode error for {row['group']}, {row['domain']}: {e}")
        return pd.Series([None, None])

    df[['latitude', 'longitude']] = df.apply(get_lat_lon, axis=1)

    if save:
        df.to_csv(csv_path, index=False)
        print(f"File with added coordinates saved: {csv_path}")
    return df
