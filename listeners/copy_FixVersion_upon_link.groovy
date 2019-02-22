import com.atlassian.jira.ComponentManager
import com.atlassian.jira.component.ComponentAccessor
import com.atlassian.jira.issue.Issue
import com.atlassian.jira.issue.IssueManager
import com.atlassian.jira.issue.link.IssueLinkManager
import com.atlassian.jira.issue.link.IssueLink
import com.atlassian.jira.issue.CustomFieldManager
import com.atlassian.jira.issue.fields.CustomField
import com.atlassian.jira.issue.MutableIssue
import com.atlassian.jira.issue.customfields.option.Option
import com.atlassian.jira.issue.fields.config.FieldConfig
import com.atlassian.jira.user.ApplicationUser
import com.atlassian.jira.issue.UpdateIssueRequest
import com.atlassian.jira.event.type.EventDispatchOption
import com.atlassian.jira.project.version.Version
import com.atlassian.jira.event.issue.link.IssueLinkCreatedEvent


import org.apache.log4j.Logger
import org.apache.log4j.Level

def log = Logger.getLogger("Feature.Update.Listener")
log.setLevel(Level.DEBUG)

log.info("Starting Feature Update Listener.")

IssueManager issueManager = ComponentAccessor.getIssueManager();
IssueLinkManager issueLinkManager = ComponentAccessor.getIssueLinkManager();
CustomFieldManager customFieldManager = ComponentAccessor.getCustomFieldManager()


//Issue parentIssue = event.getIssue()
Issue parentIssue = event.getIssueLink().getSourceObject()
//NB Note static type checking can't work this out...ignore the error

Issue issue

String versionName

//Only Proceed if parentIssue has a fixVersion value.
if ( parentIssue.getFixVersions() ) {
    
    if (parentIssue.getIssueType().getName() == "Feature") {
        issueLinkManager.getOutwardLinks(parentIssue.id).each {storyLink ->
            if ( storyLink.getIssueLinkType().getName() == "Parent/Child" ) {
                issue = storyLink.destinationObject    
                log.info("found issue: " + issue.getKey())
            
                Version[] projectVersions = issue.getProjectObject().getVersions()
                Version[] featureVerisons = parentIssue.getFixVersions()
                def resultVersions = []            
                resultVersions = issue.getFixVersions()
            
                featureVerisons.each { Version featureVersion->
                    projectVersions.each { Version projectVersion->

                        if ( featureVersion.getName() == projectVersion.getName() ) {
                            resultVersions.add(projectVersion)
                        }
                    }            
                }
           
                //JIRA requires a mutable issue to update, so we need to create one, referenced by the story we are viewing.
                MutableIssue mutableIssue = issueManager.getIssueObject(issue.id) as MutableIssue
                mutableIssue.setFixVersions(resultVersions)
            
                ApplicationUser user = ComponentAccessor.getJiraAuthenticationContext().getLoggedInUser()                           
                UpdateIssueRequest.UpdateIssueRequestBuilder issueRequestBuilder = new UpdateIssueRequest.UpdateIssueRequestBuilder();
                issueRequestBuilder.eventDispatchOption(EventDispatchOption.ISSUE_UPDATED);
                issueRequestBuilder.sendMail(false);
                UpdateIssueRequest uiRequest = new UpdateIssueRequest(issueRequestBuilder);
                issueManager.updateIssue(user, mutableIssue, uiRequest)
            }
        }
    }
}


