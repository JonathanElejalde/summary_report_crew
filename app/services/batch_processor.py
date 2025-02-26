from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from app.crew.crew import VideoAnalysisCrew
from app.crew.tools.youtube_tools import YouTubeComments, YouTubeTranscript
from app.services.youtube_search import YouTubeSearch

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
    """Synchronous video analysis"""
    try:
        transcript, comments = collect_video_data(video_url)
        
        crew_manager = VideoAnalysisCrew(
            video_url=video_url,
            analysis_type=analysis_type,
            video_metadata=video_info
        )
        
        result = crew_manager.analysis_crew().kickoff(
            inputs={
                'transcript': transcript,
                'comments': comments,
                'user_prompt': f"Analyze the comments and provide a {analysis_type} of the video",
                'video_metadata': video_info
            }
        )
        
        return {
            "content": result,
            "video_info": video_info,
            "file_path": crew_manager.output_file_path,
            "analysis_type": analysis_type,
            "status": "success"
        }
    except Exception as e:
        return {
            "video_url": video_url,
            "error": str(e),
            "status": "error"
        }

def process_video_batch(videos: List[Dict[str, Any]], analysis_type: str = "summary", query: Optional[str] = None) -> BatchResults:
    """Synchronous batch processing"""
    batch = BatchResults(query=query)
    
    for video in videos:
        result = analyze_video(video['url'], video, analysis_type)
        batch.add_result(result)
    
    batch.complete_batch()
    batch.save_metadata()
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
    from app.services.youtube_search import YouTubeSearch
    
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
