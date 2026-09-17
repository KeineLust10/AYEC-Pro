import os.path
import pickle
import logging
from ..cloud_backup import CloudProvider

# Define logger
logger = logging.getLogger('GoogleDriveProvider')

# Required libraries check
try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False
    logger.warning("Google Drive libraries not found. Run: pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveProvider(CloudProvider):
    """Google Drive Provider Implementation"""

    def __init__(self, config):
        super().__init__(config)
        self.service = None
        self.folder_id = config.get('folder_id')
        self.credentials_file = config.get('credentials_file', 'credentials.json')
        self.token_file = 'token.pickle'
        
        if GOOGLE_LIBS_AVAILABLE:
            self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API"""
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Token refresh failed: {e}")
                    creds = None
            
            if not creds:
                if os.path.exists(self.credentials_file):
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            self.credentials_file, SCOPES)
                        creds = flow.run_local_server(port=0)
                        
                        # Save the credentials for the next run
                        with open(self.token_file, 'wb') as token:
                            pickle.dump(creds, token)
                    except Exception as e:
                        logger.error(f"Authentication flow failed: {e}")
                else:
                    logger.error(f"Credentials file not found: {self.credentials_file}")
                    return

        try:
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive service built successfully")
        except Exception as e:
            logger.error(f"Failed to build drive service: {e}")

    def upload(self, file_path, customer_name=None):
        """Upload file to Google Drive"""
        if not self.service:
            return {'success': False, 'error': 'Google Drive service not initialized'}

        try:
            file_name = os.path.basename(file_path)
            
            file_metadata = {'name': file_name}
            
            # Use folder if specified in config
            if self.folder_id:
                file_metadata['parents'] = [self.folder_id]
            
            # Simple upload
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            logger.info(f"File ID: {file.get('id')} uploaded to Google Drive")
            return {
                'success': True, 
                'provider': 'gdrive', 
                'file_id': file.get('id'),
                'file_name': file_name
            }
            
        except Exception as e:
            logger.error(f"Google Drive upload error: {e}")
            return {'success': False, 'error': str(e)}

    def list_backups(self):
        """List backups in Google Drive"""
        if not self.service:
            return []
            
        try:
            query = "trashed = false"
            if self.folder_id:
                query += f" and '{self.folder_id}' in parents"
                
            results = self.service.files().list(
                q=query,
                pageSize=10, 
                fields="nextPageToken, files(id, name, size, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()
            
            items = results.get('files', [])
            backups = []
            for item in items:
                backups.append({
                    'name': item['name'],
                    'id': item['id'],
                    'size': int(item.get('size', 0)),
                    'last_modified': item.get('modifiedTime')
                })
            return backups
            
        except Exception as e:
            logger.error(f"Google Drive list error: {e}")
            return []

    def download(self, file_name, destination):
        """Download file from Google Drive (by ID or Name search)"""
        # Note: file_name argument here is treated as file ID or Name 
        # Base class implies name. We might need to search for it first.
        pass # Not implementing download extensively for now
