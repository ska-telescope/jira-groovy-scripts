# Import google api tools
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import jira tools
from jira import JIRA

import sys, getopt
import os, fnmatch
import pandas as pd
import time
import re
import requests
import io
import requests
import field_mapping
import json

from requests.auth import HTTPBasicAuth
from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from field_mapping import get_field_mapping

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Google doc ID for Jama Requirements
JAMA_REQUIREMENTS   = "19BbDwbxKszNVM7UQjcHYlZBmUFdOMDH16lQ0j4SMx3M"
JAMA_BASEURL        = "https://skaoffice.jamacloud.com/rest/v1"

# Cached pairing of item IDs and folder names {'ID' : 'Folder Name'}
# So that we do not need to hit Jama via the rest API as much
folder_hierarchy = {}

PRODUCT_URLS = {

     # Common / Observatory

    "COM TMC SW":           "2192",
    "COM OSO SW":           "2193",
    "COM SDP SW":           "2194",
    "COM Software Platform":"2195",
    "COM Software Services":"2885",
    "COM Telescope Model":  "2887",
    "COM Alarm Mgt System": "2890",
    "COM EDA":              "2886",
    "COM Tango Base":       "2889",
    "COM Taranta":          "2888",

     # Low Telescope

    "LOW CSP":              "2196",
    "LOW CBF":              "2366",
    "LOW PSS":              "2367",
    "LOW PST":              "2368",
    "LOW CSP LMC SW":       "2369",
    "LOW SAT LMC":          "2880",
    "LOW SPS":              "2191",
    "LOW MCCS":             "2370",
    "LOW Networks":         "2206",
    "LOW Antenna Assembly": "2190",
    "LOW LFAA":             "2205",
    "LOW Field Node":       "2371",
    "LOW INAU":             "2207",
    "LOW PaSD":             "2208",
    "LOW SAT":              "2876",
    "LOW SAT STFR FRQ":     "2882",
    "LOW SAT STFR UTC":     "2883",
    "LOW SAT Timescale":    "2881",

    # Mid Telescope

    "MID CSP":              "2197",
    "MID CSP LMC SW":       "2375",
    "MID CBF":              "2372",
    "MID PST":              "2374",
    "MID PSS":              "2373",
    "MID Dish LMC":         "2198",
    "MID SAT LMC":          "2878",
    "MID Networks":         "2211",
    "MID Dish":             "2213",
    "MID SPF B1":           "2200",
    "MID SPF B2":           "2201",
    "MID SPF B345":         "2202",
    "MID B5 DC":            "2216",
    "MID SPF Helium":       "2204",
    "MID SPF Vacuum":       "2884",
    "MID SPF Controller":   "2203",
    "MID INSA":             "2210",
    "MID SPFRx":            "2212",
    "MID DS":               "2199",
    "MID INFRA":            "2214",
    "MID SAT":              "2209",
    "MID SAT STFR FRQ":     "2215",
    "MID SAT STFR UTC":     "2877",
    "MID SAT Timescale":    "2879"
}

def html2markup(html: str) -> str:
    """
    Parse HTML content to extract text if valid.
    """
    html = re.sub('<b>|<strong>|<\\/b>|<\\/strong>', "*", html)
    html = re.sub('<i>|<em>|</i>|<\\/em>', "_", html)
    html = re.sub('<li>', "# ", html)
    html = re.sub('&nbsp;', " ", html)
    html = re.sub('<\\S+[^<>]*>|&.*?;', "", html)

    markup = html.strip()
    if markup == "":
        markup = "-"

    return markup
    
def get_jama_relationships(item_id: str) -> str:
    """
    Invokes the Jama rest API to retrieve an item's down stream related items

    Args:
        - item_id (str): The jama item id of the item for which we need the downstream related items

    Returns:
        Related items in the form <Document Key>|<ID>;<Document Key>|<ID>;...
    """

    url = "https://skaoffice.jamacloud.com/rest/v1/items/"+str(item_id)+"/downstreamrelated?maxResults=50&include=179"

    try:
        response = requests.get(url, auth=auth, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Failed to retrieve data from JAMA: %s"% e)
        raise

    result = response.json()
    data = result.get("data", [])

    derivations = ""

    for elem in data:
        if get_field_value(elem,"itemType") == 1090:
            derivations = derivations + get_field_value(elem,"documentKey") + "|" + str(get_field_value(elem,"id")) + ";"

    return derivations 
        
def get_jama_folder(item_id: str, parent_id:str, level=2) -> str:
    """
    Invokes the Jama rest API to search a maximum of 2 folder level ups following
    a parent item id, and returns the item name as the folder

    Args:
        - item_id (str): The jama item id of the item for which we need the folder name
        - parent_id (str): The item's parent id
        - level (int): The number of levels to search for a folder name

    Returns:
        The item name once we have reached level 1
    """

    if str(item_id) in folder_hierarchy:
        folder = folder_hierarchy[str(item_id)]
        folder_hierarchy[str(parent_id)] = folder
        return folder
    elif str(parent_id) in folder_hierarchy:
        folder = folder_hierarchy[str(parent_id)]
        folder_hierarchy[str(item_id)] = folder
        return folder

    url = "https://skaoffice.jamacloud.com/rest/v1/items/"+str(parent_id)

    try:
        response = requests.get(url, auth=auth, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("Failed to retrieve data from JAMA: %s"% e)
        raise

    result = response.json()
    data = result.get("data", [])

    if level <= 1:
        folder = get_field_value(data,"fields.name")
        folder_hierarchy[str(item_id)] = folder
        folder_hierarchy[str(parent_id)] = folder
        return folder
    else:
        return get_jama_folder(item_id, get_field_value(data,"location.parent.item"), level-1)


def get_field_value(document: dict, jama_key: str):
    """
    Extracts the value from a document using a given Jama key and applies an optional
    transformer.

    Args:
        - document (dict): The Jama document to extract the value from.
        - jama_key (str): The key to access the desired field in the document.
        - transformer (callable, optional): A function to transform the extracted value.

    Returns:
        The extracted and possibly transformed value.
    """

    keys = jama_key.split(".")
    value = document
    for key in keys:
        value = value.get(key, None)

        if value is None:
            break

    return value


def extract_field_mapping_data(artifacts, mapping_type, product=None):
    """
    Extracts and maps JAMA artifacts based on a specified field mapping type.

    Args:
        - artifacts (list): A list of JAMA artifacts to be processed.
        - mapping_type (str): The type of field mapping to be used for extraction.
        - product (str): The product that needs to be added to the extracted data.

    Returns:
        list: A list of dictionaries containing the extracted and mapped data
    """

    total = len(artifacts)
    count = 0

    # Load field mappings from YAML file
    field_mappings = get_field_mapping(mapping_type)

    # Extract data using field mappings
    extracted_data = []
    for artifact in artifacts:

        count += 1

        extracted_document = {}
        for field_mapping in field_mappings:
            field_name = field_mapping["name"]

            if "jama_field" in field_mapping:
                jama_field = field_mapping["jama_field"]
                if "key" in jama_field:
                    key = jama_field["key"]

                    extracted_document[field_name] = get_field_value(artifact, key)

        print("Processing "+extracted_document["Document Key"])

        if count%50 == 0:
            print("Processed %s artefacts"% count)
                        
        # Transform data where necessary                
        if product:
            extracted_document["Component"] = product

            if product == "System":

                if extracted_document["Parent ID"] != None:
                    extracted_document["Folder"] = get_jama_folder(
                        extracted_document["Parent ID"], 
                        extracted_document["Parent ID"],2)

                extracted_document["Derivations"] = get_jama_relationships(extracted_document["Id"])

        # Convert html description to marked up text
        if extracted_document["Description"] != None:
            extracted_document["Description"] = html2markup(extracted_document["Description"])[0:2000]
        else:
            extracted_document["Description"] = "-"

        # Convert milestone ids to string and form ';' seperated list
        if extracted_document["Milestone Id"] != None:
            extracted_document["Milestone Id"] = ';'.join(str(x) for x in extracted_document["Milestone Id"])
        else:
            extracted_document["Milestone Id"] = "Unassigned"

        # Form ';' seperated list of Allocations
        if extracted_document["Allocation"] != None:          
            extracted_document["Allocation"] = ';'.join(str(x) for x in extracted_document["Allocation"])
        else:
            extracted_document["Allocation"] = "Unassigned"

        # Convert html verification requirement to marked up text
        if extracted_document["Verification Requirement"] != None:
            extracted_document["Verification Requirement"] = html2markup(extracted_document["Verification Requirement"])[0:2000]
        else:
            extracted_document["Verification Requirement"] = "-"

        # Convert html compliance rationale to marked up text
        if extracted_document["Compliance Rationale"] != None:
            extracted_document["Compliance Rationale"] = html2markup(extracted_document["Compliance Rationale"])[0:2000] 
        else:
            extracted_document["Compliance Rationale"] = "-"

        # Convert html compliance rationale to marked up text
        if extracted_document["Rationale"] != None:
            extracted_document["Rationale"] = html2markup(extracted_document["Rationale"])[0:2000]
        else:
            extracted_document["Rationale"] = "-"

        # Form ';' seperated list of Verification Methods
        if extracted_document["Verification"] != None:
            extracted_document["Verification"] = extracted_document["Verification"].replace(",", ";").replace(" ", "")
        else:
            extracted_document["Verification"] = "Unassigned"

        # Form ';' seperated list of Verification Methods
        if extracted_document["Verification Methods"] != None:
            extracted_document["Verification Methods"] = ';'.join(str(x) for x in extracted_document["Verification Methods"])
        else:
            extracted_document["Verification Methods"] = "Unassigned"

        extracted_data.append(extracted_document)

    print("Processed %s artefacts"% count)

    return extracted_data

def get_jama_requirements(level: str, product=None) -> pd.DataFrame:
    """
    Retrieves Jama requirements for a given requirement level and product.

    Args:
        level (str): The requirement level ('L0', 'L1', 'L2'). product (str): The
        product identifier.

    Returns:
        pd.DataFrame: A DataFrame containing Jama requirements.
    """
    if level == "L0":
        jama_requirements = get_l0_requirements()
        extracted_data = extract_field_mapping_data(jama_requirements, "requirement", "Science")

        df = pd.DataFrame(extracted_data,columns =[
            "Document Key", 
            "Created Date", 
            "Modified Date", 
            "Name", 
            "Requirement ID", 
            "Description", 
            "Status ID", 
            "Verification", 
            "Allocation To", 
            "Component", 
            "Id"])

    elif level == "L1":
        jama_requirements = get_l1_requirements()
        extracted_data = extract_field_mapping_data(jama_requirements, "requirement", "System")

        df = pd.DataFrame(extracted_data,columns =[
            "Document Key", 
            "Created Date", 
            "Modified Date", 
            "Name", 
            "Requirement ID", 
            "Description", 
            "Status ID", 
            "Verification Methods", 
            "Allocation", 
            "Compliance ID", 
            "Tag",
            "Category",
            "Component",
            "Derivations",
            "Id",
            "Milestone Id",
            "Folder",
            "Verification Requirement",
            "Compliance Rationale",
            "Rationale"
            ])

    elif level == "L2":
        jama_requirements = get_l2_requirements(product)
        extracted_data = extract_field_mapping_data(jama_requirements, "requirement", product)

        df = pd.DataFrame(extracted_data,columns =[
            "Document Key", 
            "Created Date", 
            "Modified Date", 
            "Name", 
            "Requirement ID", 
            "Description", 
            "Status ID", 
            "Verification Methods", 
            "Allocation", 
            "Compliance ID", 
            "Tag",
            "Category",
            "Component",
            "Id",
            "Milestone Id",
            "Verification Requirement",
            "Compliance Rationale",
            "Rationale"
            ])
    else:
        raise ValueError(f"Unsupported level: {level}")

    if jama_requirements is None:
        raise ValueError("Failed to retrieve requirements from Jama.")

    return df

def get_url(product: str) -> Optional[str]:
    """
    Constructs the appropriate JAMA API URL based on the product.

    Args:
        product (str): The product identifier.

    Returns:
        Optional[str]: The constructed URL, or None if the product is not recognized.
    """
    filter_id = PRODUCT_URLS.get(product)
    if filter_id:
        return f"{JAMA_BASEURL}/filters/{filter_id}/results"

    print("Product %s not recognized.", product)
    return None

def fetch_paginated_results(api_url: str) -> List[Dict[str, Any]]:
    """
    Fetches all paginated results from the provided JAMA API URL.

    Args:
        api_url (str): The base API URL for the request.

    Returns:
        List[Dict[str, Any]]: A list of all data items retrieved from the API.
    """
    all_data = []
    start_at = 0
    max_results = 50

    while True:
        paginated_url = f"{api_url}?startAt={start_at}&maxResults={max_results}"
        print("Fetching {0}".format(paginated_url))

        try:
            response = requests.get(paginated_url, auth=auth, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print("Failed to retrieve data from JAMA: %s", e)
            raise

        result = response.json()
        data = result.get("data", [])
        all_data.extend(data)

        # Pagination details
        page_info = result.get("meta", {}).get("pageInfo", {})
        total_results = page_info.get("totalResults", 0)
        result_count = page_info.get("resultCount", 0)

        # Update start_at for the next page
        start_at += result_count

        # Break the loop if we have retrieved all results
        if start_at >= total_results:
            break

    print("Fetched {0} rows from {1}".format(str(start_at), api_url))

    return all_data

def get_l0_requirements() -> List[Dict[str, Any]]:
    """
    Retrieves all L0 requirements from JAMA by fetching all paginated results.

    Returns:
        List[Dict[str, Any]]: A list of all L0 data items retrieved from the API.
    """
    api_url = f"{JAMA_BASEURL}/filters/2082/results"
    return fetch_paginated_results(api_url)

def get_l1_requirements() -> List[Dict[str, Any]]:
    """
    Retrieves all L1 requirements from JAMA by fetching all paginated results.

    Returns:
        List[Dict[str, Any]]: A list of all L1 data items retrieved from the API.
    """
    api_url = f"{JAMA_BASEURL}/filters/2087/results"
    return fetch_paginated_results(api_url)

def get_l2_requirements(product: str) -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves all L2 requirements from JAMA by fetching all paginated results.

    Args:
        product (str): The product identifier.

    Returns:
        Optional[List[Dict[str, Any]]]: A list of all L2 data items retrieved from the
        API, or None if an error occurs.
    """
    api_url = get_url(product)
    if api_url:
        return fetch_paginated_results(api_url)
    return None

# retrieve list of jira requirements
def get_jira_reqs(jira,project="L1"):

    query = "project in ("+project+") AND status not in (discarded)" # get all L1 issues from the L1 project
    fields="customfield_12133,key,summary,components,description,status,customfield_15502,customfield_13903,customfield_12149,customfield_10402,customfield_12142,customfield_12137,customfield_12143,customfield_12001,customfield_12144"  
        # customfield_12133 - ID
        # customfield_15502 - Verification Milestones
        # customfield_13903 - Jama URL
        # customfield_12149 - Verification Methods
        # customfield_10402 - Verification Requirement
        # customfield_12142 - Verification Compliance
        # customfield_12137 - Raionale
        # customfield_12143 - Compliance Rationale
        # customfield_12001 - Telescope(s)
        # customfield_12144 - Category
  
    print(('\n\r Query to jira database \n\r\n\r'+ query +'\n\r'))
    issues = jira.search_issues(query,maxResults=None,fields=fields)
    print(str(len(issues))+" Cached %s Requirements" %project)

    reqs = []

    for i in range(len(issues)):
        key         = str(issues[i].key).upper()
        summary     = str(issues[i].fields.summary)
        description = str(issues[i].fields.description)
        status      = str(issues[i].fields.status)

        components  = ""
        milestones  = ""
        methods     = ""
        telescopes  = ""
        compliances = ""

        if issues[i].fields.customfield_15502 != None: # verification milestones
            for milestone in issues[i].fields.customfield_15502:
                milestones = milestones + milestone.value + ";"
            milestones = milestones[:-1]

        if issues[i].fields.customfield_12149 != None: # verification methods
            for method in issues[i].fields.customfield_12149:
                methods = methods + method.value + ";"
            methods = methods[:-1]

        if issues[i].fields.customfield_12001 != None: # telescopes
            for telescope in issues[i].fields.customfield_12001:
                telescopes = telescopes + telescope.value + ","
            telescopes = telescopes[:-1]

        if issues[i].fields.customfield_12142 != None: # compliance
            compliances = issues[i].fields.customfield_12142.value

        if issues[i].fields.components != None: # components
            for component in issues[i].fields.components:
                components = components + component.name + ";"
            components = components[:-1]
            
        reqs.append([ "Requirement",
            issues[i].fields.customfield_12133, # ID
            key,
            summary,
            components,
            description,
            status,
            milestones,                         # Verification Milestones
            issues[i].fields.customfield_13903, # Jama URL
            methods,                            # Verification Methods
            issues[i].fields.customfield_10402, # Verification Requirement
            compliances,                        # Compliance
            issues[i].fields.customfield_12137, # Rationale
            issues[i].fields.customfield_12143, # Design Compliance Rationale
            telescopes,                         # Telescope(s)
            issues[i].fields.customfield_12144, # Category
            "TRUE"])                            # Exists

    return reqs

# update jira reqs applying deltas
def update_jira_reqs(jira,values):

    if len(values) > 1 and values[1][1] != "NO DELTAS":

        # create a data frame with the first row as the column headers
        df = pd.DataFrame(values[1:], columns = values[0])
        df = df.reset_index()
        print(df.head())

        for index, row in df.iterrows():

            # https://jira.readthedocs.io/
            issue = jira.issue(row["Key"])

            telescopes = []
            if isinstance(row["Telescope(s)"],str):
                telescope = row["Telescope(s)"]
                if telescope != "":
                    telescopes.append({'value': telescope})
            elif isinstance(row["Telescope(s)"],object):
                for telescope in row["Telescope(s)"]:
                    if telescope != "":
                        telescopes.append({'value': telescope})

            verification_milestones = []
            if isinstance(row["Verification Milestones"],str):
                verification_milestone = row["Verification Milestones"]
                if verification_milestone != "":
                    verification_milestones.append({'value': verification_milestone})
            elif isinstance(row["Verification Milestones"],object):
                for verification_milestone in row["Verification Milestones"]:
                    if verification_milestone != "":
                        verification_milestones.append({'value': verification_milestone})

            allocations = []
            try:
                if isinstance(row["Allocation"],str):
                    allocation = row["Allocation"]
                    if allocation != "":
                        allocations.append({'value': allocation})
                elif isinstance(row["Allocation"],object):
                    for allocation in row["Allocation"]:
                        if allocation != "":
                            allocations.append({'value': allocation})
            except KeyError:
                pass

            components = []
            components.append({"name":row["Component"]})

            verification_method = []
            verification_method.append({"value":row["Verification Method"]})

            compliance = {'value': "Unknown"}
            if row["Compliance"] != None and row["Compliance"] != "":
                compliance = {'value': row["Compliance"]}

            category = ""
            try:
                category = row["Category"]
            except KeyError:
                pass

            # delete outward 'derives from' links before re-generating them
            try:
                for link in issue.fields.issuelinks:
                    if hasattr(link, "outwardIssue") and link.type.outward == "derives from":
                        jira.delete_issue_link(link.id)

                if isinstance(row["Derives from"],str):
                    link = row["Derives from"]
                    if link != "" and link != None:
                        jira.create_issue_link("derives from",inwardIssue=row["Key"],outwardIssue=link)
                elif isinstance(row["Derives from"],object):
                    for link in row["Derives from"]:
                        if link != "" and link != None:
                            jira.create_issue_link("derives from",inwardIssue=row["Key"],outwardIssue=link)
            except KeyError:
                pass

            print("Updating delta {1} with Jira key:{0}".format(row["Key"],str(index)))

            issue.update(notify=False, fields={
                "summary"           :row["Summary"],
                "description"       :row["Description"],
                "customfield_12133" :row["ID"],
                "components"        :components,
                "customfield_12001" :telescopes,
                "customfield_13903" :row["Jama URL"],
                "customfield_12149" :verification_method,
                "customfield_10402" :row["Verification Requirement"],
                "customfield_12142" :compliance,
                "customfield_12143" :row["Compliance Rationale"],
                "customfield_12137" :row["Rationale"],
                "customfield_15502" :verification_milestones,
                "customfield_12144" :category
                #"customfield_16206" :allocations
                })

            if (issue.fields.status.name).upper() != (row["Status"]).upper():

                if row["Status"].upper() == "ACCEPTED":
                    jira.transition_issue(issue,'31')
                elif row["Status"].upper() == "REJECTED":
                    jira.transition_issue(issue,'21')
                elif row["Status"].upper() == "PROPOSED":
                    jira.transition_issue(issue,'11')

# uses the google spreadsheet service to replace the contents of sheet_id in range with values
def paste_sheet_values(service, sheet_id, range, values):

    print("Clearing existing data" + \
        '\b\n From Sheet:'+sheet_id + " " + range)

    body = {}
    resultClear = service.spreadsheets().values().clear(
        spreadsheetId=sheet_id, 
        range=range,
        body=body).execute()
    print(str(resultClear))
  
    print("Writing new data" + \
        '\b\n To Sheet:'+sheet_id + " " + range)

    response_data = service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        valueInputOption='RAW',
        range=range,
        body=dict(
            majorDimension='ROWS',
            values=values)
    ).execute()
    print(str(response_data))

def xstr(s): # this is just to handle converting lists to strings when there might be some empty values
	if s is None:
		return ''
	return str(s)

def main(argv):
    ##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################

    jama_user   = ''    # must be provided via the command line
    jama_pswd   = ''    # must be provided via the command line
    jira_pswd   = ''    # must be provided via the command line

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hs:j:u:p:",["help", "jira_pswd","jama_user","jama_pswd"])
    except getopt.GetoptError:
	    print('Usage: jama_sync.py -h <help> -j <jira_pswd> -u <jama_user> -p <jama_pswd>')
        
    for ou, arg in opts:
        if ou in ("-h","--help"):
            print('\b\n Usage: jama_sync.py -h <help> -j <jira_pswd> -u <jama_user> -p <jama_pswd>\b\n' + \
            '\b\n [-j] Password to login to Jira using the ServiceUser account' + \
            '\b\n [-u] Username to login to Jama to retrieve items (Reqs, Tests, etc)' + \
            '\b\n [-p] Password to login to Jama to retrieve items (Reqs, Tests, etc)')
            sys.exit()
        elif ou in ("-j", "--jira_pswd"):
            jira_pswd = arg
        elif ou in ("-u", "--jama_user"):
            jama_user = arg
        elif ou in ("-p", "--jama_pswd"):
            jama_pswd = arg

    return [jira_pswd,jama_user,jama_pswd]

if __name__ == "__main__":

    try:
        folder_hierarchy = json.load(open("folder_hierarchy.dat"))
    except FileNotFoundError as e:
        folder_hierarchy = {}

    sy = main(sys.argv[0:])

    JAMA_USER = str(sy[1])
    JAMA_PASSWORD = str(sy[2])
    
    # Use HTTPBasicAuth for authentication
    auth = HTTPBasicAuth(JAMA_USER, JAMA_PASSWORD)

    server = "https://jira.skatelescope.org"
    auth_inf = ('serviceuser',str(sy[0]))
    try:
        jira = JIRA(server=server,token_auth=str(sy[0]))
    except:
        print("ERROR: Jira authentication failed. Have you provided the correct username and password?")

    """Uses the Google Sheets API to authenticate with Google """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
    except HttpError as err:
        print(err)

    sheet = service.spreadsheets()

    # get L1 deltas and apply jira updates
    result = (sheet.values().get(spreadsheetId=JAMA_REQUIREMENTS, range='{0}!A1:BZ'.format("Delta L1s")).execute())
    values = result.get("values", [])
    print("L1 Deltas found: %s" % str(len(values)-1))
    update_jira_reqs(jira, values)

    # get L2 deltas and apply jira updates
    result = (sheet.values().get(spreadsheetId=JAMA_REQUIREMENTS, range='{0}!A1:BZ'.format("Delta L2s")).execute())
    values = result.get("values", [])
    print("L2 Deltas found: %s" % str(len(values)-1))
    update_jira_reqs(jira, values)

    # get all L1 jira issues and upload them to the Jira L1s tab on the Jama Requirements Sync sheet....for comparison with Jama data
    issues = get_jira_reqs(jira,"L1")
    df = pd.DataFrame(issues, columns =["Issue Type","ID","Key","Summary","Components","Description","Status","Verification Milestones","URL","Verification Method","Verification Requirement","Compliance","Rationale","Design Complaince Rationale","Telescopes","Category","Exists"])
    df.sort_values("Summary", ascending=True)
    # uploads values to the specified sheet, clears content first !! 
    paste_sheet_values(service=service, sheet_id=JAMA_REQUIREMENTS, range='{0}!A1:Z'.format("Jira L1s"), values=df.fillna("").T.reset_index().T.values.tolist())

    # get all L2 jira issues and upload them to the Jira L2s tab on the Jama Requirements Sync sheet....for comparison with Jama data
    issues = get_jira_reqs(jira,"L2")
    df = pd.DataFrame(issues, columns =["Issue Type","ID","Key","Summary","Components","Description","Status","Verification Milestones","URL","Verification Method","Verification Requirement","Compliance","Rationale","Design Complaince Rationale","Telescopes","Category","Exists"])
    df.sort_values("Summary", ascending=True)
    # uploads values to the specified sheet, clears content first !! 
    paste_sheet_values(service=service, sheet_id=JAMA_REQUIREMENTS, range='{0}!A1:Z'.format("Jira L2s"), values=df.fillna("").T.reset_index().T.values.tolist())

    # get L1 Jama Requirements
    df = get_jama_requirements("L1")
    if not df.empty:
        paste_sheet_values(service=service, sheet_id=JAMA_REQUIREMENTS, range='{0}!A1:Z'.format("L1"), values=df.fillna("").T.reset_index().T.values.tolist())

    json.dump(folder_hierarchy, open("folder_hierarchy.dat",'w'))

    # get L2 Jama Requirements

    # Common / Observatory L2 Requirements
    df = get_jama_requirements("L2", "COM TMC SW")
    df = pd.concat([df,get_jama_requirements("L2", "COM OSO SW")])
    df = pd.concat([df,get_jama_requirements("L2", "COM SDP SW")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Software Platform")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Software Services")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Telescope Model")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Alarm Mgt System")])
    df = pd.concat([df,get_jama_requirements("L2", "COM EDA")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Tango Base")])
    df = pd.concat([df,get_jama_requirements("L2", "COM Taranta")])

    # Low Telescope L2 Requirements
    df = pd.concat([df,get_jama_requirements("L2", "LOW CSP")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW CBF")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW PSS")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW PST")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW CSP LMC SW")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SAT LMC")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SPS")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW MCCS")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW Networks")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW Antenna Assembly")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW LFAA")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW Field Node")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW INAU")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW PaSD")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SAT")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SAT STFR FRQ")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SAT STFR UTC")])
    df = pd.concat([df,get_jama_requirements("L2", "LOW SAT Timescale")])

    # Mid Telescope L2 Requirements
    df = pd.concat([df,get_jama_requirements("L2", "MID CSP")])
    df = pd.concat([df,get_jama_requirements("L2", "MID CSP LMC SW")])
    df = pd.concat([df,get_jama_requirements("L2", "MID CBF")])
    df = pd.concat([df,get_jama_requirements("L2", "MID PST")])
    df = pd.concat([df,get_jama_requirements("L2", "MID PSS")])
    df = pd.concat([df,get_jama_requirements("L2", "MID Dish LMC")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SAT LMC")])
    df = pd.concat([df,get_jama_requirements("L2", "MID Networks")])
    df = pd.concat([df,get_jama_requirements("L2", "MID Dish")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF B1")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF B2")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF B345")])
    df = pd.concat([df,get_jama_requirements("L2", "MID B5 DC")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF Helium")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF Vacuum")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPF Controller")])
    df = pd.concat([df,get_jama_requirements("L2", "MID INSA")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SPFRx")])
    df = pd.concat([df,get_jama_requirements("L2", "MID DS")])
    df = pd.concat([df,get_jama_requirements("L2", "MID INFRA")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SAT")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SAT STFR FRQ")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SAT STFR UTC")])
    df = pd.concat([df,get_jama_requirements("L2", "MID SAT Timescale")])

    if not df.empty:
        paste_sheet_values(service=service, sheet_id=JAMA_REQUIREMENTS, range='{0}!A1:Z'.format("L2"), values=df.fillna("").T.reset_index().T.values.tolist())

    # get L0 Jama Requirements
    df = get_jama_requirements("L0")
    if not df.empty:
        paste_sheet_values(service=service, sheet_id=JAMA_REQUIREMENTS, range='{0}!A1:Z'.format("L0"), values=df.fillna("").T.reset_index().T.values.tolist())



