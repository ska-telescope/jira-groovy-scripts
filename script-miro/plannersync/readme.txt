Date: 7 Nov 2024
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-miro/plannersync
Server:   risk-register-reporting.ad.skatelescope.org

This application logs into Miro and Jira, looks for all boards that have "PlannerSync" in their board description, and syncs all planner gadgets on these boards.

A Jira login is required to authenticate to the Jira server.

The planner sync application produces a cached list of all planner gadgets to sync, stored in a file called plannersync.dat.
The cached list of gadgets is then used to perform the sync.

The cache (file) can be refreshed by running the planner sync without the -c True caching command line parmeter.

Run the following command to see command line parameters. 
python plannersync.py --help 

This application is scheduled to run every 4 hours (planner sync).
This application is scheduled to run every 24 hours (cache refresh).

See schedule by running this command:

schtasks/query /tn miro_plannersync
schtasks/query /tn miro_plannercache

schtasks /create /tn plannersync /tr c:\gitlab\jira-groovy-scripts\script-miro\plannersync\plannersync.bat /sc HOURLY /mo 4 /ru "r.brederode" /st 11:00
schtasks /create /tn plannercache /tr c:\gitlab\jira-groovy-scripts\script-miro\plannersync\plannercache.bat /sc DAILY /mo 1 /ru "r.brederode" /st 02:00



