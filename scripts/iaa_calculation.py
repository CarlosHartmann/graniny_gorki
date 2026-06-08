from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score


VALID_LABELS = {"generic_they", "singular_they", "plural_they"}


def _normalize_label(value: object) -> str:
	"""Normalize annotation labels to canonical forms used in this project."""
	if value is None:
		return ""

	text = str(value).strip().lower()
	if text in {"", "nan", "none"}:
		return ""

	text = text.replace("-", "_").replace(" ", "_")

	mapping = {
		"gen": "generic_they",
		"generic": "generic_they",
		"generic_they": "generic_they",
		"sing": "singular_they",
		"singular": "singular_they",
		"singular_they": "singular_they",
		"pl": "plural_they",
		"plural": "plural_they",
		"plural_they": "plural_they",
	}

	return mapping.get(text, text)


def calculate_cohens_kappa(
	ground_truth_path: str | Path = "assets/ground_truth.csv",
	colleague_path: str | Path = "assets/iaa/piloting_colleague_completed.csv",
) -> float:
	"""Calculate Cohen's kappa between ground truth and colleague annotations."""
	repo_root = Path(__file__).resolve().parent.parent
	gt_file = repo_root / Path(ground_truth_path)
	colleague_file = repo_root / Path(colleague_path)

	ground_truth = pd.read_csv(gt_file, dtype=str).fillna("")
	colleague = pd.read_csv(colleague_file, dtype=str).fillna("")

	required_columns = {"ID", "they_type"}
	if not required_columns.issubset(ground_truth.columns):
		missing = required_columns - set(ground_truth.columns)
		raise ValueError(f"Ground truth is missing required columns: {sorted(missing)}")
	if not required_columns.issubset(colleague.columns):
		missing = required_columns - set(colleague.columns)
		raise ValueError(f"Colleague file is missing required columns: {sorted(missing)}")

	gt_labels = (
		ground_truth[["ID", "they_type"]]
		.assign(
			ID=lambda d: d["ID"].astype(str).str.strip(),
			they_type=lambda d: d["they_type"].map(_normalize_label),
		)
		.rename(columns={"they_type": "ground_truth_label"})
	)

	colleague_labels = (
		colleague[["ID", "they_type"]]
		.assign(
			ID=lambda d: d["ID"].astype(str).str.strip(),
			they_type=lambda d: d["they_type"].map(_normalize_label),
		)
		.rename(columns={"they_type": "colleague_label"})
	)

	paired = gt_labels.merge(colleague_labels, on="ID", how="inner")
	paired = paired[
		paired["ground_truth_label"].isin(VALID_LABELS)
		& paired["colleague_label"].isin(VALID_LABELS)
	]

	if paired.empty:
		raise ValueError("No overlapping annotated items found for Cohen's kappa.")

	return float(cohen_kappa_score(paired["ground_truth_label"], paired["colleague_label"]))


if __name__ == "__main__":
	kappa = calculate_cohens_kappa()
	print(f"Cohen's kappa: {kappa:.6f}")
