from typing import List, Dict, Any, Optional
from pathlib import Path
import os
import json
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

class FinalReportGenerator:
    """
    Class for generating consolidated final reports from individual video analyses.
    
    This class reads individual summaries and reports from a batch processing run
    and generates a comprehensive final report that synthesizes the findings across
    all videos.
    """
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the report generator.
        
        Args:
            model (str): The LLM model to use for report generation
        """
        self.model = model
        self.llm = ChatOpenAI(model=model, temperature=0.7)
    
    def _read_file_content(self, file_path: str) -> str:
        """Read content from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return f"[Error reading file: {e}]"
        
    def _create_prompt_template(self, analysis_type: str) -> PromptTemplate:
        """Create the appropriate prompt template based on analysis type."""
        if analysis_type == "report":
            template = """
            You are an expert content analyst tasked with creating a comprehensive consolidated report.
            
            ORIGINAL QUERY: {query}
            
            You have been provided with analyses of {num_videos} different YouTube videos related to this query.
            Your task is to synthesize these analyses into a single, cohesive final report that provides
            a complete picture of the topic across all videos.
            
            INDIVIDUAL ANALYSES:
            {analyses}
            
            Create a comprehensive final report that:
            1. Introduces the topic and provides context
            2. Synthesizes the main themes, arguments, and insights across all videos
            3. Highlights areas of consensus and disagreement
            4. Identifies the most valuable insights and takeaways
            5. Provides a thoughtful conclusion that addresses the original query
            
            Use proper markdown formatting with clear section headers, bullet points where appropriate,
            and quotes from the original analyses when relevant. Be thorough and insightful while
            maintaining a professional tone.
            
            FINAL REPORT:
            """
        else:  # summary
            template = """
            You are an expert content analyst tasked with creating a concise consolidated summary.
            
            ORIGINAL QUERY: {query}
            
            You have been provided with summaries of {num_videos} different YouTube videos related to this query.
            Your task is to synthesize these summaries into a single, cohesive final summary that captures
            the essential information across all videos.
            
            INDIVIDUAL SUMMARIES:
            {analyses}
            
            Create a focused final summary that:
            1. Clearly states the core message/theme across all videos
            2. Presents the most important key takeaways. DO NOT limit yourself to specific amount of points. 
               Create as many points as you see fit to get a comprehensive overview.
            3. Highlights areas of consensus in the community
            4. Directly addresses the original query
            5. Create a complete summary, don't limit to specific amount of paragraphs. If you need to use multiple steps
               to explain everything, do it.
            
            Use proper markdown formatting with clear section headers and bullet points for key takeaways.
            Be concise but comprehensive, ensuring no crucial information is lost.
            
            FINAL SUMMARY:
            """
        
        return PromptTemplate(
            template=template,
            input_variables=["query", "analyses", "num_videos"]
        )
    
    def collect_analysis_files(self, batch_results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Collect all analysis files from a batch processing run.
        
        Args:
            batch_results: BatchResults object or dictionary with results metadata
            
        Returns:
            Dictionary with lists of report and summary files with their content
        """
        reports = []
        summaries = []
        
        # Check if batch_results is a BatchResults object
        if hasattr(batch_results, 'get_successful_results'):
            print("Processing BatchResults object")
            results = batch_results.get_successful_results()
        else:
            # Handle dictionary case
            print("Processing dictionary results")
            results = batch_results.get("results", [])
        
        print(f"Found {len(results)} results to process")
        
        # Process each result
        for result in results:
            if result.get("status") != "success":
                continue
                
            file_path = result.get("file_path")
            if not file_path or not os.path.exists(file_path):
                print(f"File not found or invalid path: {file_path}")
                continue
                
            print(f"Reading file: {file_path}")
            content = self._read_file_content(file_path)
            
            file_info = {
                "video_title": result.get("video_info", {}).get("title", "Unknown"),
                "video_url": result.get("video_info", {}).get("url", ""),
                "file_path": file_path,
                "content": content
            }
            
            # Categorize as report or summary
            if "/report/" in file_path:
                reports.append(file_info)
                print(f"Added as report: {file_path}")
            elif "/summary/" in file_path:
                summaries.append(file_info)
                print(f"Added as summary: {file_path}")
        
        print(f"Collected {len(reports)} reports and {len(summaries)} summaries")
        
        return {
            "reports": reports,
            "summaries": summaries
        }
    
    def generate_final_report(self, 
                             batch_results: Dict[str, Any], 
                             query: str, 
                             analysis_type: str = "report") -> Dict[str, Any]:
        """
        Generate a final consolidated report from individual analyses.
        
        Args:
            batch_results: BatchResults object or dictionary with results metadata
            query: The original search query
            analysis_type: Type of analysis ("report" or "summary")
            
        Returns:
            Dictionary with the final report content and metadata
        """
        # Collect all analysis files
        analysis_files = self.collect_analysis_files(batch_results)
        reports = analysis_files["reports"]
        summaries = analysis_files["summaries"]
        
        # Determine which files to use based on analysis type
        if analysis_type == "report":
            # For reports, use both summaries and reports if available
            analysis_content = reports if reports else summaries
        else:
            # For summaries, use only summaries
            analysis_content = summaries
        
        if not analysis_content:
            return {
                "status": "error",
                "error": "No analysis files found",
                "content": "Could not generate final report: No analysis files found."
            }
        
        # Create prompt for final report generation
        prompt_template = self._create_prompt_template(analysis_type)
        
        # Format the analyses for the prompt
        formatted_analyses = []
        for i, analysis in enumerate(analysis_content, 1):
            formatted_analyses.append(
                f"ANALYSIS {i}: {analysis['video_title']}\n"
                f"URL: {analysis['video_url']}\n\n"
                f"{analysis['content']}\n\n"
                f"{'=' * 50}\n"
            )
        
        analyses_text = "\n".join(formatted_analyses)
        
        # Generate the final report
        chain = prompt_template | self.llm | StrOutputParser()
        final_report = chain.invoke({
            "query": query,
            "analyses": analyses_text,
            "num_videos": len(analysis_content)
        })
        
        # Create output file path
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_query = "".join(c for c in query if c.isalnum() or c in " -_").strip()[:30]
        filename = f"{timestamp}_{safe_query}_final_{analysis_type}.md"
        
        output_dir = Path("docs") / "final"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / filename
        
        # Save the final report
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_report)
        
        return {
            "status": "success",
            "content": final_report,
            "file_path": str(output_file),
            "analysis_type": analysis_type,
            "query": query,
            "num_videos": len(analysis_content)
        }
    
if __name__ == "__main__":
    """
    Test the report generator functionality.
    
    This test:
    1. Finds analysis files in the docs/report and docs/summary directories
    2. Generates a final report from those files
    3. Displays the report
    """
    from dotenv import load_dotenv
    import glob
    from pathlib import Path
    
    # Load environment variables
    load_dotenv()
    
    print("\n🧪 Testing report generator")
    
    # Get query from user
    query = input("\n🔍 Enter the query for this analysis: ")
    
    # Choose analysis type
    analysis_type = input("\n📊 Enter analysis type (report/summary) [default: report]: ").strip().lower()
    if not analysis_type or analysis_type not in ["report", "summary"]:
        analysis_type = "report"
    
    # Find analysis files directly
    report_files = list(Path("docs/report").glob("*.md"))
    summary_files = list(Path("docs/summary").glob("*.md"))
    
    print(f"\n📁 Found {len(report_files)} report files and {len(summary_files)} summary files")
    
    # Create a mock batch results structure
    mock_batch_results = {
        "results": []
    }
    
    # Add report files to mock results
    for file_path in report_files:
        mock_batch_results["results"].append({
            "status": "success",
            "file_path": str(file_path),
            "video_title": file_path.stem,  # Use filename as title
            "video_url": "https://www.youtube.com/watch?v=example",  # Placeholder URL
            "analysis_type": "report"
        })
    
    # Add summary files to mock results
    for file_path in summary_files:
        mock_batch_results["results"].append({
            "status": "success",
            "file_path": str(file_path),
            "video_title": file_path.stem,  # Use filename as title
            "video_url": "https://www.youtube.com/watch?v=example",  # Placeholder URL
            "analysis_type": "summary"
        })
    
    if not report_files and not summary_files:
        print("❌ No analysis files found in docs/report or docs/summary directories.")
        exit()
    
    print(f"\n🔄 Generating final {analysis_type} for query: '{query}'")
    
    # Initialize report generator
    report_generator = FinalReportGenerator()
    
    # Generate final report
    final_report = report_generator.generate_final_report(
        batch_results=mock_batch_results,
        query=query,
        analysis_type=analysis_type
    )
    
    # Display results
    if final_report["status"] == "success":
        print("\n✨ Final Report Generated!")
        print(f"📄 Saved to: {final_report['file_path']}")
        
        print("\n📊 Final Report Preview:")
        print("-" * 50)
        # Print first 500 characters of the report with ellipsis
        preview = final_report["content"][:500]
        if len(final_report["content"]) > 500:
            preview += "...\n[Report truncated for display. See full report in the saved file.]"
        print(preview)
        print("-" * 50)
    else:
        print(f"\n❌ Error generating final report: {final_report.get('error', 'Unknown error')}")
    
    print("\n✅ Report generator test complete!")


