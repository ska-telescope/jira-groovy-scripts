{\rtf1\ansi\ansicpg1252\cocoartf2577
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww10800\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import com.atlassian.jira.component.ComponentAccessor\
import com.atlassian.jira.issue.CustomFieldManager\
import com.atlassian.jira.issue.fields.CustomField\
import com.atlassian.jira.issue.fields.config.FieldConfig\
import com.atlassian.jira.issue.CustomFieldManager\
import com.atlassian.jira.issue.customfields.manager.OptionsManager\
import com.atlassian.jira.issue.customfields.option.Option\
import com.atlassian.jira.issue.customfields.option.Options\
import com.atlassian.jira.issue.MutableIssue\
import org.apache.log4j.Logger\
import org.apache.log4j.Level\
\
def customFieldManager = ComponentAccessor.getCustomFieldManager()\
def optionsManager = ComponentAccessor.getOptionsManager()\
def issueManager = ComponentAccessor.getIssueManager()\
\
def log = Logger.getLogger("Risk mgt: Computed Expected Labor Cost K Dollars Field 12905")\
log.setLevel(Level.DEBUG)\
\
log.info("Computed Expected Labor Cost K Dollars")\
\
CustomField cfRecoverable = customFieldManager.getCustomFieldObject(12903) // Is schedule recoverable without slipping project schedule? mapped from 13405 Schedule Recoverable\
CustomField cfMonths = customFieldManager.getCustomFieldObject(12921) // mapped from 13406 Expected (months)\
CustomField cfFtes = customFieldManager.getCustomFieldObject(12904) // mapped from 13407 FTE's required\
CustomField cfOverride = customFieldManager.getCustomFieldObject(12940) // mapped from 14200 Custom Expected Labor Cost\
\
def recoverable = "" as String \
if (cfRecoverable) \{\
    recoverable = issue.getCustomFieldValue(cfRecoverable) as String\
    \
    if (recoverable == null)\
    	recoverable = "undefined"\
\}\
\
def months = 0.0 as Double;\
if (cfMonths) \{\
    months = issue.getCustomFieldValue(cfMonths) as Double\
\}\
\
def ftes = 0.0 as Double;\
if (cfFtes) \{\
    ftes = issue.getCustomFieldValue(cfFtes) as Double\
\}\
\
def cost = 10.817 as Double // 10.817 per FTE per month as of 16 Aug 24\
\
def overrideValue = 0.0 as Double;\
if (cfOverride) \{\
    overrideValue = issue.getCustomFieldValue(cfOverride) as Double\
\}\
\
log.info("recoverable "+recoverable)\
log.info("months "+months) \
log.info("ftes "+ftes) \
log.info("overrideValue "+overrideValue)\
\
if (overrideValue)\
	return overrideValue\
else \{\
    if (recoverable == "Yes") \{\
        if (months && ftes)\
            return (months * ftes * cost)\
        else\
            return 0D\
    \} else if (recoverable == "No") \{\
        if (months)\
            return months * 1000\ 
        else \
            return 0D\
    \} else \{\
        return 0D\
    \}\
\}}
