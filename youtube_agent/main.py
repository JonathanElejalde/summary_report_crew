import os
from src.video_analysis.crew import VideoAnalysisCrew
import agentops

def main():
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    agentops.init(api_key=os.getenv("AGENTOPS_API_KEY"))

    # Test query that will work with our placeholder data
    # Note: These video IDs match our sample data in metadata_extraction_tool
    test_query = {
        #"user_input": "Analyze recent developments in AI technology focusing on machine learning breakthroughs and future implications. Use these videos for analysis: abc123, def456, ghi789",
        "user_input": "Give the summary of these videos: abc123, def456, ghi789",
        "analysis_focus": [
            "Key technological breakthroughs",
            "Real-world applications",
            "Future implications",
            "Expert opinions from comments",
            "Potential challenges and concerns"
        ]
    }

    print("🤖 Starting YouTube Video Analysis...")
    print(f"📝 Query: {test_query['user_input']}")
    print("🔍 Analysis Focus Points:")
    for point in test_query['analysis_focus']:
        print(f"  • {point}")
    print("\n")

    # Initialize and run the crew
    crew = VideoAnalysisCrew()
    result = crew.crew().kickoff(inputs=test_query)
    
    print("\n✨ Analysis Complete!")
    print("=" * 50)
    print(result)
    print("=" * 50)

if __name__ == "__main__":
    main()
