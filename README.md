# jira-groovy-scripts

Jira scripts used to configure our SAFe(r) implementation. 

The Script Runner plugin is used to execute those in particular contexts. 

SKA Risk Register Scripts
=========================

python ReportData.py 

Does not take any command line arguments, but will prompt for input of a Jira username and password.
Requires wbs.csv file to be located in ../jira-database-files/wbs.csv
wbs.csv provides the mapping of wbs codes to descriptions

ReportData.py produces a Risk Report Data excel sheet populated with risk and mitigation data.


python MonteCarlo.py -n 8000 -e 0 -s ALL -o 0

Usage: MonteCarlo.py  -h <help> -n <num_trials> -e <annual_escalation> -s <subsystem> -o <output_file>

[-n] number of trials is typically between 500 and 5000'+\
[-e] escalation factor as fraction; e.g., enter 0.03 for 3% annual escalation'+\
[-s] subsystem can be:  ALL, MID, LOW, OCS, PM'  +\
[-o] if value is 1 then output goes to file in working directory named text.txt; if value is 0 output goes to python pane

MonteCarlo reads the "locale" to determine the reporting currency. 

Setup of Environment
====================
On a Mac terminal session, the following steps were followed to setup the environment:
1. Installed Brew as per https://stackoverflow.com/questions/20381128/how-to-install-homebrew-on-os-x
2. Installed PyEnv using "brew install pyenv"
3. Install Python 3 using "pyenv install 3.9.0"
4. Install zlib using "brew install zlib"
5. Install zlib2 using "brew install bzip2"
6. Install "wheel" and "pandas" using "pip install wheel" and "Pip install pandas"
7. Install openpyxl using "pip install openpyxl"
8. Install jira using "Pip install jira"
