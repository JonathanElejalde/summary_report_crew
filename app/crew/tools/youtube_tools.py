from typing import Optional, Dict, Any, List
import os
from googleapiclient.discovery import build
#from pytubefix import YouTube
#import whisper
#import tempfile
#import torch
import re
#import yt_dlp
import json  # Import json for better token debugging
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from urllib.parse import urlparse, parse_qs
import time

def extract_video_id(url: str) -> str:
    parsed_url = urlparse(url)
    if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
        return parse_qs(parsed_url.query)['v'][0]
    elif parsed_url.hostname == 'youtu.be':
        return parsed_url.path[1:]
    else:
        raise ValueError("Invalid YouTube URL")

class YouTubeComments:
    """
    Class for extracting and managing YouTube comments.
    
    This class handles authentication with the YouTube API and provides
    methods to fetch and process video comments. It can be initialized
    with an API key or use one from environment variables.
    
    Attributes:
        api_key (str): The YouTube API key for authentication
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize with optional API key, otherwise uses environment variable.
        
        Args:
            api_key (Optional[str]): YouTube API key. If None, will try to get from
                                   YOUTUBE_API_KEY environment variable
                                   
        Raises:
            ValueError: If no API key is provided and none found in environment
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY environment variable or pass it to the constructor.")

    def get_comments(self, video_url: str, max_comments: int = 200) -> List[Dict[str, Any]]:
        """
        Get comments from a YouTube video.
        
        This method fetches comments using the YouTube API, handling pagination
        to collect up to the specified maximum number of comments. Comments
        are ordered by relevance.
        
        Args:
            video_url (str): The URL of the YouTube video
            max_comments (int): Maximum number of comments to retrieve (default: 200)
            
        Returns:
            List[Dict[str, Any]]: List of comment dictionaries, each containing:
                - text (str): The comment text
                - likes (int): Number of likes on the comment
                
        Raises:
            ValueError: If the video URL is invalid
            RuntimeError: If there's an error fetching comments
        """
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL provided")

        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            comments = []
            next_page_token = None
            
            while len(comments) < max_comments:
                request_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': min(100, max_comments - len(comments)),
                    'order': 'relevance',
                    'textFormat': 'plainText'
                }
                
                if next_page_token:
                    request_params['pageToken'] = next_page_token
                
                response = youtube.commentThreads().list(**request_params).execute()
                
                for item in response.get('items', []):
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'text': comment['textDisplay'],
                        'likes': comment['likeCount'],
                    })
                
                next_page_token = response.get('nextPageToken')
                if not next_page_token or len(comments) >= max_comments:
                    break
            
            return comments
            
        except Exception as e:
            raise RuntimeError(f"Error getting comments: {e}")

class YouTubeTranscript:
    def __init__(self):
        # Get credentials from environment variables
        self.username = os.getenv('SMARTPROXY_USERNAME')
        self.password = os.getenv('SMARTPROXY_PASSWORD')
        
        # SmartProxy HTTPS endpoints from your dashboard
        self.proxy_host = "gate.smartproxy.com"
        self.proxy_ports = [
            "10001",
            "10002",
            "10003",
            "10004",
            "10005",
            "10006",
            "10007",
            "10008",
            "10009",
            "10010",
        ]
        
        # Retry configuration
        self.max_retries = 5
        self.base_delay = 2
        self.max_delay = 30
        self.jitter = 0.1
        print(f"Initializing YouTubeTranscript with {len(self.proxy_ports)} proxy ports")

    def _get_proxy_config(self, port: str) -> Dict[str, str]:
        """Create proxy configuration for a specific port"""
        proxy_url = f"https://{self.username}:{self.password}@{self.proxy_host}:{port}"
        print(f"Created proxy configuration for port {port}")
        return {"https": proxy_url}

    def get_transcript(self, video_url: str, cookies: str = None, proxies: Dict[str, str] = None) -> Dict[str, str]:
        video_id = extract_video_id(video_url)
        print(f"\n--- Starting transcript fetch for video {video_id} ---")
        last_error = None
        attempts_made = 0

        # If custom proxies are provided, try those first
        if proxies:
            print(f"Attempting with custom proxy configuration: {proxies}")
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, cookies=cookies, proxies=proxies)
                print("Successfully retrieved transcript with custom proxy!")
                return {"source": "youtube", "text": " ".join([entry['text'] for entry in transcript])}
            except (TranscriptsDisabled, NoTranscriptFound) as e:
                print(f"Transcript not available: {str(e)}")
                return {"source": "error", "text": str(e)}
            except Exception as e:
                print(f"Custom proxy attempt failed: {str(e)}")
                last_error = e

        # Try with our proxy endpoints
        print("\nStarting retry loop with SmartProxy endpoints...")
        for attempt in range(self.max_retries):
            print(f"\nAttempt {attempt + 1}/{self.max_retries}")
            
            for port in self.proxy_ports:
                attempts_made += 1
                print(f"\nTrying port {port} (attempt {attempts_made} overall)")
                
                try:
                    proxy_config = self._get_proxy_config(port)
                    print("Sending request to YouTube...")
                    
                    transcript = YouTubeTranscriptApi.get_transcript(
                        video_id, 
                        cookies=cookies, 
                        proxies=proxy_config
                    )
                    
                    print(f"Success! Retrieved transcript using port {port}")
                    return {"source": "youtube", "text": " ".join([entry['text'] for entry in transcript])}
                
                except TranscriptsDisabled:
                    print("Video has transcripts disabled")
                    return {"source": "error", "text": "Transcripts are disabled for this video."}
                
                except NoTranscriptFound:
                    print("No transcript available for this video")
                    return {"source": "error", "text": "No transcript found for this video."}
                
                except Exception as e:
                    print(f"Failed with port {port}: {str(e)}")
                    last_error = e
                    delay = min(self.max_delay, self.base_delay * (2 ** attempt))
                    print(f"Waiting {delay:.1f} seconds before next attempt...")
                    time.sleep(delay)
                    continue

        print(f"\n--- All attempts failed after trying {attempts_made} times ---")
        return {
            "source": "error", 
            "text": f"Failed to get transcript after {attempts_made} attempts. Last error: {str(last_error)}"
        }

