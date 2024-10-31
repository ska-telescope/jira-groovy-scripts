Date: 30 Oct 2024
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-miro/colouriser
Server:   risk-register-reporting.ad.skatelescope.org

This application applies colour themes to miro boards.

Run the following command to see command line parameters. 
python miro_colouriser.py --help 

This application is scheduled to run every hour.

See schedule by running this command:

schtasks/query /tn miro_colouriser /v /fo LIST

Create schedule by running this command
schtasks /create /tn miro_colouriser /tr c:\gitlab\jira-groovy-scripts\script-miro\colouriser\miro_colouriser.bat /sc HOURLY /mo 1 /ru "r.brederode" /st 11:00

Delete schedule by running this command
schtasks /delete /tn miro_colouriser