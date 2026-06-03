
# The following modules will be needed
import os
import re
import pandas as pd

# 1. Set up paths to raw data and ground truth
data_root = "../raw_data"
ground_truth_path = "../assets/ground_truth.csv"

assert os.path.isdir(data_root)
assert os.path.isfile(ground_truth_path)


# 2. The Ground Truth will be used to compare the results with. The Ground Truth file also tells which entries were examples deemed context-dependent, i.e. the pronoun in question could not have been disambiguated without researching the context in some capacity.

gt = pd.read_csv(ground_truth_path, header=0, dtype=str)
gt = gt.fillna("")  # normalize strings
gt = gt.iloc[10:].reset_index(drop=True)    # drop the first 10 rows

# set of all IDs where 'context_dependent' is "X"
context_dependent_ids = set(gt.loc[gt["context_dependent"] == "X", "ID"].astype(str).str.strip())

# 3. Necessary functions for the processing.

def process_sheets(filepath, criteria=True, pilot=False):    
    # --- get prolificID from filename ---
    base = os.path.basename(filepath)
    if not base.lower().endswith(".csv"):
        raise ValueError("Expected a .csv file.")
    stem = os.path.splitext(base)[0]
    if "_" not in stem:
        raise ValueError("Filename does not contain an underscore-separated prolificID.")
    prolificID = stem.split("_")[-1] if not pilot else "pilot"+stem.split("_")[1]
    
    df = pd.read_csv(filepath, header=0, dtype=str)
    
    # normalize strings
    df = df.fillna("")
        
    # drop the first 10 rows
    df = df.iloc[10:].reset_index(drop=True)
    # ensure at least 46 rows remain, otherwise raise error
    if len(df) < 46:
        raise ValueError(f"Not enough rows after dropping first 10: found {len(df)}, need at least 46.")
    
    # build output dict
    out = {}
    out["prolificID"] = prolificID
    out["EnglishLingFamiliar"] = ""
    out["GenderEnglishAge"] = "Yes" if criteria else "No"
    
    for _, row in df.iterrows():
        rid = (row["ID"] or "").strip()
        if not rid:
            # skip rows without an ID
            continue
        out[rid] = (row["they_type"] or "")
        out[rid + "[comment]"] = (row["comment"] or "")
    
    return out


def process_lime(filepath, linguists=True):
    df = pd.read_csv(filepath, dtype=str)
    
    # drop unwanted columns
    drop_cols = [
        "startlanguage", "id", "seed", "startdate", "lastpage", "G01Q04", "G00Q02", "G00Q01", "G01Q03",
        "G01Q05", "G01Q06", "G01Q07", "G01Q08", "G01Q09", "G01Q10", "G01Q11",
        "G01Q12", "G04Q63", "G02Q62", "datestamp"
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    
    # turn comment ids back to original form
    df = df.rename(
        columns=lambda c: c.replace("maera", "ma_era_").replace("LoRes", "LoRes_")
    )
    
    # drop rows with empty submitdate
    df = df[df["submitdate"].notna() & (df["submitdate"].str.strip() != "")]
    df = df.drop("submitdate", axis=1)
    
    # check required columns are present
    required = ["prolificID", "EnglishLingFamiliar"] if linguists else ["prolificID"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
        if df[col].isna().any() or (df[col].str.strip() == "").any():
            raise ValueError(f"Column {col} has missing values")
    
    # convert rows to list of dicts (values remain strings)
    return df.to_dict(orient="records")


def check_block_consistency(block: list, block_name):
    first_keys = set(block[0].keys())
    for idx, rec in enumerate(block[1:], start=1):
        keys = set(rec.keys())
        if keys != first_keys:
            extra = sorted(list(keys - first_keys))
            missing = sorted(list(first_keys - keys))
            print(rec)
            raise ValueError(f"Inconsistent keys in block {block_name} at index {idx}: extra={extra}, missing={missing}")
    return True


# 4. Load all human participant data as Python dictionaries.


block_a_sheet_path = data_root + '/Humans/linguists_prolific/sheet_version/Block A/block_A_11_5f6ce7a067864711ebb0f66e.csv'
block_a_lime_initial_path = data_root + '/Humans/linguists_prolific/limesurvey/limesurvey_blockA.csv'
block_a_lime_topup_path = data_root + '/Humans/linguists_prolific/limesurvey/limesurvey_blockA_topup.csv'

block_a_sheet = process_sheets(block_a_sheet_path)
block_a_initial_lime = process_lime(block_a_lime_initial_path)
block_a_topup_lime = process_lime(block_a_lime_topup_path)

block_a = block_a_initial_lime + block_a_topup_lime + [block_a_sheet]
assert check_block_consistency(block_a, "A") is True

block_b_lime_path = data_root + '/Humans/linguists_prolific/limesurvey/limesurvey_blockB.csv'
block_b_sheet_path = data_root + '/Humans/linguists_prolific/sheet_version/Block B/Block_B_13_655788501826eeea1b788f8b.csv'

block_b_lime = process_lime(block_b_lime_path)
block_b_sheet = process_sheets(block_b_sheet_path)

block_b = [block_b_sheet] + block_b_lime
assert check_block_consistency(block_b, "B") is True

block_c_lime_path = data_root + '/Humans/linguists_prolific/limesurvey/limesurvey_blockC.csv'
block_c = process_lime(block_c_lime_path)
assert check_block_consistency(block_c, "C") is True

block_d_lime_path = data_root + '/Humans/linguists_prolific/limesurvey/limesurvey_blockD.csv'
block_d = process_lime(block_d_lime_path)
assert check_block_consistency(block_d, "D") is True

block_pilot = []
pilot_sheets_path = data_root + "/Humans/pilot"
pilot_sheets = [os.path.join(pilot_sheets_path, file) for file in os.listdir(pilot_sheets_path) if file.endswith(".csv")]
for file in pilot_sheets:
    block_pilot.append(process_sheets(file, criteria=False, pilot=True))

# 4b. Load all non-linguist participant data as Python dictionaries.
non_ling_path = data_root + '/Humans/non-linguists_control'
non_ling_files = [os.path.join(non_ling_path, file) for file in os.listdir(non_ling_path) if file.endswith(".csv")]
non_ling_participants = []
for file in non_ling_files:
    non_ling_participants.append(process_lime(file, linguists=False))
# flatten list
non_ling_participants = [item for sublist in non_ling_participants for item in sublist]

# 5. Load all LLM data as Python dictionaries.

def collect_responses_for_llm_class(path) -> dict:
    runs = [elem for elem in os.listdir(path) if elem.endswith(".csv") and "running" not in elem.lower()]
    # there is a CSV for each run from each LLM (usually 3, sometimes just 2 or fewer)
    # every filename begins with "results_" and ends with "_runN" where N is the iteration
    # everything in between is the combination of prompting technique and LLM which can be taken together as one "participant"
    # establish list of all participants first:
    participants = sorted(set(
        filename.replace("results_", "").rsplit("_run", 1)[0] 
        for filename in runs
    ))
    participants_dict = {participant: [] for participant in participants}

    pat = re.compile(r"^results_(.+)_run\d+\.csv$", flags=re.IGNORECASE)
    for fname in runs:
        m = pat.match(fname)
        if not m:
            continue  # skip non-matching files
        name = m.group(1)  # keep the [name] part
        fpath = os.path.join(path, fname)
        
        # open each file, top row as headers
        df = pd.read_csv(fpath, header=0, dtype=str).fillna("")
        
        # sanity check for required columns
        for col in ("ID", "LLM_response", "LLM_annotation"):
            if col not in df.columns:
                raise ValueError(f"File {fname} missing required column '{col}'")
        
        # build participant dict: ID -> LLM_annotation
        participant_responses = {}
        for _, r in df.iterrows():
            rid = r["ID"]
            if rid == "":
                continue
            participant_responses[rid] = r["LLM_annotation"]
            participant_responses[f"{rid}[comment]"] = r["LLM_response"]
        
        participants_dict[name].append(participant_responses)
    
    return participants_dict


# Loading LLM data as dictionaries

commercial_path = os.path.join(data_root, "LLMS/commercial")
assert os.path.isdir(commercial_path)

opensource_path = os.path.join(data_root, "LLMS/opensource")
assert os.path.isdir(opensource_path)

local_path = os.path.join(data_root, "LLMS/local")
assert os.path.isdir(local_path)

commercial_llm_responses = collect_responses_for_llm_class(commercial_path)

opensource_llm_responses = collect_responses_for_llm_class(opensource_path)

local_llm_responses = collect_responses_for_llm_class(local_path)