from dotenv import load_dotenv
import os
import agentops

from youtube_agent.src.tools.youtube_tools import extract_video_id
from youtube_agent.src.query_parser import parse_user_query
from youtube_agent.src.youtube_search import YouTubeSearch
from youtube_agent.src.batch_processor import analyze_video, process_video_batch
from youtube_agent.src.report_generator import FinalReportGenerator
from youtube_agent.src.google_drive import GoogleDriveManager

from typing import Dict, Any

def get_user_query() -> str:
    """Prompt user for their search query or video URL."""
    return input("\n🔍 What YouTube videos would you like to analyze? ").strip()

def main():
    """
    Main function to run the YouTube video analysis tool.
    
    This function orchestrates the entire analysis process:
    1. Loads environment variables and initializes tracking
    2. Collects user input (search query or video URL)
    3. Parses the query to extract search parameters
    4. If a specific URL is provided, analyzes that video
    5. Otherwise, searches for videos based on the query parameters
    6. Analyzes each video and collects the results
    7. Generates a final consolidated report
    8. Uploads all reports to Google Drive
    9. Displays and saves the analysis results
    
    The function handles the complete workflow from user input to final output,
    including error handling and progress display.
        
    Output:
        - Saves analysis results to docs/report/ or docs/summary/
        - Saves final consolidated report to docs/final/
        - Uploads all reports to Google Drive
        - Displays analysis results in the console
    """
    # Load environment variables
    load_dotenv()

    # Initialize agentops for tracking
    agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))
    
    print("\n🎬 YouTube Video Analysis Tool")
    print("=" * 50)

    # Get user query
    user_input = get_user_query()
    
    # Parse the query to extract parameters
    print("\n🧠 Analyzing your request...")
    query_params = parse_user_query(user_input)
    
    # Display the extracted parameters
    print("\n📊 Analysis Parameters:")
    if query_params.query:
        print(f"Search Query: {query_params.query}")
    if query_params.url:
        print(f"Specific Video URL: {query_params.url}")
    print(f"Date Filter: {query_params.date_filter}")
    print(f"Minimum Views: {query_params.views_filter}")
    print(f"Analysis Type: {query_params.analysis_type.capitalize()}")
    
    # Initialize YouTube search
    youtube_search = YouTubeSearch()
    
    # If a specific URL is provided, analyze that video
    if query_params.url:
        video_url = query_params.url
        analysis_type = query_params.analysis_type
        
        # Get video metadata
        video_info = youtube_search.get_video_by_url(video_url)
        if not video_info:
            print(f"❌ Could not retrieve information for video: {video_url}")
            return
            
        print(f"\n📺 Video: {video_info['title']}")
        print(f"👤 Channel: {video_info['channel_title']}")
        print(f"👁️ Views: {video_info['view_count']:,}")
        print(f"📊 Analysis Type: {analysis_type.capitalize()}")
        
        # Analyze the video
        result = analyze_video(video_url, video_info, analysis_type)
        
        print("\n✨ Analysis Complete!")
        print("=" * 50)
        print("\n🤖 AI Analysis:")
        print("-" * 50)
        print(result["content"])
        print("-" * 50)
        print(f"\n📄 Analysis saved to: {result['file_path']}")
    
    else:
        # Search for videos based on query parameters
        if not query_params.query:
            print("❌ No search query provided. Please specify what to search for.")
            return
            
        print(f"\n🔎 Searching for videos about: {query_params.query}")
        print(f"⏱️ Time frame: {query_params.date_filter}")
        print(f"👁️ Minimum views: {query_params.views_filter}")
        print(f"📊 Analysis Type: {query_params.analysis_type.capitalize()}")
        
        videos = youtube_search.search_and_filter(
            query=query_params.query,
            date_filter=query_params.date_filter,
            min_views=query_params.views_filter,
            max_results=3  # Limit to 3 videos for now
        )
        
        if not videos:
            print(f"❌ No videos found matching your criteria.")
            return
            
        print(f"\n✅ Found {len(videos)} videos:")
        for i, video in enumerate(videos, 1):
            print(f"\n{i}. {video['title']}")
            print(f"   Channel: {video['channel_title']}")
            print(f"   Views: {video['view_count']:,}")
            print(f"   URL: {video['url']}")
        
        # Process videos in batch
        analysis_type = query_params.analysis_type
        batch_results = process_video_batch(
            videos=videos,
            analysis_type=analysis_type,
            query=query_params.query
        )
        
        # Display successful results
        successful_results = batch_results.get_successful_results()
        if successful_results:
            print("\n🎯 Successful Analyses:")
            for i, result in enumerate(successful_results, 1):
                video_info = result["video_info"]
                print(f"\n{i}. {video_info['title']}")
                print(f"   File: {result['file_path']}")
        
        # Generate consolidated final report
        print("\n🔄 Generating final consolidated report...")
        report_generator = FinalReportGenerator()
        final_report = report_generator.generate_final_report(
            batch_results=batch_results,
            query=query_params.query,
            analysis_type=analysis_type
        )
        
        if final_report["status"] == "success":
            print("\n✨ Final Report Generated!")
            print(f"📄 Saved to: {final_report['file_path']}")
            
            print("\n📊 Final Analysis:")
            print("-" * 50)
            # Print first 500 characters of the report with ellipsis
            preview = final_report["content"][:500]
            if len(final_report["content"]) > 500:
                preview += "...\n[Report truncated for display. See full report in the saved file.]"
            print(preview)
            print("-" * 50)
        else:
            print(f"\n❌ Error generating final report: {final_report.get('error', 'Unknown error')}")
        
        # Upload reports to Google Drive
        try:
            print("\n🔄 Uploading reports to Google Drive...")
            drive_manager = GoogleDriveManager()
            
            # Set up folder structure (will use FOLDER_ID from .env if available)
            print("Setting up folder structure...")
            folder_ids = drive_manager.setup_folder_structure()
            
            # Upload individual analysis files
            print("Uploading individual analysis files...")
            uploaded_files = drive_manager.upload_analysis_files(batch_results, folder_ids)
            
            # Upload final report
            print("Uploading final report...")
            uploaded_final = drive_manager.upload_final_report(final_report, folder_ids)
            
            # Collect all uploaded files
            all_uploaded = []
            all_uploaded.extend(uploaded_files.get("summaries", []))
            all_uploaded.extend(uploaded_files.get("reports", []))
            if uploaded_final:
                all_uploaded.append(uploaded_final)
            
            # Display upload results
            print("\n📤 Upload Results:")
            print(f"Summaries: {len(uploaded_files.get('summaries', []))}")
            print(f"Reports: {len(uploaded_files.get('reports', []))}")
            print(f"Final Report: {'✅' if uploaded_final else '❌'}")
            
            # Generate shareable links
            print("\n🔗 Shareable Links:")
            if uploaded_final:
                print(f"Final Report: {uploaded_final['link']}")
            
            # Delete local files after successful upload
            print("\n🗑️ Cleaning up local files...")
            deleted_files = drive_manager.delete_local_files(all_uploaded)
            print(f"Deleted {len(deleted_files)} local files")
            
        except Exception as e:
            print(f"\n❌ Error uploading to Google Drive: {e}")
            print("Local files have been preserved.")

if __name__ == "__main__":
    main()