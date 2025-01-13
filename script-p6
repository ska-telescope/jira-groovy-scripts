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
import openpyxl
import time
import re
import requests
import io
import glob

from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# ID of the Primavera Export google sheet
PRIMAVERA_EXPORT = "1DOsGzsq_3dt9AGJsVbiFxLYnQUAXnO5dhG5qfAilFrA"

# retrieve list of jira issues containing an Activity ID
def get_jira_p6(jira):

    query = "project in (TPO,TAIV) and 'Activity ID' is not EMPTY ORDER BY project ASC" # get all issues with an Activity ID
    fields="key,summary,status,customfield_11945,customfield_14820,customfield_14819,customfield_14900"  
    # customfield_11945 - Activity ID
    # customfield_14820 - IPS Finish
    # customfield_14819 - IPS Start
    # customfield_14900 - IPS Status
  
    print(('\n\r P6 query to jira database \n\r\n\r'+ query +'\n\r'))
    issues = jira.search_issues(query,maxResults=None,fields=fields)
    print(str(len(issues))+" Cached P6 Items")

    p6_items = []

    for i in range(len(issues)):
        key         = str(issues[i].key).upper()
        summary     = str(issues[i].fields.summary)
        status      = str(issues[i].fields.status)

        activity_id = ""
        ips_finish  = None
        ips_start   = None
        ips_status  = ""

        if issues[i].fields.customfield_11945 != None: # activity id
            activity_id = xstr(issues[i].fields.customfield_11945)

        if issues[i].fields.customfield_14819 != None: # ips start
            ips_start = issues[i].fields.customfield_14819

        if issues[i].fields.customfield_14820 != None: # ips finish
            ips_finish = issues[i].fields.customfield_14820

        if issues[i].fields.customfield_14900 != None: # ips status
            ips_status = xstr(issues[i].fields.customfield_14900[0].value)

        p6_items.append([key,summary,activity_id,ips_finish,ips_start,ips_status,status])

    return p6_items

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

# initialise a selium driver session, and login to P6
def get_p6_session(mode='headless',username='skaouser2', password=''):

    # sets "headless" mode is chosen i.e. does not show the browser
    options = webdriver.ChromeOptions()
    if mode == 'headless':    
        options.add_argument('--headless')
  
    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options)

    #Sets a "sticky" timeout to implicitly wait for an element to be found, or a command to complete. 
    # This method only needs to be called one time per session
    driver.implicitly_wait(10) # seconds

    # login to P6 to start loading all the details...
    driver.get("https://ska-web.milestoneuk.com/p6/action/login")
    print("Loading "+driver.current_url)

    try:
        # enter username
        user = driver.find_element(By.ID,'username') # username
        user.send_keys(username)
        # enter password
        pword = driver.find_element(By.ID,"password") #password
        pword.send_keys(password)

        # suspend the processing thread for 1 seconds
        time.sleep(1)
        
        # click signin button
        signinButton = driver.find_element(By.ID,"login")
        signinButton.click()

        # suspend the processing thread for 3 seconds
        time.sleep(3)

        # load EPS projects
        driver.get("https://ska-web.milestoneuk.com/p6/action/pm/projects?isApplet=false&")
        print("Loading "+driver.current_url)

        # give P6 some time to load...
        time.sleep(10)

        # click the Actions menu item
        actions = driver.find_element(By.XPATH,'//*[@id="master-panel"]/div[1]/div/div[1]/button') # actions
        actions.click()

        time.sleep(2)

        # click close all projects
        closeAll = driver.find_element(By.XPATH,'//*[@id="epsActionDropdownMenu"]/li[6]/a') # close all
        closeAll.click()

        time.sleep(1)

    except NoSuchElementException as e:
        print("No Such Element Exception "+str(e))

    return driver

# open the SKAO project in the EPS (Enterprise Project Structure) view of P6
def open_p6_skao(driver):

    try:   
        # find the project search input box, search for SKAO Square
        search = driver.find_element(By.XPATH,'//*[@id="pgbu-input-306"]') 
        search.send_keys("SKAO Square")

        time.sleep(2)

        # click Open on menu
        proj_open = driver.find_element(By.XPATH,'//*[@id="master-panel"]/div[1]/div/div[2]/button') 
        proj_open.click()

        time.sleep(1)

        # click Project on menu i.e. Open->Project
        project = driver.find_element(By.XPATH,'//*[@id="pgbu-dropdown-menu-305"]/li[1]/a')
        project.click()

        time.sleep(2)

        # navigate to Activities of Square Kilometre Array
        driver.get("https://ska-web.milestoneuk.com/p6/action/pm/activities?")
        print("Loading "+driver.current_url)

        # give P6 some time to load...
        time.sleep(15)

        try:

            # Check if warning pops up about some filter conditions are no longer valid
            views = driver.find_element(By.XPATH,'//*[@id="alert-modal"]/div[3]/button')
            views.click()
            
        except NoSuchElementException as e:
            print("No Such Element Exception "+str(e))
        
        # switch views to 'Ray's View DO NOT EDIT'
        views = driver.find_element(By.XPATH,'//*[@id="pgbu-input-136"]')
        views.click()

        # delete current view selected 
        views.send_keys(Keys.CONTROL + "a")
        views.send_keys(Keys.DELETE)

        time.sleep(1)

        # enter the correct view to use...press ENTER
        views.send_keys("Ray's View DO NOT EDIT" + Keys.ENTER)

        # if a popup appears to ignore changes to the previous view...then click Yes...ignore the changes
        try:
            driver.implicitly_wait(3) # seconds
            ignore_changes = driver.find_element(By.XPATH,'//*[@id="confirm-modal"]/div[3]/button[2]')
            ignore_changes.click()
        except NoSuchElementException as e:
            print("No changes to P6 view identified")

    except NoSuchElementException as e:
        print("No Such Element Exception "+str(e))

    return driver

# expand all activities in P6, and select the download link
def download_p6_skao(driver):
    try:   
         # collapse all activities
        collapse = driver.find_element(By.XPATH,'//*[@id="collapseAll"]')
        collapse.click()

        time.sleep(3)

        # expand all activities
        expand = driver.find_element(By.XPATH,'//*[@id="expandAll"]')
        expand.click()
       
        time.sleep(3)

        # click download link
        download = driver.find_element(By.XPATH,'//*[@class="pgbu-icon pgbu-icon-download"]')
        download.click()

        time.sleep(10)
    except NoSuchElementException as e:
        print("No Such Element Exception "+str(e))

    return driver

# find files in the Downloads folder matching a pattern
# if found, load the data file into a Pandas Dataframe
# else return an empty dataframe
def load_p6_excel():

    data_file = None
    pattern = "Primavera*.xlsx"

    # find the ~/Downloads folder
    downloads_path = str(Path.home() / "Downloads")

    # directory listing of the downloads folder
    files = glob.glob(downloads_path + "/" + pattern)
    if files == None or files == []:
        print("Path "+downloads_path + "/" +pattern)
        print("\b\n******* DID NOT FIND RESULTS FILE MATCHING: "+pattern+" *******\b\n")
        return pd.DataFrame()
    else:
        data_file = max(files, key=os.path.getmtime)
        print("Found downloaded file matching the pattern: "+data_file)

    # open the downloaded csv file and read contents
    p6_data = pd.read_excel(data_file, engine='openpyxl')
    print("Dowloaded and read data from file: "+data_file)
    print(p6_data.head())

    # delete the downloaded file...we are done with it
    if os.path.exists(data_file):
        os.remove(data_file)
    else:
        print("File does not exist "+data_file)

    return p6_data

def xstr(s): # this is just to handle converting lists to strings when there might be some empty values
	if s is None:
		return ''
	return str(s)

def main(argv):
    ##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################

    mode        = 'headless'   # headless = do not show the browser while executing, show=show the browser
    password    = ''           # must be provided via the command line
    jira_pswd   = ''           # must be provided via the command line

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hs:p:j:",["help", "show", "password", "jira_pswd"])
    except getopt.GetoptError:
	    print('Usage: p6_sync.py -h <help> -s show -p <password> -j <jira_pswd>')
        
    for ou, arg in opts:
        if ou in ("-h","--help"):
            print('\b\n Usage: p6_sync.py -h <help> -s show -p <password> -j <jira_pswd>\b\n' + \
            '\b\n [-s] Show the browser while the script executes' + \
            '\b\n [-p] Password to login to P6, encapsulate in single quotes if there are special characters' +\
            '\b\n [-j] Password to login to Jira using the ServiceUser account')
            sys.exit()
        elif ou in ("-s", "--show"):
            mode = 'show'
        elif ou in ("-p", "--password"):
            password =  arg
        elif ou in ("-j", "--jira_pswd"):
            jira_pswd =  arg
        
    return [mode, password, jira_pswd]

# log in to jira
# log in to google
# log in to P6
#   - open SKAO project
#   - Download all activities (xlsx file)
# upload activities to PRIMAVERA_EXPORT sheet (IPS tab)
# read and upload all jira issues (with an Activity ID) to PRIMAVERA_EXPORT sheet (Jira Import tab)
# let the PRIMAVERA_EXPORT sheet compare IPS & Jira activities and produce a delta (Delta CSV tab)
# read the PRIMAVERA_EXPORT Delta CSV tab, and update Jira issues with new fields for:
#   - ips start
#   - ips finish
#   - ips status
#   - summary (on TPO tickets)

if __name__ == "__main__":

    sy = main(sys.argv[0:])
    print(' Show:     %s' %str(sy[0]))

    server = "https://jira.skatelescope.org"
    auth_inf = ('ServiceUser',sy[2])
    try:
         jira = JIRA(server=server,token_auth=str(sy[2]))
    except:
        print("ERROR: Jira authentication failed. Have you provided the correct username and password?")
        exit(1)

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
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)

            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
    except HttpError as err:
        print(err)

    # login to P6
    driver = get_p6_session(mode=str(sy[0]),password=str(sy[1]))
    driver = open_p6_skao(driver)
    driver = download_p6_skao(driver)
    # Close the browser window
    driver.close()

    # find and load the downloaded p6 data file
    df = load_p6_excel()
    # uploads values to the specified sheet, clears content first !! 
    if not df.empty:
        paste_sheet_values(service=service, sheet_id=PRIMAVERA_EXPORT, range='{0}!A2:Z'.format("IPS"), values=df.fillna("").T.reset_index().T.values.tolist()[1:])

    # get all jira issues with an activity ID and upload them to the Jira Import tab on the Primavera P6 - All Activities Export sheet....for comparison with P6 data
    issues = get_jira_p6(jira)
    df = pd.DataFrame(issues, columns =["Key","Summary", "Activity ID", "IPS Finish", "IPS Start", "IPS Status","Status"])
    df.sort_values("Summary", ascending=True)
    # uploads values to the specified sheet, clears content first !! 
    paste_sheet_values(service=service, sheet_id=PRIMAVERA_EXPORT, range='{0}!A1:Z'.format("Jira Import"), values=df.fillna("").T.reset_index().T.values.tolist())

    # give the PRIMAVERA_EXPORT sheet some time to compare data
    time.sleep(10) # seconds

     # Now see if there are any differences in the data
    sheet = service.spreadsheets()
  
    # read the DELTA CSV tab of the PRIMAVERA_EXPORT sheet
    result = (
        sheet.values()
        .get(spreadsheetId=PRIMAVERA_EXPORT, range='{0}!A1:K'.format("Delta CSV"))
        .execute()
    )

    # get values from the DELTA CSV tab
    values = result.get("values", [])

    if len(values) > 1 and values[1][3] != "NO DELTAS":

        # create a data frame with the first row as the column headers
        df = pd.DataFrame(values[1:], columns = values[0])
        df = df.reset_index()
        print(df.head())

        # for each Delta CSV row in the PRIMAVERA_EXPORT sheet
        for index, row in df.iterrows():

            print("Updated key={} ips status={} ips start={} ips_finish={}".format(
                row["Issue key"],
                row["Custom field (IPS Status)"],
                row["Custom field (IPS Start)"],
                row["Custom field (IPS Finish)"]))

            # get the jira issue based on its key
            issue = jira.issue(row["Issue key"])

            date_format = '%d/%m/%Y'

            # prepare to update the ips status
            ips_status = []
            if row["Custom field (IPS Status)"] != None and row["Custom field (IPS Status)"] != "":
                ips_status.append({"value": row["Custom field (IPS Status)"]})

            # prepare to update the ips start
            ips_start = None
            if row["Custom field (IPS Start)"] != None and row["Custom field (IPS Start)"] != "":
                ips_start = datetime.strptime(row["Custom field (IPS Start)"], date_format)

            # prepare to update the ips finish
            ips_finish = None
            if row["Custom field (IPS Finish)"] != None and row["Custom field (IPS Finish)"] != "":
                ips_finish = datetime.strptime(row["Custom field (IPS Finish)"], date_format)

            # update the jira issue
            issue.update(fields={
                "summary"           :row["Summary"],
                "customfield_14900" :ips_status,
                "customfield_14819" :ips_start.strftime("%Y-%m-%d"), # customfield_14819 - IPS Start
                "customfield_14820" :ips_finish.strftime("%Y-%m-%d") # customfield_14820 - IPS Finish
            })

            # add comment to the issue to indicate an IPS Sync took place
            jira.add_comment(issue, row["Comment"])
    else:
        print("NO DELTAS detected !")

    
