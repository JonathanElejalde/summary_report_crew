from dotenv import load_dotenv
import os
import agentops

from src.video_analysis.crew import VideoAnalysisCrew
from src.video_analysis.tools.youtube_tools import (
    extract_video_id,
    YouTubeComments,
    YouTubeTranscript
)

from typing import Tuple, Dict, Any, List

def get_youtube_url() -> str:
    """Prompt user for YouTube URL and validate it."""
    while True:
        url = input("\n🎥 Please enter the YouTube video URL: ").strip()
        video_id = extract_video_id(url)
        
        if video_id:
            return url
        print("❌ Invalid YouTube URL. Please enter a valid YouTube video URL.")

def get_analysis_type() -> str:
    """Prompt user for analysis type preference."""
    while True:
        print("\n📊 What type of analysis would you like?")
        print("1. Detailed Report - A comprehensive analysis of the video")
        print("2. Concise Summary - Key points and main takeaways")
        
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == "1":
            return "report"
        elif choice == "2":
            return "summary"
        print("❌ Invalid choice. Please enter 1 for Report or 2 for Summary.")

def collect_video_data(url: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Collect transcript and comments data for a YouTube video.
    
    This function handles both transcript extraction and comment collection.
    For transcripts, it first attempts to get official captions and falls back
    to Whisper transcription if needed. For comments, it collects up to the
    specified maximum number of comments.
    
    Args:
        url (str): The YouTube video URL to analyze
        
    Returns:
        Tuple[str, List[Dict[str, Any]]]: A tuple containing:
            - str: The video transcript text
            - List[Dict[str, Any]]: List of comment dictionaries, each containing:
                - text (str): The comment text
                - likes (int): Number of likes on the comment
                
    Raises:
        RuntimeError: If transcript extraction fails
        ValueError: If the URL is invalid
    """
    print("\n📥 Collecting video data...")
    
    # Get transcript
    print("Getting video transcript...")
    transcript_data = YouTubeTranscript().get_transcript(url)
    if transcript_data["source"] == "error":
        raise RuntimeError(f"Failed to get transcript: {transcript_data['text']}")
    transcript = transcript_data["text"]
    
    # Get comments
    print("Getting video comments...")
    try:
        comments = YouTubeComments().get_comments(url, max_comments=200)
        print(f"Retrieved {len(comments)} comments")
    except Exception as e:
        print(f"Warning: Failed to get comments: {e}")
        comments = []

    return transcript, comments

def main():
    """
    Main function to run the YouTube video analysis tool.
    
    This function orchestrates the entire analysis process:
    1. Loads environment variables and initializes tracking
    2. Collects user input (video URL and analysis type)
    3. Extracts video data (transcript and comments)
    4. Initializes and runs the AI analysis crew
    5. Displays and saves the analysis results
    
    The function handles the complete workflow from user input to final output,
    including error handling and progress display.
        
    Output:
        - Saves analysis results to docs/report/ or docs/summary/
        - Displays analysis results in the console
    """
    # Load environment variables
    load_dotenv()

    # Initialize agentops for tracking
    agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))
    
    print("\n🎬 YouTube Video Analysis Tool")
    print("=" * 50)

    # Get user inputs
    video_url = get_youtube_url()
    analysis_type = get_analysis_type()
    
    # Collect video data
    transcript, comments = collect_video_data(video_url)
    
    print("\n🔍 Starting Analysis...")
    print("=" * 50)
    print(f"Video URL: {video_url}")
    print(f"Analysis Type: {analysis_type.capitalize()}")
    print(f"Comments collected: {len(comments)}")
    
    print("\n💬 Original Comments (top 5):")
    print("-" * 50)
    for i, comment in enumerate(comments[:5], 1):
        print(f"{i}. Likes: {comment['likes']}")
        print(f"   {comment['text']}\n")
    print("-" * 50)
    
    print("\n📝 Transcript:")
    print("-" * 50)
    print(transcript[:1000] + "..." if len(transcript) > 1000 else transcript)
    print("-" * 50)
    print("=" * 50)
    
    # Initialize the crew manager with all data
    crew_manager = VideoAnalysisCrew(
        video_url=video_url,
        analysis_type=analysis_type
    )
    
    # Get the crew instance and kickoff
    crew = crew_manager.analysis_crew()
    result = crew.kickoff(
        inputs={
            'transcript': transcript,
            'comments': comments,
            'user_prompt': f"Analyze the comments and provide a {analysis_type} of the video"
        }
    )
    
    print("\n✨ Analysis Complete!")
    print("=" * 50)
    print("\n🤖 AI Analysis:")
    print("-" * 50)
    print(result)
    print("-" * 50)
    
    print("\n💭 Original Comments (top 5):")
    print("-" * 50)
    for i, comment in enumerate(comments[:5], 1):
        print(f"{i}. Likes: {comment['likes']}")
        print(f"   {comment['text']}\n")
    print("-" * 50)
    
    print("\n📜 Original Transcript:")
    print("-" * 50)
    print(transcript[:1000] + "..." if len(transcript) > 1000 else transcript)
    print("-" * 50)
    print("=" * 50)

if __name__ == "__main__":
    main()
