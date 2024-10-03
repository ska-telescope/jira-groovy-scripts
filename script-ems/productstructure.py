import os.path
import requests
import io
from io import StringIO
import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of the ALIM SYNC google sheet
SAMPLE_SPREADSHEET_ID = "1bEPGIV_ubMjdn_2cKbStaPfc_QS7pvf29lhUvzfDkik"
SAMPLE_RANGE_NAME = "BOMUpload!A1:Z"

# Invokes the EMS API to get the BOM (consult Brendon Taljaard about this part)
def get_configuration_control_items():
    api_url = "https://ems-api.internal.skao.int/pbs"
    response = requests.get(api_url)
    #print(response.content)
    # if api call was successful, return the vsc buffer data
    if response.status_code == 200:
        csv_data = response.content.decode("utf-8")
        csv_buffer = StringIO(csv_data)
        return csv_buffer
    elif response.status_code == 401:
        logging.error("401 Unauthorized Error!")
    else:
        return

def main():

  # get the Bill of Material by invoking the EMS API
  df = pd.read_csv(get_configuration_control_items())

  #print(df.T.reset_index().T.values.tolist())

  """Uses the Google Sheets API to authenticate with Google 
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet = service.spreadsheets()

    # Attempt to read values from the Google Sheet
    result = (
        sheet.values()
        .get(spreadsheetId=SAMPLE_SPREADSHEET_ID, range=SAMPLE_RANGE_NAME)
        .execute()
    )

    values = result.get("values", [])

    if not values:
      print("No existing BOM data found in the Alim Sync Google Sheet.")

  except HttpError as err:
    print(err)

  rangeAll = '{0}!A1:Z'.format("BOMUpload")
  body = {}
  print("Clearing existing BOM data in the Alim Sync Google Sheet.")
  resultClear = service.spreadsheets().values().clear(
      spreadsheetId=SAMPLE_SPREADSHEET_ID, 
      range=rangeAll,
      body=body).execute()

  print("Writing new BOM data to the Alim Sync Google Sheet.")
  response_date = service.spreadsheets().values().update(
        spreadsheetId=SAMPLE_SPREADSHEET_ID,
        valueInputOption='RAW',
        range=SAMPLE_RANGE_NAME,
        body=dict(
            majorDimension='ROWS',
            values=df.fillna("").T.reset_index().T.values.tolist())
    ).execute()


if __name__ == "__main__":
  main()