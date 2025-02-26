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

def _process_single_video(params, youtube_search):
    video_info = youtube_search.get_video_by_url(params.url)
    if not video_info:
        return {"status": "error", "message": "Video not found"}

    result = analyze_video(params.url, video_info, params.analysis_type)
    return {
        "status": "success",
        "type": "single",
        "content": result["content"],
        "metadata": _format_metadata(result, video_info)
    }

def _handle_drive_upload(batch, report, drive_manager):
    try:
        folder_ids = drive_manager.setup_folder_structure()
        uploaded_files = drive_manager.upload_analysis_files(batch, folder_ids)
        final_report = drive_manager.upload_final_report(report, folder_ids)
        
        return {
            "summaries": [f["link"] for f in uploaded_files.get("summaries", [])],
            "reports": [f["link"] for f in uploaded_files.get("reports", [])],
            "final_report": final_report["link"] if final_report else None
        }
    except Exception as e:
        return {"error": str(e)}
    

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
    report = FinalReportGenerator().generate_final_report(batch, params.query, params.analysis_type)
    
    drive_links = _handle_drive_upload(batch, report, drive_manager)
    return {
        "status": "success",
        "type": "batch",
        "preview": report["content"][:500] + "..." if report["content"] else "",
        "drive_links": drive_links,
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






