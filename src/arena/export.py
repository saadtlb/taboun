import csv
import os
from typing import List, Dict, Any


def write_results_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_ranking_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    write_results_csv(path, rows)


def write_matrix_csv(path: str, bot_names: List[str], matrix: List[List[str]]) -> None:
    if not bot_names:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    header = [""] + bot_names
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for name, row in zip(bot_names, matrix):
            writer.writerow([name] + row)
