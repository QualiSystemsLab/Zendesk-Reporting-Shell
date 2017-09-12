from cloudshell.shell.core.resource_driver_interface import ResourceDriverInterface
from cloudshell.shell.core.driver_context import InitCommandContext, ResourceCommandContext, AutoLoadResource, \
    AutoLoadAttribute, AutoLoadDetails, CancellationContext
#from data_model import *  # run 'shellfoundry generate' to generate data model classes

import json
import requests
import cloudshell.api.cloudshell_api as csapi
import time
import datetime
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


class ZendeskReportingShellDriver (ResourceDriverInterface):

    def __init__(self):
        """
        ctor must be without arguments, it is created with reflection at run time
        """
        pass

    def initialize(self, context):
        """
        Initialize the driver session, this function is called everytime a new instance of the driver is created
        This is a good place to load and cache the driver configuration, initiate sessions etc.
        :param InitCommandContext context: the context the command runs on
        """
        pass

    def cleanup(self):
        """
        Destroy the driver session, this function is called everytime a driver instance is destroyed
        This is a good place to close any open sessions, finish writing to log files
        """
        pass

    # <editor-fold desc="Discovery">

    def get_inventory(self, context):
        """
        Discovers the resource structure and attributes.
        :param AutoLoadCommandContext context: the context the command runs on
        :return Attribute and sub-resource information for the Shell resource you can return an AutoLoadDetails object
        :rtype: AutoLoadDetails
        """
        # See below some example code demonstrating how to return the resource structure and attributes
        # In real life, this code will be preceded by SNMP/other calls to the resource details and will not be static
        # run 'shellfoundry generate' in order to create classes that represent your data model

        '''
        resource = ZendeskReportingShell.create_from_context(context)
        resource.vendor = 'specify the shell vendor'
        resource.model = 'specify the shell model'

        port1 = ResourcePort('Port 1')
        port1.ipv4_address = '192.168.10.7'
        resource.add_sub_resource('1', port1)

        return resource.create_autoload_details()
        '''
        return AutoLoadDetails([], [])

    # </editor-fold>

    # <editor-fold desc="Help Functions">

    def create_a_session(self, host, domain, token):
        cs_session = csapi.CloudShellAPISession(host=host, domain=domain, token_id=token)
        return cs_session

    def get_global_inputs(self, reservationId, cs_session):
        global_inputs = cs_session.GetReservationInputs(reservationId).GlobalInputs
        for tempVar in global_inputs:
            if tempVar.ParamName == 'user':
                user = tempVar.Value
            if tempVar.ParamName == 'pwd':
                pwd = tempVar.Value
        return user, pwd

    def create_tickets_matrix(self, viewID, reservationId, headers, cs_session, user, pwd, switchVariable, url):
        if viewID == 30298148 or viewID == 38205246:
            ticketsMatrix = [['Ticket ID', 'Priority', 'Subject', 'Product Area', 'Organization', 'Requester',
                             'Requested', 'Related WI', 'Resolution State', 'Resolution Target']]
        else:
            ticketsMatrix = [['Ticket ID', 'Priority', 'Status', 'Subject', 'Created', 'Internal Owner', 'OrganizationID', 'OrganizationName']]
        while switchVariable == 1:

            getting_all_the_tickets = requests.get(url, auth=(user, pwd), headers=headers)

            if getting_all_the_tickets.status_code != 200:
                cs_session.WriteMessageToReservationOutput(reservationId=reservationId,
                                                           message='Status: {0} Problem With Authentication.'.format(
                                                               getting_all_the_tickets.status_code))
                exit()

            Decoded_Json_For_Tickets = getting_all_the_tickets.json()
            Number_Of_Tickets = len(Decoded_Json_For_Tickets['tickets'])

            for i in range(0, Number_Of_Tickets):
                ticketID = Decoded_Json_For_Tickets['tickets'][i]['id']
                ticketPriority= [tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id']==21413096]
                ticketPriority=str(ticketPriority[0])
                ticketPriority=ticketPriority.replace('__', ' - ')
                ticketSubject = Decoded_Json_For_Tickets['tickets'][i]['subject']
                ticketSubject=ticketSubject.encode('ascii', 'ignore')
                ticketCreated = Decoded_Json_For_Tickets['tickets'][i]['created_at']
                ticketCreated = str(ticketCreated)
                ticketCreated = ticketCreated.replace('Z', '')
                ticketCreated = ticketCreated.replace('T', ' ')
                ticketOrganizationID = Decoded_Json_For_Tickets['tickets'][i]['organization_id']
                if Decoded_Json_For_Tickets['tickets'][i]['organization_id'] == None:
                    ticketOrganizationName = 'No Organization Entered'
                else:
                    tempUrl = 'https://qualisystemscom.zendesk.com/api/v2/organizations/' + str(
                        ticketOrganizationID) + '.json'
                    get_organization_name = requests.get(tempUrl, auth=(user, pwd), headers=headers)
                    Decoded_Json = get_organization_name.json()
                    ticketOrganizationName = Decoded_Json['organization']['name']

                if viewID==30298148 or viewID==38205246:
                    ticketProductArea=[tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 21401902]
                    ticketProductArea=str(ticketProductArea[0])
                    ticketProductArea = ticketProductArea.replace('__', ' : ')
                    ticketProductArea = ticketProductArea.replace('_', ' ')
                    ticketProductArea = ticketProductArea.title()

                    ticketRequesterID=Decoded_Json_For_Tickets['tickets'][i]['requester_id']
                    tempUrl = 'https://qualisystemscom.zendesk.com/api/v2/users/' + str(ticketRequesterID) + '.json'
                    get_requester_name = requests.get(tempUrl, auth=(user, pwd), headers=headers)
                    Decoded_Json = get_requester_name.json()
                    ticketRequesterName = Decoded_Json['user']['name']
                    ticketRequesterName=ticketRequesterName.encode('ascii', 'ignore')

                    ticketRelatedWI=[tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 21422828]
                    ticketRelatedWI=str(ticketRelatedWI[0])
                    ticketResolutionState=[tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 23325216]
                    ticketResolutionState=str(ticketResolutionState[0])
                    ticketResolutionTarget=[tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 21989137]
                    ticketResolutionTarget=str(ticketResolutionTarget[0])
                    ticketsMatrix.append([ticketID, ticketPriority, ticketSubject, ticketProductArea, ticketOrganizationName, ticketRequesterName, ticketCreated, ticketRelatedWI, ticketResolutionState, ticketResolutionTarget])
                else:
                    ticketStatus = [tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 21409521]
                    ticketStatus=str(ticketStatus[0])
                    ticketStatus=ticketStatus.replace('_', ' ')
                    ticketStatus=ticketStatus.title()
                    ticketOwner = [tempVar['value'] for tempVar in Decoded_Json_For_Tickets['tickets'][i]['fields'] if tempVar['id'] == 21393023]
                    ticketOwner=str(ticketOwner[0])
                    ticketOwner = ticketOwner.replace('_', ' ')
                    ticketOwner=ticketOwner.title()
                    ticketsMatrix.append([ticketID, ticketPriority, ticketStatus, ticketSubject, ticketCreated, ticketOwner, ticketOrganizationID, ticketOrganizationName])

            nextPage = Decoded_Json_For_Tickets['next_page']

            if nextPage != None:
                url = nextPage
            else:
                switchVariable = 0

        return ticketsMatrix

    def get_audit_creation_time(self , infoVector, user_input, headers, user, pwd, switchVariable, url):
        ticketAudits = []
        while switchVariable == 1:
            get_audits = requests.get(url, auth=(user, pwd), headers=headers)
            Decoded_Json = get_audits.json()
            Number_Of_Audits = len(Decoded_Json['audits'])

            for x in range(0, Number_Of_Audits):
                ticketAudits.append(Decoded_Json['audits'][x])
                for tempVar in Decoded_Json['audits'][x]['events']:
                    if tempVar['type'] == 'Change':
                        if tempVar['field_name'] == str(infoVector.get(user_input)[1]) and tempVar['value'] == infoVector.get(user_input)[2]:
                            auditCreationTime = Decoded_Json['audits'][x]['created_at']
                            auditCreationTime = auditCreationTime.replace('T', ' ')
                            auditCreationTime = auditCreationTime.replace('Z', '')

            nextPage = Decoded_Json['next_page']

            if nextPage != None:
                url = nextPage
            else:
                switchVariable = 0

        return  auditCreationTime

    def calculate_time_delta(self, auditCreationTime):
        GMT_Time = time.strftime("%Y-%m-%d %H:%M:%S")
        GMT_Time_In_Sec = time.mktime(datetime.datetime.strptime(GMT_Time, "%Y-%m-%d %H:%M:%S").timetuple())
        auditCreationTimeInSec = time.mktime(
            datetime.datetime.strptime(auditCreationTime, "%Y-%m-%d %H:%M:%S").timetuple())
        delta = (GMT_Time_In_Sec - auditCreationTimeInSec) / 3600 / 24
        return delta

    def calculate_ticket_age(self, ticketMatrix, i):
        GMT_Time = time.strftime("%Y-%m-%d %H:%M:%S")
        GMT_Time_In_Sec = time.mktime(datetime.datetime.strptime(GMT_Time, "%Y-%m-%d %H:%M:%S").timetuple())
        ticketCreationTimeInSec = time.mktime(
            datetime.datetime.strptime(ticketMatrix[i][4], "%Y-%m-%d %H:%M:%S").timetuple())
        ticketAge = (GMT_Time_In_Sec - ticketCreationTimeInSec) / 3600 / 24
        return ticketAge

    def create_tickets_wait_time_matrix(self, viewID, i, delta, ticketAge, auditCreationTime, ticketsMatrix, ticketWaitTime, unassignedTicketsCounter):
        tempVector = []
        tempVector.append(delta)
        tempVector.append(ticketsMatrix[i][0])
        tempVector.append(ticketsMatrix[i][1])
        if viewID == 30298148 or viewID == 38205246:
            tempVector.append(ticketsMatrix[i][2])
            tempVector.append(ticketsMatrix[i][3])
            tempVector.append(ticketsMatrix[i][4])
            tempVector.append(ticketsMatrix[i][5])
            tempVector.append(auditCreationTime)
            tempVector.append(ticketsMatrix[i][7])
            tempVector.append(ticketsMatrix[i][8])
            tempVector.append(ticketsMatrix[i][9])
        else:
            tempVector.append(ticketsMatrix[i][2])
            if ticketsMatrix[i][5] != '':
                tempVector.append(ticketsMatrix[i][5])
            else:
                tempVector.append('--')
                unassignedTicketsCounter = unassignedTicketsCounter + 1
            tempVector.append(ticketsMatrix[i][3])
            tempVector.append(ticketAge)
            tempVector.append(ticketsMatrix[i][6])
            tempVector.append(ticketsMatrix[i][7])


        ticketWaitTime.append(tempVector)
        return ticketWaitTime, unassignedTicketsCounter

    def create_priorities_vector_and_priority_age_matrix(self, medianAgeVector, i, ticketWaitTime, prioritiesVector, priorityAgeMatrix):
        tempIndex = 1
        if medianAgeVector[i] >= 1:
            tempIndex = 2
        if medianAgeVector[i] >= 10:
            tempIndex = 3
        if medianAgeVector[i] >= 30:
            tempIndex = 4

        # prioritiesTempVector.append(ticketWaitTime[i][2])
        tempVar = int((ticketWaitTime[i][2])[0])

        prioritiesVector[tempVar - 1] = prioritiesVector[tempVar - 1] + 1

        priorityAgeMatrix[tempIndex][tempVar] = priorityAgeMatrix[tempIndex][tempVar] + 1
        return prioritiesVector, priorityAgeMatrix

    def create_SLACompVector_and_SLAMap(self, ticketWaitTime, i, SLACompVector, SLAMap, internalSLATarget):
        tempSLAcompVector = []
        tempVar = int((ticketWaitTime[i][2])[0])
        tempSLAcompVector.append(ticketWaitTime[i][1])
        tempSLAcompVector.append(ticketWaitTime[i][2])
        tempSLAcompVector.append(ticketWaitTime[i][0])
        tempSLAcompVector.append('Yes')
        if tempVar == 1 and ticketWaitTime[i][0] > internalSLATarget[0]:
            tempSLAcompVector[3] = 'No'
        elif tempVar == 2 and ticketWaitTime[i][0] > internalSLATarget[1]:
            tempSLAcompVector[3] = 'No'
        elif tempVar == 3 and ticketWaitTime[i][0] > internalSLATarget[2]:
            tempSLAcompVector[3] = 'No'
        elif ticketWaitTime[i][0] > internalSLATarget[3]:
            tempSLAcompVector[3] = 'No'
        SLACompVector.append(tempSLAcompVector)

        if SLACompVector[i][3] == 'Yes':
            SLAMap[tempVar][1] = SLAMap[tempVar][1] + 1
        else:
            SLAMap[tempVar][2] = SLAMap[tempVar][2] + 1
        return SLACompVector, SLAMap

    def detrmine_style(self, sortedTicketWaitTimeByPriority, i, SLACompVector):
        for j in range(0, len(SLACompVector)):
            if sortedTicketWaitTimeByPriority[i][1] == SLACompVector[j][0]:
                tempIndex = j
        if SLACompVector[tempIndex][3] == 'No':
            style = 'slaBreach'
        else:
            style = 'centred'
        return style

    def sendemail(self, sender, recipients, content):

        smtpObj = smtplib.SMTP('smtp.office365.com', 587)

        smtpObj.ehlo()

        smtpObj.starttls()

        smtpObj.login('noreply@qualisystems.com', 'Qu@li1234')

        smtpObj.sendmail(sender, recipients, content)

        smtpObj.quit()

    # </editor-fold>

    # <editor-fold desc="Help Commands">

    def get_all_view_tickets(self, context, view_id):
        resid = context.reservation.reservation_id
        headers = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        url = 'https://qualisystemscom.zendesk.com/api/v2/views/' + view_id + '.json'
        getting_view_info = requests.get(url, auth=(user, pwd), headers=headers)
        Decoded_Json_For_View = getting_view_info.json()
        View_Title = Decoded_Json_For_View['view']['title']

        url= 'https://qualisystemscom.zendesk.com/api/v2/views/'+view_id+'/tickets.json'

        getting_all_the_tickets = requests.get(url, auth=(user, pwd), headers=headers)
        if getting_all_the_tickets.status_code != 200:
            cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                       message='Status: {0} Problem With Authentication.'.format(
                                                           getting_all_the_tickets.status_code))
            exit()
        Decoded_Json_For_Tickets = getting_all_the_tickets.json()
        Number_Of_View_Tickets = len(Decoded_Json_For_Tickets['tickets'])
        Tickets_Vector=[]
        for i in range(0, Number_Of_View_Tickets):
            ticket_id = Decoded_Json_For_Tickets['tickets'][i]['id']
            ticket_id = str(ticket_id)
            Tickets_Vector.append(ticket_id)

        return ("View Title : {2}\nNumber Of View Tickets : {0}\nTickets ID : {1}".format(Number_Of_View_Tickets,Tickets_Vector,View_Title))

    def get_all_views_titles_number_of_tickets_and_tickets_id(self, context):
        resid = context.reservation.reservation_id
        headers = {'Content-Type': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        switchVariable=1
        Views_ID_Vector = []
        url = 'https://qualisystemscom.zendesk.com/api/v2/views.json'
        while switchVariable == 1:

            getting_all_the_views = requests.get(url, auth=(user, pwd), headers=headers)
            if getting_all_the_views.status_code != 200:
                cs_session.WriteMessageToReservationOutput(reservationId=resid,
                                                           message='Status: {0} Problem With Authentication.'.format(
                                                               getting_all_the_views.status_code))
                exit()

            Decoded_Json_For_Views = getting_all_the_views.json()
            Number_Of_Views = len(Decoded_Json_For_Views['views'])

            for i in range(0, Number_Of_Views):
                view_title = Decoded_Json_For_Views['views'][i]['title']
                view_title = str(view_title)
                Views_ID_Vector.append(view_title)
                cs_session.WriteMessageToReservationOutput(resid, '{0}'.format(view_title))
                # self.get_all_view_tickets(context,view_id)

            nextPage = Decoded_Json_For_Views['next_page']

            if nextPage != None:
                url = nextPage
            else:
                switchVariable = 0

        return len(Views_ID_Vector)


        #return ("{0}".format(Number_Of_View_Tickets))


    # </editor-fold>

    # <editor-fold desc="Commands">

    def update_global_inputs(self, context, input_user_mail, input_user_pwd):
        resid = context.reservation.reservation_id
        cs_session=self.create_a_session(context.connectivity.server_address, context.reservation.domain, context.connectivity.admin_auth_token)
        cs_session.UpdateReservationGlobalInputs(reservationId=resid,globalInputs=[csapi.UpdateTopologyGlobalInputsRequest('user',input_user_mail),csapi.UpdateTopologyGlobalInputsRequest('pwd',input_user_pwd)])
        user,pwd=self.get_global_inputs(resid,cs_session)
        cs_session.WriteMessageToReservationOutput(reservationId=resid, message='Global Inputs Successfully Updated\nUser Email Entered: {0}\nUser Password Entered: {1}'.format(user, pwd))

    def Zendesk_Queues_Extended(self, context, user_input):

        resid = context.reservation.reservation_id
        headers = {'Accept': 'application/json'}
        cs_session = self.create_a_session(context.connectivity.server_address, context.reservation.domain,
                                           context.connectivity.admin_auth_token)
        user, pwd = self.get_global_inputs(resid, cs_session)

        mail=[['Subject',''], ['Body', ''], ['Ticket Header', ''], ['Recipient', ''], ['SMTP Server', '192.168.42.29'], ['Port', '25'], ['User', 'noreply@qualisystems.com'], ['Password', 'Qu@li1234']]

        infoVector= {
            'RnD': [29772268, 21747272, 'under_investigation',
                    'yakir.d@qualisystems.com, guy.ba@qualisystems.com, edan.e@qualisystems.com, st@qualisystems.com, ariel.k@qualisystems.com, alex.a@qualisystems.com, Shaul.B@qualisystems.com, Liron.A@qualisystems.com, ronen.a@qualisystems.com, shay.k@qualisystems.com, Alona.G@qualisystems.com, nahum.t@qualisystems.com, Efrat.m@qualisystems.com',
                    'The following tickets require ' + user_input + "'s attention:", 'Tickets pending ' + user_input],
            'Product': [32067333, 21747272, 'product_team_review',
                        'Product@QualiSystems.com, st@qualisystems.com, ariel.k@qualisystems.com',
                        'The following tickets require ' + user_input + "'s attention:",
                        'Tickets pending ' + user_input],
            'Customer Success': [43992063, 21747272, 'delivery_team_review',
                         'amos.s@qualisystems.com, alon.s@qualisystems.com, igor.k@qualisystems.com, Shaul.B@qualisystems.com, st@qualisystems.com',
                         'The following tickets require ' + user_input + "'s attention:",
                         'Tickets pending ' + user_input],
            'RM': [43992073, 21747272, 'release_manager_review', 'st@qualisystems.com',
                   'The following tickets require ' + user_input + "'s attention:", 'Tickets pending ' + user_input],
            'TnD' : [48066816, 21747272, 'training_and_documentation', 'Naama.g@qualisystems.com, st@qualisystems.com', 'The following tickets require '+ user_input + "'s attention:", 'Tickets pending ' + user_input],
            'Bugs' : [38205246, 21409521, 'reported_bug', 'edan.e@qualisystems.com, guy.ba@qualisystems.com, roni.d@qualisystems, st@qualisystems.com ', 'These are the currently open customer Bug tickets:', 'Pending customer Bugs'],
            'Features' : [30298148, 21409521, 'requested_feature', 'Product@QualiSystems.com, st@qualisystems.com', 'These are the currently open customer Feature Request tickets:', 'Pending customer Feature Requests'],
        }
        viewID = infoVector.get(user_input,'X')[0]
        if viewID=='X':
            cs_session.WriteMessageToReservationOutput(resid, 'No Value / UnValid Value Was Entered')
            exit()

        mail[0][1] = infoVector.get(user_input)[5]
        mail[2][1] = infoVector.get(user_input)[4]
        mail[3][1] = infoVector.get(user_input)[3]

        sender = 'noreply@qualisystems.com'
        recipients = mail[3][1]

        msg = MIMEMultipart('alternative')
        msg['Subject'] = mail[0][1]
        msg['From'] = sender
        msg['To'] = recipients


        url = 'https://qualisystemscom.zendesk.com/api/v2/views/' + str(viewID) + '/tickets.json'
        ticketsMatrix=self.create_tickets_matrix(viewID, resid, headers, cs_session, user, pwd, 1, url)

        if len(ticketsMatrix)-1==0 :
            mail[2][1] = 'There are currently no tickets pending '+user_input+"'s attention"

            # <editor-fold desc="HTML Body">

            mail[1][1] = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
	<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
	<style type="text/css">
	body {
		margin:0 0 0 0;
		padding:0 0 0 0;
		background-color: #ffffff !important;
		font-size:10pt;
		font-family: Verdana,Arial,sans-serif;
		line-height:11px;
		color:#303030; }
		
	table td {border-collapse: collapse;}
	td {margin:0;}
	td img {display:block;}
	a {color:#blue;text-decoration:underline;}
	a:hover {text-decoration: underline;color:blue;}
	a img {text-decoration:none;}
	a:visited {color: blue;}
	a:active {color: blue;}
	h1 {font-size: 18pt; color:#865827; line-height: 20px;}
	h3 {font-size: 16pt; color:blue; line-height: 20px; text-align: center;}
	h4 {font-size: 14pt; color:#58585a;}  
	p {font-size: 12pt;}  
	

	table.gridtable {
		font-family: verdana,arial,sans-serif;
		font-size:11px;
		color:#333333;
		border-width: 1px;
		border-color: #666666;
		border-collapse: collapse;
	}
	table.gridtable th {
		border-width: 1px;
		padding: 8px;
		border-style: solid;
		border-color: #666666;
		background-color: #dedede;
	}
	table.gridtable td {
		border-width: 1px;
		padding: 8px;
		border-style: solid;
		border-color: #666666;
		background-color: #ffffff;
		
	}
	
	table.gridtable tr.even1 td {background: #F3F3F3}
	table.gridtable tr.even0 td {background: #FFFFFF}

	td.gridtable_header {
		vertical-align: center;
		text-align: center;
		margin-left: auto;
		margin-right: auto;
		background-color: #C9E3F0 !important;
		font-weight:bold;
	}
	
	.ageGroupTable tr td:first-child {
		background-color:#bbbbbb;
		width: 60px;
	}
	
	.ageGroupHeader {
		background-color: #bbbbbb;
<!-- 		width: 100px; -->
	}
	
	.showstopper_s {		
		border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf3000; 
        width:115px
    }
	
	.critical_s {
		border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf7000; 
        width:110px 
	}
	
	.urgent_s {
		border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf9600; 
        width:115px 
	}
	
	.medium_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#93bf00; 
        width:115px
	}
	
	.low_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#00bf76; 
        width:115px
	}
	
	.ageGroupTable tbody tr td span {
			padding:5px !important;
			color: white !important;
			text-shadow: 2px 2px #000000;
	}
	.PriorityList 
			color: white;
			text-shadow: 2px 2px #000000;
	}
	.PriorityList tbody tr td {
	padding:5px;
	}
	
  </style>
</head>

<body>

<h3><a href="https://support.qualisystems.com/rules/"""+str(viewID)+"""" target="_blank">Tickets Pending """+user_input+"""</a></h3>

<h4>Executive Summary:</h4>

<p>Number of Tickets in queue: 0</p>
<p>Number of Unassigned Tickets: 0</p>
<p>Median current wait period of ticket: N/A</p>

<h4>Number of tickets per priority:</h4>
<table class="PriorityList">
<tbody>
<tr>
<td class="showstopper_s">Showstoppers</td>
<td class="critical_s">Critical</td>
<td class="urgent_s">Urgent</td>
<td class="medium_s">Medium</td>
<td class="low_s">Low</td>
</tr>
<tr>
<td class="showstopper_s">0</td>
<td class="critical_s">0</td>
<td class="urgent_s">0</td>
<td class="medium_s">0</td>
<td class="low_s">0</td>
</tr>
</tbody></table>

<h4>Current wait period by priority:</span></h4>

<table class="ageGroupTable"><tbody>
<tr>
<td class="ageGroupHeader">&lt;=1 Day</td>
<td>
	<span class="showstopper_s AgeGroupStack">0</span>
	<span class="critical_s AgeGroupStack">0</span>
	<span class="urgent_s AgeGroupStack">0</span>
	<span class="medium_s AgeGroupStack">0</span>
	<span class="low_s AgeGroupStack">0</span>
</td>
</tr>
<tr>
<td class="ageGroupHeader">1 to 10 Days</td>
<td>
	<span class="showstopper_s AgeGroupStack">0</span>
	<span class="critical_s AgeGroupStack">0</span>
	<span class="urgent_s AgeGroupStack">0</span>
	<span class="medium_s AgeGroupStack">0</span>
	<span class="low_s AgeGroupStack">0</span>
</td>
</tr><tr>
<td class="ageGroupHeader">10 to 30 Days</td>
<td>
    <span class="showstopper_s AgeGroupStack">0</span>
	<span class="critical_s AgeGroupStack">0</span>
	<span class="urgent_s AgeGroupStack">0</span>
	<span class="medium_s AgeGroupStack">0</span>
	<span class="low_s AgeGroupStack">0</span>  
</td>
</tr><tr>
<td class="ageGroupHeader">&gt;30 Days</td>
<td>
    <span class="showstopper_s AgeGroupStack">0</span>
	<span class="critical_s AgeGroupStack">0</span>
	<span class="urgent_s AgeGroupStack">0</span>
	<span class="medium_s AgeGroupStack">0</span>
	<span class="low_s AgeGroupStack">0</span>
</td>
</tr>
</tbody></table>

<p style="text-align: left;" align="center">&nbsp;</p>
<hr />
<p style="text-align: center;" align="center"><span style="text-decoration: underline; font-size: x-large;">"""+mail[2][1]+"""<br /></span></p>
<p style="text-align: center;" align="center">&nbsp;</p>

</body>
</html>
"""
            # </editor-fold>

            #file = open("C:\\"+user_input+".html", 'w')
            #file.write('{0}'.format(mail[1][1]))
            #file.close()

            part = MIMEText(mail[1][1], 'html')
            msg.attach(part)
            self.sendemail(sender, recipients, msg.as_string())
            exit()

        ticketWaitTime = []
        unassignedTicketsCounter=0
        for i in range(1, len(ticketsMatrix)):

            url = 'https://qualisystemscom.zendesk.com//api/v2/tickets/' + str(ticketsMatrix[i][0]) + '/audits.json'
            auditCreationTime=self.get_audit_creation_time(infoVector, user_input, headers, user, pwd, 1, url)

            delta = self.calculate_time_delta(auditCreationTime)
            if viewID == 30298148 or viewID == 38205246:
                ticketAge=None
            else:
                ticketAge = self.calculate_ticket_age(ticketsMatrix, i)
            ticketWaitTime, unassignedTicketsCounter = self.create_tickets_wait_time_matrix(viewID, i, delta, ticketAge, auditCreationTime,
                                                                                            ticketsMatrix,
                                                                                            ticketWaitTime,
                                                                                            unassignedTicketsCounter)

        sortedTicketWaitTimeBySLA=ticketWaitTime[:]
        sortedTicketWaitTimeBySLA.sort(reverse=True)
        sortedTicketWaitTimeByPriority = sortedTicketWaitTimeBySLA[:]
        sortedTicketWaitTimeByPriority.sort(key=lambda z: z[2])


        medianAgeVector = []
        prioritiesVector = [0,0,0,0,0]
        if viewID == 30298148 or viewID == 38205246:
            priorityAgeMatrix = [[0, 1, 2, 3, 4, 5], [30, 0, 0, 0, 0, 0], [90, 0, 0, 0, 0, 0], [365, 0, 0, 0, 0, 0],
                                 [9999999, 0, 0, 0, 0, 0]]
        else:
            priorityAgeMatrix = [[0, 1, 2, 3, 4, 5], [1, 0, 0, 0, 0, 0], [10, 0, 0, 0, 0, 0], [30, 0, 0, 0, 0, 0],
                                 [9999999, 0, 0, 0, 0, 0]]
        SLACompVector = []
        SLAMap = [['Priority', 'Within SLA', 'Breach SLA'], ['1 - Showstopper', 0, 0], ['2 - Critical', 0, 0],
                  ['3 - Urgent', 0, 0], ['4 - Medium', 0, 0], ['5 - Low', 0, 0]]

        internalSLATarget=[2,3,5,7]


        for i in range(0, len(ticketWaitTime)):
            medianAgeVector.append(ticketWaitTime[i][0])

            prioritiesVector, priorityAgeMatrix= self.create_priorities_vector_and_priority_age_matrix(medianAgeVector,
                                                                                                       i,
                                                                                                        ticketWaitTime,
                                                                                                        prioritiesVector,
                                                                                                        priorityAgeMatrix)

            if viewID != 30298148 and viewID != 38205246:
                SLACompVector, SLAMap = self.create_SLACompVector_and_SLAMap(ticketWaitTime, i, SLACompVector, SLAMap, internalSLATarget)

        if viewID == 30298148 or viewID == 38205246:
            for x in range (1, len(priorityAgeMatrix)):
                for y in range (1, len(priorityAgeMatrix[0])):
                    if priorityAgeMatrix[x][y]!=0:
                        for z in range (0, (priorityAgeMatrix[x][y]*4)-1):
                            priorityAgeMatrix[x][y]=str(priorityAgeMatrix[x][y])+ """&nbsp;"""


        medianAgeVector.sort()

        if len(medianAgeVector)%2 == 1 :
            medianAge = medianAgeVector[len(medianAgeVector)/2]
        else:
            medianAge =(medianAgeVector[len(medianAgeVector)/2] + medianAgeVector[len(medianAgeVector)/2-1])/2


        if viewID == 30298148 or viewID == 38205246:
            mail[1][1] ="""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <style type="text/css">
    body {
        margin:0 0 0 0;
        padding:0 0 0 0;
        background-color: #ffffff !important;
        font-size:10pt;
        font-family: Verdana,Arial,sans-serif;
        line-height:11px;
        color:#303030; }
    	
    table td {border-collapse: collapse;}
    td {margin:0;}
    td img {display:block;}
    a {color:#blue;text-decoration:underline;}
    a:hover {text-decoration: underline;color:blue;}
    a img {text-decoration:none;}
    a:visited {color: blue;}
    a:active {color: blue;}
    h1 {font-size: 18pt; color:#865827; line-height: 20px;}
    h3 {font-size: 16pt; color:blue; line-height: 20px; text-align: center;}
    h4 {font-size: 14pt; color:#58585a;}  
    p {font-size: 12pt;}  
    
    table.gridtable {
    	font-family: verdana,arial,sans-serif;
    	font-size:11px;
    	color:#333333;
    	border-width: 1px;
    	border-color: #666666;
    	border-collapse: collapse;
    }
    table.gridtable th {
		border-width: 1px;
		padding: 8px;
		border-style: solid;
		border-color: #666666;
		background-color: #dedede;
	}
	table.gridtable td {
		border-width: 1px;
		padding: 8px;
		border-style: solid;
		border-color: #666666;
		background-color: #ffffff;
		
	}
	
	table.gridtable tr.even1 td {background: #F3F3F3}
	table.gridtable tr.even0 td {background: #FFFFFF}

    td.gridtable_header {
    	vertical-align: center;
    	text-align: center;
    	margin-left: auto;
    	margin-right: auto;
    	background-color: #C9E3F0 !important;
    	font-weight:bold;
    }
    
    .ageGroupTable tr td:first-child {
        background-color:#bbbbbb;
        width: 60px;
    }
    
    .ageGroupHeader {
        background-color: #bbbbbb;
<!-- 		width: 100px; -->
    }
    
    .showstopper_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf3000; 
        width:115px
    }
    
    .critical_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf7000; 
        width:115px
    }
    
    .urgent_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#bf9600; 
        width:115px
    }
    
    .medium_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#93bf00; 
        width:115px
    }
    
    .low_s {
        border-style: solid;
        border-width: 1px;
        border-color:black;
        background-color:#00bf76; 
        width:115px
    }

	.ageGroupTable tbody tr td span {
			padding:5px !important;
			color: white !important;
			text-shadow: 2px 2px #000000;
		    display: block;
		    margin-bottom: 5px;
	}
	.PriorityList {

			color: white;
			text-shadow: 2px 2px #000000;
	}
	.PriorityList tbody tr td {
	padding:5px;
	}

	
  </style>
</head>

<body>

<h3><a href="https://support.qualisystems.com/rules/""" + str(viewID) + """" target="_blank">""" + mail[0][1] + """</a></h3>

<h4>Executive Summary:</h4>

<p>Number of """ + user_input + """ in queue: """ + str(len(ticketsMatrix) - 1) + """ </p>
<p>Median current wait period of """ + user_input + """: """ + str(round(medianAge, 2)) + """</p>

<h4>Number of """ + user_input + """ per priority:</h4>
<table class="PriorityList">
<tbody>
<tr>
<td class="showstopper_s">Showstoppers</td>
<td class="critical_s">Critical</td>
<td class="urgent_s">Urgent</td>
<td class="medium_s">Medium</td>
<td class="low_s">Low</td>
</tr>
<tr>
<td class="showstopper_s">""" + str(prioritiesVector[0]) + """</td>
<td class="critical_s">""" + str(prioritiesVector[1]) + """</td>
<td class="urgent_s">""" + str(prioritiesVector[2]) + """</td>
<td class="medium_s">""" + str(prioritiesVector[3]) + """</td>
<td class="low_s">""" + str(prioritiesVector[4]) + """</td>
</tr>
</tbody></table>

<h4>Current wait period by priority:</span></h4>

<table class="ageGroupTable"><tbody>
<tr>
<td class="ageGroupHeader">Up to 30 Days</td>
<td>
	<span class="showstopper_s AgeGroupStack">""" + str(priorityAgeMatrix[1][1]) + """</span>
	<span class="critical_s AgeGroupStack">""" + str(priorityAgeMatrix[1][2]) + """</span>
	<span class="urgent_s AgeGroupStack">""" + str(priorityAgeMatrix[1][3]) + """</span>
	<span class="medium_s AgeGroupStack">""" + str(priorityAgeMatrix[1][4]) + """</span>
	<span class="low_s AgeGroupStack">""" + str(priorityAgeMatrix[1][5]) + """</span>
</td>
</tr>
<tr>
<td class="ageGroupHeader">30 to 90 Days</td>
<td>
	<span class="showstopper_s AgeGroupStack">""" + str(priorityAgeMatrix[2][1]) + """</span>
	<span class="critical_s AgeGroupStack">""" + str(priorityAgeMatrix[2][2]) + """</span>
	<span class="urgent_s AgeGroupStack">""" + str(priorityAgeMatrix[2][3]) + """</span>
	<span class="medium_s AgeGroupStack">""" + str(priorityAgeMatrix[2][4]) + """</span>
	<span class="low_s AgeGroupStack">""" + str(priorityAgeMatrix[2][5]) + """</span>
</td>
</tr><tr>
<td class="ageGroupHeader">90 to 365 Days</td>
<td>
    <span class="showstopper_s AgeGroupStack">""" + str(priorityAgeMatrix[3][1]) + """</span>
	<span class="critical_s AgeGroupStack">""" + str(priorityAgeMatrix[3][2]) + """</span>
	<span class="urgent_s AgeGroupStack">""" + str(priorityAgeMatrix[3][3]) + """</span>
	<span class="medium_s AgeGroupStack">""" + str(priorityAgeMatrix[3][4]) + """</span>
	<span class="low_s AgeGroupStack">""" + str(priorityAgeMatrix[3][5]) + """</span>
</td>
</tr><tr>
<td class="ageGroupHeader">&gt;365 Days</td>
<td>
    <span class="showstopper_s AgeGroupStack">""" + str(priorityAgeMatrix[4][1]) + """</span>
	<span class="critical_s AgeGroupStack">""" + str(priorityAgeMatrix[4][2]) + """</span>
	<span class="urgent_s AgeGroupStack">""" + str(priorityAgeMatrix[4][3]) + """</span>
	<span class="medium_s AgeGroupStack">""" + str(priorityAgeMatrix[4][4]) + """</span>
	<span class="low_s AgeGroupStack">""" + str(priorityAgeMatrix[4][5]) + """</span>
</td>
</tr>
</tbody></table>

<p style="text-align: left;" align="center">&nbsp;</p>
<hr />
<p style="text-align: center;" align="center"><span style="text-decoration: underline; font-size: x-large;">""" + mail[2][1] + """<br /></span></p>
<p style="text-align: center;" align="center">&nbsp;</p>
<table class="gridtable">
<tbody>
<tr>
<td class = "gridtable_header">Ticket ID</td>
<td class = "gridtable_header">Priority</td>
<td class = "gridtable_header">Subject</td>
<td class = "gridtable_header">Product Area</td>
<td class = "gridtable_header">Organization</td>
<td class = "gridtable_header">Requester</td>
<td class = "gridtable_header">Requested</td>
<td class = "gridtable_header">Related WI</td>
<td class = "gridtable_header">Resolution State</td>
<td class = "gridtable_header">Resolution Target</td>
<td class = "gridtable_header">Days since reported</td>
</tr>\n"""

            for i in range(0,len(sortedTicketWaitTimeByPriority)):
                mail[1][1]=mail[1][1]+"""\n<tr class="even"""+str(i%2)+"""">
<td>"""+str(sortedTicketWaitTimeByPriority[i][1])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][2])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][3])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][4])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][5])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][6])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][7])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][8])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][9])+"""</td>
<td>"""+str(sortedTicketWaitTimeByPriority[i][10])+"""</td>
<td>"""+str(int(round(sortedTicketWaitTimeByPriority[i][0])))+"""</td>
</tr>\n"""

        else:
            mail[1][1] = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
            <style type="text/css">
            body {
                margin:0 0 0 0;
                padding:0 0 0 0;
                background-color: #ffffff !important;
                font-size:10pt;
                font-family: Verdana,Arial,sans-serif;
                line-height:11px;
                color:#303030; }

            table td {border-collapse: collapse;}
            td {margin:0;}
            td img {display:block;}
            a {color:#blue;text-decoration:underline;}
            a:hover {text-decoration: underline;color:blue;}
            a img {text-decoration:none;}
            a:visited {color: blue;}
            a:active {color: blue;}
            h1 {font-size: 18pt; color:#865827; line-height: 20px;}
            h3 {font-size: 16pt; color:blue; line-height: 20px; text-align: center;}
            h4 {font-size: 14pt; color:#58585a;}  
            p {font-size: 12pt;}  


            table.gridtable {
                font-family: verdana,arial,sans-serif;
                font-size:11px;
                color:#333333;
                border-width: 1px;
                border-color: #666666;
                border-collapse: collapse;
            }
            table.gridtable th {
                border-width: 1px;
                padding: 8px;
                border-style: solid;
                border-color: #666666;
                background-color: #dedede;
            }
            table.gridtable td {
                border-width: 1px;
                padding: 8px;
                border-style: solid;
                border-color: #666666;

            }

            table.gridtable tr.even1 td {background: #F3F3F3}
            table.gridtable tr.even0 td {background: #FFFFFF}   
            td.gridtable_header {
                vertical-align: center;
                text-align: center;
                margin-left: auto;
                margin-right: auto;
                background-color: #C9E3F0 !important;
                font-weight:bold;
            }

            .ageGroupTable tr td:first-child {
                background-color:#bbbbbb;
                width: 60px;
            }

            .ageGroupHeader {
                background-color: #bbbbbb;
        <!-- 		width: 100px; -->
            }

            .showstopper_s {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                background-color:#bf3000; 
                width:115px
            }

            .critical_s {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                background-color:#bf7000; 
                width:110px
            }

            .urgent_s {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                background-color:#bf9600; 
                width:115px
            }

            .medium_s {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                background-color:#93bf00; 
                width:115px
            }

            .low_s {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                background-color:#00bf76; 
                width:115px
            }

            .ageGroupTable tbody tr td span {
                    padding:5px !important;
                    color: white !important;
                    text-shadow: 2px 2px #000000;
            }
            .PriorityList { 
                    color: white;
                    text-shadow: 2px 2px #000000;
            }
            .PriorityList tbody tr td {
            padding:5px;
            }

            .slaHeader {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                padding:5px;
                text-align: center;
                color:black;
                font-size: 12pt;
                font-weight:bold;
                color:#58585a;
            }

            .slaBreach {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                padding:5px;
                text-align: center;
                background-color:#FF0000 !important;;
                color:white;
                }

            .slaNoBreach {
                border-style: solid;
                border-width: 1px;
                border-color:black;
                padding:5px;
                text-align: center;
                background-color:#006400;
                color:white;
                }

            .centred{
                text-align: center;
                }

          </style>
        </head>

        <body>

        <h3><a href="https://support.qualisystems.com/rules/""" + str(viewID) + """" target="_blank">""" + mail[0][1] + """</a></h3>

        <h4>Executive Summary:</h4>

        <p>Number of Tickets in queue: """ + str(len(ticketsMatrix) - 1) + """ </p>
        <p>Number of Unassigned Tickets: """ + str(unassignedTicketsCounter) + """ </p>
        <p>Median current wait period of ticket: """ + str(round(medianAge, 2)) + """</p>

        <h4>Number of tickets per priority:</h4>
        <table class="PriorityList">
        <tbody>
        <tr>
        <td class="showstopper_s">Showstoppers</td>
        <td class="critical_s">Critical</td>
        <td class="urgent_s">Urgent</td>
        <td class="medium_s">Medium</td>
        <td class="low_s">Low</td>
        </tr>
        <tr>
        <td class="showstopper_s">""" + str(prioritiesVector[0]) + """</td>
        <td class="critical_s">""" + str(prioritiesVector[1]) + """</td>
        <td class="urgent_s">""" + str(prioritiesVector[2]) + """</td>
        <td class="medium_s">""" + str(prioritiesVector[3]) + """</td>
        <td class="low_s">""" + str(prioritiesVector[4]) + """</td>
        </tr>
        </tbody></table>

        <h4>SLA Status:</h4>
        <table><tbody>
        <tr>
        <td class="slaHeader">Priority</td>
        <td class="slaHeader">Within SLA</td>
        <td class="slaHeader">Breach SLA</td>
        </tr>
        <tr>
        <td class="showstopper_s" style="color:white">1 - Showstopper</td>
        <td class="slaNoBreach">""" + str(SLAMap[1][1]) + """</td>
        <td class="slaBreach">""" + str(SLAMap[1][2]) + """</td>
        </tr>

        <tr>
        <td class="critical_s" style="color:white">2 - Critical</td>
        <td class="slaNoBreach">""" + str(SLAMap[2][1]) + """</td>
        <td class="slaBreach">""" + str(SLAMap[2][2]) + """</td>
        </tr>

        <tr>
        <td class="urgent_s" style="color:white">3 - Urgent</td>
        <td class="slaNoBreach">""" + str(SLAMap[3][1]) + """</td>
        <td class="slaBreach">""" + str(SLAMap[3][2]) + """</td>
        </tr>

        <tr>
        <td class="medium_s" style="color:white">4 - Medium</td>
        <td class="slaNoBreach">""" + str(SLAMap[4][1]) + """</td>
        <td class="slaBreach">""" + str(SLAMap[4][2]) + """</td>
        </tr>

        <tr>
        <td class="low_s" style="color:white">5 - Low</td>
        <td class="slaNoBreach">""" + str(SLAMap[5][1]) + """</td>
        <td class="slaBreach">""" + str(SLAMap[5][2]) + """</td>
        </tr>
        </tbody></table>

        <h4 style="font-size: 12pt; margin-top: 0.5em; margin-bottom: 0.5em;">SLA:</h4>
        <p style="font-size: 9pt; margin-top: 0.5em; margin-bottom: 0.5em;">1 - Showstopper < """+str(internalSLATarget[0])+""" Days</p>
        <p style="font-size: 9pt; margin-top: 0.5em; margin-bottom: 0.5em;">2 - Critical < """+str(internalSLATarget[1])+""" Days</p>
        <p style="font-size: 9pt; margin-top: 0.5em; margin-bottom: 0.5em;">3 - Urgent < """+str(internalSLATarget[2])+""" Days</p>
        <p style="font-size: 9pt; margin-top: 0.5em; margin-bottom: 0.5em;">4&5 - Med & Low < """+str(internalSLATarget[3])+""" Days </p>

        <p style="text-align: left;" align="center">&nbsp;</p>
        <hr />
        <p style="text-align: center;" align="center"><span style="text-decoration: underline; font-size: x-large;">""" + \
                     mail[2][1] + """<br /></span></p>
        <p style="text-align: center;" align="center">&nbsp;</p>
        <table class="gridtable">
        <tbody>
        <tr>
        <td class = "gridtable_header">Ticket ID</td>
        <td class = "gridtable_header">Customer</td>
        <td class = "gridtable_header">Priority</td>
        <td class = "gridtable_header">Status</td>
        <td class = "gridtable_header">Internal Owner</td>
        <td class = "gridtable_header">Subject</td>
        <td class = "gridtable_header">Days currently pending&nbsp;""" + user_input + """:&nbsp;</td>
        <td class = "gridtable_header">Ticket Age</td>
        </tr>\n"""



            for i in range(0,len(sortedTicketWaitTimeByPriority)):
                style = self.detrmine_style(sortedTicketWaitTimeByPriority, i, SLACompVector)
                mail[1][1]=mail[1][1]+"""\n<tr class="even"""+str(i%2)+"""">
    <td><a href="https://support.qualisystems.com/tickets/"""+str(sortedTicketWaitTimeByPriority[i][1])+"""">"""+str(sortedTicketWaitTimeByPriority[i][1])+"""</td>
    <td><a href="https://qualisystemscom.zendesk.com/agent/organizations/"""+str(sortedTicketWaitTimeByPriority[i][7])+"""/tickets">"""+str(sortedTicketWaitTimeByPriority[i][8])+"""</td>
    <td>"""+str(sortedTicketWaitTimeByPriority[i][2])+"""</td>
    <td>"""+str(sortedTicketWaitTimeByPriority[i][3])+"""</td>
    <td>"""+str(sortedTicketWaitTimeByPriority[i][4])+"""</td>
    <td>"""+str(sortedTicketWaitTimeByPriority[i][5])+"""</td>
    <td class=\""""+style+"""">"""+str(int(round(sortedTicketWaitTimeByPriority[i][0])))+"""</td>
    <td>"""+str(int(round(sortedTicketWaitTimeByPriority[i][6])))+"""</td>
    </tr>\n"""

        mail[1][1]=mail[1][1]+"""</tbody>
</table>

</body>
</html>
"""

        #file = open("C:\\"+user_input+".html", 'w')
        #file.write('{0}'.format(mail[1][1]))
        #file.close()

        part = MIMEText(mail[1][1], 'html')
        msg.attach(part)
        self.sendemail(sender, recipients, msg.as_string())

    # </editor-fold>



    # <editor-fold desc="Orchestration Save and Restore Standard">
    def orchestration_save(self, context, cancellation_context, mode, custom_params):
      """
      Saves the Shell state and returns a description of the saved artifacts and information
      This command is intended for API use only by sandbox orchestration scripts to implement
      a save and restore workflow
      :param ResourceCommandContext context: the context object containing resource and reservation info
      :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
      :param str mode: Snapshot save mode, can be one of two values 'shallow' (default) or 'deep'
      :param str custom_params: Set of custom parameters for the save operation
      :return: SavedResults serialized as JSON
      :rtype: OrchestrationSaveResult
      """

      # See below an example implementation, here we use jsonpickle for serialization,
      # to use this sample, you'll need to add jsonpickle to your requirements.txt file
      # The JSON schema is defined at:
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/saved_artifact_info.schema.json
      # You can find more information and examples examples in the spec document at
      # https://github.com/QualiSystems/sandbox_orchestration_standard/blob/master/save%20%26%20restore/save%20%26%20restore%20standard.md
      '''
            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.

            # By convention, all dates should be UTC
            created_date = datetime.datetime.utcnow()

            # This can be any unique identifier which can later be used to retrieve the artifact
            # such as filepath etc.
            identifier = created_date.strftime('%y_%m_%d %H_%M_%S_%f')

            orchestration_saved_artifact = OrchestrationSavedArtifact('REPLACE_WITH_ARTIFACT_TYPE', identifier)

            saved_artifacts_info = OrchestrationSavedArtifactInfo(
                resource_name="some_resource",
                created_date=created_date,
                restore_rules=OrchestrationRestoreRules(requires_same_resource=True),
                saved_artifact=orchestration_saved_artifact)

            return OrchestrationSaveResult(saved_artifacts_info)
      '''
      pass

    def orchestration_restore(self, context, cancellation_context, saved_artifact_info, custom_params):
        """
        Restores a saved artifact previously saved by this Shell driver using the orchestration_save function
        :param ResourceCommandContext context: The context object for the command with resource and reservation info
        :param CancellationContext cancellation_context: Object to signal a request for cancellation. Must be enabled in drivermetadata.xml as well
        :param str saved_artifact_info: A JSON string representing the state to restore including saved artifacts and info
        :param str custom_params: Set of custom parameters for the restore operation
        :return: None
        """
        '''
        # The saved_details JSON will be defined according to the JSON Schema and is the same object returned via the
        # orchestration save function.
        # Example input:
        # {
        #     "saved_artifact": {
        #      "artifact_type": "REPLACE_WITH_ARTIFACT_TYPE",
        #      "identifier": "16_08_09 11_21_35_657000"
        #     },
        #     "resource_name": "some_resource",
        #     "restore_rules": {
        #      "requires_same_resource": true
        #     },
        #     "created_date": "2016-08-09T11:21:35.657000"
        #    }

        # The example code below just parses and prints the saved artifact identifier
        saved_details_object = json.loads(saved_details)
        return saved_details_object[u'saved_artifact'][u'identifier']
        '''
        pass

    # </editor-fold>
