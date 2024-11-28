# Import selenium tools
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

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

from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The IDs of key ALIM SYNC google sheets
ALIM_JIRA_SYNC = "1m0OTpcREK_GvJ36jfnB0bEyxKHofeSwpuk2y8kiXAVc"
ALIM_SYNC      = "1bEPGIV_ubMjdn_2cKbStaPfc_QS7pvf29lhUvzfDkik"
ALIM_INFO_SYNC = "16v_nScc2MN2QuEfSuR57lj8jaC4a_krdDohHajOw1is"

# calls the ems rest API to retrieve the PBS Bill of Materials (BOM)
def get_ems_api(method, params, token):

  url = "https://ems-api.internal.skao.int/"+method

  # Prepare the headers
  if token != None:      
    headers = {
      "Content-Type": "application/json",
      "Authorization": f"Bearer {token}"
    }
  else:
    headers = {"Content-Type": "application/json"}

  print("Calling EMS API..."+url)

  # Make a GET request
  response = requests.get(url, params=headers)

  if response.ok:
    print("Request successful "+url)
    csv_data = response.content.decode("utf-8")
    csv_buffer = StringIO(csv_data)
    return csv_buffer
  else:
    print("Failed to make request "+url)
    print("Status Code:", response.status_code)
    print("Error Response:", response.text)

# retrieve list of jira VCS components
def get_jira_components(jira):

  # get components for PBS jira project (VCS)
  vcs = jira.project('PBS')
  vcs_components = jira.project_components(vcs)

  components = []

  # for each compoment extract name, description, assignee type and lead 
  for i in range(len(vcs_components)):

    name = vcs_components[i].name
    desc = ""
    assn = vcs_components[i].assigneeType
    lead = ""

    if hasattr(vcs_components[i], 'description'):
      desc = vcs_components[i].description

    if hasattr(vcs_components[i], 'lead'):
      lead = vcs_components[i].lead.displayName

    components.append([name,desc,assn,lead])

  return components
  
# retrieve list of jira PBS issues
def get_jira_pbs(jira):

  query = "project = PBS and status not in (Discarded) ORDER BY summary ASC" # get all PBS issues from the VCS project
  fields="key,summary,components,customfield_12130,customfield_14905,customfield_15108,customfield_16306,customfield_16300,customfield_16307,customfield_16304,description,customfield_15601"  
    # customfield_12130 - ARTs
    # customfield_14905 - PDTs
    # customfield_15108 - Agile Teams
    # customfield_16306 - Design Authorities
    # customfield_16300 - Project Manager
    # customfield_16307 - Delegated DAs
    # customfield_16304 - Configuration
    # customfield_15601 - Tier1 Contracts
  
  print(('\n\r PBS query to jira database \n\r\n\r'+ query +'\n\r'))
  issues = jira.search_issues(query,maxResults=None,fields=fields)
  print(str(len(issues))+" Cached PBS Items")

  pbs_items = []

  for i in range(len(issues)):
    key         = str(issues[i].key).upper()
    summary     = str(issues[i].fields.summary)
    description = str(issues[i].fields.description)

    components = ""
    teams      = ""
    pdts       = ""
    arts       = ""
    configs    = ""
    contracts  = ""
    pm         = ""
    ddas       = ""

    if issues[i].fields.customfield_12130 != None: # arts
      for art in issues[i].fields.customfield_12130:
        arts = arts + art.value + " "

    if issues[i].fields.customfield_16304 != None: # config
      for config in issues[i].fields.customfield_16304:
        configs = configs + config.value + " "

    if issues[i].fields.customfield_15108 != None: # agile teams
      for team in issues[i].fields.customfield_15108:
        teams = teams + team.value + " "

    if issues[i].fields.customfield_14905 != None: # pdts
      for pdt in issues[i].fields.customfield_14905:
        pdts = pdts + pdt.value + " "

    if issues[i].fields.customfield_16300 != None: # project manager
      pm = re.sub("JiraServiceUser","",issues[i].fields.customfield_16300.displayName)

    if issues[i].fields.customfield_15601 != None: # contracts
      for contract in issues[i].fields.customfield_15601:
        contracts = contracts + contract.value[0:12] + " " 

    if issues[i].fields.components != None: # components
        components = issues[i].fields.components[0].name

    if issues[i].fields.customfield_16307 != None: # delegated das
        ddas = re.sub("SERVICEUSER","",issues[i].fields.customfield_16307)

    pbs_items.append([key,summary,components,arts,pdts,teams,issues[i].fields.customfield_16306,pm,ddas,configs,description,contracts])

  return pbs_items

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

# copy contents of a sheet range to another sheet range
def copy_sheet_tab(service, from_id, to_id, from_range, to_range):
  
  sheet = service.spreadsheets()
  
  print("Copying sheet values" + \
    '\b\n From Sheet:'+from_id + " " + from_range + \
    '\b\n To Sheet:'+to_id + " " + to_range)
  
  # get from sheet's values in range
  result = (
    sheet.values()
    .get(spreadsheetId=from_id, range=from_range)
    .execute()
  )

  values = result.get("values", [])

  if not values:
    print("No data found in the Google Sheet: "+from_id)
    return

  paste_sheet_values(service=service, sheet_id=to_id, range=to_range, values=values)

  print("Copy complete" + \
    '\b\n From Sheet:'+from_id + " " + from_range + \
    '\b\n To Sheet:'+to_id + " " + to_range +\
    '\b\n')

# initialise a selium driver session
# login to Alim
def get_alim_session(mode='headless',email='', password=''):

  # sets "headless" mode is chosen i.e. does not show the browser
  options = webdriver.ChromeOptions()
  if mode == 'headless':    
      options.add_argument('--headless')
  
  # Create a new instance of the Chrome driver
  driver = webdriver.Chrome(options)

  #Sets a "sticky" timeout to implicitly wait for an element to be found, or a command to complete. 
  # This method only needs to be called one time per session
  driver.implicitly_wait(10) # seconds

  # login to miro to start loading all the details...
  driver.get("https://ska-aw.bentley.com/SKAPROD/")
  print("Loading "+driver.current_url)

  try:
    email_entry = driver.find_element(By.ID,'identifierInput')
    email_entry.send_keys(email)

    signinButton = driver.find_element(By.XPATH,"//*[@id='sign-in-button']")
    signinButton.click()

    # suspend the processing thread for 1 seconds
    time.sleep(1)

    # select Bentley account
    #account = driver.find_element(By.XPATH,"//*[@id='existingAccountsSelectionList']/li[1]")
    #account.click()

    pword = driver.find_element(By.XPATH,"//*[@id='password']") #password
    # password not stored in the code !
    pword.send_keys(password)

    # suspend the processing thread for 1 seconds
    time.sleep(1)
    
    signinButton = driver.find_element(By.XPATH,"//*[@id='sign-in-button']")
    signinButton.click()

    # suspend the processing thread for 1 seconds
    time.sleep(1)

    loginButton = driver.find_element(By.XPATH,"//*[@id='logonButton']")
    loginButton.click()

  except NoSuchElementException as e:
    print("No Such Element Exception "+str(e))
      
  return driver

def get_alim_report_csv(driver, url):

  print("\b\nPrepare to download from "+url)
  
  # Navigate to the provided URL
  driver.get(url)
  # press the download button
  downloadButton = driver.find_element(By.XPATH,"//*[@id='dlRep']")
  downloadButton.click()

  # suspend processing thread for 10 seconds to download
  time.sleep(10) 

  # downloaded file will be timestamped
  now = datetime.now()

  # find the ~/Downloads folder
  downloads_path = str(Path.home() / "Downloads")
  # directory listing of the downloads folder
  files = os.listdir(downloads_path)
  
  results_csv = None
  
  pattern0 = "results - " + now.strftime('%Y-%m-%dT%H%M')+"*.csv"
  pattern1 = "results - " +(now - timedelta(hours=0, minutes=1)).strftime('%Y-%m-%dT%H%M')+"*.csv"
  pattern2 = "results.csv"

  for filename in files:
    if fnmatch.fnmatch(filename, pattern0) or fnmatch.fnmatch(filename, pattern1) or fnmatch.fnmatch(filename, pattern2):
      print("Found downloaded file matching the filter: "+filename)
      results_csv = filename
      break

  # if we did not find the results file, return an empty dataframe
  if results_csv == None:
    print("\b\n******* DID NOT FIND RESULTS FILE MATCHING: "+pattern0+" *******\b\n")
    return pd.DataFrame()

  # open the downloaded csv file and read contents
  pbs_data = pd.read_csv(downloads_path+"/"+filename)
  print("Dowloaded and read data from file: "+downloads_path+"/"+filename)

  # delete the downloaded file...we are done with it
  if os.path.exists(downloads_path+"/"+filename):
    os.remove(downloads_path+"/"+filename)
  else:
    print("File does not exist "+downloads_path+"/"+filename)

  return pbs_data

def xstr(s): # this is just to handle converting lists to strings when there might be some empty values
	if s is None:
		return ''
	return str(s)

def main(argv):
  ##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################

    mode       = 'headless'   # headless = do not show the browser while executing, show=show the browser
    email      = ''           # must be provided via the command line
    password   = ''           # must be provided via the command line
    jira_name  = ''           # must be provided via the command line
    jira_pswd  = ''           # must be provided via the command line

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hs:e:p:u:j:",["help", "show", "email", "password", "jira_name", "jira_pswd"])
    except getopt.GetoptError:
	    print('Usage: alim_sync.py -h <help> -s show -e <email> -p <password> -u <jira_name> -j <jira_pswd>')
        
    for ou, arg in opts:
        if ou in ("-h","--help"):
            print('\b\n Usage: alim_sync.py   -h <help> -s show -e <email> -p <password>\b\n' + \
            '\b\n [-s] Show the browser while the script executes' + \
            '\b\n [-e] Email to login to Alim' + \
            '\b\n [-p] Password to login to Alim, encapsulate in single quotes if there are special characters' +\
            '\b\n [-u] Username to login to Jira' +\
            '\b\n [-j] Password to login to Jira')
            sys.exit()
        elif ou in ("-s", "--show"):
            mode = 'show'
        elif ou in ("-e", "--email"):
            email = arg
        elif ou in ("-p", "--password"):
            password =  arg
        elif ou in ("-u", "--jira_name"):
            jira_name =  arg
        elif ou in ("-j", "--jira_pswd"):
            jira_pswd =  arg
        
    return [mode, email, password, jira_name, jira_pswd]

if __name__ == "__main__":

  sy = main(sys.argv[0:])
  print(' Show:     %s' %str(sy[0]))

  server = "https://jira.skatelescope.org"
  auth_inf = (str(sy[3]),str(sy[4]))
  try:
      jira = JIRA(server=server,token_auth=str(sy[4]))
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
  
  # get from sheet's values in range
  result = (
    sheet.values()
    .get(spreadsheetId=ALIM_JIRA_SYNC, range='{0}!A1:BW'.format("Delta PBS"))
    .execute()
  )

  values = result.get("values", [])
  print(len(values))

  if len(values) > 1 and values[1][0] != "NO DELTAS":

    # create a data frame with the first row as the column headers
    df = pd.DataFrame(values[1:], columns = values[0])
    df = df.reset_index()
    print(df.head())

    for index, row in df.iterrows():
      
      issue = jira.issue(row["Key"])

      das = []
      if isinstance(row["Design Authorities"],str):
        da = row["Design Authorities"]
        if da != "" and da != "ServiceUser":
          user = jira.user(id=row["Design Authorities"])
          if user.active:
            das.append({"name": row["Design Authorities"]})
      else:
        for da in row["Design Authorities"]:
          if da != "" and da != "ServiceUser":
            user = jira.user(id=da)
            if user.active:
              das.append({"name": da})

      ddas = []
      if isinstance(row["Delegated DAs"],str):
        dda = row["Delegated DAs"]
        if dda != "" and dda != "ServiceUser":
          user = jira.user(id=row["Delegated DAs"])
          if user.active:
            ddas.append({"name": row["Delegated DAs"]})
      else:
        for dda in row["Delegated DAs"]:
          if dda != "" and dda != "ServiceUser":
            user = jira.user(id=dda)
            if user.active:
              ddas.append({"name": dda})

      tier1 = []
      if isinstance(row["Tier1 Contracts"],str):
        contract = row["Tier1 Contracts"]
        if contract != "":
          tier1.append({'value': contract})
      elif isinstance(row["Tier1 Contracts"],object):
        for contract in row["Tier1 Contracts"]:
          if contract != "":
            tier1.append({'value': contract})

      telescopes = []
      if isinstance(row["Telescope(s)"],str):
        telescope = row["Telescope(s)"]
        if telescope != "":
          telescopes.append({'value': telescope})
      elif isinstance(row["Telescope(s)"],object):
        for telescope in row["Telescope(s)"]:
          if telescope != "":
            telescopes.append({'value': telescope})

      configs = []
      if isinstance(row["Configuration"],str):
        config = row["Configuration"]
        if config != "":
          configs.append({'value': config})
      elif isinstance(row["Configuration"],object):
        for config in row["Configuration"]:
          if config != "":
            configs.append({'value': config})

      components = []
      components.append({"name":row["Component"]})

      pdts = []
      if row["PDTs"] != None and row["PDTs"] != "":
        pdts.append({"value": row["PDTs"]})

      # delete outward Parent Of links before re-generating them
      for link in issue.fields.issuelinks:
        if hasattr(link, "outwardIssue") and link.type.outward == "Parent Of":
          jira.delete_issue_link(link.id)

      if isinstance(row["Parent Of"],str):
        link = row["Parent Of"]
        if link != "":
          jira.create_issue_link("Parent Of",inwardIssue=row["Key"],outwardIssue=link)
      elif isinstance(row["Parent Of"],object):
        for link in row["Parent Of"]:
          if link != "":
            jira.create_issue_link("Parent Of",inwardIssue=row["Key"],outwardIssue=link)

      issue.update(fields={
        "summary"           :row["Summary"],
        "description"       :row["Description"],
        "components"        :components,
        "customfield_10500" :row["URL"],
        "customfield_16300" :{'name': row["Project Manager"]},
        "customfield_16404" :row["PBS Level"],
        "customfield_14905" :pdts,
        "customfield_16305" :das,
        "customfield_16302" :ddas,
        "customfield_15601" :tier1,
        "customfield_12001" :telescopes,
        "customfield_16304" :configs})

      
  # get the Bill of Material by invoking the EMS API
  df = pd.read_csv(get_ems_api(method="pbs", params=None, token=None))
  # uploads values to the specified sheet, clears content first !! 
  paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("BOMUpload"), values=df.fillna("").T.reset_index().T.values.tolist())

  # get all PBS components and upload them to the Jira Components tab on the Alim-Jira Sync sheet
  components = get_jira_components(jira)
  df = pd.DataFrame(components, columns =["Component", "Description","AssigneeType","Lead"])
  df.sort_values("Component")
  # uploads values to the specified sheet, clears content first !! 
  paste_sheet_values(service=service, sheet_id=ALIM_JIRA_SYNC, range='{0}!A1:D'.format("Jira Components"), values=df.fillna("").T.reset_index().T.values.tolist())

  # get all PBS jira issues and upload them to the Jira Import tab on the Alim-Jira Sync sheet....for comparison with Alim data
  issues = get_jira_pbs(jira)
  df = pd.DataFrame(issues, columns =["Key","Summary", "Components", "ARTs", "PDTs", "Agile Teams","Design Authorities", "Project Manager", "Delegated DAs", "Configuration","Description","Tier1 Contracts"])
  df.sort_values("Summary", ascending=True)
  # uploads values to the specified sheet, clears content first !! 
  paste_sheet_values(service=service, sheet_id=ALIM_JIRA_SYNC, range='{0}!A1:Z'.format("Jira Import"), values=df.fillna("").T.reset_index().T.values.tolist())

  # login to Alim
  driver = get_alim_session(str(sy[0]),str(sy[1]),sy[2])

  # physical items export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=196&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("PhysicalItems"), values=df.fillna("").T.reset_index().T.values.tolist())

  # documents export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=183&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("Documents"), values=df.fillna("").T.reset_index().T.values.tolist())

  # ECPs export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=197&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("ECPs"), values=df.fillna("").T.reset_index().T.values.tolist())

  # PBS Responsibilities export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=203&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("Responsibilities"), values=df.fillna("").T.reset_index().T.values.tolist())

  # SpecTree export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=204&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("SpecTree"), values=df.fillna("").T.reset_index().T.values.tolist())

  # Tier1 Contracts export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=205&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("Contract"), values=df.fillna("").T.reset_index().T.values.tolist())

  # Docs under Change export report
  url = "https://ska-aw.bentley.com/SKAProd/PlugIns/Reporting/ReportWizard.aspx?o=216&t=171&run=true"
  df = get_alim_report_csv(driver, url)
  # uploads values to the specified sheet, clears content first !! 
  if not df.empty:
    paste_sheet_values(service=service, sheet_id=ALIM_SYNC, range='{0}!A1:Z'.format("DocsChanging"), values=df.fillna("").T.reset_index().T.values.tolist())

  # Close the browser window
  driver.close()

  # push the Alim Sync data to the Alim-Jira Synchronisation spreadsheet
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("DocsChanging-API"), to_range='{0}!A1:Z'.format("DocsChanging"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("ECPs-API"), to_range='{0}!A1:Z'.format("ECPs"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("Documents-API"), to_range='{0}!A1:Z'.format("Documents"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("PhysicalItems-API"), to_range='{0}!A1:Z'.format("PhysicalItems"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("Responsibilities-API"), to_range='{0}!A1:Z'.format("Responsibilities"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("SpecTree-API"), to_range='{0}!A1:Z'.format("SpecTree"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("Contract-API"), to_range='{0}!A1:Z'.format("Contract"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_JIRA_SYNC, from_range='{0}!A1:Z'.format("IndentedBOM-API"), to_range='{0}!A1:Z'.format("IndentedBOM"))

  # push the Alim Sync data to the Alim Information Sync spreadsheet
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:K'.format("SpecTree-API"), to_range='{0}!A2:K'.format("Alim SpecTree"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:G'.format("Contract-API"), to_range='{0}!A2:G'.format("Alim ContractName"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:W'.format("DocsChanging-API"), to_range='{0}!A2:W'.format("Alim DocsChanging"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:G'.format("Responsibilities-API"), to_range='{0}!A2:G'.format("Alim Responsibilities"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:S'.format("PhysicalItems-API"), to_range='{0}!A2:S'.format("Alim Physical Items"))
  copy_sheet_tab(service=service, from_id=ALIM_SYNC, to_id=ALIM_INFO_SYNC, from_range='{0}!A1:U'.format("IndentedBOM-API"), to_range='{0}!A2:U'.format("Alim IndentedBOM"))

 
