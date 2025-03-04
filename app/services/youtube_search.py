from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.crew.tools.youtube_tools import extract_video_id


class YouTubeSearch:
    YOUTUBE_SEARCH_MAX_RESULTS = int(os.getenv("YOUTUBE_SEARCH_MAX_RESULTS", 50))
    MIN_DURATION_MINUTES = int(os.getenv("MIN_DURATION_MINUTES", 10))
    MAX_DURATION_MINUTES = int(os.getenv("MAX_DURATION_MINUTES", 150))

    """
    Class for searching and filtering YouTube videos.
    
    This class handles YouTube API search requests with various filters
    including date ranges and view counts. It provides methods to search
    for videos and filter results based on specified criteria.
    
    Attributes:
        api_key (str): YouTube Data API key for authentication
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
    
    def _convert_date_filter_to_published_after(self, date_filter: str) -> str:
        """
        Convert a date filter string to an ISO 8601 datetime string.
        
        Maps common time frame descriptions to specific datetime ranges.
        
        Args:
            date_filter (str): Date filter description (e.g., "24 hours", "week", "month")
            
        Returns:
            str: ISO 8601 formatted datetime string for the publishedAfter parameter
            
        Examples:
            "24 hours" -> (current datetime - 1 day) in ISO format
            "week" -> (current datetime - 7 days) in ISO format
            "month" -> (current datetime - 30 days) in ISO format
            "year" -> (current datetime - 365 days) in ISO format
        """
        # Replace deprecated datetime.utcnow() with timezone-aware alternative
        now = datetime.now(timezone.utc)
        
        if date_filter == "24 hours" or date_filter.lower() == "today":
            published_after = now - timedelta(days=1)
        elif date_filter.lower() in ["week", "this week", "last week"]:
            published_after = now - timedelta(days=7)
        elif date_filter.lower() in ["month", "this month", "last month"]:
            published_after = now - timedelta(days=30)
        elif date_filter.lower() in ["year", "this year", "last year"]:
            published_after = now - timedelta(days=365)
        else:
            # Default to 24 hours if the date filter is not recognized
            published_after = now - timedelta(days=1)
            
        return published_after.isoformat()
    
    def _parse_duration_to_seconds(self, duration: str) -> int:
        """
        Parse ISO 8601 duration format to seconds.
        
        Args:
            duration (str): Duration in ISO 8601 format (e.g., 'PT1H30M15S')
            
        Returns:
            int: Duration in seconds
        """
        import re
        import datetime
        
        # Extract hours, minutes, seconds from ISO 8601 duration
        hours = re.search(r'(\d+)H', duration)
        minutes = re.search(r'(\d+)M', duration)
        seconds = re.search(r'(\d+)S', duration)
        
        hours = int(hours.group(1)) if hours else 0
        minutes = int(minutes.group(1)) if minutes else 0
        seconds = int(seconds.group(1)) if seconds else 0
        
        return hours * 3600 + minutes * 60 + seconds
    
    
    def search_videos(self, query: str, date_filter: str = "24 hours", 
                     video_duration: str = "any") -> List[Dict[str, Any]]:
        """
        Search for YouTube videos based on query and date filter.
        
        This method searches YouTube for videos matching the specified query
        and published after the date determined by the date filter.
        
        Args:
            query (str): Search query for finding videos
            date_filter (str): Time frame filter (e.g., "24 hours", "week", "month")
            video_duration (str): Duration filter ('any', 'short', 'medium', 'long')
                                 short: < 4 min, medium: 4-20 min, long: > 20 min
            
        Returns:
            List[Dict[str, Any]]: List of video metadata dictionaries
                
        Raises:
            HttpError: If there's an error with the YouTube API request
        """
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            # Convert date filter to publishedAfter parameter
            published_after = self._convert_date_filter_to_published_after(date_filter)
            
            # Execute search request
            search_response = youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                videoDuration=video_duration,  # Add duration filter
                order="relevance",
                publishedAfter=published_after,
                maxResults=self.YOUTUBE_SEARCH_MAX_RESULTS
            ).execute()
            
            # Extract video information from search results
            videos = []
            for item in search_response.get("items", []):
                if item["id"]["kind"] == "youtube#video":
                    video_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    
                    videos.append({
                        "id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": snippet["title"],
                        "channel_title": snippet["channelTitle"],
                        "published_at": snippet["publishedAt"],
                        "description": snippet["description"],
                    })
            
            return videos
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return []
    
    def get_video_details(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get combined statistics and content details for a list of video IDs.
        
        This method combines what was previously separate calls for statistics and duration
        into a single API call to reduce API usage costs.
        
        Args:
            video_ids (List[str]): List of YouTube video IDs
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping video IDs to their details:
                {
                    "video_id": {
                        "view_count": int,
                        "like_count": int,
                        "comment_count": int,
                        "favorite_count": int,
                        "duration": str,
                        "duration_seconds": int
                    },
                    ...
                }
                
        Raises:
            HttpError: If there's an error with the YouTube API request
        """
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            # Split video IDs into chunks of 50 (API limit)
            video_id_chunks = [video_ids[i:i+50] for i in range(0, len(video_ids), 50)]
            
            all_details = {}
            for chunk in video_id_chunks:
                # Execute videos list request with both statistics and contentDetails parts
                videos_response = youtube.videos().list(
                    part="statistics,contentDetails",
                    id=",".join(chunk)
                ).execute()
                
                # Extract details for each video
                for item in videos_response.get("items", []):
                    video_id = item["id"]
                    statistics = item["statistics"]
                    content_details = item["contentDetails"]
                    
                    # Parse duration
                    duration_str = content_details["duration"]
                    duration_seconds = self._parse_duration_to_seconds(duration_str)
                    
                    all_details[video_id] = {
                        "view_count": int(statistics.get("viewCount", 0)),
                        "like_count": int(statistics.get("likeCount", 0)),
                        "comment_count": int(statistics.get("commentCount", 0)),
                        "favorite_count": int(statistics.get("favoriteCount", 0)),
                        "duration": duration_str,
                        "duration_seconds": duration_seconds
                    }
            
            return all_details
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return {}
    
    def filter_videos(self, videos: List[Dict[str, Any]], min_views: int = 5000, 
                     min_duration_seconds: int = 9000) -> List[Dict[str, Any]]:
        """
        Filter videos by minimum view count and duration in one operation.
        
        This method combines what was previously separate filtering methods to reduce API calls.
        
        Args:
            videos (List[Dict[str, Any]]): List of video metadata dictionaries
            min_views (int): Minimum view count for filtering (default: 5000)
            min_duration_seconds (int): Minimum duration in seconds (default: 9000 seconds = 2.5 hours)
            
        Returns:
            List[Dict[str, Any]]: Filtered list of video metadata dictionaries
        """
        if not videos:
            return []
        
        # Extract video IDs
        video_ids = [video["id"] for video in videos]
        
        # Get combined details for all videos
        details = self.get_video_details(video_ids)
        
        # Filter videos by both view count and duration
        filtered_videos = []
        for video in videos:
            video_id = video["id"]
            if video_id in details:
                video_details = details[video_id]
                
                # Only include videos with enough views AND sufficient duration
                if (video_details["view_count"] >= min_views and 
                    video_details["duration_seconds"] >= min_duration_seconds):
                    
                    # Add details to video metadata
                    video.update({
                        "view_count": video_details["view_count"],
                        "like_count": video_details["like_count"],
                        "comment_count": video_details["comment_count"],
                        "duration": video_details["duration"],
                        "duration_seconds": video_details["duration_seconds"]
                    })
                    filtered_videos.append(video)
        
        # Sort by view count (descending)
        filtered_videos.sort(key=lambda x: x["view_count"], reverse=True)
        
        return filtered_videos
    
    def search_and_filter(self, query: str, date_filter: str = "24 hours", 
                         min_views: int = 5000, max_results: int = 3,
                         exclude_video_ids: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for videos and filter by view count and duration in one operation.
        
        This method processes videos in order of relevance (as returned by YouTube API)
        and stops once it has found enough videos that meet the criteria.
        
        Args:
            query (str): Search query for finding videos
            date_filter (str): Time frame filter (e.g., "24 hours", "week", "month")
            min_views (int): Minimum view count for filtering (default: 5000)
            max_results (int): Maximum number of final results to return (default: 3)
            exclude_video_ids (List[str]): List of video IDs to exclude from results
            
        Returns:
            List[Dict[str, Any]]: Filtered list of video metadata dictionaries
        """
        # Get search results sorted by relevance
        search_results = self.search_videos(query, date_filter, video_duration="any")
        
        # Define our duration range in seconds
        min_seconds = self.MIN_DURATION_MINUTES * 60
        max_seconds = self.MAX_DURATION_MINUTES * 3600
        
        # Process videos in batches to minimize API calls
        filtered_videos = []
        batch_size = 10  # Process 10 videos at a time
        
        for i in range(0, len(search_results), batch_size):
            # If we already have enough videos, stop processing
            if len(filtered_videos) >= max_results:
                break
                
            # Get the next batch of videos
            batch = search_results[i:i+batch_size]
            video_ids = [video["id"] for video in batch]
            
            # Get details for this batch
            details = self.get_video_details(video_ids)
            
            # Filter this batch
            for video in batch:
                video_id = video["id"]
                if video_id in details:
                    video_details = details[video_id]
                    duration_seconds = video_details["duration_seconds"]
                    view_count = video_details["view_count"]
                    
                    # Only include videos with enough views AND within the specified duration range
                    if (view_count >= min_views and 
                        min_seconds <= duration_seconds <= max_seconds):
                        
                        # Add details to video metadata
                        video.update({
                            "view_count": view_count,
                            "like_count": video_details["like_count"],
                            "comment_count": video_details["comment_count"],
                            "duration": video_details["duration"],
                            "duration_seconds": duration_seconds
                        })
                        filtered_videos.append(video)
                        
                        # If we have enough videos, stop processing
                        if len(filtered_videos) >= max_results:
                            break
        
        # Add filtering for already processed videos
        if exclude_video_ids:
            filtered_videos = [video for video in filtered_videos 
                              if video['id'] not in exclude_video_ids]
        
        return filtered_videos

    def get_video_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video metadata for a specific YouTube URL.
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            Optional[Dict[str, Any]]: Video metadata dictionary or None if not found
        """
        video_id = extract_video_id(url)
        if not video_id:
            return None
            
        try:
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            # Get video details
            video_response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=video_id
            ).execute()
            
            # Check if video exists
            if not video_response.get("items"):
                return None
                
            item = video_response["items"][0]
            snippet = item["snippet"]
            statistics = item["statistics"]
            content_details = item["contentDetails"]
            
            # Parse duration
            duration_str = content_details["duration"]
            duration_seconds = self._parse_duration_to_seconds(duration_str)
            
            return {
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet["title"],
                "channel_title": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "description": snippet["description"],
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0)),
                "duration": duration_str,
                "duration_seconds": duration_seconds
            }
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None



if __name__ == "__main__":
    # Test the YouTube search functionality
    import dotenv
    import time
    dotenv.load_dotenv()

    searcher = YouTubeSearch()
    
    # Test search and filter
    print("\n=== Testing Search and Filter ===")
    query = "Ai agent tutorials"
    date_filter = "week"
    min_views = 10000
    min_duration_minutes = 10
    max_duration_hours = 2.5
    
    print(f"Searching for: '{query}' from {date_filter} with at least {min_views} views")
    print(f"Duration range: {min_duration_minutes} minutes to {max_duration_hours} hours")
    
    # Track time to measure performance
    start_time = time.time()
    
    videos = searcher.search_and_filter(
        query, date_filter, min_views, 
        min_duration_minutes=min_duration_minutes,
        max_duration_hours=max_duration_hours
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Found {len(videos)} videos in {elapsed_time:.2f} seconds:")
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   Duration: {video['duration']} ({video['duration_seconds']/60:.1f} minutes)")
        print(f"   URL: {video['url']}")
    
    # Test with different parameters
    print("\n=== Testing with Different Parameters ===")
    query = "podcast interview"
    date_filter = "month"
    min_views = 50000
    min_duration_minutes = 30
    max_duration_hours = 3.0
    max_results = 3
    
    print(f"Searching for: '{query}' from {date_filter} with at least {min_views} views")
    print(f"Duration range: {min_duration_minutes} minutes to {max_duration_hours} hours")
    print(f"Max results: {max_results}")
    
    start_time = time.time()
    
    videos = searcher.search_and_filter(
        query, date_filter, min_views, max_results,
        min_duration_minutes=min_duration_minutes,
        max_duration_hours=max_duration_hours
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Found {len(videos)} videos in {elapsed_time:.2f} seconds:")
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   Duration: {video['duration']} ({video['duration_seconds']/60:.1f} minutes)")
        print(f"   URL: {video['url']}")
    
    # Test batch processing behavior
    print("\n=== Testing Batch Processing Behavior ===")
    
    # Create a subclass to track batch processing
    class TrackedYouTubeSearch(YouTubeSearch):
        def get_video_details(self, video_ids):
            print(f"  Getting details for batch of {len(video_ids)} videos...")
            return super().get_video_details(video_ids)
    
    tracked_searcher = TrackedYouTubeSearch()
    
    query = "ted talks"
    date_filter = "month"
    min_views = 100000
    min_duration_minutes = 15
    max_duration_hours = 1.0
    max_results = 2  # Small number to test early stopping
    
    print(f"Searching for: '{query}' from {date_filter} with at least {min_views} views")
    print(f"Duration range: {min_duration_minutes} minutes to {max_duration_hours} hours")
    print(f"Max results: {max_results} (Testing early stopping)")
    
    start_time = time.time()
    
    videos = tracked_searcher.search_and_filter(
        query, date_filter, min_views, max_results,
        min_duration_minutes=min_duration_minutes,
        max_duration_hours=max_duration_hours
    )
    
    elapsed_time = time.time() - start_time
    
    print(f"Found {len(videos)} videos in {elapsed_time:.2f} seconds:")
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   Duration: {video['duration']} ({video['duration_seconds']/60:.1f} minutes)")
        print(f"   URL: {video['url']}")
    
    # Test getting video by URL
    print("\n=== Testing Get Video by URL ===")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Famous video
    video = searcher.get_video_by_url(test_url)
    
    if video:
        print(f"Video: {video['title']}")
        print(f"Channel: {video['channel_title']}")
        print(f"Views: {video['view_count']:,}")
        print(f"Duration: {video['duration']} ({video['duration_seconds']/60:.2f} minutes)")
    else:
        print("Video not found")
