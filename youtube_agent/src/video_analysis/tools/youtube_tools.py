from typing import Optional, Dict, Any, List
import os
from googleapiclient.discovery import build
from dotenv import load_dotenv
from pytubefix import YouTube
import whisper
import tempfile
import torch
import re

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various forms of YouTube URLs."""
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
    """Class for extracting and managing YouTube comments"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with optional API key, otherwise uses environment variable."""
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key is required. Set YOUTUBE_API_KEY environment variable or pass it to the constructor.")

    def get_comments(self, video_url: str, max_comments: int = 200) -> List[Dict[str, Any]]:
        """
        Get comments from a YouTube video.
        
        Args:
            video_url: The URL of the YouTube video
            max_comments: Maximum number of comments to retrieve (default: 200)
            
        Returns:
            List of comments with text and likes count
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
    """Class for extracting and managing YouTube video transcripts"""
    
    def __init__(self, model_size: str = "medium", device: Optional[str] = None):
        """
        Initialize with Whisper model configuration.
        
        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to use (cuda if available, otherwise cpu)
        """
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(model_size, device=device)

    def _parse_srt_captions(self, srt_content: str) -> Optional[str]:
        """Parse SRT format captions and extract only the text."""
        try:
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
            print(f"Error parsing SRT format: {e}")
            return None

    def _get_youtube_captions(self, yt: YouTube) -> Optional[str]:
        """Try to get official YouTube captions."""
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
        """Transcribe audio using Whisper when captions are not available."""
        audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
        if not audio_stream:
            raise RuntimeError("No audio stream found for video")

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Downloading audio for transcription...")
            audio_path = os.path.join(temp_dir, "audio.mp4")
            audio_stream.download(output_path=temp_dir, filename="audio.mp4")
            
            print("Transcribing with Whisper...")
            result = self.model.transcribe(
                audio_path,
                fp16=torch.cuda.is_available(),
                language='en',
            )
            return result["text"]

    def get_transcript(self, video_url: str) -> Dict[str, str]:
        """
        Get transcript for a YouTube video.
        
        Args:
            video_url: The URL of the YouTube video
            
        Returns:
            Dictionary with source (youtube_captions/whisper/error) and text
        
        Raises:
            ValueError: If the video URL is invalid
            RuntimeError: If transcription fails with a specific error
        """
        video_id = extract_video_id(video_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL provided")
        
        try:
            yt = YouTube(
                f"https://www.youtube.com/watch?v={video_id}",
                use_oauth=True,
                allow_oauth_cache=True
            )
        except Exception as e:
            if "detected as a bot" in str(e):
                raise RuntimeError("YouTube detected this as a bot request") from e
            raise RuntimeError(f"Failed to initialize YouTube object: {str(e)}") from e
            
        # Try official captions first
        print("Attempting to get official captions...")
        captions = self._get_youtube_captions(yt)
        
        if captions:
            return {
                "source": "youtube_captions",
                "text": captions
            }
        
        # Fall back to Whisper
        print("No official captions found, using Whisper...")
        try:
            transcript = self._transcribe_with_whisper(video_id, yt)
            return {
                "source": "whisper",
                "text": transcript
            }
        except FileNotFoundError as e:
            raise RuntimeError("FFmpeg not found. Please install FFmpeg to use Whisper transcription.") from e
        except RuntimeError as e:
            raise RuntimeError(f"Whisper transcription failed: {str(e)}") from e

if __name__ == "__main__":
    """Test the YouTube tools"""
    load_dotenv()
    
    # Test video URL
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # Test comments
    print("\n=== Testing Comments Extraction ===")
    comments = YouTubeComments().get_comments(test_url, max_comments=5)
    print(f"Found {len(comments)} comments:")
    for i, comment in enumerate(comments, 1):
        print(f"{i}. {comment['text']} (Likes: {comment['likes']})")
    
    # Test transcript
    print("\n=== Testing Transcript Extraction ===")
    transcript_data = YouTubeTranscript().get_transcript(test_url)
    print(f"Transcript source: {transcript_data['source']}")
    print("First 200 characters:", transcript_data['text'][:200] + "...") 