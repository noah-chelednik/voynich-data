"""
HuggingFace Export Utilities
============================

Utilities for exporting VCAT datasets to HuggingFace-compatible formats.

This module provides functions to:
    - Export data to Parquet format via HuggingFace Dataset
    - Create DatasetDict structures for multi-split datasets
    - Generate dataset cards from templates

Example:
    >>> from hf.export import export_to_hf, create_dataset_card
    >>> records = [{"page_id": "f1r", "line_number": 1, ...}]
    >>> ds = export_to_hf(records, "output/")
    >>> ds.num_rows
    4072
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from datasets import Dataset, DatasetDict


def export_to_hf(
    data: list[dict[str, Any]],
    output_dir: str | Path,
    split: str = "train",
) -> Dataset:
    """Export data to HuggingFace dataset format.

    Creates a HuggingFace Dataset from the data and saves it as
    a Parquet file in the output directory.

    Args:
        data: List of records (dictionaries) to export.
        output_dir: Directory to save the dataset. Will be created
            if it doesn't exist.
        split: Dataset split name (default: "train").

    Returns:
        HuggingFace Dataset object containing the data.

    Example:
        >>> records = [
        ...     {"page_id": "f1r", "line_number": 1, "text": "fachys.ykal"},
        ...     {"page_id": "f1r", "line_number": 2, "text": "shory.cthy"},
        ... ]
        >>> ds = export_to_hf(records, "output/")
        >>> ds.num_rows
        2
        >>> ds[0]["page_id"]
        'f1r'
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create dataset
    ds = Dataset.from_list(data)

    # Save as parquet
    ds.to_parquet(output_dir / f"{split}.parquet")

    return ds


def create_dataset_dict(
    data: list[dict[str, Any]],
    output_dir: str | Path,
) -> DatasetDict:
    """Create a DatasetDict with a single train split.

    Creates a HuggingFace DatasetDict containing the data in a
    "train" split and saves it to disk.

    Args:
        data: List of records (dictionaries) to include.
        output_dir: Directory to save the DatasetDict. Will be
            created if it doesn't exist.

    Returns:
        HuggingFace DatasetDict object with a "train" split.

    Example:
        >>> records = [{"page_id": "f1r", "line_number": 1}]
        >>> dd = create_dataset_dict(records, "output/")
        >>> "train" in dd
        True
        >>> dd["train"].num_rows
        1
    """
    ds = Dataset.from_list(data)
    dd = DatasetDict({"train": ds})

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    dd.save_to_disk(str(output_dir))

    return dd


def create_dataset_card(
    template_path: str | Path,
    output_path: str | Path,
    replacements: dict[str, str],
) -> None:
    """Generate a dataset card from template.

    Reads a template file and replaces placeholders with provided
    values. Placeholders in the template should be in the format
    {{PLACEHOLDER_NAME}}.

    Args:
        template_path: Path to the dataset card template file.
        output_path: Path to write the generated dataset card.
        replacements: Dictionary mapping placeholder names to values.
            Keys should not include the {{ }} delimiters.

    Example:
        >>> create_dataset_card(
        ...     template_path="templates/dataset_card.md",
        ...     output_path="output/README.md",
        ...     replacements={
        ...         "DATASET_NAME": "voynich-eva",
        ...         "RECORD_COUNT": "4072",
        ...         "VERSION": "0.1.0",
        ...     }
        ... )

    Template format:
        # {{DATASET_NAME}}

        This dataset contains {{RECORD_COUNT}} records.
        Version: {{VERSION}}
    """
    template = Path(template_path).read_text()

    for placeholder, value in replacements.items():
        template = template.replace(f"{{{{{placeholder}}}}}", value)

    Path(output_path).write_text(template)
