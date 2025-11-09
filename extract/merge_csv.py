import pandas as pd
import os
import glob

def merge_and_update_shodan_csv(directory_path):
    """
    Merges all CSV files in the specified directory into a base file (shodan_data.csv),
    adding only new rows that are not already in the base file.
    Missing columns in any file are filled with NaN.
    After merging, all source CSV files used in the process are deleted.

    In case of duplicates based on the 'url' column, the existing rows
    in the base file (shodan_data.csv) are preserved and new duplicates are removed.

    Args:
        directory_path (str): Path to the directory containing target CSV files.
    """
    print(f"Starting merge process for directory: {directory_path}")

    target_path = os.path.expanduser(directory_path)
    if not os.path.isdir(target_path):
        print(f"Error: Directory does not exist - {target_path}")
        return

    output_filename = "shodan_data.csv"
    output_filepath = os.path.join(target_path, output_filename)

    csv_files_to_merge = [
        f for f in glob.glob(os.path.join(target_path, "*.csv"))
        if os.path.abspath(f) != os.path.abspath(output_filepath)
    ]

    if not csv_files_to_merge and not os.path.exists(output_filepath):
        print(f"Info: No CSV files to merge and no base file ({output_filename}) found. Exiting.")
        return
    elif not csv_files_to_merge:
        print(f"Info: No new CSV files to merge. Only base file ({output_filename}) exists. Exiting.")
        return

    if os.path.exists(output_filepath):
        try:
            df_existing = pd.read_csv(output_filepath)
            print(f"Base file loaded: {output_filename} ({len(df_existing)} rows)")
        except Exception as e:
            print(f"Error: Failed to load base file ({output_filepath}) - {e}")
            df_existing = pd.DataFrame()
            print("Info: Proceeding with an empty base dataframe.")
    else:
        df_existing = pd.DataFrame()
        print(f"Info: No base file found. Creating a new one.")

    new_dfs = []
    all_columns = set(df_existing.columns)
    temp_new_dfs_data = []

    for f_path in csv_files_to_merge:
        try:
            df_temp = pd.read_csv(f_path)
            temp_new_dfs_data.append({'path': f_path, 'df': df_temp})
            all_columns.update(df_temp.columns)
            print(f"Scanned file: {os.path.basename(f_path)} ({len(df_temp)} rows, {len(df_temp.columns)} columns)")
        except Exception as e:
            print(f"Warning: Error while scanning file for columns - {os.path.basename(f_path)}: {e}")

    final_columns = list(df_existing.columns) + [col for col in all_columns if col not in df_existing.columns]

    for item in temp_new_dfs_data:
        f_path = item['path']
        df_new = item['df']
        try:
            df_new = df_new.reindex(columns=final_columns, fill_value=pd.NA)
            new_dfs.append(df_new)
            print(f"File loaded and aligned: {os.path.basename(f_path)} ({len(df_new)} rows)")
        except Exception as e:
            print(f"Error while loading or aligning file - {os.path.basename(f_path)}: {e}")

    if not new_dfs:
        print("Warning: No valid dataframes found for merging.")
        return

    if new_dfs:
        df_new_all = pd.concat(new_dfs, ignore_index=True)
    else:
        df_new_all = pd.DataFrame(columns=final_columns if final_columns else None)

    if df_existing.empty:
        df_merged = df_new_all
        if not df_merged.empty:
            if 'url' in df_merged.columns:
                df_merged.drop_duplicates(subset=['url'], keep='first', inplace=True)
            else:
                print("Warning: 'url' column not found, skipping duplicate removal.")
        print(f"Info: Created new data file ({len(df_merged)} rows).")
    else:
        df_existing = df_existing.reindex(columns=final_columns, fill_value=pd.NA)
        df_new_all = df_new_all.reindex(columns=final_columns, fill_value=pd.NA)

        df_combined = pd.concat([df_existing, df_new_all], ignore_index=True)

        if 'url' in df_combined.columns:
            df_merged = df_combined.drop_duplicates(subset=['url'], keep='first')
            print("Duplicate removal complete (preserving existing entries).")
        else:
            df_merged = df_combined
            print("Warning: 'url' column not found, skipping duplicate removal.")

        df_existing_dedup_count = len(df_existing.drop_duplicates(subset=['url'], keep='first')) if 'url' in df_existing.columns else len(df_existing)
        added_rows = len(df_merged) - df_existing_dedup_count
        print(f"Estimated new rows added: {max(0, added_rows)}")

    if not df_merged.empty:
        try:
            df_merged.to_csv(output_filepath, index=False, encoding="utf-8-sig")
            print(f"Final merged file saved: {output_filename} ({len(df_merged)} rows)")
        except Exception as e:
            print(f"Error saving final file ({output_filepath}): {e}")
            return
    else:
        print(f"Info: No data to save in {output_filename}.")

    deleted_count = 0
    failed_to_delete = []
    if new_dfs:
        print("Deleting merged source CSV files...")
        for f_path in csv_files_to_merge:
            try:
                os.remove(f_path)
                print(f"Deleted: {os.path.basename(f_path)}")
                deleted_count += 1
            except Exception as e:
                print(f"Failed to delete: {os.path.basename(f_path)} - {e}")
                failed_to_delete.append(os.path.basename(f_path))

        if failed_to_delete:
            print(f"Warning: Some files were not deleted - {', '.join(failed_to_delete)}")
        print(f"Total {deleted_count} source files deleted.")
    else:
        print("Info: No source files to delete.")

    print(f"Process completed for directory: {directory_path}")
