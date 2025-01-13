"""
This module provides various utility functions to interact with YAML-based lookup fields
and process HTML content. It includes functions to retrieve statuses, compliances,
milestones, and allocations from a YAML file, and also to parse and format HTML content
for test cases.
"""

import html2text
import yaml

from html2jira import convert_to_jira_wiki

# Load the YAML file
with open(
    "src/ska_jama_jira_integration/jama/lookup_fields.yaml", "r", encoding="utf-8"
) as file:
    data = yaml.safe_load(file)


def lookup_status(status_id):
    """
    Looks up a status in the loaded YAML data based on the provided Status ID.
    """
    for status in data["statuses"]:
        if status["Status ID"] == status_id:
            return status["Status"]
    return "Status ID not found"


def lookup_compliances(compliance_id):
    """
    Looks up a compliance in the loaded YAML data based on the provided Compliance ID.
    """
    for status in data["compliances"]:
        if status["Compliance ID"] == compliance_id:
            return status["Compliance"]
    return "Compliance ID not found"


def lookup_milestones(milestone_id):
    """
    Looks up a milestone in the loaded YAML data based on the provided Milestone ID.
    """
    for status in data["milestones"]:
        if status["Milestone ID"] == milestone_id:
            return status["Milestone"]
    return "Milestone ID not found"


def lookup_allocations(allocation_id):
    """
    Looks up an allocation in the loaded YAML data based on the provided Allocation ID.
    """
    for status in data["allocations"]:
        if status["Allocation ID"] == allocation_id:
            return status["Allocation"]
    return "Allocation ID not found"


def get_milestones(milestone_ids):
    """
    Retrieve milestones from IDs.
    """
    if milestone_ids:
        return ";".join(lookup_milestones(m_id) for m_id in milestone_ids)
    return "Unassigned"


def get_verification_method(method):
    """
    Retrieve verification method.
    """
    if method:
        return method
    return "Unassigned"


def get_test_case(test_steps):
    """
    Transform test steps into a full test
    """
    result = []

    if test_steps:
        for idx, step in enumerate(test_steps, start=1):
            action = parse_html(step.get("action", ""))
            expected_result = parse_html(step.get("expectedResult", ""))

            step_str = f"Step #{idx} {action}\n"
            step_str += f"Result #{idx} {expected_result}\n"

            result.append(step_str)

    return "----\n".join(result)


def parse_to_array(text: str) -> str:
    """
    Replace commas with semicolons in the input text.
    """
    if text:
        return text.replace(",", ";")
    return text


def parse_html(html: str) -> str:
    """
    Parse HTML content to extract text if valid.
    """

    print(html)

    jira_wiki = convert_to_jira_wiki(html)
    return jira_wiki


def parse_html_2text(html: str) -> str:
    """
    Parse HTML content to extract text if valid.
    """
    converter = html2text.HTML2Text()
    markdown = converter.handle(html)

    jira_markup = markdown.replace("* ", "*").replace("1. ", "#")

    return jira_markup
