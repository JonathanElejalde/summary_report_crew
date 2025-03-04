from typing import List, Dict, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from app.crew.crew import VideoAnalysisCrew
from app.crew.tools.youtube_tools import YouTubeComments, YouTubeTranscript
from app.services.youtube_search import YouTubeSearch
from app.services.google_drive import GoogleDriveManager
from app.services.report_generator import FinalReportGenerator
from app.models.database import get_db
from app.repositories.processed_video import ProcessedVideoRepository

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

    def get_drive_links(self) -> Dict[str, Any]:
        """Collect all drive links from successful results"""
        all_links = {
            "summaries": [],
            "reports": [],
            "final_report": None  # Initialize as None, not an empty list
        }
        
        # First, collect links from individual results
        for result in self.get_successful_results():
            if "drive_links" in result:
                for link_type in ["summaries", "reports"]:
                    all_links[link_type].extend(result["drive_links"].get(link_type, []))
                
                # If this result has a final_report, use it
                if "final_report" in result["drive_links"] and result["drive_links"]["final_report"]:
                    all_links["final_report"] = result["drive_links"]["final_report"]
        
        # Check if we have a final_report attribute directly on the batch
        if hasattr(self, 'final_report_link') and self.final_report_link:
            all_links["final_report"] = self.final_report_link
        
        return all_links


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


def cleanup_files(file_paths: List[str]) -> None:
    """Remove local files after successful upload."""
    print("\n=== Starting cleanup_files ===")
    for file_path in file_paths:
        print(f"\nAttempting to cleanup: {file_path}")
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                print(f"Successfully deleted file: {file_path}")
                
                # Try to remove parent directory if empty
                parent_dir = path.parent
                if parent_dir.exists() and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    print(f"Removed empty directory: {parent_dir}")
            else:
                print(f"File already deleted: {file_path}")
                
        except Exception as e:
            print(f"Cleanup error for {file_path}: {e}")


def upload_analysis_files(video_info: Dict[str, Any], crew_manager: VideoAnalysisCrew, cleanup: bool = True) -> Dict[str, Any]:
    """Upload analysis files to Drive and return links"""
    print("\n=== Starting upload_analysis_files ===")
    print(f"Output files to process: {crew_manager.output_files}")
    
    drive_manager = GoogleDriveManager()
    folder_ids = drive_manager.setup_folder_structure()
    
    drive_links = {
        "summaries": [],
        "reports": []
    }
    
    successful_uploads = []

    # Upload only existing files
    for file_path in crew_manager.output_files:
        print(f"\nProcessing file: {file_path}")
        path = Path(file_path)
        
        if not path.exists():
            print(f"File does not exist: {file_path}")
            continue
                
        try:
            file_type = "summaries" if "/summary/" in file_path else "reports"
            print(f"Detected file type: {file_type}")
            
            upload_result = drive_manager.upload_file(file_path, folder_ids[file_type])
            print(f"Upload result: {upload_result}")
            
            if upload_result and 'id' in upload_result:
                drive_links[file_type].append({
                    "title": video_info.get("title", "Analysis"),
                    "link": f"https://drive.google.com/file/d/{upload_result['id']}/view",
                    "is_gdoc": upload_result.get('is_gdoc', False)
                })
                successful_uploads.append(file_path)
                print(f"Added to successful uploads: {file_path}")
        except Exception as e:
            print(f"Upload error for {file_path}: {e}")
            continue
    
    print(f"\nSuccessful uploads: {successful_uploads}")
    print(f"Final drive_links: {drive_links}")
    
    # Clean up files only after all uploads are complete and if cleanup is requested
    if successful_uploads and cleanup:
        print("\nStarting cleanup...")
        cleanup_files(successful_uploads)
        print("Cleanup complete")
    
    return drive_links


def upload_final_report(final_report: Dict[str, Any]) -> Dict[str, Any]:
    """Upload final report to Drive and return link"""
    print("\n=== Starting upload_final_report ===")
    
    if final_report.get("status") != "success" or not final_report.get("file_path"):
        print(f"No valid final report to upload: {final_report.get('status')}")
        return None
    
    file_path = final_report.get("file_path")
    path = Path(file_path)
    
    if not path.exists():
        print(f"Final report file does not exist: {file_path}")
        return None
    
    try:
        drive_manager = GoogleDriveManager()
        folder_ids = drive_manager.setup_folder_structure()
        
        # Create a custom name for the final report
        custom_name = f"{datetime.now().strftime('%Y%m%d')}_{final_report.get('query', 'Analysis')}_final.md"
        
        # Upload the file
        upload_result = drive_manager.upload_file(file_path, folder_ids["final"], custom_name)
        print(f"Final report upload result: {upload_result}")
        
        if upload_result and 'id' in upload_result:
            # Clean up the file after successful upload
            cleanup_files([file_path])
            
            return {
                "title": final_report.get("query", "Final Analysis"),
                "link": f"https://drive.google.com/file/d/{upload_result['id']}/view",
                "is_gdoc": upload_result.get('is_gdoc', False)
            }
        
    except Exception as e:
        print(f"Final report upload error: {e}")
    
    return None


def analyze_video(video_url: str, video_info: Dict[str, Any], analysis_type: str = "report", cleanup: bool = True, user_id: str = None, message_id: str = None) -> Dict[str, Any]:
    """Analyze a single video and generate report/summary"""
    try:
        transcript, comments = collect_video_data(video_url)
        
        crew_manager = VideoAnalysisCrew(
            video_url=video_url,
            analysis_type=analysis_type,
            video_metadata=video_info
        )
        
        # Run analysis
        # TODO: think about how to handle the output of the crew
        result = crew_manager.analysis_crew().kickoff(
            inputs={
                'transcript': transcript,
                'comments': comments,
                'user_prompt': f"Analyze this video and provide a {analysis_type}"
            }
        )

        # Upload files and get links, but don't clean up yet if cleanup=False
        drive_links = upload_analysis_files(video_info, crew_manager, cleanup=cleanup)
        
        # Store file paths for later cleanup if needed
        file_paths = [path for path in crew_manager.output_files if Path(path).exists()]
        
        # After successful analysis and before returning the result
        if user_id and video_info.get('id'):
            try:
                db = next(get_db())
                repo = ProcessedVideoRepository(db)
                
                # Save the processed video using the repository
                repo.create(
                    user_id=user_id,
                    video_id=video_info['id'],
                    title=video_info.get('title'),
                    url=video_url,
                    duration=video_info.get('duration'),
                    message_id=message_id
                )
            except Exception as e:
                # Log the error but don't fail the processing
                print(f"Error saving processed video: {str(e)}")
        
        return {
            "status": "success",
            "type": "single",
            "drive_links": drive_links,
            "file_paths": file_paths,  # Store for later cleanup
            "video_info": {  # Add this to match what FinalReportGenerator expects
                "title": video_info.get("title"),
                "url": video_url,
                "channel_title": video_info.get("channel_title"),
                "view_count": video_info.get("view_count")
            },
            "metadata": {
                "title": video_info.get("title"),
                "channel": video_info.get("channel_title"),
                "views": video_info.get("view_count"),
                "analysis_type": analysis_type
            }
        }
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        return {
            "video_url": video_url,
            "error": str(e),
            "status": "error"
        }

def process_video_batch(videos: List[Dict[str, Any]], analysis_type: str = "summary", query: Optional[str] = None, user_id: str = None, message_id: str = None) -> BatchResults:
    """Synchronous batch processing with final report generation"""
    batch = BatchResults(query=query)
    
    for video in videos:
        # Pass cleanup=False to prevent immediate file deletion
        result = analyze_video(video['url'], video, analysis_type, cleanup=False, user_id=user_id, message_id=message_id)
        batch.add_result(result)

    batch.complete_batch()
    batch.save_metadata()
    
    # Generate final report
    final_report_link = None
    if len(batch.get_successful_results()) > 0:
        print("\n📊 Generating final report...")
        report_generator = FinalReportGenerator()
        
        # Just pass the batch object - the FinalReportGenerator will extract file paths
        final_report = report_generator.generate_final_report(
            batch_results=batch,
            query=query, 
            analysis_type=analysis_type
        )
        
        # Upload final report
        if final_report.get("status") == "success":
            final_report_link = upload_final_report(final_report)
            if final_report_link:
                # Add final report link to batch results
                drive_links = batch.get_drive_links()
                drive_links["final_report"] = final_report_link
                # Store the final report link directly on the batch object
                batch.final_report_link = final_report_link
                print(f"\n✅ Added final report link to batch results: {final_report_link}")
                print(f"Updated drive_links: {drive_links}")
    
    # Now that the final report is generated, clean up the individual analysis files
    print("\n🧹 Cleaning up individual analysis files...")
    for result in batch.get_successful_results():
        if "file_paths" in result:
            cleanup_files(result["file_paths"])
    
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
