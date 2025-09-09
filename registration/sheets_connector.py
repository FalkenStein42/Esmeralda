from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1neWaw0rKhIBjZbc8ZmsJwFyf2vMVpeN6ifqYwcKGS1U"
SAMPLE_RANGE_NAME = "A1:I2"


def create_sheets_service(credentials:Path, token:Path):
    """Shows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if token.exists():
        creds = Credentials.from_authorized_user_file(token, SCOPES)
    else:
        creds = None
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials, SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        token.write_text(creds.to_json())

    try:
        service = build("sheets", "v4", credentials=creds)
    except HttpError as err:
        print(err)
        service = None
    except Exception as e:
        print(e)

    return service



