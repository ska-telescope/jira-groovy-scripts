# Import the 'MiroApi' object
from miro_api import MiroApi
from miro_api.exceptions import NotFoundException
from miro_api.exceptions import BadRequestException
from miro_api.models.card_update_request import CardUpdateRequest
from miro_api.models.update_card_style import UpdateCardStyle
from miro_api.models.card_style import CardStyle
from miro_api.models.card_data import CardData
from miro_api.models.geometry import Geometry

from jira import JIRA

from pydantic import BaseModel, ValidationError

import sys, getopt
import numpy as np
import getpass      #password input
import re           #regular expressions

def retrieveJiraDetails(username,password):

    server = "https://jira.skatelescope.org"
    auth_inf = (username,password)
    try:
        jira = JIRA(server=server,basic_auth=auth_inf)
    except:
        print("ERROR: Jira authentication failed. Have you provided the correct username and password?")
        return


    query = "project in (SP,SS) AND issuetype not in (Epic) AND (filter='SAFe - ActivePI' or filter='SAFe-NextPI') order by key ASC"
    fields="key,summary,issuetype,priority,customfield_14100,customfield_16916,customfield_15707"  # 16916 = Capabilities_MIRO  15707 = Goals_MIRO 14100 = Teams_MIRO
    print(('\n\r Feature query to database \n\r\n\r'+ query +'\n\r'))
    features = jira.search_issues(query,maxResults=None,fields=fields)
    print(str(len(features))+" Cached Feature Tickets")

    query = "project in (SDR, SPO, ROAM, REL, TPO) AND (filter='SAFe - ActivePI' or filter='SAFe-NextPI') OR (project=SKB and status not in (Discarded, Done)) order by key ASC"
    print(('\n\r All other relevant issues query to database \n\r\n\r'+ query +'\n\r'))
    other = jira.search_issues(query,maxResults=None,fields=fields) 

    print(str(len(other))+" Cached Other Tickets")
    return features + other


def colourise(board_id, frame_name, theme, priorityDict, keyDict, teamDict, capDict, goalDict):

    # Create a new instance of the 'MiroApi' object,
    # and pass the OAuth access token as a parameter
    api = MiroApi('eyJtaXJvLm9yaWdpbiI6ImV1MDEifQ_nAgXzlHiOmWaUXpaIv4xdh9fk2Y')

    # https://miroapp.github.io/api-clients/python/miro_api/api.html#MiroApiEndpoints.get_specific_board
    board = api.get_specific_board(board_id=board_id)

    #for board in boards:
    #    print(str(board.id) + str(board.name))
    frame_id = ''

    # Find the specific frame id based on the name
    if frame_name != 'ALL':
        # Get all frames on the board
        frames = list(api.get_all_items(board_id=board_id,type='frame'))  

        # For each frame item
        for frame in frames:
            if str(frame.data.actual_instance.title) == frame_name:
                frame_id = frame.id
                print("Found frame " + str(frame.data.actual_instance.title) + " with id " + frame_id)
                break
            
    if frame_id != '':
        # Get all card items in the frame
        items = list(api.get_all_items_within_frame(board_id=board_id,parent_item_id=frame_id))
        print(str(len(list(items))) + " Miro cards in the frame " + frame_name + " on board " + board.name)

    else:
         # Get all card items on the board
        items = list(api.get_all_items(board_id=board_id,type='card'))
        print(str(len(list(items))) + " Miro cards on the board " + board.name)

    # For each card item
    for item in items:

        if item.type == 'card':

            if item.data is None:
                continue

            try:
                print("About to get_card_item "+str(item.id))
                card = api.get_card_item(board_id=board_id, item_id=item.id)

                if card is not None:

                    if card.data is None:
                        continue
                    
                    card_title = str(card.data.title).replace("&amp;","&")
                    card_title = str(card_title).replace("&#43;","+")
                    
                    print("Found card "+card_title)

                    card_style = UpdateCardStyle()
                    card_style.card_theme = "<not set>"

                    # Priority theme sets High = red, Medium = Amber, Low = Blue
                    if theme == 'PRIORITY':
                        priority = priorityDict.get(card_title)

                        if priority is not None:
                            print("Found Priority "+str(priority))
                
                            if priority == 'HIGH' or priority == 'MUST HAVE':
                                card_style.card_theme = "#F24726" #red
                                print("Updating card to red")
                            elif priority == 'MEDIUM' or priority == 'SHOULD HAVE':
                                card_style.card_theme = "#FAC710" #yellow
                                print("Updating card to yellow")
                            elif priority == 'LOW' or priority == 'COULD HAVE':
                                card_style.card_theme = "#2D9BF0" #blue 
                                print("Updating card to blue")
                            elif priority == "WON'T HAVE (THIS TIME)":
                                card_style.card_theme = "#808080" #grey 
                                print("Updating card to blue")
                            elif priority == 'NOT ASSIGNED':
                                card_style.card_theme = "#E6E6E6" #light gray
                                print("Updating card to light gray")
                    
                    elif theme == 'ISSUETYPE':
                        issuetype = keyDict.get(card_title)

                        if issuetype is not None:
                            if str(issuetype)[:4] == 'SDR-' or str(issuetype)[:4] == 'SKB-' or str(issuetype)[:5] == 'ROAM-' :
                                print("Found Dependency / Bug / Risk "+str(issuetype))
                                card_style.card_theme = "#F24726" #red
                                print("Updating card to red")
                            elif str(issuetype)[:4] == 'SPO-':
                                colour = goalDict.get(card_title)

                                if colour is not None:
                                    print("Found Linked Objective "+str(keyDict.get(card_title)))
                                    card_style.card_theme = "#2684FF" #Blue
                                    print("Updating card to Blue")
                                else:
                                    print("Found Unlinked Objective "+str(keyDict.get(card_title)))
                                    card_style.card_theme = "#BED4F6" #Light Blue
                                    print("Updating card to Light Blue")

                            elif str(issuetype)[:4] == 'REL-':
                                print("Found Release "+str(keyDict.get(card_title)))
                                card_style.card_theme = "#0CA789" #dark green
                                print("Updating card to dark green")
                    
                    elif theme == 'PULLED':
                        team = teamDict.get(card_title)
                        issuetype = keyDict.get(card_title)

                        if team is not None and issuetype is not None:
                            if str(team) != '' and str(team) != 'None' and str(issuetype)[:3] == 'SP-':
                                print("Found pulled Feature by Team "+str(team))
                                card_style.card_theme = "#808080" #gray
                                print("Updating card to gray")

                    elif theme == 'CAPABILITY':
                        capability = capDict.get(card_title)

                        if capability is not None:
                            if str(capability) != '' and str(capability) != 'None':
                                print("Found Capability relationship "+str(capability))
                                card_style.card_theme = "#DA0063" #magenta
                                print("Updating card to magenta")

                    elif theme == 'GOAL':
                        colour = goalDict.get(card_title)

                        if colour is not None:
                            print("Found Goal mapping colour")
                            card_style.card_theme = colour
                            print("Updating card to "+colour)
                        else:
                            card_style.card_theme = '#343C4C' # black
                            print("Updating card to black")

                    if card_style.card_theme != "<not set>":        
                        card_update = CardUpdateRequest()   
                        card_update.style = card_style
                        
                        api.update_card_item(board_id=board_id, item_id=item.id,card_update_request=card_update)
                        print("Updated update_card_item "+str(item.id)+chr(10))
                    else:
                        print("Skipping card item "+str(item.id)+chr(10))

            except NotFoundException as e:
                print("Card not found exception "+str(item))
                print("Skipping "+str(item.id)+chr(10))
                continue

            except BadRequestException as e:
                print("Bad Request exception "+str(item))
                print("Skipping "+card_title+chr(10))   
                print(e)
                continue

            except ValidationError as e:
                print("ValidationError exception "+str(item))
                print("Skipping "+card_title+chr(10))   
                print(e)
                continue

            except Exception as e:
                print(type(e))    # the exception type
                print("Skipping "+str(item.id)+chr(10))
                continue
        

def main(argv):
    ##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################
    username = '' 				# default value if not given in command line
    password = 'eUuXJyPtRX1yEGFwh6RjdfFHESf41yW6Ax6efu'				# default value if not given in command line
    board_id = 'uXjVK6qyNUc='   # default value if not given in command line (Program of Program - Next PI)
    frame    = 'ALL'            # default value if not given in command line
    theme    = 'PRIORITY'       # default value for theme is Priority

    try:
        opts, args = getopt.getopt(sys.argv[1:],"hu:p:b:t:",["help","username","password","board","theme"])
    except getopt.GetoptError:
	    print('Usage: miro_colouriser.py -h <help> -u <username> -p <password> -b board -t theme')
        
    for ou, arg in opts:
        if ou in ("-h","--help"):
            print('\b\n Usage: miro_colouriser.py   -h <help> -b <board> -t <theme>\b\n' + \
            '\b\n [-u] jira username to access active and next PI jira ticket details'+\
			'\b\n [-p] jira password to access active and next PI jira ticket details'+\
            '\b\n [-b] Miro Board ID to colourise (found via a web browser in the URL) e.g. uXjVK6qyNUc=' + \
            '\b\n [-t] PRIORITY|ISSUETYPE|PULLED|CAPABILITY|GOAL (Default=PRIORITY)' + \
            '\b\n' + \
            '\b\n Themes Explained' + \
            '\b\n PRIORITY      High=Red, Medium=Amber, Low=Blue, Not Assigned=Light Gray' + \
            '\b\n ISSUETYPE     Objective=Blue, Risk=Red, Dependency=Red, Bug=Red, Release=Dark Green' + \
            '\b\n CAPABILITY    SP issue linked to SS Capability=Magenta' + \
            '\b\n PULLED        SP issue Agile Teams<>None=Gray' + \
            '\b\n GOAL          Each Goal is assigned a colour together with related Objectives, multiple goal links are coloured magenta')
            sys.exit()
        elif ou in ("-u", "--username"):
            username = arg
        elif ou in ("-p", "--password"):
            password = arg
        elif ou in ("-b", "--board"):
            board_id = arg
        elif ou in ("-t", "--theme"):
            theme = arg.upper()
        
    return [username,password,board_id,frame,theme]

def xstr(s): # this is just to handle converting lists to strings when there might be some empty values
	if s is None:
		return ''
	return str(s)

#################################################################################################

if __name__ == "__main__":

    sy = main(sys.argv[2:])

    if str(sy[0])=='':
   	    # prompt for Jira username
        username = input("Please enter your Jira username: ")
    else:
        username = str(sy[0])

    if str(sy[1])=='':
        # prompt for Jira password
        password = getpass.getpass(prompt="Please enter your Jira password: ")
    else:
        password = str(sy[1])

    print(' Board ID: %s' %str(sy[2]))
    print(' Frame: %s' %str(sy[3]))
    print(' Theme: %s' %str(sy[4])) 

    # retrieve active PI Jira tickets directly from Jira...to link up to the Miro Jira Cards
    issues = retrieveJiraDetails(username, password)      

    priorityDict = {}
    keyDict = {}
    teamDict = {}
    capDict = {}
    goalDict = {}
    goalKeyDict = {}

    # Initialise a colour map
    colours = [
        '#FEF445', #light yellow
        '#FAC710', #yellow
        '#F24726', #red
        '#CEE741', #light green
        '#8FD14F', #green
        '#DA0063', #magenta
        '#12CDD4', #cyan
        '#652CB3', #purple
        '#2D9BF0', #blue
        '#414BB2', #dark blue
        '#9510AC', #violet
        '#08C6FF', #08C6FF
        '#97A8FE', #97A8FE
        '#D7F8FD', #D7F8FD
        '#E1B60E', #E1B60E
        '#FC6CE7'  #pink
    ]
    goalCount = 0
    print("Length of goal colour map "+str(len(colours)))

    # Iterate through all issues returned by the Jira queries
    # Initialise dictionary mappings for miro card titles to jira field values
    for i in range(len(issues)):
        try:
            issue_key       = str(issues[i].key).upper()
            issue_summary   = str(issues[i].fields.summary)
            issue_type      = str(issues[i].fields.issuetype).upper()
            issue_teams     = xstr(issues[i].fields.customfield_14100).upper()

            keyDict[issue_summary] = issue_key
            teamDict[issue_summary] = issue_teams 

            # We want to set goal based colours for SPO, SS, SP, TPO tickets
            if issue_key[:3] == 'SP-' or issue_key[:3] == 'SS-' or issue_key[:4] == 'SPO-':
                issue_goals     = xstr(issues[i].fields.customfield_15707).upper()
                goalKey = issue_goals

                # if the issue is linked to a goal i.e. != ''
                if goalKey != '':

                    # find out how many goals the issue is linked to
                    goalLinks = goalKey.count("MID") + goalKey.count("LOW") + goalKey.count("OBS") + goalKey.count("SPO")
                    if goalLinks > 1:
                        goalKey = "MULTIPLE"

                    # if we have not yet encountered this goal, then we need to pull a colour from the colour map using a colour index
                    if goalKeyDict.get(goalKey) is None:
                        print("Adding Goal Key to Goal Key Dict "+goalKey+" with colour index "+str(goalCount % len(colours)))
                       
                        # Override with magenta for issues that link to multiple goals
                        if goalKey == "MULTIPLE":
                            goalKeyDict[goalKey] = '#DA0063' #magenta
                        else:
                            goalKeyDict[goalKey] = colours[goalCount % len(colours)]
                        goalCount = goalCount+1

                    goalDict[issue_summary] = goalKeyDict[goalKey]    
                    
            # We want to set priority based colours for SP, SS, SKB tickets
            if issue_key[:3] == 'SP-' or issue_key[:3] == 'SS-' or issue_key[:4] == 'SKB-':
                issue_priority = str(issues[i].fields.priority).upper()
                priorityDict[issue_summary] = issue_priority
            
            # We want to set capability based colours for SP tickets
            if issue_key[:3] == 'SP-':
                issue_capabilities = xstr(issues[i].fields.customfield_16916).upper()
                capDict[issue_summary] = issue_capabilities

        except Exception as e:
            print('Exception with '+issue_key)
            print(e)
            continue

    print("Number of goals found "+str(goalCount))

     # Map Goal Tickets to their allocated colours
    for i in range(len(issues)):
        try:

            issue_key       = str(issues[i].key)
            issue_summary   = str(issues[i].fields.summary)
            issue_type      = str(issues[i].fields.issuetype).upper()

            if issue_type == 'GOAL':
                print('Found Goal '+ issue_key + " " + issue_type + " " + issue_summary)

                # look for the goal key in the Summary of the goal issue
                x = re.search("Mid G[0-9]+|Low G[0-9]+|Obs G[0-9]+", issue_summary, re.IGNORECASE)

                # if we did'nt find the goal key in the Summary, then the goal key must be the goal issue key
                if x is None:
                    if goalKeyDict.get(issue_key) is None:
                        print("Could not find colour key for goal "+issue_key + " " + issue_summary)
                    else:
                        goalDict[issue_summary] = goalKeyDict.get(issue_key)
                        print("Setting goal key "+ issue_summary + " to " + goalKeyDict.get(issue_key))   
                else:
                    # extract the matched goal key from the issue summary 
                    goal = x.group().upper()

                    # find the mapped colour for the goal key
                    if goalKeyDict.get(goal) is None:
                        print("Could not find colour map entry for goal "+goal)
                    else:
                        goalDict[issue_summary] = goalKeyDict.get(goal)
                        print("Setting goal key "+ issue_summary + " to " + goalKeyDict.get(goal))  
                    

        except Exception as e:
            print('Exception with '+issue_key)
            print(e)
            continue

    colourise(str(sy[2]), str(sy[3]), str(sy[4]), priorityDict, keyDict, teamDict, capDict, goalDict)