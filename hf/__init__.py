"""
VCAT HuggingFace Export Module
==============================

Utilities for exporting VCAT datasets to HuggingFace format.

This module provides functions to export processed VCAT data to
HuggingFace-compatible formats (Parquet, Dataset) and generate
dataset cards from templates.

Main functions:
    export_to_hf: Export data to HuggingFace dataset format
    create_dataset_dict: Create a HuggingFace DatasetDict
    create_dataset_card: Generate dataset card from template

Example:
    >>> from hf import export_to_hf, create_dataset_card
    >>> records = [{"page_id": "f1r", "line_number": 1, ...}]
    >>> ds = export_to_hf(records, "output/")
    >>> len(ds)
    4072

    >>> create_dataset_card(
    ...     template_path="templates/dataset_card.md",
    ...     output_path="output/README.md",
    ...     replacements={"DATASET_NAME": "voynich-eva"}
    ... )

For publishing to HuggingFace Hub:
    1. Create the dataset with export_to_hf()
    2. Generate the dataset card with create_dataset_card()
    3. Use the HuggingFace CLI or API to push to the Hub
"""

from __future__ import annotations

from .export import create_dataset_card, create_dataset_dict, export_to_hf

__all__ = [
    "create_dataset_card",
    "create_dataset_dict",
    "export_to_hf",
]
