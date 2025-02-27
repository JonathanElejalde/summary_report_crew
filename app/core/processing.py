from typing import Dict, Any
from app.services import (
    parse_user_query,
    YouTubeSearch,
    analyze_video,
    process_video_batch,
    FinalReportGenerator,
    GoogleDriveManager
)

def _format_metadata(result, video_info):
    return {
        "title": video_info.get("title"),
        "channel": video_info.get("channel_title"),
        "views": video_info.get("view_count"),
        "analysis_type": result.get("analysis_type"),
        "file_path": result.get("file_path")
    }

def _process_single_video(params, youtube_search: YouTubeSearch):
    video_info = youtube_search.get_video_by_url(params.url)
    if not video_info:
        return {"status": "error", "message": "Video not found"}

    result = analyze_video(params.url, video_info, params.analysis_type)
    return {
        "status": "success",
        "type": "single",
        "metadata": _format_metadata(result, video_info),
        "drive_links": result.get("drive_links", {})  # Include drive links from analyze_video
    }
    

def _process_search_query(params, youtube_search, drive_manager):
    videos = youtube_search.search_and_filter(
        query=params.query,
        date_filter=params.date_filter,
        min_views=params.views_filter,
        max_results=3
    )
    
    if not videos:
        return {"status": "error", "message": "No videos found"}

    batch = process_video_batch(videos, params.analysis_type, params.query)
    
    return {
        "status": "success",
        "type": "batch",
        "drive_links": batch.get_drive_links(),  # We need to add this method to BatchResults
        "statistics": batch.get_statistics()
    }

def handle_analysis_request(user_input: str) -> Dict[str, Any]:
    """Orchestrate the entire analysis workflow"""
    query_params = parse_user_query(user_input)
    youtube_search = YouTubeSearch()
    drive_manager = GoogleDriveManager()

    if query_params.url:
        return _process_single_video(query_params, youtube_search)
    return _process_search_query(query_params, youtube_search, drive_manager)

def handle_scheduled_analysis(query_params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle analysis for scheduled jobs using stored parameters"""
    youtube_search = YouTubeSearch()
    drive_manager = GoogleDriveManager()

    if query_params.get('url'):
        return _process_single_video(query_params, youtube_search)
    return _process_search_query(query_params, youtube_search, drive_manager)






