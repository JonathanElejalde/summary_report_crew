from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel
from .youtube_tools import YouTubeComments, YouTubeTranscript

class CommentsExtractionTool(BaseTool):
    """CrewAI tool for extracting YouTube comments"""
    name: str = "YouTube Comments Extraction Tool"
    description: str = """Extract comments from a YouTube video.
    Returns the most relevant comments including text and likes."""
    args_schema: Type[BaseModel] = BaseModel

    def _run(self, video_url: str, max_comments: int = 200) -> str:
        comments = YouTubeComments().get_comments(video_url, max_comments)
        
        # Format the results as a readable string
        result = f"\nFound {len(comments)} comments:\n"
        for i, comment in enumerate(comments, 1):
            result += f"{i}. Text: {comment['text']}\n"
            result += f"   Likes: {comment['likes']}\n\n"
        
        return result.strip()

class TranscriptExtractionTool(BaseTool):
    """CrewAI tool for extracting YouTube transcripts"""
    name: str = "YouTube Transcript Extraction Tool"
    description: str = """Extract transcript/captions from a YouTube video.
    First tries to get official captions, falls back to Whisper transcription if no captions are available."""
    args_schema: Type[BaseModel] = BaseModel

    def _run(self, video_url: str) -> str:
        transcript_data = YouTubeTranscript().get_transcript(video_url)
        
        result = f"\n=== Transcript ===\n"
        result += f"Source: {transcript_data['source']}\n\n"
        
        if transcript_data['source'] == 'error':
            result += f"Error: {transcript_data['text']}\n"
        else:
            result += f"{transcript_data['text']}\n"
        
        result += "\n" + "="*50 + "\n"
        
        return result.strip() 