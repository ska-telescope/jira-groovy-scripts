# Import selenium tools
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.common.exceptions import ElementNotInteractableException

# Import the Miro Api
from miro_api import MiroApi
from miro_api.exceptions import NotFoundException
from miro_api.exceptions import BadRequestException
from miro_api.models.board_changes import BoardChanges
from miro_api.models.board_with_links import BoardWithLinks
from miro_api.models.geometry import Geometry

import time
from datetime import datetime
import sys, getopt
import numpy as np
import re

# Shows a red dot where the cursor moves
cursor_script = '''
var cursor = document.createElement('div');
cursor.style.position = 'absolute';
cursor.style.zIndex = '9999';
cursor.style.width = '10px';
cursor.style.height = '10px';
cursor.style.borderRadius = '50%';
cursor.style.backgroundColor = 'red';
cursor.style.pointerEvents = 'none';
document.body.appendChild(cursor);

document.addEventListener('mousemove', function(e) {
  cursor.style.left = e.pageX - 5 + 'px';
  cursor.style.top = e.pageY - 5 + 'px';
});
'''

# dictionary of board ids and last sync times populated whilst updating planner gadgets and used
# to set a board description to show when last the Planner Sync app visited that board
board_syncs = {}

# SKAO Team and Org IDs
SKAO_TEAM_ID = '3074457347197154901'
SKAO_ORG_ID = '3074457354731830733'

sync_hits = 0
sync_misses = 0

# retrieve a list of all planner gadgets on a spacified miro board
def get_planner_gadgets(api, board_id=None):

    # we need an api to get planners !
    if api == None:
        return None

    # we need to build up a list of boards to visit and planner gadgets on these boards
    board_ids = []  # list of board ids to visit
    planners = []   # list of planner gadget urls 

    # if a specific board id was provided
    if board_id != None:
        # add it to the board ids list
        board_ids.append(board_id)
    else: # find a list of boards to update (those containing PlannerSync in their Board Description)
        
        # get all boards in team SKAO
        boards = list(api.get_all_boards(team_id=SKAO_TEAM_ID))

        # find the subset of boards containing "PlannerSync" in their Description
        # add them to the board_ids list
        for i in range(0,len(boards)):

            if boards[i].description.upper().find("PLANNERSYNC") >= 0:
                print("Found board to sync planners on..."+boards[i].name)
                board_ids.append(boards[i].id)

    # for each board found to contain "PlannerSync" in their Description
    for i in range(0,len(board_ids)):

        # https://miroapp.github.io/api-clients/python/miro_api/api.html#MiroApiEndpoints.get_specific_board
        board = api.get_specific_board(board_id=board_ids[i])

        # Get all card items on the board
        items = list(api.get_all_items(board_id=board_ids[i]))
        print("Searching through "+str(len(list(items))) + " items for planner gadgets on board: " + board.name)

        # For each item on a board
        for item in items:

            # is the item a planner gadget
            if item.type == 'pipmatrix':
                url = "https://miro.com/app/board/"+board_ids[i]+"/?moveToWidget="+str(item.id)+"&cot=14"
                # record the planner url in the planners list
                planners.append(url)
                print("Found planner gadget: "+url)

    return planners

# initialise a selium driver session
# login to Miro and Jira using the DevPortal-Services user
def get_miro_session(mode='headless',password=''):

    # sets "headless" mode is chosen i.e. does not show the browser
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    
    if mode == 'headless':    
        options.add_argument('--headless')
    
    # Create a new instance of the Chrome driver
    driver = webdriver.Chrome(options)

    #Sets a "sticky" timeout to implicitly wait for an element to be found, or a command to complete. 
    # This method only needs to be called one time per session
    driver.implicitly_wait(10) # seconds

    # login to miro to start loading all the details...
    driver.get("https://miro.com/sso/login/")
    print("Loading "+driver.current_url)

    time.sleep(5) 

    try:

        # select no SSO
        no_sso = driver.find_element(By.XPATH,"//a[@data-testid='mr-link-without-sso-1']")
        no_sso.click()

        time.sleep(5) 

        # login to Miro
        email = driver.find_element(By.XPATH,"//*[@id='email']")
        email.send_keys("jiraserviceuser@skatelescope.org")
        print("Populated email...")

        cookies = driver.find_element(By.XPATH,"//button[@id='onetrust-accept-btn-handler']")
        cookies.click()
        print("Accepted all cookies...")
        
        pword = driver.find_element(By.CSS_SELECTOR,"#password") #password
        # password not stored in the code !
        pword.send_keys(password)
        print("Populated password...")
        
        # click the signin button
        continueButton = driver.find_element(By.XPATH,"//button[@data-testid='mr-form-login-btn-signin-1']")
        continueButton.click()
        print("Continue...")
        
    except NoSuchElementException as e:

        print("No such element exception...trying again "+str(e))

        email = driver.find_element(By.XPATH,"//*[@id='email']")
        email.send_keys("jiraserviceuser@skatelescope.org")
        print("Populated email...")

        pword = driver.find_element(By.CSS_SELECTOR,"#password") #password
        # password not stored in the code !
        pword.send_keys(password)
        print("Populated password...")
        
        # click the signin button
        continueButton = driver.find_element(By.XPATH,"//button[@data-testid='mr-form-login-btn-signin-1']")
        continueButton.click()
        print("Continue...")

    time.sleep(3) 
        
    miro_handle = driver.current_window_handle

    # open another tab in chrome
    driver.execute_script("window.open('');")

    # suspend the processing thread for 3 seconds
    time.sleep(3) 

    # Switch to the new tab and load jira login 
    # needed to authenticate to jira to update the planner frames
    driver.switch_to.window(driver.window_handles[1])
    driver.get("https://jira.skatelescope.org/login.jsp")
    print("Loading "+driver.current_url)

    # login to Jira
    username = driver.find_element(By.XPATH,"//*[@id='login-form-username']")
    username.send_keys("ServiceUser")
    print("Populated username...")
    
    pword = driver.find_element(By.XPATH,"//*[@id='login-form-password']")
    # password not stored in the code !
    pword.send_keys(password)
    print("Populated password...")
    # click the submit form button
    login = driver.find_element(By.XPATH,"//*[@id='login-form-submit']")
    login.click()
    print("Continue...")

    # switch back to the Miro chrome tab
    driver.switch_to.window(miro_handle)
    return driver

# updates the miro board descriptions to contains the last planner sync date and time dd-MMM-yyyy HH:mm:ss
def update_board_descs(api):

    # for each board that was synced
    # key = board id, value = datetime is was last synced
    for key, value in board_syncs.items():

        # get the miro board object
        board = api.get_specific_board(board_id=key)

        # get ready to update the miro board object
        board_changes = BoardChanges()
        board_changes.name = board.name
        board_changes.description = value

        # integrate the PlannerSync date time into the board description if there was existing content
        if board.description != None:
            # look for PlannerSync text (and/or datetime) in the board description
            x = re.search(r'PlannerSync[ed]* [0-9]{1,}-[\D]{3}-[0-9]{4} [0-9]{1,}:[0-9]{2}|PlannerSync[ed]*', board.description)
            # integrate the latest datetime stamp into the existing board description
            if len(x.group()) > 0:
                board_changes.description = (board.description[0:x.start()] + value + board.description[x.end():])[0:299]

        # update the board
        board = api.update_board(board_id=key,board_changes=board_changes)
        print("Updated Board "+board.name+" with key "+key+" with changes "+board_changes.description)

    # clear the board syncs dictionary  
    board_syncs.clear()

# sync a single planner gadget specified by the url, using the miro api and selenium driver
def sync_planner(api, driver, url):

    global sync_hits
    global sync_misses
    
    # Navigate to the Miro planner gadget given by its url
    driver.get(url)

    # Extract board id and item id from URL
    board_id = re.search(r'board/.+/', url).group()[6:-1]
    item_id  = re.search(r'moveToWidget=.+&', url).group()[13:-1]

    # record current date time (to update the board description later)
    now = datetime.now()
    print(str(now)+" Looking for planner gadget at "+url)

    # shorten how long we will wait for if the mouse click on the planner hits a jira ticket instead of the planner gadget
    driver.implicitly_wait(0) # seconds

    # suspend processing for 15 seconds to load the url
    time.sleep(15)

    # offset from the top left chrome window
    # this is where we start looking for the planner gadget
    x = 900; y = 400

     # move mouse to the planner gadget and click
    action = ActionBuilder(driver)
    driver.execute_script(cursor_script)
    action.pointer_action.move_to_location(x, y)
    action.pointer_action.click()
    action.perform()

    # we are going to try to find the planner gadget 10 times in total
    for i in range(10):
        # refresh our sync date time
        now = datetime.now()

        try:
            # try to find the sync button on the planner gadget 
            element = driver.find_element(By.CSS_SELECTOR,"#pipmatrix-sync")
            print(str(now)+" Syncing planner gadget at "+url)
            print("location:", element.location)
            print("size", element.size)
            
            # click the sync button
            element.click()

            # suspect processing for 3 seconds to do the sync
            print(str(now)+" Waiting for 3 seconds to complete sync")
            time.sleep(3)
            # record the fact that we sync'ed this planner
            board_syncs.update({board_id:"PlannerSync "+now.strftime('%d-%b-%Y %H:%M')})
            sync_hits+=1
            break

        # if the HTML element is no longer on the page...
        except StaleElementReferenceException:
            print("Stale Element Reference Exception: Aborting planner sync for "+url)
            sync_misses+=1
            break

        # if we did not find the sync button, move the mouse and try again
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            print(str(now)+" Attempt "+str(i)+": Did not find the planner gadget at x="+str(x)+" y="+str(y))
            # move the mouse to search for the planner gadget...
            if i < 6:
                if (i%2) == 0:
                    y=y+50 # move the mouse downwards
                else: 
                    x=x+50 # move the mouse to the right
            elif i == 6:
                x = 500; y = 400 # reset and start going upwards and left
            elif i >= 6 and i < 9:
                x = x - 50 # move the mouse to the left
                y = y - 50 # move the mouse upwards
            elif i >= 9:
                print("Giving up on planner gadget at "+url)
                sync_misses+=1
                break
           
            # try again
            action.pointer_action.move_to_location(x, y)
            action.pointer_action.click()
            action.perform()

        # if the HTML element is not interactable...
        except ElementNotInteractableException:
            print("Element Not Interactable Exception: Aborting planner sync for "+url)
            sync_misses+=1
            break
    

def main(argv):
    ##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################
    token    = ''           # must be provided via the command line
    board_id = None         # if None, then planner sync will look for all boards that have PlannerSync in the Description
    mode     = 'headless'   # headless = do not show the browser while executing, show=show the browser
    password = ''           # must be provided via the command line
    cache    = False        # use cached list of planners to sync

    try:
        opts, args = getopt.getopt(sys.argv[1:],"ht:b:s:p:c:",["help","token","board", "show", "password", "cache"])
    except getopt.GetoptError:
	    print('Usage: miro_colouriser.py -h <help> -t token -b board -s show -p <password> -c <cache>')
        
    for ou, arg in opts:
        if ou in ("-h","--help"):
            print('\b\n Usage: miro_planners.py   -h <help> -t <token> -b <board> -s show\b\n' + \
            '\b\n [-t] Token to access the miro api' + \
            '\b\n [-b] Miro Board ID to find planners (found via a web browser in the URL) e.g. uXjVK6qyNUc=' +\
            '\b\n [-s] Show the browser while the script executes' + \
            '\b\n [-c] True ...Use cached list of planners to sync read from file plannersync.dat')
            sys.exit()
        elif ou in ("-b", "--board"):
            board_id = arg
        elif ou in ("-t", "--token"):
            token = arg
        elif ou in ("-s", "--show"):
            mode = 'show'
        elif ou in ("-p", "--password"):
            password =  arg
        elif ou in ("-c", "--cache"):
            cache = True
        
    return [token, board_id, mode, password, cache]

if __name__ == "__main__":

    sy = main(sys.argv[0:])

    print(' Board ID: %s' %str(sy[1]))
    print(' Show:     %s' %str(sy[2]))
    print(' Cache:    %s' %str(sy[4]))

    # Create a new instance of the 'MiroApi' object,
    # and pass the OAuth access token as a parameter
    api = MiroApi(str(sy[0]))

    # if we are using a cached list of planners to sync
    if sy[4]:
        with open("plannersync.dat", 'r') as f:
            planners = [line.rstrip('\n') for line in f]
    else:
        # get all planner gadgets that need a sync, passing board id if set
        planners = get_planner_gadgets(api, sy[1])

        # record planners to sync to a file 
        with open("plannersync.dat", 'w') as f:
            for planner in planners:
                f.write(planner + '\n')

        # terminate the program here, short and sweet !        
        exit(0)

    # login to miro & jira 
    driver = get_miro_session(str(sy[2]),str(sy[3]))
    
    # keep track of the length of the session and last board id
    start = datetime.now()
    last_board_id = ""

    # sync all identified planner gadgets
    for planner in planners:
        # Extract board id from URL
        board_id = re.search(r'board/.+/', planner).group()[6:-1]

        # flush latest sync date time to board descriptions if we have moved to a new board
        if board_id != last_board_id:
            print("Board: "+str(last_board_id)+" Hits: "+str(sync_hits)+" Misses: "+str(sync_misses))
            sync_hits=0;sync_misses=0
            update_board_descs(api)
            last_board_id = board_id
        
        sync_planner(api, driver, planner)

        duration_sec = (datetime.now() - start).total_seconds()

        # if we have been sync'ing for over an hour, refresh the driver session
        if duration_sec >= 3600:  
            # close existing driver session
            driver.close()
            # start up a new driver session
            driver = get_miro_session(str(sy[2]),str(sy[3]))
            # keep track of the length of the session
            start = datetime.now()

    # flush remaining sync date times to board descriptions
    update_board_descs(api)

    # Close the browser window
    driver.close()
