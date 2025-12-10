import os
import pandas as pd
import numpy as np


def _norm_type(x):
    """Normalize label variants to canonical: generic_they / singular_they / plural_they."""
    if x is None:
        return ""
    s = str(x).strip().lower()
    if s in {"", "nan", "none"}:
        return ""
    # unify separators
    s = s.replace("-", "_").replace(" ", "_")

    mapping = {
        # singular variants
        "sing": "singular_they", "sing.": "singular_they", "s": "singular_they",
        "sg": "singular_they", "singular": "singular_they", "singular_they": "singular_they",
        "they_singular": "singular_they",
        # plural variants
        "pl": "plural_they", "pl.": "plural_they", "p": "plural_they",
        "plural": "plural_they", "plural_they": "plural_they", "they_plural": "plural_they",
        # generic variants
        "gen": "generic_they", "gen.": "generic_they", "g": "generic_they",
        "generic": "generic_they", "generic_they": "generic_they", "they_generic": "generic_they",
    }
    return mapping.get(s, s)


def process_sheets(filepath, criteria=True, pilot=False):    
    # --- get prolificID from filename ---
    base = os.path.basename(filepath)
    if not base.lower().endswith(".csv"):
        raise ValueError("Expected a .csv file.")
    stem = os.path.splitext(base)[0]
    if "_" not in stem:
        raise ValueError("Filename does not contain an underscore-separated prolificID.")
    prolificID = stem.split("_")[-1] if not pilot else "pilot"+stem.split("_")[1]
    
    if pilot and stem.split("_")[1] == "9": # Isla Doell
        criteria = True
    
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


def process_lime(filepath):
    df = pd.read_excel(filepath, dtype=str)
    
    # drop unwanted columns
    drop_cols = [
        "startlanguage", "id", "seed", "startdate", "lastpage", "G01Q04", "G00Q02", "G00Q01", "G01Q03",
        "G01Q05", "G01Q06", "G01Q07", "G01Q08", "G01Q09", "G01Q10", "G01Q11",
        "G01Q12", "G04Q63"
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
    required = ["prolificID", "EnglishLingFamiliar"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
        if df[col].isna().any() or (df[col].str.strip() == "").any():
            raise ValueError(f"Column {col} has missing values")
    
    # convert rows to list of dicts (values remain strings)
    return df.to_dict(orient="records")
    

# assemble Ground Truth data
gt_path = '/Users/Carlitos/Library/CloudStorage/GoogleDrive-carlos.hartm@gmail.com/Meine Ablage/2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/2 - annotation/4-final version w stats/complete_version.xlsm'
gt = pd.read_excel(gt_path, sheet_name="data", header=0, dtype=str)
# normalize strings
gt = gt.fillna("")        
# drop the first 10 rows
gt = gt.iloc[10:].reset_index(drop=True)

# set of all IDs where 'context_dependent' is "X"
context_dependent_ids = set(gt.loc[gt["context_dependent"] == "X", "ID"].astype(str).str.strip())

def compute_accuracy(participant_dict, context_dependent=0):
    """
    context_dependent:
      0 -> use all eligible items
      1 -> use ONLY IDs in context_dependent_ids
      2 -> SKIP IDs in context_dependent_ids
    """
    if context_dependent not in (0, 1, 2):
        raise ValueError("context_dependent must be 0, 1, or 2.")

    # sanity check for required GT columns
    if "ID" not in gt.columns or "they_type" not in gt.columns:
        raise ValueError("Ground Truth must contain 'ID' and 'they_type' columns.")

    # fast lookup: ID -> normalized they_type
    gt_lookup = (
        gt[["ID", "they_type"]]
        .dropna(subset=["ID"])
        .assign(ID=lambda d: d["ID"].astype(str).str.strip())
        .set_index("ID")["they_type"]
        .to_dict()
    )
    gt_lookup = {k: _norm_type(v) for k, v in gt_lookup.items()}

    correct = 0
    total = 0

    for key, pred_val in participant_dict.items():
        # only evaluate non-comment items that are LoRes or ma_era
        if "[comment]" in key:
            continue
        if ("LoRes" not in key) and ("ma_era" not in key):
            continue

        kid = key.strip()

        # apply context-dependency filter
        if context_dependent == 1 and kid not in context_dependent_ids:
            continue
        if context_dependent == 2 and kid in context_dependent_ids:
            continue

        # require GT present
        if kid not in gt_lookup:
            continue

        total += 1
        gt_val = gt_lookup[kid]
        pred_norm = _norm_type(pred_val)

        if pred_norm == gt_val:
            correct += 1

    return (correct / total) if total else float("nan")


def compute_accuracy_by_label(participant_dict, context_dependent=0,
                              labels=("generic_they", "singular_they", "plural_they")):
    """
    Returns a dict mapping each label to its accuracy, computed over items whose GT is that label.
    context_dependent:
      0 -> use all eligible items
      1 -> ONLY IDs in context_dependent_ids
      2 -> SKIP IDs in context_dependent_ids
    """
    if context_dependent not in (0, 1, 2):
        raise ValueError("context_dependent must be 0, 1, or 2.")

    # sanity check
    if "ID" not in gt.columns or "they_type" not in gt.columns:
        raise ValueError("Ground Truth must contain 'ID' and 'they_type' columns.")

    # GT lookup with normalized labels
    gt_lookup = (
        gt[["ID", "they_type"]]
        .dropna(subset=["ID"])
        .assign(ID=lambda d: d["ID"].astype(str).str.strip())
        .set_index("ID")["they_type"]
        .to_dict()
    )
    gt_lookup = {k: _norm_type(v) for k, v in gt_lookup.items()}

    totals = {lbl: 0 for lbl in labels}
    corrects = {lbl: 0 for lbl in labels}

    for key, pred_val in participant_dict.items():
        # only evaluate non-comment items that are LoRes or ma_era
        if "[comment]" in key:
            continue
        if ("LoRes" not in key) and ("ma_era" not in key):
            continue

        kid = key.strip()

        # apply context-dependency filter
        if context_dependent == 1 and kid not in context_dependent_ids:
            continue
        if context_dependent == 2 and kid in context_dependent_ids:
            continue

        if kid not in gt_lookup:
            continue

        gt_val = gt_lookup[kid]
        if gt_val not in totals:  # ignore unexpected GT labels
            continue

        pred_norm = _norm_type(pred_val)
        totals[gt_val] += 1
        if pred_norm == gt_val:
            corrects[gt_val] += 1

    # compute accuracies per label
    accs = {}
    for lbl in labels:
        if totals[lbl] == 0:
            accs[lbl] = float("nan")
        else:
            accs[lbl] = corrects[lbl] / totals[lbl]
    return accs


### Block A data

# files for within-criteria sheet version
gdrive_basepath = '/Users/Carlitos/Library/CloudStorage/GoogleDrive-carlos.hartm@gmail.com/Meine Ablage/'
within_criteria_sheets_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/6 - study proper/humans/filled-out/sheet version/Block A/approved_by_new_criteria'
within_criteria_sheets = [('Block A', os.path.join(within_criteria_sheets_path, elem)) for elem in os.listdir(within_criteria_sheets_path) if elem.endswith(".xlsm") and not elem.startswith("~")]

# files for within-criteria lime
within_criteria_lime_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/6 - study proper/humans/filled-out/sheet version/Block A/approved_by_new_criteria'
within_criteria_lime = [('Block A', os.path.join(within_criteria_lime_path, elem)) for elem in os.listdir(within_criteria_lime_path) if elem.startswith("limesurvey")]

# files for without-criteria sheet version
without_criteria_sheets_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/6 - study proper/humans/filled-out/sheet version/Block A/does_not_fit_new_criteria'
without_criteria_sheets = [('Block A', os.path.join(without_criteria_sheets_path, elem)) for elem in os.listdir(without_criteria_sheets_path) if elem.endswith(".xlsm") and not elem.startswith("~")]

# files for without-criteria lime
without_criteria_lime_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/6 - study proper/humans/filled-out/sheet version/Block A/does_not_fit_new_criteria'
without_criteria_lime = [('Block A', os.path.join(without_criteria_lime_path, elem)) for elem in os.listdir(without_criteria_lime_path) if elem.startswith("limesurvey")]


block_a = list()
block_a_dash = list()

for file in within_criteria_sheets:
    block_a.append(process_sheets(file[1], criteria=True))
for file in within_criteria_lime:
    block_a.extend(process_lime(file[1]))

for file in without_criteria_sheets:
    block_a_dash.append(process_sheets(file[1], criteria=False))
for file in without_criteria_lime:
    block_a_dash.extend(process_lime(file[1]))


### Blocks B–D

dir_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/6 - study proper/humans/filled-out/limesurvey/responses'
block_b = process_lime(os.path.join(dir_path, "limesurvey_blockB.xlsx"))
block_c = process_lime(os.path.join(dir_path, "limesurvey_blockC.xlsx"))
block_d = process_lime(os.path.join(dir_path, "limesurvey_blockD.xlsx"))
block_a_topup = process_lime(os.path.join(dir_path, "limesurvey_blockA_topup.xlsx"))


### pilot data

pilot_path = gdrive_basepath + '2 - Uni-Ablage/04 sg.they/05 – Studies/2 - THEY Disambiguation/5 - pilot phase/A - humans/data/annotated'
pilot_sheets = [('Block A', os.path.join(pilot_path, elem)) for elem in os.listdir(pilot_path) if elem.endswith(".xlsm") and not elem.startswith("~")]

block_pilot = list()

for file in pilot_sheets:
    block_pilot.append(process_sheets(file[1], criteria=False, pilot=True))


# lists containing participant dicts: block_a, block_a_dash, block_b, block_c, block_d, block_pilot

# Helper: interpret Yes/No across strings/bools
def _is_yes(val):
    if isinstance(val, bool):
        return val is True
    s = str(val).strip().lower()
    return s in {"Yes", "yes", "y", "Y", "true", "1"}

def _is_no(val):
    if isinstance(val, bool):
        return val is False
    s = str(val).strip().lower()
    return s in {"No", "no", "n", "N", "false", "0"}

# Helper: collect accuracies from blocks with optional filter and context flag
def _collect_accuracies(blocks, context_flag=0, pred=None):
    accs = []
    for block in blocks:
        for d in block:
            if pred is not None and not pred(d):
                continue
            acc = compute_accuracy(d, context_dependent=context_flag)
            if acc == acc:  # drop NaN (NaN != NaN)
                accs.append(acc)
    return accs

# Helper: mean and (sample) std; std=0 for n==1, NaN for empty
def _mean_std(values):
    if not values:
        return float("nan"), float("nan")
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
    return mean, std

# ---- Assemble blocks ----
non_pilot_blocks = [block_a, block_a_dash, block_b, block_c, block_d]
all_blocks = non_pilot_blocks + [block_pilot]

# 1) Native speakers within criteria (exclude block_pilot; GenderEnglishAge == Yes)
acc_native = _collect_accuracies(
    non_pilot_blocks,
    context_flag=0,
    pred=lambda d: _is_yes(d.get("GenderEnglishAge", ""))
)
native_mean, native_std = _mean_std(acc_native)

# 2) L2 Pilots (only block_pilot; GenderEnglishAge == No)
acc_l2_pilots = _collect_accuracies(
    [block_pilot],
    context_flag=0,
    pred=lambda d: _is_no(d.get("GenderEnglishAge", ""))
)
l2_pilots_mean, l2_pilots_std = _mean_std(acc_l2_pilots)

# 3) All participants in all blocks (no filter)
acc_all = _collect_accuracies(all_blocks, context_flag=0)
all_mean, all_std = _mean_std(acc_all)

# 4) Human performance for context-dependent examples (context_dependent=1)
acc_ctx_dep = _collect_accuracies(all_blocks, context_flag=1)
ctx_dep_mean, ctx_dep_std = _mean_std(acc_ctx_dep)

# 5) Human performance for context-independent examples (context_dependent=2)
acc_ctx_indep = _collect_accuracies(all_blocks, context_flag=2)
ctx_indep_mean, ctx_indep_std = _mean_std(acc_ctx_indep)

# Optional: gather everything in one dict (with sample sizes)
measures = {
    "native speakers within criteria": {
        "mean": native_mean, "std": native_std, "n": len(acc_native)
    },
    "L2 Pilots": {
        "mean": l2_pilots_mean, "std": l2_pilots_std, "n": len(acc_l2_pilots)
    },
    "all participants": {
        "mean": all_mean, "std": all_std, "n": len(acc_all)
    },
    "human performance for context-dependent examples": {
        "mean": ctx_dep_mean, "std": ctx_dep_std, "n": len(acc_ctx_dep)
    },
    "human performance for context-independent examples": {
        "mean": ctx_indep_mean, "std": ctx_indep_std, "n": len(acc_ctx_indep)
    },
}


import pprint
pp = pprint.PrettyPrinter(indent=4)
pp.pprint(measures)

# File Export

def export_participant_accuracies(output_filename="participant_accuracies.xlsx"):
    # Assemble all blocks; each is a list of participant dicts
    blocks = {
        "block_a": block_a,
        "block_a_dash": block_a_dash,
        "block_a_topup": block_a_topup,
        "block_b": block_b,
        "block_c": block_c,
        "block_d": block_d,
        "block_pilot": block_pilot,
    }

    rows = []

    def _yn(val):
        # keep original if string; normalize booleans to Yes/No for readability
        if isinstance(val, bool):
            return "Yes" if val else "No"
        return val

    for block_name, participants in blocks.items():
        if not participants:
            continue
        for d in participants:
            if not isinstance(d, dict):
                continue

            pid = "" if d.get("prolificID") is None else str(d.get("prolificID"))
            engfam = "" if d.get("EnglishLingFamiliar") is None else str(d.get("EnglishLingFamiliar"))
            gea = _yn(d.get("GenderEnglishAge", ""))

            # overall + per-label
            acc_overall = compute_accuracy(d, context_dependent=0)
            by_overall = compute_accuracy_by_label(d, context_dependent=0)

            # context-dependent (1) + per-label
            acc_ctx_dep = compute_accuracy(d, context_dependent=1)
            by_ctx_dep = compute_accuracy_by_label(d, context_dependent=1)

            # context-independent (2) + per-label
            acc_ctx_ind = compute_accuracy(d, context_dependent=2)
            by_ctx_ind = compute_accuracy_by_label(d, context_dependent=2)

            rows.append({
                "block": block_name,
                "prolificID": pid,
                "EnglishLingFamiliar": engfam,
                "GenderEnglishAge": gea,

                "accuracy_overall": acc_overall,
                "accuracy_context_dependent": acc_ctx_dep,
                "accuracy_context_independent": acc_ctx_ind,

                # per-label (overall)
                "accuracy_generic_they": by_overall.get("generic_they", float("nan")),
                "accuracy_singular_they": by_overall.get("singular_they", float("nan")),
                "accuracy_plural_they": by_overall.get("plural_they", float("nan")),

                # per-label (ctx-dependent = 1)
                "accuracy_generic_they_ctx_dep": by_ctx_dep.get("generic_they", float("nan")),
                "accuracy_singular_they_ctx_dep": by_ctx_dep.get("singular_they", float("nan")),
                "accuracy_plural_they_ctx_dep": by_ctx_dep.get("plural_they", float("nan")),

                # per-label (ctx-independent = 2)
                "accuracy_generic_they_ctx_indep": by_ctx_ind.get("generic_they", float("nan")),
                "accuracy_singular_they_ctx_indep": by_ctx_ind.get("singular_they", float("nan")),
                "accuracy_plural_they_ctx_indep": by_ctx_ind.get("plural_they", float("nan")),
            })

    out_df = pd.DataFrame(rows)
    if not out_df.empty:
        out_df = out_df.sort_values(["block", "prolificID"], kind="stable").reset_index(drop=True)
        for col in [
            "accuracy_overall",
            "accuracy_context_dependent",
            "accuracy_context_independent",
            "accuracy_generic_they", "accuracy_singular_they", "accuracy_plural_they",
            "accuracy_generic_they_ctx_dep", "accuracy_singular_they_ctx_dep", "accuracy_plural_they_ctx_dep",
            "accuracy_generic_they_ctx_indep", "accuracy_singular_they_ctx_indep", "accuracy_plural_they_ctx_indep",
        ]:
            out_df[col] = out_df[col].astype(float).round(4)


    # Save next to the running script; fall back to CWD if __file__ is absent (e.g., notebook)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd()

    out_path = os.path.join(script_dir, output_filename)
    out_df.to_excel(out_path, index=False)
    return out_path

excel_path = export_participant_accuracies()
print(f"Exported to: {excel_path}")