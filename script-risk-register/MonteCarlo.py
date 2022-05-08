import sys, getopt
import numpy as np
import datetime
import locale
import platform
import time
import getpass
from random import randrange
from matplotlib import pyplot as plt
from matplotlib import ticker
from  matplotlib import pylab
from pylab import *
from jira import JIRA

def mybar(ax,x1,x2,y2):
	Xbars = [[0., .3],[.7,.4]]
	left,right = x1,x2
	bottom,top = 0.0,y2
##    ax.imshow(Xbars, interpolation='bicubic', cmap=cm.Blues,
##          extent=(left, right, bottom, top), alpha=1)
	return

# Format the date to the proper form of year, month, day
def format_date(x, pos=None):
#    return pl.num2date(x).strftime('%Y-%m-%d')
	 return pylab.num2date(x).strftime('%b, %Y')

# Use a sorting method of the "data" to find the total cost at a specified confidence level "breakfraction"
def percentage(data,breakfraction):
	breaknumber = int(breakfraction * len(data))
# data is a list of total costs for each iteration, sort from lowest cost to highest cost
	data.sort() # sorts input from lowest to highest value
	return data[breaknumber]

def xstr(s): # this is just to handle converting lists to strings when there might be some empty values
	if s is None:
		return ''
	return str(s)

def montecarlorisk(username,password,num_trials,annual_escalation,subsystem,output_file):
	## define output location; if variable output_file is true then output goes to test.txt in working directory
	fhold = sys.stdout
	if output_file:
		f = open('./test.txt', 'w')
		sys.stdout = f

	#########################################################################################
	###################### Some basic values ###############################
	#########################################################################################
	total_contingency = 230694.0  # total contingency in K EUR  TBD !!!!
	nyears = 7  ## number of years with construction activity
	date_start = "2021-07-01"
	date_end = "2028-07-31"
	date_commissioning_start =  "2028-08-01"
	date_base_year = "2021"
	date_year_start = "2021"
	date_year_end = "2028"
	annual_esc = 1.0 + annual_escalation  # convert annual fractional escalation to factor
	yer = ['2021','2022','2023','2024','2025','2026','2027','2028']


	final_totals_distribution = []
	#cost_lowest = np.zeros(1000)
	#cost_expected = np.zeros(1000)
	#cost_highest = np.zeros(1000)

	subsystem = subsystem.upper()
	if subsystem == 'ALL':
		fundingstring = " "
		projectname = "SKA"
	elif subsystem == 'MID':
		fundingstring = " AND component = 'MID' "
		projectname = 'MID'
	elif subsystem == 'LOW':
		fundingstring = " AND component = 'LOW' "
		projectname = 'LOW'
	elif subsystem == 'OCS':
		fundingstring = " AND component = 'OCS' "
		projectname = 'OCS'
	elif subsystem == 'PM':
		fundingstring = " AND component = 'PM' "
		projectname = 'PM'

	##############################################################################
	################### Simple escalation model
	##############################################################################
	escalate = array(10)
	sum = 0.0
	escalate = {}   # a dictionary
	escalate[date_base_year] = 1.0
	for jj in range(nyears):
		escalate[yer[jj+1]] = escalate[yer[jj]] * annual_esc
		sum += escalate[yer[jj+1]]
	escalate['dist_sum'] = sum/nyears

	server = "https://jira.skatelescope.org"
	auth_inf = (username,password)
	try:
		jira = JIRA(server=server,basic_auth=auth_inf)
	except:
		print("ERROR: Jira authentication failed. Have you provided the correct username and password?")
		return

	# AND (cf[12916] is EMPTY OR cf[12916] ='False') 

	query = "project=RM AND issuetype='RM-Risk' AND status in ('Active Risk/Opportunity','Subordinated') " + fundingstring + "ORDER BY cf[12933]"
	fields="components,summary,customfield_12926,customfield_12901,customfield_12905,customfield_12915,customfield_12933,customfield_12936,customfield_12938,description"
	print(('\n\r Query to database \n\r\n\r'+ query +'\n\r'))
	issues = jira.search_issues(query,maxResults=None,fields=fields)
	nrisks = len(issues)
	rows=[]

	mean_prob_lookup = {'2%':0.02,
						'5%':0.05,
						'10%':0.1,
						'25%':0.25,
						'50%':0.5,
						'80%':0.8}
	rows=[]
	for i in range(len(issues)):
		rows.append({'riskid':int(''.join([i for i in issues[i].key if i.isdigit()])),
					'projectsystem':xstr(issues[i].fields.components[0].name),
					'current_probability':xstr(issues[i].fields.customfield_12926), #map from 13200
					'current_expense_expected':(float(issues[i].fields.customfield_12901) if issues[i].fields.customfield_12901 else 0.0), #map from 13404
					'current_schedule_cost_expected':(float(issues[i].fields.customfield_12905) if issues[i].fields.customfield_12905 else 0.0), #map from 13606
					'meanprobability':mean_prob_lookup[issues[i].fields.customfield_12926.value], #map from 13200
					'total_cost':0.0,
					'obligationmodel':xstr(issues[i].fields.customfield_12915), #map from 13107
					'triggerdate':(datetime.datetime.strptime(issues[i].fields.customfield_12933,'%Y-%m-%d').date() if issues[i].fields.customfield_12933 else datetime.date(2000,1,1)), #map from 13108
					'randomtrigger':(int(issues[i].fields.customfield_12938) if issues[i].fields.customfield_12938 else 0), #map from 13110
					'risktitle':xstr(issues[i].fields.summary),
					'riskdescription':xstr(issues[i].fields.description),
					'randomperiod':xstr(issues[i].fields.customfield_12936) }) # map from 13111



	# setup lists
	nyears=[1 for i in range(nrisks)]
	riskheader = ['     ' for i in range(20000)]
	riskid=[] 							# issue.key
	projectsystem=[] 					# issue.fields.components
	current_probability=[] 				# issue.fields.customfield_12926
	current_expense_expected=[] 		# issue.fields.customfield_12901
	current_schedule_cost_expected=[] 	# issue.fields.customfield_12905
	meanprobability=[] 					# calculate from cf 12926
	total_cost=[] 						# issue.fields.customfield_12905 + issue.customfield_12901
	obligationmodel=[] 					# issue.fields.customfield_12915
	triggerdate=[] 						# issue.fields.customfield_12933
	randomtrigger=[] 					# issue.fields.customfield_12936 and issue.customfield_12938
	risktitle=[] 						# issue.fields.summary
	riskdescription = [] 				# issue.fields.description
	randomperiod = []

	## Rule 0  - Accept all risks, simple passthrough
	##    print "\n\r Rule 1 - Accept only risks that have total cost of more than €1M \n\r"
	##        print "\n\r Rule 2 - Accept only risks that have expected exposure of more that €200K \n\r"
	##        print "\n\r Rule 3 - Accept risks that pass Rule 1 OR Rule 2 \n\r"
	## Store the database values into arrays

	print('\n\r Summary of risks ordered by triggerdate \n\r\n\r')
	for ii in range(nrisks):
		lasttotalcost = (float(rows[ii]['current_expense_expected'])+float(rows[ii]['current_schedule_cost_expected']))

		##############################################################################
		################### Use simple model of escalation to convert to as-spent dollars
		##############################################################################

		if rows[ii]['obligationmodel'] == "trigger" :
			yr =  rows[ii]['triggerdate'].year
			yr = max(int(date_year_start),int(yr))
			yr = min(int(date_year_end),int(yr))
			lasttotalcost = lasttotalcost * escalate[str(yr)]
		else:
			lasttotalcost = lasttotalcost * escalate['dist_sum']

		##############################################################################

		if lasttotalcost >= 0.00:
			## print("\n\r Rule 0  - Accept all risks, simple passthrough \n\r")
			## Rule 1 - Accept only risks that have total cost of more than €1M
			##        if lasttotalcost >= 1000.00:
			## Rule 2 - Accept only risks that have expected exposure of more that €200K
			##        if float(rows[ii]['meanprobability'])*lasttotalcost >= 200.0:
			## Rule 3 - Accept risks that pass Rule 1 OR Rule 2
			##       if float(rows[ii]['meanprobability'])*lasttotalcost >= 200.0 or lasttotalcost >= 1000.00:
			riskid.append(rows[ii]['riskid'])
			projectsystem.append(rows[ii]['projectsystem'])
			current_probability.append(rows[ii]['current_probability'])
			current_expense_expected.append(rows[ii]['current_expense_expected'])
			current_schedule_cost_expected.append(rows[ii]['current_schedule_cost_expected'])
			meanprobability.append(float(rows[ii]['meanprobability']))
			obligationmodel.append(rows[ii]['obligationmodel'])
			triggerdate.append(rows[ii]['triggerdate'])
			randomtrigger.append(rows[ii]['randomtrigger'])
			risktitle.append(rows[ii]['risktitle'])
			riskdescription.append(rows[ii]['riskdescription'])
			total_cost.append(lasttotalcost)
			randomperiod.append(rows[ii]['randomperiod'])

			## Print formatted output
			print('{:>30} RM-{:4} {:>10}  {:>22} {:>5} [{:>8.2f} {:>8.2f}] {:>8.2f}   {:40} {:80}'.format(
					 rows[ii]['projectsystem'],
					 str(rows[ii]['riskid']),
					 str(rows[ii]['triggerdate']),
					 #rows[ii]['obligationmodel'][0:4],
					 rows[ii]['obligationmodel'],
					 #rows[ii]['randomtrigger'] % 1000,
					 rows[ii]['randomtrigger'],
					 lasttotalcost,
					 rows[ii]['meanprobability'],
					 float(rows[ii]['meanprobability'])*lasttotalcost,
					 str(rows[ii]['risktitle']),
					 str(rows[ii]['riskdescription']),
					 ))
		nrisks = len(riskid)
	##   Print risks ordered by riskid
	print(('\n\r Summary of {:>3} risks ordered by riskid \n\r\n\r'.format(str(nrisks))))
	hold_riskid,hold_projectsystem,hold_risktitle = (list(t) for t in zip(*sorted(zip(riskid,projectsystem,risktitle))))
	for ii in range(nrisks):
		print('{:>30} RM-{:3}   {:40}'.format( hold_projectsystem[ii],str(hold_riskid[ii]),hold_risktitle[ii]))

	## Print risk description ordered by totalcost
	print(('\n\r Summary of {:>3} risks ordered by totalcost \n\r\n\r'.format(str(nrisks))))
	hold_total_cost,hold_riskdescription,hold_projectsystem,hold_riskid,hold_meanprobability = (list(t) for t in zip(*sorted(zip(total_cost,riskdescription,projectsystem,riskid,meanprobability), reverse=True)))

	for ii in range(nrisks):
		print('{:>30} RM-{:3} €{:8,.7}K [{:<4}]   {:<100}'.format( hold_projectsystem[ii],str(hold_riskid[ii]),hold_total_cost[ii],hold_meanprobability[ii],hold_riskdescription[ii]))

	## Figure 4
	##  Interaction loop over risks. Also, plot fig 4 with the risk spend curve
	max_hold = 0.0
	fig4 = plt.figure(4)
	ax1 = fig4.add_subplot(111)
	###################################################################
	############ Begin main Monte Carlo iteration loop ################
	###################################################################
	for ii in range(num_trials):
		delta_this_iteration = []
		triggerdate_this_iteration = []
		projectsystem_this_iteration = []
		riskid_this_iteration = []
	###################################################################
	############ Random loop over each risk ################
	###################################################################
	##
	##  Each risk has a specified date of possible occurence.  A risk can occur at a specified trigger date;
	#   at some random time; or a risk may occur more than once over a specified range of dates.
	## Trigger case
		for jj in range(nrisks):
			if obligationmodel[jj] ==  "Trigger date":
				choice=np.random.uniform(0.0,1.0,1)
				if choice <= meanprobability[jj] :
					addit = float(total_cost[jj])
				else:
					addit = float(0.0)
				delta_this_iteration.append(addit)
				triggerdate_this_iteration.append(triggerdate[jj])
				projectsystem_this_iteration.append(projectsystem[jj])
				riskid_this_iteration.append(int(riskid[jj]))
			## Random case
			elif obligationmodel[jj] ==  "Random occurrence(s)":
				nrandom = randomtrigger[jj]
				#print("random risk; nrandom = "+str(nrandom))
				#periodcode = randomtrigger[jj] / 1000
				#print("random risk periodcode = "+str(periodcode))
				periodcode = 3

				if randomperiod[jj] == 'Construction only':
					periodcode = 1
				elif randomperiod[jj] == 'Commissioning only':
					periodcode = 2
				elif randomperiod[jj] == 'Both Construction and Commissioning':
					periodcode = 3
				date1 = date_start
				date2 = date_commissioning_start
				if periodcode == 1:             # random during construction only
					date1 = date_start
					date2 = date_commissioning_start
				elif periodcode == 2:           # random during commissioning only
					date1 = date_commissioning_start
					date2 = date_end
				elif periodcode == 3:           # random throughout project
					date1 = date_start
					date2 = date_end
				for kk in range(nrandom):
					stime = time.mktime(time.strptime(date1, '%Y-%m-%d'))
					etime = time.mktime(time.strptime(date2, '%Y-%m-%d'))
					ptime = stime + np.random.uniform(etime - stime)
					randomdate = datetime.date.fromtimestamp(int(ptime))
					#print(randomdate)
					choice = np.random.uniform(0.0,1.0)
					if choice <= meanprobability[jj] :
						addit = float(total_cost[jj])/float(nrandom)
					else:
						addit = float(0.0)
					delta_this_iteration.append(addit)
					triggerdate_this_iteration.append(randomdate)
					projectsystem_this_iteration.append(projectsystem[jj])
					riskid_this_iteration.append(int(riskid[jj]))
			## Distributed case
			elif obligationmodel[jj] ==  "Distributed occurrence":
				if ii == 0:  # only on first pass through will triggerdate always have the proper value
					#print ii,jj,triggerdate[jj],triggerdate[jj].year
					ny = max(triggerdate[jj].year - 2021,1)   # risk is distributed over this many years but must be at least 1
					nyears[jj] = min(ny,8)                  # must store the corect values of nyears for each distributed risk
				for kk in range(nyears[jj]):
					year = 2022 + kk  #kk starts at zero.  Don't include short period in 2021
					choice=np.random.uniform(0.0,1.0,1)
					if choice <= meanprobability[jj] :
						addit = float(total_cost[jj])/float(nyears[jj])
					else:
						addit = float(0.0)
					delta_this_iteration.append(addit)
					triggerdate_this_iteration.append(datetime.date(year,randrange(1,12),1))    # random month in year, always assign the first day of the month
					projectsystem_this_iteration.append(projectsystem[jj])
					riskid_this_iteration.append(int(riskid[jj]))
			else:
				sys.exit(" obligationmode not defined for risk "+str(projectsystem[jj]) + str(riskid[jj])+"  " +str(jj))
		###################################################################
		############    End short random loop over risk    ################
		###################################################################
		# Since random and distributed risks have been added the lists are no longer in date order.
		# Need to resort the two arrays by effective trigger dates using: list1, list2 = (list(t) for t in zip(*sorted(zip(list1, list2))))  - YIKES
		#print(riskid_this_iteration)
		triggerdate_this_iteration, delta_this_iteration,projectsystem_this_iteration, riskid_this_iteration = (list(t) for t in zip(*sorted(zip(triggerdate_this_iteration,delta_this_iteration,projectsystem_this_iteration,riskid_this_iteration))))
		#print(type(riskid_this_iteration),riskid_this_iteration)
		#print(" ")
		#print(delta_this_iteration)
		# Compute the running sum
		xx_this_iteration = np.cumsum(delta_this_iteration)
		len_xx = len(xx_this_iteration)
		###################################################################
		############# Some diagnostic output  #############################
		###################################################################
		nprintout = 5    # number of simulations with diagnostic output
		diagnostic_steps = num_trials / nprintout
		if ii % diagnostic_steps == 0:
			print(('\n\r\n\r\n\r Diagnostic output for iteration '+str(ii)+' \n\r'))
			for mm in range(len_xx):
				header = riskheader[riskid_this_iteration[mm]]
				line = [header,projectsystem_this_iteration[mm],riskid_this_iteration[mm],str(triggerdate_this_iteration[mm]),delta_this_iteration[mm],xx_this_iteration[mm]]
				print('{:>6}{:>30} RM-{:3} {:>15} {:12.1f} {:12.1f}'.format(*line))
				#print(line)
		# Store the grand totals
			# reserve the storage arrays on the first iteration
		if ii == 0:
			totals = np.zeros(len_xx)
			totals2 = np.zeros(len_xx)
			#print len(xx),len_xx,len(totals),len(totals2)
		totals += xx_this_iteration
		totals2 += xx_this_iteration * xx_this_iteration
		final_totals_distribution.append(xx_this_iteration[len_xx - 1]*0.001)  # Convert from K€ to M€
		## The step method plots the spend curve, plot only every 50th iteration line
		if ii%50 == 0:
			#print len(triggerdate),len(xx)
			#print(triggerdate)
			#print(" ")
			#print(xx)
			pylab.step(triggerdate_this_iteration,total_contingency - xx_this_iteration,where='post')  # plot the spend curve using step
			max_hold = max([max_hold,max(xx_this_iteration)])
		gca().xaxis.set_major_formatter(ticker.FuncFormatter(format_date))

	###################################################################
	###########    End Monte Carlo iteration loop       ###############
	###################################################################
	## Spend curve plot labeling
	dd1 = date2num(datetime.datetime.strptime('2021-07-01', "%Y-%m-%d").date())
	dd2 = date2num(datetime.datetime.strptime('2029-07-31', "%Y-%m-%d").date())
	yyy = 5.0 * ceil(total_contingency/5.0)
	ax1.set_ylim(0.0,yyy)
	ax1.set_xlim(dd1,dd2)
	gcf().autofmt_xdate()
	# Plot some extra bold lines in the spend curve plot
	mean = totals/num_trials
	variance = totals2/num_trials - mean*mean
	sigma = np.sqrt(variance)

	ax1.plot(triggerdate_this_iteration,total_contingency -mean ,linewidth=5.0,color='blue')
	ax1.plot(triggerdate_this_iteration,total_contingency -mean + sigma,linewidth=5.0,color='black')
	ax1.plot(triggerdate_this_iteration,total_contingency -mean - sigma,linewidth=5.0,color='black')
	#  Print tabular data
	#print "length of triggerdate",len(triggerdate_this_iteration),type(triggerdate_this_iteration)
	#print " mean ",len( mean ),type(mean)
	#print "length of  sigma",len( sigma),type(sigma)
	for mm in range(len(triggerdate_this_iteration)):
		line = [str(triggerdate_this_iteration[mm]),total_contingency-mean[mm],total_contingency-mean[mm]-sigma[mm],total_contingency-mean[mm]+sigma[mm]]
		print('{:>15} ,  {:12.1f},  {:12.1f},   {:12.1f}'.format(*line))
	#  Plot the contingency funding curve in as spent EUR
	if  subsystem == 'NSF':
		fundingdates = [datetime.date(2014,0o7,0o1),datetime.date(2014,10,0o1),datetime.date(2015,10,0o1),datetime.date(2016,10,0o1),datetime.date(2017,10,0o1),datetime.date(2018,10,0o1),datetime.date(2019,10,0o1),datetime.date(2020,10,0o1),datetime.date(2021,10,0o1)]
		fundinglevels = [2600.,13100.,23600.,34100,44600.,55100.,65600.,76100.]
		print(fundingdates)
		print(fundinglevels)
	#        pylab.step(fundingdates,fundinglevels,linewidth=5.0,color='red',where='post')
	##    ax1.set_ylim([0.0,80.])
	pylab.title('%s  Contingency spend curve in as-spent K-EUR'%projectname)
	ax1.set_xlabel('Date')
	ax1.set_ylabel('Contingency Balance (as-spent K€)')
	fig4.savefig('fig4.png')
	###################################################################
	###########    End of spend curve plot      ###############
	###################################################################
	#     Total probability weighted cost
	weightedcost = 0.0
	for kk in range(nrisks):
		weightedcost += total_cost[kk]*meanprobability[kk]
	weightedcost = locale.currency(weightedcost*0.001,grouping=True) # convert to M€
	##   weightedcost = weightedcost*.001
	#     Expected cost of risks from Monte Carlo
	expectedcost = locale.currency(mean[len_xx-1],grouping=True)
	##    expectedcost = mean[len_xx-1]
	#     Standard deviation of costs from Monte Carlo
	#deviationcost = sigma[nrisks-1]
	#     50,70,80,90,99% confidence level; output is formatted string
	hold50 = percentage(final_totals_distribution,0.5)
	cellbound50 = locale.currency(hold50,grouping=True)
	#    cellbound50 = hold50
	hold70 = percentage(final_totals_distribution,0.7)
	cellbound70 = locale.currency(hold70,grouping=True)
	#    cellbound70 = hold70
	hold80 =  percentage(final_totals_distribution,0.8)
	cellbound80 = locale.currency(hold80,grouping=True)
	#    cellbound80 = hold80
	hold90 =  percentage(final_totals_distribution,0.9)
	cellbound90 = locale.currency(hold90,grouping=True)
	#    cellbound90 = hold90
	hold99 =  percentage(final_totals_distribution,0.99)
	cellbound99 = locale.currency(hold99,grouping=True)
	#    cellbound99 = hold99
	#  Write the output
	print("\n\r Total number of iterations %d  " % num_trials)
	print("\n\r Total number of risks %d  " % nrisks)
	print("\n\r Probability weighted total cost of risks: "+ str(weightedcost)+"M")
	print("\n\r Cost at 50 percent confidence level: "+ str(cellbound50)+"M")
	print("\n\r Cost at 70 percent confidence level: "+ str(cellbound70)+"M")
	print("\n\r Cost at 80 percent confidence level: "+ str(cellbound80)+"M")
	print("\n\r Cost at 90 percent confidence level: "+ str(cellbound90)+"M")
	print("\n\r Cost at 99 percent confidence level: "+ str(cellbound99)+"M")
	## Prepare the data for plotting all plots except the spend curve (Figures 1, 2, and 3)
	final_totals_distribution.sort() # sorts input from lowest to highest value
	num_trials100 = num_trials/100.
	niter = list(range(num_trials))
	niter2 = [float(i)/num_trials for i in niter]
	niter3 = [100.-float(i)/num_trials100 for i in niter]
	ylim = 1000.0
	if(num_trials > 10000):
		 ylim = 1500.
	elif(num_trials <= 1000):
		 ylim = 500.
	##
	#######################################################################3
	#  Plotting package below for everything except spend curve
	#######################################################################3
	##                                                                            Figure 1
	##
	fig = plt.figure(1)
	ax = fig.add_subplot(111)
	ax.hist(final_totals_distribution,bins = 30)
	ax.set_ylim([0.0,ylim])
	xlim =  20. * (int(max(final_totals_distribution)/20.) + 1)
	ax.set_xlim([0.0,xlim])
	pylab.title('%s Risk Monte Carlo'%projectname)
	ax.set_xlabel('Total Cost as-spent €M')
	ax.set_ylabel('Number of occurrences')
	ax.grid(True)
	textstring = "Number of iterations: %d " % num_trials
	textstring0 = "Number of risks: %d " % nrisks
	textstring1 = "Prob weighted risk exposure: "+ str(weightedcost)+ "M"
	textstring2 = "Cost at 50% confidence: "+ str(cellbound50)+ "M"
	textstring3 = "Cost at 80% confidence: "+ str(cellbound80)+ "M"
	pylab.text(.1,.85,textstring,transform = ax.transAxes)
	pylab.text(.1,.80,textstring0,transform = ax.transAxes)
	pylab.text(.1,.75,textstring1,transform = ax.transAxes)
	pylab.text(.1,.70,textstring2,transform = ax.transAxes)
	pylab.text(.1,.65,textstring3,transform = ax.transAxes)
	ax2 = ax.twinx()
	ax2.set_ylabel('Cumulative fraction of occurances', color='r')
	ax2.plot(final_totals_distribution,niter2,c='r')
	ax2.set_ylim([0.0,1.0])
	# draw an arrow
	arga = {'color':'r'}
	ax2.arrow(hold50,.50,10.,.00,shape='full',lw=2,head_length=3,head_width=.03,**arga)
	##
	##                                                                            Figure 2
	##
	fig = plt.figure(2)
	ax = fig.add_subplot(111)
	pylab.title('%s Risk Monte Carlo'%projectname)
	ax.set_xlabel('Total Cost as-spent €M')
	ax.set_ylabel('Percent Probability{Cost > x }')
	ax.grid(True)
	#
		#Xbackground = [[.6, .6],[.5,.5]]
	# plot the probability line
	ax.plot(final_totals_distribution,niter3)
	ax.set_xlim([0.0,xlim])
	ax.set_ylim([0.0,100.0])
	# draw the background
	##    ax.imshow(Xbackground, interpolation='bicubic', cmap=cm.copper,
	##         extent=(40.0,xlim, 0.0, 100.), alpha=.5)  # alpha --> transparency
	# resample the x-axis
	xx = []
	yy = []
	nsteps = 110
	delx = xlim/(nsteps-10)
	for ii in range(nsteps):
		 xx.append(ii * delx)
	yy = np.interp(xx,final_totals_distribution,niter3)
	for jj in range(0,nsteps-5,3):
		 x1 =  xx[jj-1]
		 x2 =  xx[jj+1]
		 y2 =  yy[jj]
	##         mybar(ax,x1,x2,y2)
		 ax.bar(xx[jj],yy[jj],align='center',color='r')
	# draw a few arrows and vertical lines
	ax.arrow(hold50+10,50,-10.,.0,shape='full',lw=3,length_includes_head=True,head_width=2)
	ax.vlines(hold50,0.0,50,linewidth=4)
	ax.arrow(hold80+10,20,-10.,.0,shape='full',lw=3,length_includes_head=True,head_width=2)
	ax.vlines(hold80,0.0,20,linewidth=4)
	pylab.text(hold50+1,52,textstring2 ) # 50% value
	pylab.text(hold80+1,22,textstring3 ) # 80% value
	ax.set_aspect('auto')
	fig.savefig('fig2.png')
	##
	##                                                                            Figure 3 subplot 1
	##
	fig, axes = plt.subplots(nrows=2, ncols=1)
	fig.subplots_adjust(hspace = .75)
	##    fig.tight_layout()
	ax3 = fig.add_subplot(211)
	pylab.title('Histogram of %s risk costs (as-spent EUR)'%projectname)
	ax3.set_xlabel('Cost as-spent €K')
	ax3.set_ylabel('Number of risks')
	##    yy = hist(total_cost,bins=20)
	##    ax3.set_xlim(0.0,yy[1].max())
	##    ax3.set_ylim(0.0,yy[0].max())
	ax3.autoscale(enable=True, axis='both', tight=None)
	labels = ax3.get_xticklabels()
	for label in labels:
		label.set_rotation(45)
	ax3.plot = hist(total_cost,bins=20)
	fig.savefig('fig3.1.png')
	##
	##                                                                            Figure 3 subplot 2
	##
	ax4 = fig.add_subplot(212)
	ax4.autoscale(enable=True, axis='both', tight=None)
	pylab.title('Histogram of %s prob-wght\'ed as-spent risk costs'%projectname)
	ax4.set_xlabel('Cost €K')
	ax4.set_ylabel('Number of risks')
	temp = [total_cost[ii]*meanprobability[ii] for ii in range(nrisks)]
	labels = ax4.get_xticklabels()
	for label in labels:
		label.set_rotation(45)
	ax4.plot = hist(temp,bins=20)
	fig.savefig('fig3.2.png')
	plt.show()
	sys.stdout = fhold

def main(argv):
	##########################################
	#####  DEFAULT PARAMETER VALUES ##########
	##########################################
	username = '' 				# default value if not given in command line
	password = ''				# default value if not given in command line
	num_trials = '500'  		# default value if not given in command line
	annual_escalation = '.030'  # default for annual escalation
	subsystem = 'ALL'  			# default for subsystem
	output_file = '0' 			# zero sends to terminal, 1 sends to file test.txt in working directory
	##########################################
	##########################################
	try:
		opts, args = getopt.getopt(sys.argv[1:],"hu:p:n:e:s:o:",["help","username","password","num_trials=","annual_escalation=","subsystem=","output_file="])
	except getopt.GetoptError:
		print('Usage: montecarlo_riskanalysis.py  -h <help> -u <username> -p <password> -n <num_trials> -e <annual_escalation> -s <subsystem> -o <output_file>')
	for ou, arg in opts:
		if ou in ("-h","--help"):
			print('\b\n Usage: montecarlo_riskanalysis.py   -h <help> -n <num_trials> -e <annual_escalation> -s <subsystem> -o <output_file> \b\n' + \
			'\b\n [-u] jira username to access the risk register'+\
			'\b\n [-p] jira password to access the risk register'+\
			'\b\n [-n] number of trials is typically between 500 and 5000'+\
			'\b\n [-e] escalation factor as fraction; e.g., enter 0.03 for 3% annual escalation'+\
			'\b\n [-s] subsystem can be:  ALL, MID, LOW, OCS, PM'  +\
			'\b\n [-o] if value is 1 then output goes to file in working directory named text.txt; if value is 0 output goes to python pane')
			sys.exit()
		elif ou in ("-u", "--username"):
			username = arg
		elif ou in ("-p", "--password"):
			password = arg
		elif ou in ("-n", "--num_trials"):
			num_trials = arg
		elif ou in ("-e", "--annual_escalation"):
			annual_escalation = arg
		elif ou in ("-s", "--subsystem"):
			subsystem = arg
		elif ou in ("-o", "--output_file"):
			output_file = arg
	return [username,password,num_trials,annual_escalation,subsystem,output_file]
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

   print('\n\r Number of iterations: %d' %int(sy[2]))
   print('\n\r Annual escalation as a fraction: %s' %str(sy[3]))
   print('\n\r Subsystem: %s' %str(sy[4]))
   print('\n\r Output File: %d' %int(sy[5]))

   if platform.system() == 'Windows':
      locale.setlocale( locale.LC_MONETARY, 'fr-FR' )
   else:
      locale.setlocale( locale.LC_ALL, 'en_IE.UTF-8' )

   montecarlorisk(username,password,int(sy[2]),float(sy[3]),str(sy[4]),int(sy[5]))
