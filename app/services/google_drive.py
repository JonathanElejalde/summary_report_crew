from typing import List, Dict, Any, Optional
import os
from datetime import datetime
import re
from concurrent.futures import ThreadPoolExecutor

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class GoogleDriveManager:
    """
    Class for managing Google Drive operations using a Service Account.
    
    This class handles:
    - Authentication with Google Drive API using a service account
    - Creating folder structures
    - Uploading files
    - Generating shareable links
    - Deleting local files after upload
    """
    
    # Define scopes needed for the application
    SCOPES = ['https://www.googleapis.com/auth/drive']
    
    def __init__(self, credentials_file: str = None):
        """
        Initialize the Google Drive manager.
        
        Args:
            credentials_file: Path to the service account JSON file
        """
        # Use provided path or default to project root
        if credentials_file is None:
            # Try to find credentials in the project root
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
            credentials_file = os.path.join(project_root, 'credentials.json')
        
        self.credentials_file = credentials_file
        
        # Check if credentials file exists
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(
                f"Service account credentials file not found: {self.credentials_file}. "
                "Please download it from the Google Cloud Console."
            )
        
        print(f"Using service account credentials file: {self.credentials_file}")
        
        self.service = self._authenticate()
        self.root_folder_id = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def _authenticate(self):
        """
        Authenticate with Google Drive API using service account.
        
        Returns:
            Google Drive API service
            
        Raises:
            Exception: If authentication fails
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_file, scopes=self.SCOPES
            )
            
            # Build and return the Drive service
            return build('drive', 'v3', credentials=credentials)
            
        except Exception as e:
            print(f"Authentication error: {e}")
            raise
    
    def _create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: ID of the parent folder (None for root)
            
        Returns:
            ID of the created folder
            
        Raises:
            HttpError: If folder creation fails
        """
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        if parent_id:
            folder_metadata['parents'] = [parent_id]
            
        try:
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            return folder.get('id')
            
        except HttpError as error:
            print(f"Error creating folder: {error}")
            raise
    
    def _find_or_create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> str:
        """
        Find a folder by name or create it if it doesn't exist.
        
        Args:
            folder_name: Name of the folder to find/create
            parent_id: ID of the parent folder (None for root)
            
        Returns:
            ID of the found or created folder
        """
        query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"
            
        try:
            response = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            files = response.get('files', [])
            
            if files:
                # Folder exists, return its ID
                return files[0].get('id')
            else:
                # Folder doesn't exist, create it
                return self._create_folder(folder_name, parent_id)
                
        except HttpError as error:
            print(f"Error finding folder: {error}")
            return self._create_folder(folder_name, parent_id)
    
    def setup_folder_structure(self, base_folder_name: str = "YouTube Analysis") -> Dict[str, str]:
        """
        Set up the folder structure for storing analysis files.
        
        If FOLDER_ID is provided in environment variables, uses that as the base folder.
        Otherwise, creates or finds a folder with the specified name.
        
        Creates:
        - Base folder (or uses existing one from FOLDER_ID)
        - Summaries subfolder
        - Reports subfolder
        - Final Reports subfolder
        
        Args:
            base_folder_name: Name of the base folder (used only if FOLDER_ID is not set)
            
        Returns:
            Dictionary with folder IDs for each folder
        """
        # Check if we have a folder ID in environment variables
        env_folder_id = os.getenv("FOLDER_ID")
        
        if env_folder_id:
            print(f"Using folder ID from environment variable: {env_folder_id}")
            base_folder_id = env_folder_id
        else:
            # Create or find the base folder
            print(f"Creating or finding folder: {base_folder_name}")
            base_folder_id = self._find_or_create_folder(base_folder_name)
        
        self.root_folder_id = base_folder_id
        
        # Create subfolders
        summaries_folder_id = self._find_or_create_folder("Summaries", base_folder_id)
        reports_folder_id = self._find_or_create_folder("Reports", base_folder_id)
        final_folder_id = self._find_or_create_folder("Final Reports", base_folder_id)
        
        return {
            "base": base_folder_id,
            "summaries": summaries_folder_id,
            "reports": reports_folder_id,
            "final": final_folder_id
        }
    
    def upload_file(self, file_path: str, folder_id: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to Google Drive and make it accessible via link.
        
        If UPLOAD_GOOGLE_DOCS environment variable is set to 'true', 
        markdown files will be automatically converted to Google Docs format.
        
        Args:
            file_path: Path to the file to upload
            folder_id: ID of the folder to upload to
            custom_name: Optional custom name for the file
            
        Returns:
            Dictionary with file metadata including ID and webViewLink
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_name = custom_name or os.path.basename(file_path)
        
        # Check if we should convert markdown to Google Docs
        convert_to_gdoc = False
        if os.getenv("UPLOAD_GOOGLE_DOCS", "false").lower() == "true":
            # Only convert markdown files
            file_ext = os.path.splitext(file_path)[1].lower()
            if file_ext in ['.md', '.markdown']:
                convert_to_gdoc = True
                print(f"Converting {file_path} to Google Docs format")
        
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        
        # Determine the MIME type based on file extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.md':
            mime_type = 'text/markdown'
        elif file_ext == '.txt':
            mime_type = 'text/plain'
        elif file_ext == '.html':
            mime_type = 'text/html'
        elif file_ext in ['.docx', '.doc']:
            mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        else:
            mime_type = 'application/octet-stream'
        
        # If converting to Google Docs, set the appropriate parameters
        if convert_to_gdoc:
            file_metadata['mimeType'] = 'application/vnd.google-apps.document'
        
        media = MediaFileUpload(
            file_path,
            mimetype=mime_type,
            resumable=True
        )
        
        try:
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink, mimeType',
            ).execute()
            
            # Set file permissions to "Anyone with the link can view"
            self.service.permissions().create(
                fileId=file.get('id'),
                body={
                    'type': 'anyone',
                    'role': 'reader'
                }
            ).execute()
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'link': file.get('webViewLink'),
                'mimeType': file.get('mimeType'),
                'local_path': file_path,
                'is_gdoc': convert_to_gdoc
            }
            
        except HttpError as error:
            print(f"Error uploading file: {error}")
            raise
    
    def upload_markdown_as_gdoc(self, file_path: str, folder_id: str, custom_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a markdown file and convert it to Google Docs format.
        
        Args:
            file_path: Path to the markdown file
            folder_id: ID of the folder to upload to
            custom_name: Optional custom name for the file
            
        Returns:
            Dictionary with file metadata including ID and webViewLink
        """
        # Ensure the file is a markdown file
        if not file_path.lower().endswith(('.md', '.markdown')):
            raise ValueError(f"File must be a markdown file: {file_path}")
        
        # If custom name doesn't have an extension, add .md
        if custom_name and not custom_name.lower().endswith(('.md', '.markdown')):
            custom_name = f"{custom_name}.md"
        
        # Upload the file with conversion to Google Docs
        return self.upload_file(file_path, folder_id, custom_name)
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename to be safe for Google Drive.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[\\/*?:"<>|]', "_", filename)
        # Limit length
        return sanitized[:100] if len(sanitized) > 100 else sanitized
    
    def create_custom_filename(self, video_info: Dict[str, Any], file_type: str) -> str:
        """
        Create a custom filename based on video metadata.
        
        Args:
            video_info: Dictionary with video metadata
            file_type: Type of file (summary/report/final)
            
        Returns:
            Custom filename
        """
        timestamp = datetime.now().strftime('%Y%m%d')
        
        title = video_info.get('title', 'Unknown')
        channel = video_info.get('channel_title', 'Unknown')
        
        # Sanitize title and channel
        safe_title = self._sanitize_filename(title)
        safe_channel = self._sanitize_filename(channel)
        
        return f"{timestamp}_{safe_channel}_{safe_title}_{file_type}.md"
    
    def upload_analysis_files(self, batch, folder_ids):
        """Synchronous file upload"""
        uploaded = {"summaries": [], "reports": []}
        
        for result in batch.get_successful_results():
            file_path = result.get("file_path")
            if not file_path:
                continue
            
            video_info = result.get("video_info", {})
            analysis_type = result.get("analysis_type", "")
            
            folder_id = folder_ids["reports" if analysis_type == "report" else "summaries"]
            custom_name = self.create_custom_filename(video_info, analysis_type)
            
            try:
                uploaded_file = self.upload_file(file_path, folder_id, custom_name)
                
                if analysis_type == "report":
                    uploaded["reports"].append(uploaded_file)
                else:
                    uploaded["summaries"].append(uploaded_file)
                    
            except Exception as e:
                print(f"Error uploading file: {e}")
        
        return uploaded

    def upload_final_report(self, final_report, folder_ids):
        """Synchronous final report upload"""
        if final_report.get("status") != "success":
            return None
            
        file_path = final_report.get("file_path")
        if not file_path:
            return None
            
        custom_name = self.create_custom_filename(
            {"title": final_report.get("query", "Report")}, 
            "final"
        )
        
        try:
            return self.upload_file(file_path, folder_ids["final"], custom_name)
        except Exception as e:
            print(f"Error uploading final report: {e}")
            return None
    
    def delete_local_files(self, file_metadata_list: List[Dict[str, Any]]) -> List[str]:
        """
        Delete local files after successful upload.
        
        Args:
            file_metadata_list: List of file metadata dictionaries
            
        Returns:
            List of successfully deleted file paths
        """
        deleted_files = []
        
        for file_metadata in file_metadata_list:
            local_path = file_metadata.get("local_path")
            
            if local_path and os.path.exists(local_path):
                try:
                    os.remove(local_path)
                    deleted_files.append(local_path)
                    print(f"🗑️ Deleted local file: {local_path}")
                except Exception as e:
                    print(f"❌ Error deleting local file {local_path}: {e}")
        
        return deleted_files

if __name__ == "__main__":
    """
    Test the Google Drive integration functionality.
    
    This test:
    1. Authenticates with Google Drive
    2. Sets up the folder structure
    3. Uploads test files
    4. Generates shareable links
    5. Optionally deletes local test files
    """
    import json
    from dotenv import load_dotenv
    import argparse
    import sys
    
    # Print Python version and path for debugging
    print(f"Python version: {sys.version}")
    print(f"Script path: {__file__}")
    
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test Google Drive integration')
    parser.add_argument('--delete', action='store_true', help='Delete local files after upload')
    parser.add_argument('--test-file', type=str, help='Path to a specific test file to upload')
    parser.add_argument('--convert-to-gdoc', action='store_true', 
                        help='Convert markdown to Google Docs format')
    args = parser.parse_args()
    
    print("\n🧪 Testing Google Drive integration")
    
    # Check if credentials file exists
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    credentials_file = os.path.join(project_root, 'credentials.json')
    
    if not os.path.exists(credentials_file):
        print(f"❌ Credentials file not found: {credentials_file}")
        print("Please download it from the Google Cloud Console and place it in the project root.")
        print("See the setup instructions for details.")
        sys.exit(1)
    
    print(f"Found credentials file: {credentials_file}")
    
    try:
        # Initialize the Google Drive manager
        print("\n🔑 Authenticating with Google Drive using service account...")
        drive_manager = GoogleDriveManager(credentials_file=credentials_file)
        
        # Set up folder structure (will use FOLDER_ID from .env if available)
        print("\n📁 Setting up folder structure...")
        folder_ids = drive_manager.setup_folder_structure("YouTube Analysis - Team")
        
        print(f"Created/found folders:")
        for folder_type, folder_id in folder_ids.items():
            print(f"- {folder_type}: {folder_id}")
        
        # Create a test file if none provided
        if not args.test_file:
            print("\n📝 Creating test file...")
            test_file_path = "test_upload.md"
            with open(test_file_path, 'w') as f:
                f.write("# Test Upload\n\nThis is a test file for Google Drive integration.")
        else:
            test_file_path = args.test_file
            print(f"\n📝 Using provided test file: {test_file_path}")
        
        # Upload the test file
        print(f"\n📤 Uploading test file: {test_file_path}")
        
        # Create mock video info for custom filename
        mock_video_info = {
            "title": "Test Video Title",
            "channel_title": "Test Channel"
        }
        
        # Create custom filename
        custom_name = drive_manager.create_custom_filename(mock_video_info, "test")
        print(f"Custom filename: {custom_name}")
        
        # Upload to the summaries folder
        uploaded_file = drive_manager.upload_file(
            test_file_path, 
            folder_ids["summaries"],
            custom_name
        )
        
        print("\n✅ Upload successful!")
        print(f"File ID: {uploaded_file['id']}")
        print(f"File name: {uploaded_file['name']}")
        print(f"Shareable link: {uploaded_file['link']}")
        
        # Test markdown to Google Docs conversion if requested
        if args.convert_to_gdoc:
            print("\n🔄 Testing Markdown to Google Docs conversion...")
            
            # Use the test file path from earlier
            print(f"Converting file: {test_file_path}")
            
            # Create a custom name for the Google Doc
            gdoc_custom_name = drive_manager.create_custom_filename(mock_video_info, "gdoc_test")
            
            # Upload and convert to Google Docs
            gdoc_file = drive_manager.upload_markdown_as_gdoc(
                test_file_path, 
                folder_ids["final"],  # Using final reports folder
                gdoc_custom_name
            )
            
            print("\n✅ Google Docs conversion successful!")
            print(f"File ID: {gdoc_file['id']}")
            print(f"File name: {gdoc_file['name']}")
            print(f"MIME Type: {gdoc_file['mimeType']}")
            print(f"Shareable link: {gdoc_file['link']}")
        
        # Delete local file if requested
        if args.delete and not args.test_file:  # Only delete if we created the file
            print("\n🗑️ Deleting local test file...")
            deleted = drive_manager.delete_local_files([uploaded_file])
            print(f"Deleted files: {deleted}")
        
        print("\n✅ Google Drive integration test complete!")
        
    except Exception as e:
        print(f"\n❌ Error during Google Drive test: {e}")
        import traceback
        traceback.print_exc()
   