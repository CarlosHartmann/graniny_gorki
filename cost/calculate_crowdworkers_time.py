import os
import pandas as pd
from datetime import timedelta


linguists_limesurvey_path = "../raw_data/Humans/linguists_prolific/limesurvey"
non_linguists_limesurvey_path = "../raw_data/Humans/non-linguists_control"

total_time = timedelta()

def calculate_time_duration(start_time_str, end_time_str):
    """Calculate the time duration between start and end times given as strings."""
    # the time strings are formatted like so: 2025-08-14 23:54:44	
    # pd.to_datetime can parse these strings directly
    start_time = pd.to_datetime(start_time_str)
    end_time = pd.to_datetime(end_time_str)
    return end_time - start_time

def process_limesurvey_file(file_path):
    """Process a LimeSurvey CSV file to calculate total time spent by respondents."""
    df = pd.read_csv(file_path)
    total_duration = timedelta()

    for index, row in df.iterrows():
        start_time = row['startdate']
        end_time = row['datestamp']
        duration = calculate_time_duration(start_time, end_time)
        total_duration += duration

    return total_duration

# Process linguists LimeSurvey directory
for path in [linguists_limesurvey_path, non_linguists_limesurvey_path]:
    for file_name in os.listdir(path):
        if file_name.endswith('.csv'):
            file_path = os.path.join(path, file_name)
            try:
                total_time += process_limesurvey_file(file_path)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

print(f"Total time spent by crowdworkers in h: {total_time.total_seconds() / 3600:.2f} h")