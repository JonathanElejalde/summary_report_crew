from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import os
from pathlib import Path

from youtube_agent.src.crew import VideoAnalysisCrew
from youtube_agent.src.tools.youtube_tools import YouTubeComments, YouTubeTranscript
from youtube_agent.src.youtube_search import YouTubeSearch

class BatchResults:
    """
    Class to store and manage batch processing results.
    
    This class provides methods to:
    - Add individual analysis results
    - Get all successful results
    - Get statistics about the batch
    - Save results to disk
    """
    
    def __init__(self, query: Optional[str] = None):
        """
        Initialize a new batch results container.
        
        Args:
            query: Optional search query that generated this batch
        """
        self.results = []
        self.start_time = datetime.now()
        self.end_time = None
        self.query = query
        
        # Create batch directory
        self.batch_id = self.start_time.strftime('%Y%m%d_%H%M%S')
        self.batch_dir = Path("docs") / "batches" / self.batch_id
        self.batch_dir.mkdir(parents=True, exist_ok=True)
    
    def add_result(self, result: Dict[str, Any]):
        """Add a result to the batch."""
        self.results.append(result)
    
    def complete_batch(self):
        """Mark the batch as complete."""
        self.end_time = datetime.now()
    
    def get_successful_results(self):
        """Get all successful results."""
        return [r for r in self.results if r.get("status") == "success"]
    
    def get_failed_results(self):
        """Get all failed results."""
        return [r for r in self.results if r.get("status") == "error"]
    
    def get_statistics(self):
        """Get statistics about the batch."""
        successful = len(self.get_successful_results())
        failed = len(self.get_failed_results())
        total = len(self.results)
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time else None
        
        return {
            "batch_id": self.batch_id,
            "query": self.query,
            "total_videos": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration
        }
    
    def save_metadata(self):
        """Save batch metadata to a JSON file."""
        metadata = {
            "statistics": self.get_statistics(),
            "results": [
                {
                    "video_url": r.get("video_info", {}).get("url") or r.get("video_url"),
                    "video_title": r.get("video_info", {}).get("title"),
                    "status": r.get("status"),
                    "analysis_type": r.get("analysis_type"),
                    "file_path": r.get("file_path"),
                    "error": r.get("error")
                }
                for r in self.results
            ]
        }
        
        metadata_file = self.batch_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return str(metadata_file)


def collect_video_data(url: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Collect transcript and comments data for a YouTube video.
    
    Args:
        url: The YouTube video URL to analyze
        
    Returns:
        Tuple containing transcript text and list of comments
        
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


def analyze_video(video_url: str, video_info: Dict[str, Any], analysis_type: str = "report") -> Dict[str, Any]:
    """
    Analyze a single YouTube video.
    
    Args:
        video_url: The URL of the YouTube video to analyze
        video_info: Metadata about the video
        analysis_type: Type of analysis to perform ("report" or "summary")
        
    Returns:
        Dictionary containing analysis results and metadata
    """
    # Collect video data
    transcript, comments = collect_video_data(video_url)
    
    print(f"\n🔍 Analyzing video: {video_info.get('title', video_url)}")
    print(f"👤 Channel: {video_info.get('channel_title', 'Unknown')}")
    print(f"👁️ Views: {video_info.get('view_count', 'Unknown'):,}")
    print(f"💬 Comments collected: {len(comments)}")
    print(f"📊 Analysis Type: {analysis_type.capitalize()}")
    
    # Initialize the crew manager with all data
    crew_manager = VideoAnalysisCrew(
        video_url=video_url,
        analysis_type=analysis_type,
        video_metadata=video_info
    )
    
    # Get the crew instance and kickoff
    crew = crew_manager.analysis_crew()
    result = crew.kickoff(
        inputs={
            'transcript': transcript,
            'comments': comments,
            'user_prompt': f"Analyze the comments and provide a {analysis_type} of the video",
            'video_metadata': video_info
        }
    )
    
    # Return both the result and metadata
    return {
        "content": result,
        "video_info": video_info,
        "file_path": crew_manager.output_file_path,
        "analysis_type": analysis_type
    }


def process_video_batch(
    videos: List[Dict[str, Any]], 
    analysis_type: str = "summary",
    query: Optional[str] = None
) -> BatchResults:
    """
    Process a batch of YouTube videos.
    
    Args:
        videos: List of video metadata dictionaries
        analysis_type: Type of analysis to perform ("report" or "summary")
        query: Optional search query that generated these videos
        
    Returns:
        BatchResults object containing all results and metadata
    """
    # Initialize batch results
    batch = BatchResults(query=query)
    
    print(f"\n🔄 Starting batch processing of {len(videos)} videos...")
    print(f"📊 Analysis type: {analysis_type.capitalize()}")
    
    # Process each video
    for i, video in enumerate(videos, 1):
        video_title = video.get('title', 'Unknown title')
        video_url = video.get('url')
        
        print(f"\n📽️ Processing video {i}/{len(videos)}: {video_title}")
        
        try:
            # Analyze the video
            result = analyze_video(video_url, video, analysis_type)
            
            # Add success metadata
            result["status"] = "success"
            batch.add_result(result)
            
            print(f"✅ Successfully analyzed video {i}/{len(videos)}")
            
        except Exception as e:
            # Handle errors
            print(f"❌ Error analyzing video {i}/{len(videos)}: {e}")
            
            # Add error metadata
            batch.add_result({
                "video_url": video_url,
                "video_info": video,
                "error": str(e),
                "status": "error",
                "analysis_type": analysis_type
            })
    
    # Mark batch as complete
    batch.complete_batch()
    
    # Save batch metadata
    metadata_file = batch.save_metadata()
    
    # Display batch statistics
    stats = batch.get_statistics()
    print("\n✨ Batch processing complete!")
    print(f"📊 Total videos: {stats['total_videos']}")
    print(f"✅ Successful: {stats['successful']}")
    print(f"❌ Failed: {stats['failed']}")
    print(f"⏱️ Duration: {stats['duration_seconds']:.2f} seconds")
    print(f"📁 Batch metadata saved to: {metadata_file}")
    
    return batch


if __name__ == "__main__":
    """
    Test the batch processing functionality.
    
    This test:
    1. Searches for videos on a test query
    2. Processes them in batch
    3. Displays the results
    """
    from dotenv import load_dotenv
    from youtube_agent.src.youtube_search import YouTubeSearch
    
    # Load environment variables
    load_dotenv()
    
    # Test parameters
    test_query = "machine learning tutorial"
    date_filter = "week"
    min_views = 10000
    analysis_type = "summary"  # Change to "report" to test report generation
    
    print(f"\n🧪 Testing batch processing with query: '{test_query}'")
    print(f"⏱️ Time frame: {date_filter}")
    print(f"👁️ Minimum views: {min_views}")
    print(f"📊 Analysis Type: {analysis_type}")
    
    # Search for videos
    print("\n🔍 Searching for videos...")
    youtube_search = YouTubeSearch()
    videos = youtube_search.search_and_filter(
        query=test_query,
        date_filter=date_filter,
        min_views=min_views,
        max_results=2  # Limit to 2 videos for testing
    )
    
    if not videos:
        print("❌ No videos found matching the criteria.")
        exit()
        
    print(f"\n✅ Found {len(videos)} videos:")
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   URL: {video['url']}")
    
    # Process videos in batch
    print("\n🔄 Processing videos in batch...")
    batch_results = process_video_batch(
        videos=videos,
        analysis_type=analysis_type,
        query=test_query
    )
    
    # Display batch statistics
    stats = batch_results.get_statistics()
    print("\n📊 Batch Statistics:")
    print(f"Total videos: {stats['total_videos']}")
    print(f"Successful: {stats['successful']}")
    print(f"Failed: {stats['failed']}")
    print(f"Success rate: {stats['success_rate'] * 100:.1f}%")
    print(f"Duration: {stats['duration_seconds']:.2f} seconds")
    
    # Display successful results
    successful_results = batch_results.get_successful_results()
    if successful_results:
        print("\n🎯 Successful Analyses:")
        for i, result in enumerate(successful_results, 1):
            video_info = result["video_info"]
            print(f"\n{i}. {video_info['title']}")
            print(f"   File: {result['file_path']}")
    
    print("\n✅ Batch processing test complete!")
