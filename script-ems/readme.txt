Date: 3 Oct 2024
Author: Ray Brederode

Location: gitlab SKAO/jira-groovy-scripts/script-ems

The productstructure application invokes a rest api exposed by the Engineering Management System (EMS) to retrieve the SKA Bill of Materials from Alim.
The BOM is then published to a Google sheet located here:

https://docs.google.com/spreadsheets/d/1bEPGIV_ubMjdn_2cKbStaPfc_QS7pvf29lhUvzfDkik/edit?gid=1516391082#gid=1516391082

The data from this sheet is used to synchronise Jira Components (PBS items), Jira PBS tickets as well as forwarding this information onto the System Engineering team:
- Richard Lord and Kaila Hall-Smith

The System Engineering team uses this information to produce Cameo diagrams. 
See Alim Information Sync google sheet that the SE team uses:
https://docs.google.com/spreadsheets/d/16v_nScc2MN2QuEfSuR57lj8jaC4a_krdDohHajOw1is/edit?gid=1201947163#gid=1201947163

