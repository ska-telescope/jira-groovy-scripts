Date: 13 Jan 2025
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-jama
Server:   risk-register-reporting.ad.skatelescope.org

This application does the following:
- Reads L0, L1, L2 requirements from Jama & uploads them to the Jama Requirements google sheet (L0,L1,L2 tabs)
- Reads L1, L2 requirements from Jira & uploads them them to the Jama Requirements google sheet (Jira L1s, Jira L2s tabs)
- Reads L1 and L2 Deltas from the Jama Requirements google sheet, and applies the deltas to Jira

Jama Requirements google sheet: https://docs.google.com/spreadsheets/d/19BbDwbxKszNVM7UQjcHYlZBmUFdOMDH16lQ0j4SMx3M/

Run the following command to see command line parameters. 
python jama_sync.py --help 

This application is scheduled to run every hour.

See schedule by running this command:

schtasks/query /tn jama_sync /v /fo LIST
schtasks /create /tn jama_sync /tr c:\gitlab\jira-groovy-scripts\script-jama\jama_sync.bat /sc HOURLY /mo 4 /ru "r.brederode" /st 12:00