from flask import Flask
from flask_restful import reqparse, fields, marshal_with, Api, Resource
from flask_cors import CORS
from flask import abort

from googleapiclient import discovery
from oauth2client import file, client, tools
from datetime import datetime
import json
import httplib2

free_busy_parser = reqparse.RequestParser()
free_busy_parser.add_argument(
    'calendars', help='Calendar Ids list. ["<CALID>","<CALID>"]',
    location = 'json', required=True, action='append'
)

# Sample: 2018-04-07T09:00:00-04:00
free_busy_parser.add_argument(
    'start_time', help='start time', required=True
)

free_busy_parser.add_argument(
    'end_time', help='end time', required=True
)

parser = reqparse.RequestParser()
parser.add_argument('calendar_name', required=True)

class Calendar(Resource):
    def getCalendar(self, calendarName):
        try:
            calendar = service.calendars().get(calendarId = calendarName).execute()
            return calendar
        except Exception:
            abort(400, 'email is private')

    # """This method creates a new secondary calendar with given name"""
    def createCalendarInGoogle(self, newCalendarName):
        print('Get request to create calendar: ', newCalendarName)
        # Creating a new secondary calendar is a two step process,
        # Step 1: Create a new calendar. This new calendar will have
        # a globally unique id, generated by Google Calendar API.
        calendar = {
            'summary': newCalendarName,
            'timeZone': 'America/New_York'
        }

        created_calendar = service.calendars().insert(body=calendar).execute()
        print(created_calendar['id'])

        # Step 2: Add the new calendar to the list of secondary calendars
        calendarListEntry = {
            'id': created_calendar['id']
        }
        newCalendarListEntry = service.calendarList().insert(body=calendarListEntry).execute()
        return newCalendarListEntry['id']

    def post(self):
        args = parser.parse_args()
        print(args)
        return {'calendarId': self.createCalendarInGoogle(args['calendar_name'])}

    def get(self, calendar_email):
        print("checking calendar email if it is open: ", calendar_email)
        return self.getCalendar(calendar_email)

class Availability(Resource):

    def getFreeBusyInfo(self, calendars, startTime, endTime):
        body = {
          'timeMin': startTime,
          'timeMax': endTime,
          'timeZone': 'America/New_York',
          'items': list(map(lambda e: {"id": e}, calendars))
        }
        eventsResult = service.freebusy().query(body=body).execute()
        result = [{k:v} for k,v in eventsResult['calendars'].items()]
        return result

    def put(self):
        args = free_busy_parser.parse_args()
        print("calendars: ", args.calendars)
        test = self.getFreeBusyInfo(args.calendars,
            args.start_time,
            args.end_time
        )
        return test

# All initialization code
def setup_app(app):
    global service
    credentials = file.Storage('google_creds.json').get()
    if not credentials or credentials.invalid:
       print("Credentials not loaded!")
    else:
       print("Successfully loaded google credentials", credentials.access_token)
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

application = Flask(__name__)
setup_app(application)

@application.errorhandler(400)
def custom400(error):
    response = jsonify({'message': error.description['message']})

api = Api(application)
CORS(application)
api.add_resource(Calendar, '/<string:calendar_email>', '/')
api.add_resource(Availability, '/availability/')


if __name__ == '__main__':
    application.run(host='0.0.0.0')
