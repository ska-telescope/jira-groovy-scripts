Date: 13 Jan 2025
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-p6
Server:   risk-register-reporting.ad.skatelescope.org

This application logs into Primavera, opens the SKAO project and downloads all activities in a csv file using a particular view (Ray's View - Do not edit)


It pushes all Activities to:
- Primavera P6 - All Activities Export google sheet

It reads issues from Jira that have an Activity ID, and pushes them to the Jira Import tab. 
The sheet automatically performs a comparison of P6 and Jira data, and produces a delta (difference report)
The deltas are read from the google sheet, and applied to the Jira system 

Run the following command to see command line parameters. 
python p6-sync.py --help 

This application is scheduled to run every day.

See schedule by running this command:

schtasks/query /tn p6_sync
schtasks /create /tn p6_sync /tr c:\gitlab\jira-groovy-scripts\script-p6\p6_sync.bat /sc DAILY /mo 1 /ru "r.brederode" /st 06:00



