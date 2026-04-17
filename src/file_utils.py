import os
import json


def collect_file_names(input_dir, output_path="file_list.json"):
    """Collect all file names under input_dir and write them to a JSON file.

    Each entry contains the relative path starting from input_dir.
    """
    file_names = []
    for root, _, files in os.walk(input_dir):
        for fname in files:
            full_path = os.path.join(root, fname)
            rel_path = os.path.relpath(full_path, input_dir)
            file_names.append(rel_path)
    file_names.sort()
    tmp_path = output_path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(file_names, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, output_path)
    return file_names


def is_file_ready(file_path):
    """Check if a file has [SPEC] ... [SPEC] and [INFO] ... [INFO] headers."""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return False

    lines = content.splitlines()
    spec_count = 0
    info_count = 0

    for line in lines:
        if '[SPEC]' in line:
            spec_count += 1
        if '[INFO]' in line:
            info_count += 1

    return spec_count >= 2 and info_count >= 2
