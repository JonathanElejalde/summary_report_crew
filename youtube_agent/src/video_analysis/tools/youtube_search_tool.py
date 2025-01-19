from typing import List, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class YouTubeSearchInput(BaseModel):
    """Input schema for YouTubeSearchTool."""
    query: str = Field(
        ..., 
        description="The search query string to find relevant YouTube videos"
    )
    max_results: int = Field(
        default=10, 
        description="Maximum number of results to return",
        ge=1,
        le=50
    )

class YouTubeSearchTool(BaseTool):
    name: str = "YouTube Search Tool"
    description: str = "Searches YouTube for videos matching the given query and returns their video IDs"
    args_schema: Type[BaseModel] = YouTubeSearchInput

    def _run(self, query: str, max_results: int = 10) -> List[str]:
        """
        Search YouTube for videos matching the search query.
        Replace this implementation with actual API calls.
        
        Args:
            query: The search query string
            max_results: Maximum number of results to return (default: 10)
            
        Returns:
            list: List of video IDs matching the search query
        """
        # Placeholder data for testing
        sample_videos = [
            {
                "video_id": "abc123",
                "title": "Introduction to AI - Latest Developments 2024",
                "channel": "TechInsights",
                "views": 150000,
                "published_date": "2024-01-15",
                "thumbnail": "https://example.com/thumbnail1.jpg"
            },
            {
                "video_id": "def456",
                "title": "Machine Learning Breakthroughs - A Deep Dive",
                "channel": "AI Academy",
                "views": 75000,
                "published_date": "2024-01-10",
                "thumbnail": "https://example.com/thumbnail2.jpg"
            },
            {
                "video_id": "ghi789",
                "title": "The Future of Artificial Intelligence",
                "channel": "Future Tech Today",
                "views": 200000,
                "published_date": "2024-01-05",
                "thumbnail": "https://example.com/thumbnail3.jpg"
            }
        ]
        
        return [video['video_id'] for video in sample_videos]