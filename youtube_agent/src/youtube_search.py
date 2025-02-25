from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_agent.src.tools.youtube_tools import extract_video_id

class YouTubeSearch:
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
        now = datetime.utcnow()
        
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
            
        return published_after.isoformat("T") + "Z"
    
    def search_videos(self, query: str, date_filter: str = "24 hours", max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for YouTube videos based on query and date filter.
        
        This method searches YouTube for videos matching the specified query
        and published after the date determined by the date filter.
        
        Args:
            query (str): Search query for finding videos
            date_filter (str): Time frame filter (e.g., "24 hours", "week", "month")
            max_results (int): Maximum number of results to return (default: 10)
            
        Returns:
            List[Dict[str, Any]]: List of video metadata dictionaries, each containing:
                - id (str): Video ID
                - url (str): Full YouTube video URL
                - title (str): Video title
                - channel_title (str): Channel name
                - published_at (str): Publication date/time
                - description (str): Video description
                - thumbnail_url (str): URL of video thumbnail
                
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
                order="relevance",
                publishedAfter=published_after,
                maxResults=max_results
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
                        "thumbnail_url": snippet["thumbnails"]["high"]["url"] if "high" in snippet["thumbnails"] else snippet["thumbnails"]["default"]["url"]
                    })
            
            return videos
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return []
    
    def get_video_statistics(self, video_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for a list of video IDs.
        
        Fetches view count, like count, comment count, and other statistics
        for the specified videos.
        
        Args:
            video_ids (List[str]): List of YouTube video IDs
            
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary mapping video IDs to their statistics:
                {
                    "video_id": {
                        "view_count": int,
                        "like_count": int,
                        "comment_count": int,
                        "favorite_count": int
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
            
            all_stats = {}
            for chunk in video_id_chunks:
                # Execute videos list request
                videos_response = youtube.videos().list(
                    part="statistics",
                    id=",".join(chunk)
                ).execute()
                
                # Extract statistics for each video
                for item in videos_response.get("items", []):
                    video_id = item["id"]
                    statistics = item["statistics"]
                    
                    all_stats[video_id] = {
                        "view_count": int(statistics.get("viewCount", 0)),
                        "like_count": int(statistics.get("likeCount", 0)),
                        "comment_count": int(statistics.get("commentCount", 0)),
                        "favorite_count": int(statistics.get("favoriteCount", 0))
                    }
            
            return all_stats
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return {}
    
    def filter_videos_by_views(self, videos: List[Dict[str, Any]], min_views: int = 5000) -> List[Dict[str, Any]]:
        """
        Filter videos by minimum view count.
        
        This method fetches statistics for the provided videos and filters
        out those with fewer views than the specified minimum.
        
        Args:
            videos (List[Dict[str, Any]]): List of video metadata dictionaries
            min_views (int): Minimum view count for filtering (default: 5000)
            
        Returns:
            List[Dict[str, Any]]: Filtered list of video metadata dictionaries,
                                 with statistics added to each video
        """
        if not videos:
            return []
        
        # Extract video IDs
        video_ids = [video["id"] for video in videos]
        
        # Get statistics for all videos
        statistics = self.get_video_statistics(video_ids)
        
        # Filter videos by view count and add statistics
        filtered_videos = []
        for video in videos:
            video_id = video["id"]
            if video_id in statistics:
                stats = statistics[video_id]
                
                # Only include videos with enough views
                if stats["view_count"] >= min_views:
                    # Add statistics to video metadata
                    video.update({
                        "view_count": stats["view_count"],
                        "like_count": stats["like_count"],
                        "comment_count": stats["comment_count"]
                    })
                    filtered_videos.append(video)
        
        # Sort by view count (descending)
        filtered_videos.sort(key=lambda x: x["view_count"], reverse=True)
        
        return filtered_videos
    
    def search_and_filter(self, query: str, date_filter: str = "24 hours", 
                         min_views: int = 5000, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for videos and filter by view count in one operation.
        
        This is a convenience method that combines searching and filtering.
        
        Args:
            query (str): Search query for finding videos
            date_filter (str): Time frame filter (e.g., "24 hours", "week", "month")
            min_views (int): Minimum view count for filtering (default: 5000)
            max_results (int): Maximum number of final results to return (default: 5)
            
        Returns:
            List[Dict[str, Any]]: Filtered list of video metadata dictionaries
        """
        # Search for videos (get more than we need since we'll filter some out)
        search_results = self.search_videos(query, date_filter, max_results=20)
        
        # Filter by view count
        filtered_videos = self.filter_videos_by_views(search_results, min_views)
        
        # Limit to requested number of results
        return filtered_videos[:max_results]

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
                part="snippet,statistics",
                id=video_id
            ).execute()
            
            # Check if video exists
            if not video_response.get("items"):
                return None
                
            item = video_response["items"][0]
            snippet = item["snippet"]
            statistics = item["statistics"]
            
            return {
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": snippet["title"],
                "channel_title": snippet["channelTitle"],
                "published_at": snippet["publishedAt"],
                "description": snippet["description"],
                "thumbnail_url": snippet["thumbnails"]["high"]["url"] if "high" in snippet["thumbnails"] else snippet["thumbnails"]["default"]["url"],
                "view_count": int(statistics.get("viewCount", 0)),
                "like_count": int(statistics.get("likeCount", 0)),
                "comment_count": int(statistics.get("commentCount", 0))
            }
            
        except HttpError as e:
            print(f"An HTTP error occurred: {e}")
            return None


if __name__ == "__main__":
    # Test the YouTube search functionality
    import dotenv
    dotenv.load_dotenv()

    searcher = YouTubeSearch()
    
    # Test search and filter
    print("\n=== Testing Search and Filter ===")
    query = "machine learning tutorial"
    date_filter = "week"
    min_views = 10000
    
    print(f"Searching for: '{query}' from {date_filter} with at least {min_views} views")
    videos = searcher.search_and_filter(query, date_filter, min_views)
    
    print(f"Found {len(videos)} videos:")
    for i, video in enumerate(videos, 1):
        print(f"\n{i}. {video['title']}")
        print(f"   Channel: {video['channel_title']}")
        print(f"   Views: {video['view_count']:,}")
        print(f"   URL: {video['url']}")
    
    # Test getting video by URL
    print("\n=== Testing Get Video by URL ===")
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Famous video
    video = searcher.get_video_by_url(test_url)
    
    if video:
        print(f"Video: {video['title']}")
        print(f"Channel: {video['channel_title']}")
        print(f"Views: {video['view_count']:,}")
    else:
        print("Video not found")
