"""
Loads the field mappings from a YAML configuration file.
"""

import yaml

def get_field_mapping(mapping_type: str) -> list:
    """
    Loads the field mappings from a YAML configuration file.

        Returns:
        list: A list of dictionaries representing the field mappings.
    """
    yaml_file = "./field_mapping.yaml"

    try:
        with open(yaml_file, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        if mapping_type == "requirement":
            return config["requirement_fields"]
        if mapping_type == "test_case":
            return config["test_case_fields"]
        if mapping_type == "interfaces":
            return config["interfaces_fields"]

        raise ValueError(f"Unsupported mapping type: {mapping_type}")

    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML file: {e}") from e
