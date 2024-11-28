Date: 7 Nov 2024
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-alim
Server:   risk-register-reporting.ad.skatelescope.org

This application logs into Alim, runs reports and downloads resultant csv files:
- Documents
- Physical Items
- ECPs
- Responsibilities
- Contracts
- Docs Changing

It interfaces with the EMS API to download a Bill of Materials (BOM).

It pushes all Alim content to:
- Alim Sync google sheet
- Alim-Jira Sync google sheet
- Alim Information Sync google sheet

It reads PBS issues from Jira, and pushes them to the Alim-Jira Sync sheet. 
The sheet automatically performs a comparison of Alim and Jira data, and produces a delta (difference report)
The deltas are read from the google sheet, and applied to the Jira system 

Run the following command to see command line parameters. 
python alim-sync.py --help 

This application is scheduled to run every hour.

See schedule by running this command:

schtasks/query /tn alim_sync
schtasks /create /tn alim_sync /tr c:\gitlab\jira-groovy-scripts\script-alim\alim_sync.bat /sc HOURLY /mo 1 /ru "r.brederode" /st 11:00



