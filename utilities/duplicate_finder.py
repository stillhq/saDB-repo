import yaml
from collections import defaultdict
import os

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

def check_duplicate_src_pkg_names():
    yaml_file_path = os.path.join(ARTIFACTS_DIR, "repo.yaml")
    # Read the YAML file
    with open(yaml_file_path, 'r') as file:
        data = yaml.safe_load(file)

    # Create a dictionary to store src_pkg_names and their corresponding items
    src_pkg_dict = defaultdict(list)

    # Iterate through the items in the YAML data
    for item_name, item_data in data.items():
        if 'src_pkg_name' in item_data:
            src_pkg_name = item_data['src_pkg_name']
            src_pkg_dict[src_pkg_name].append(item_name)

    # Find and return items with duplicate src_pkg_names
    duplicates = {src_pkg: items for src_pkg, items in src_pkg_dict.items() if len(items) > 1}

    return duplicates

print(check_duplicate_src_pkg_names())