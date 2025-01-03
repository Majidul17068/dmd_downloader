import requests
import os
import sys
from typing import Optional, List, Dict
import json
from dotenv import load_dotenv
from datetime import datetime
import logging
import pytz 
import zipfile

class TRUDApiClient:
    def __init__(self, api_key: str):
        self.api_key = api_key.lower()
        self.base_url = "https://isd.digital.nhs.uk/trud/api/v1"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json'
        }
        self.timezone = pytz.timezone('Asia/Dhaka')
        self.setup_logging()
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_dir = 'logs'
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now(self.timezone).strftime('%Y%m%d')
        log_file = os.path.join(log_dir, f'dmd_downloader_{timestamp}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - Bangladesh Time - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        bd_time = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
        logging.info(f"Script started at {bd_time}")

    def extract_zip(self, zip_path: str) -> bool:
        """Extract zip file to a folder named after the zip file."""
        try:
            # Create extraction directory name from zip file
            zip_name = os.path.splitext(os.path.basename(zip_path))[0]
            extract_dir = os.path.join('extracted', zip_name)
            
            # Create extraction directory
            os.makedirs(extract_dir, exist_ok=True)
            
            logging.info(f"Extracting {zip_path} to {extract_dir}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            completion_time = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
            logging.info(f"Successfully extracted {zip_path} at {completion_time}")
            return True
            
        except Exception as e:
            logging.error(f"Error extracting {zip_path}: {str(e)}")
            return False

    def get_releases(self, item_id: str, latest_only: bool = True) -> List[Dict]:
        """Get releases for an item."""
        try:
            url = f"{self.base_url}/keys/{self.api_key}/items/{item_id}/releases"
            if latest_only:
                url += "?latest"
            
            logging.info(f"Fetching releases from API")
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            if data.get('message') != 'OK':
                raise Exception(f"API Error: {data.get('message', 'Unknown error')}")
            
            return data.get('releases', [])
        
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching releases: {str(e)}")
            if hasattr(e, 'response'):
                logging.error(f"Response status: {e.response.status_code}")
                logging.error(f"Response body: {e.response.text}")
            return []

    def is_new_release(self, filename: str, file_url: str) -> bool:
        """Check if this is a new release that needs to be downloaded."""
        downloads_dir = 'downloads'
        existing_file = os.path.join(downloads_dir, filename)
        
        if not os.path.exists(existing_file):
            return True
            
        try:
            response = requests.head(file_url)
            remote_size = int(response.headers.get('content-length', 0))
            local_size = os.path.getsize(existing_file)
            
            if remote_size != local_size:
                return True
                
            if 'last-modified' in response.headers:
                remote_date = datetime.strptime(
                    response.headers['last-modified'], 
                    '%a, %d %b %Y %H:%M:%S %Z'
                ).replace(tzinfo=pytz.UTC)
                local_date = datetime.fromtimestamp(
                    os.path.getmtime(existing_file)
                ).astimezone(pytz.UTC)
                if remote_date > local_date:
                    return True
            
            return False
            
        except Exception as e:
            logging.warning(f"Error checking file status: {str(e)}")
            return True

    def download_file(self, url: str, filename: str) -> bool:
        """Download a file with progress indicator."""
        try:
            if not self.is_new_release(filename, url):
                logging.info(f"File {filename} is already up to date. Skipping download.")
                return True
            
            downloads_dir = 'downloads'
            os.makedirs(downloads_dir, exist_ok=True)
            filepath = os.path.join(downloads_dir, filename)
            
            logging.info(f"Starting download: {filename}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # chunk size for optimization
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for data in response.iter_content(block_size):
                    downloaded += len(data)
                    f.write(data)
                    if total_size:
                        percent = int(100 * downloaded / total_size)
                        sys.stdout.write(f"\rProgress: {percent}%")
                        sys.stdout.flush()
            
            completion_time = datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')
            logging.info(f"Successfully downloaded {filepath} at {completion_time}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading {filename}: {str(e)}")
            return False

    def download_release(self, release: Dict, 
                        include_checksum: bool = False,
                        include_signature: bool = False,
                        extract_after_download: bool = True) -> bool:
        """Download a specific release and its associated files."""
        success = True
        
        if 'archiveFileUrl' in release:
            file_success = self.download_file(
                release['archiveFileUrl'],
                release['archiveFileName']
            )
            success &= file_success
            
            if file_success and extract_after_download:
                zip_path = os.path.join('downloads', release['archiveFileName'])
                success &= self.extract_zip(zip_path)
        
        if include_checksum and 'checksumFileUrl' in release:
            success &= self.download_file(
                release['checksumFileUrl'],
                release['checksumFileName']
            )
        
        if include_signature and 'signatureFileUrl' in release:
            success &= self.download_file(
                release['signatureFileUrl'],
                release['signatureFileName']
            )
        
        return success

def main():
    load_dotenv()
    
    api_key = os.getenv('TRUD_API_KEY')
    if not api_key:
        logging.error("Error: TRUD_API_KEY not found in .env file")
        sys.exit(1)
    
    item_id = "24"  # here we can use our item count based on subscription we can keep it 24 or 14 
    
    try:
        client = TRUDApiClient(api_key)
        
        logging.info(f"Fetching dm+d releases (item ID: {item_id})...")
        releases = client.get_releases(item_id, latest_only=True)
        
        if not releases:
            logging.warning("No releases found")
            sys.exit(1)
        
        for release in releases:
            logging.info("\nRelease Information:")
            logging.info(f"Release ID: {release.get('releaseId', 'N/A')}")
            logging.info(f"Release Date: {release.get('releaseDate', 'N/A')}")
            logging.info(f"File Name: {release.get('archiveFileName', 'N/A')}")
            
            success = client.download_release(
                release,
                include_checksum=True,
                include_signature=False,
                extract_after_download=True
            )
            
            if not success:
                logging.error("Failed to download or extract some files")
                sys.exit(1)
        
        completion_time = datetime.now(pytz.timezone('Asia/Dhaka')).strftime('%Y-%m-%d %H:%M:%S %Z')
        logging.info(f"All downloads and extractions completed successfully at {completion_time}")
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()