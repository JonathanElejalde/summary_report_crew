from typing import Optional, Dict, Any, List
import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
from pytubefix import YouTube
import whisper
import tempfile
#import torch
import re
import yt_dlp

def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various forms of YouTube URLs.
    
    Supports multiple URL formats including:
    - Standard watch URLs (youtube.com/watch?v=VIDEO_ID)
    - Shortened URLs (youtu.be/VIDEO_ID)
    - Embed URLs (youtube.com/embed/VIDEO_ID)
    
    Args:
        url (str): The YouTube URL to extract ID from
        
    Returns:
        Optional[str]: The video ID if found, None if no valid ID could be extracted
    """
    patterns = [
        r'(?:v=|/v/|youtu\.be/|/embed/)([^&?\n]+)',  # Standard, shortened and embed URLs
        r'(?:watch\?|youtube\.com/)(?:.*v=|v/|embed/)([^&?\n]+)',  # Watch URLs
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

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
    """
    Class for extracting and managing YouTube video transcripts.
    
    This class provides functionality to extract video transcripts using two methods:
    1. Official YouTube captions (preferred method)
    2. Whisper audio transcription (fallback method)
    
    The class automatically handles the process of attempting official captions first
    and falling back to Whisper transcription if needed.
    
    Attributes:
        model (whisper.Whisper): The loaded Whisper model for transcription
    """
    
    def __init__(self, model_size: str = "medium", device: Optional[str] = None):
        """
        Initialize with Whisper model configuration data.
        
        Args:
            model_size (str): Whisper model size (tiny, base, small, medium, large).
                            Larger models are more accurate but slower and use more memory.
            device (Optional[str]): Device to use for Whisper model (cuda/cpu).
                                  If None, will use CUDA if available.
        """
        # Whisper data
        self.model_size = model_size
        self.device = device
        

    def _parse_srt_captions(self, srt_content: str) -> Optional[str]:
        """
        Parse both traditional SRT and YouTube's JSON caption formats
        """
        try:
            # Handle JSON format (new YouTube format)
            if srt_content.strip().startswith('{'):
                import json
                captions = []
                data = json.loads(srt_content)
                
                # Extract text from events->segs->utf8
                for event in data.get("events", []):
                    if "segs" in event:
                        for seg in event["segs"]:
                            text = seg.get("utf8", "").strip()
                            if text and text not in ["\n", "[Music]"]:
                                captions.append(text)
                
                return " ".join(captions).replace("\n", " ").strip()
                
            # Handle traditional SRT format (existing code)
            lines = srt_content.strip().split('\n')
            text_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                if line.isdigit():
                    i += 2
                    text_buffer = []
                    while i < len(lines) and lines[i].strip():
                        text_buffer.append(lines[i].strip())
                        i += 1
                    if text_buffer:
                        text_lines.append(' '.join(text_buffer))
                i += 1
            
            return ' '.join(text_lines)
            
        except Exception as e:
            print(f"Error parsing captions: {e}")
            return None

    def _get_youtube_captions(self, yt: YouTube) -> Optional[str]:
        """
        Try to get official YouTube captions.
        
        Attempts to fetch official captions in the following language priority:
        1. English (en)
        2. Auto-generated English (a.en)
        3. Spanish (es)
        4. Auto-generated Spanish (a.es)
        
        Args:
            yt (YouTube): Initialized YouTube object for the video
            
        Returns:
            Optional[str]: Caption text if found and successfully parsed, None otherwise
        """
        try:
            captions = yt.captions
            if not captions:
                return None
                
            caption = None
            for lang_code in ['en', 'a.en', 'es', 'a.es']:
                if lang_code in captions:
                    caption = captions[lang_code]
                    break
            
            if not caption:
                return None
                
            srt_captions = caption.generate_srt_captions()
            
            if srt_captions and srt_captions.strip().split('\n')[0].isdigit():
                print("Found official captions")
                parsed_text = self._parse_srt_captions(srt_captions)
                if parsed_text:
                    return parsed_text
                    
            return srt_captions
            
        except Exception as e:
            print(f"Error getting YouTube captions: {e}")
            return None

    def _transcribe_with_whisper(self, video_id: str, yt: YouTube) -> Optional[str]:
        """
        Transcribe audio using Whisper when captions are not available.
        
        This method:
        1. Downloads the audio stream from the video
        2. Saves it to a temporary file
        3. Uses Whisper to transcribe the audio
        4. Cleans up temporary files
        
        Args:
            video_id (str): YouTube video ID
            yt (YouTube): Initialized YouTube object for the video
            
        Returns:
            Optional[str]: Transcribed text if successful
            
        Raises:
            RuntimeError: If audio stream is not found or transcription fails
        """
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
        if not audio_stream:
            raise RuntimeError("No audio stream found for video")

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Downloading audio for transcription...")
            audio_path = os.path.join(temp_dir, "audio.mp4")
            audio_stream.download(output_path=temp_dir, filename="audio.mp4")
            
            print("Transcribing with Whisper...")
            # Only initialize the model when needed. Most of the times we won't need it.
            if self.device is None:
                #self.device = "cuda" if torch.cuda.is_available() else "cpu"
                self.device = "cpu"
            model = whisper.load_model(self.model_size, device=self.device)

            result = model.transcribe(
                audio_path,
                #fp16=torch.cuda.is_available(),
                fp16=False,
                language='en',
            )
            return result["text"]

    def _get_ytdlp_captions(self, video_id: str) -> Optional[str]:
        """
        Try to get captions using yt-dlp with cookie authentication.
        
        Args:
            video_id (str): YouTube video ID
            
        Returns:
            Optional[str]: Extracted caption text if successful
        """
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en', 'a.en', 'es', 'a.es'],
            'cookiefile': os.getenv("COOKIES_PATH"),
            'quiet': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_id, download=False)
                subs = info.get('subtitles', {})
                auto_subs = info.get('automatic_captions', {})

                # Combine manual and auto subs, preferring manual
                all_subs = {**auto_subs, **subs}
                
                for lang in ['en', 'a.en', 'es', 'a.es']:
                    if lang in all_subs:
                        sub_url = all_subs[lang][0]['url']
                        sub_content = ydl.urlopen(sub_url).read().decode('utf-8')
                        return self._parse_srt_captions(sub_content)
        except Exception as e:
            print(f"yt-dlp caption extraction failed: {e}")
            return None

    def _download_audio_with_ytdlp(self, video_id: str) -> Optional[str]:
        """
        Download audio using yt-dlp with cookie authentication.
        
        Args:
            video_id (str): YouTube video ID
            
        Returns:
            Optional[str]: Path to downloaded audio file if successful
        """
        temp_dir = tempfile.mkdtemp()
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(temp_dir, '%(id)s.%(ext)s'),
            'cookiefile': os.getenv("COOKIES_PATH"),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'quiet': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_id, download=True)
                return ydl.prepare_filename(info).replace('.webm', '.mp3').replace('.m4a', '.mp3')
        except Exception as e:
            print(f"yt-dlp audio download failed: {e}")
            return None

    def get_transcript(self, video_url: str) -> Dict[str, str]:
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL provided")

        yt_pytube = None
        pytube_error = None
        
        # First try with pytubefix
        try:
            yt_pytube = YouTube(
                f"https://www.youtube.com/watch?v={video_id}",
                use_oauth=True,
                allow_oauth_cache=True
            )
            print("Attempting to get official captions with pytubefix...")
            captions = self._get_youtube_captions(yt_pytube)
            if captions:
                return {"source": "youtube_captions", "text": captions}
        except Exception as e:
            pytube_error = str(e)
            print(f"pytubefix failed: {pytube_error}")

        # Fallback to yt-dlp for captions
        print("Trying yt-dlp with cookies for captions...")
        ytdlp_captions = self._get_ytdlp_captions(video_id)
        if ytdlp_captions:
            return {"source": "ytdlp_captions", "text": ytdlp_captions}

        # Try pytubefix audio download
        audio_path = None
        if yt_pytube:
            try:
                print("Attempting pytubefix audio download...")
                return {
                    "source": "whisper_pytube",
                    "text": self._transcribe_with_whisper(video_id, yt_pytube)
                }
            except Exception as e:
                print(f"pytubefix audio download failed: {e}")

        # Final fallback to yt-dlp audio download
        print("Trying yt-dlp audio download with cookies...")
        audio_path = self._download_audio_with_ytdlp(video_id)
        if audio_path:
            try:
                print("Transcribing yt-dlp audio with Whisper...")
                # Only initialize the model when needed. Most of the times we won't need it.
                if self.device is None:
                    #self.device = "cuda" if torch.cuda.is_available() else "cpu"
                    self.device = "cpu"
                model = whisper.load_model(self.model_size, device=self.device)

                result = model.transcribe(
                    audio_path,
                    #fp16=torch.cuda.is_available(),
                    fp16=False,
                    language='en',
                )
                return {"source": "whisper_ytdlp", "text": result["text"]}
            finally:
                try:
                    os.remove(audio_path)
                    os.rmdir(os.path.dirname(audio_path))
                except:
                    pass

        error_msg = "Failed to get transcript through all methods"
        if pytube_error and "age restricted" in pytube_error.lower():
            error_msg += " (Video may be age restricted)"
            
        return {"source": "error", "text": error_msg}

if __name__ == "__main__":
    """Test the YouTube tools"""
    load_dotenv()
    
    # Test videos - normal and age-restricted
    test_cases = [
        {
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Normal video
            "description": "Standard video (Rick Roll)"
        },
        {
            "url": "https://www.youtube.com/watch?v=veqn4Klbkh4",  # Age-restricted video
            "description": "Age-restricted video (Test video)"
        }
    ]

    # Color codes for output
    GREEN = "\033[92m"
    RED = "\033[91m"
    RESET = "\033[0m"

    passed_tests = 0
    failed_tests = 0

    def print_result(success: bool, message: str):
        global passed_tests, failed_tests
        if success:
            print(f"{GREEN}✓ {message}{RESET}")
            passed_tests += 1
        else:
            print(f"{RED}✗ {message}{RESET}")
            failed_tests += 1

    print("\n=== Starting Comprehensive Tests ===")
    
    # Check cookies availability
    cookies_available = os.path.exists(os.getenv("COOKIES_PATH", ""))
    print(f"Cookies available: {'Yes' if cookies_available else 'No'}")
    
    for case in test_cases:
        print(f"\n=== Testing: {case['description']} ===")
        print(f"URL: {case['url']}")
        
        # Test transcript extraction
        try:
            print("\nTesting Transcript Extraction:")
            transcript_data = YouTubeTranscript().get_transcript(case['url'])
            
            # Validate transcript
            valid_transcript = (
                transcript_data['source'] != 'error' and 
                len(transcript_data['text']) > 50 and
                not any(error_word in transcript_data['text'].lower() 
                       for error_word in ['error', 'failed', 'age restricted'])
            )
            
            print_result(
                valid_transcript,
                f"Transcript obtained via {transcript_data['source']} | "
                f"First 100 chars: {transcript_data['text'][:100]}..."
            )
            
        except Exception as e:
            print_result(False, f"Transcript test failed: {str(e)}")
            continue

        # Test comments extraction (if not age-restricted)
        if "age-restricted" not in case['description'].lower():
            try:
                print("\nTesting Comments Extraction:")
                comments = YouTubeComments().get_comments(case['url'], max_comments=3)
                valid_comments = len(comments) > 0 and all(
                    'text' in c and 'likes' in c for c in comments
                )
                
                print_result(
                    valid_comments,
                    f"Found {len(comments)} valid comments | "
                    f"Sample: {comments[0]['text'][:50]}..."
                )
                
            except Exception as e:
                print_result(False, f"Comments test failed: {str(e)}")

    # Final summary
    print(f"\n=== Test Summary ===")
    print(f"Total tests: {passed_tests + failed_tests}")
    print(f"{GREEN}Passed: {passed_tests}{RESET}")
    print(f"{RED if failed_tests else RESET}Failed: {failed_tests}{RESET}")
    
    # Additional check for age-restricted handling
    if not cookies_available:
        print(f"\n{RED}Warning: No cookies found - age-restricted tests may fail!{RESET}")
        print("Set COOKIES_PATH environment variable with valid cookies for full testing") 