from typing import Optional, Literal
from pydantic import BaseModel, Field
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import PydanticOutputParser
import os

class UserQueryParams(BaseModel):
    """Parameters extracted from a user query for YouTube video search and analysis."""
    
    query: Optional[str] = Field(
        description="The search query to use for finding YouTube videos"
    )
    url: Optional[str] = Field(
        None, 
        description="Specific YouTube video URL if the user provided one"
    )
    date_filter: Optional[str] = Field(
        "24 hours", 
        description="Time frame for the search (e.g., '24 hours', 'week', 'month', 'year')"
    )
    views_filter: Optional[int] = Field(
        5000, 
        description="Minimum view count for filtering videos"
    )
    analysis_type: Literal["report", "summary"] = Field(
        "report",
        description="Type of analysis to perform"
    )
    # New fields for scheduling
    is_scheduled: bool = Field(
        False,
        description="Whether this is a scheduled request"
    )
    schedule_frequency: Optional[str] = Field(
        None,
        description="Frequency of scheduled analysis (daily/weekly/monthly)"
    )
    preferred_time: Optional[str] = Field(
        None,
        description="Preferred time of day for scheduled analysis (HH:MM format)"
    )

def parse_user_query(user_input: str, model: str = "gpt-4o-mini") -> UserQueryParams:
    """
    Parse a user's natural language query into structured search parameters.
    
    This function handles both immediate analysis requests and scheduling requests.
    For scheduling requests, it extracts frequency and preferred time information.
    
    Args:
        user_input (str): The natural language query from the user. Can be either:
            - Regular analysis request: "Find videos about AI from last week"
            - Scheduling request: "Analyze AI news every week at 9am"
        model (str): The model to use for parsing (default: "gpt-4o-mini")
        
    Returns:
        UserQueryParams: Structured parameters containing:
            - Basic search parameters (query, url, date_filter, views_filter, analysis_type)
            - Scheduling parameters if applicable (is_scheduled, schedule_frequency, preferred_time)
        
    Examples:
        Regular analysis:
        >>> params = parse_user_query("Find me videos about machine learning from last week")
        >>> params.query
        'machine learning'
        >>> params.is_scheduled
        False
        
        Scheduled analysis:
        >>> params = parse_user_query("Analyze AI news every week at 9am")
        >>> params.query
        'AI news'
        >>> params.is_scheduled
        True
        >>> params.schedule_frequency
        'weekly'
        >>> params.preferred_time
        '09:00'
        
        URL analysis:
        >>> params = parse_user_query("Analyze this video: https://youtube.com/watch?v=...")
        >>> params.url
        'https://youtube.com/watch?v=...'
    
    Notes:
        - For scheduling requests, frequency must be one of: daily, weekly, monthly
        - Preferred time is converted to 24-hour format (HH:MM)
        - If no preferred time is specified in a scheduling request, defaults to "00:00"
    """
    # Add logging at the beginning
    print("\n==== Parsing User Query ====")
    print(f"Input text: {user_input}")
    
    # Initialize the parser with our Pydantic model
    parser = PydanticOutputParser(pydantic_object=UserQueryParams)
    
    # Create the prompt template
    template = """You are an AI assistant that extracts search parameters from user queries about YouTube videos.
Pay special attention to scheduling requests.

USER QUERY: {query}

First, determine if this is a scheduling request by looking for keywords like:
- "schedule", "every day", "every week", "daily", "weekly", "monthly"
- Time specifications like "at 9am", "every morning", etc.

If it's a scheduling request, extract:
1. The frequency (daily/weekly/monthly)
2. Preferred time (in HH:MM format, default to "14:00" if not specified)

For all requests, extract:
1. The search query for YouTube
2. A specific video URL if provided
3. Time frame for the search (default to "24 hours" if not specified)
4. Minimum view count for filtering (default to 5000 if not specified)
5. Analysis type (default to "report" if not specified)

Examples:
"Analyze AI news every week at 9am" ->
{{
    "query": "AI news",
    "is_scheduled": true,
    "schedule_frequency": "weekly",
    "preferred_time": "09:00"
}}

"Search for machine learning videos from last week" ->
{{
    "query": "machine learning",
    "is_scheduled": false,
    "date_filter": "week"
}}

{format_instructions}"""

    prompt = PromptTemplate(
        template=template.strip(),
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Initialize the language model
    llm = ChatOpenAI(
        model=model,
        temperature=0,
    )
    
    # Generate the formatted prompt and get response
    formatted_prompt = prompt.format(query=user_input)
    response = llm.invoke(formatted_prompt).content
    
    # Parse the response into our Pydantic model
    try:
        params = parser.parse(response)
    except Exception as e:
        # Fallback to default values if parsing fails
        print(f"Error parsing query parameters: {e}")
        params = UserQueryParams(query=user_input)
    
    # Add logging at the end
    print(f"Parsed parameters: URL={params.url}, Query={params.query}, Analysis={params.analysis_type}, Date={params.date_filter}, Views={params.views_filter}, Scheduled={params.is_scheduled}")
    
    return params
    
if __name__ == "__main__":
    # Test regular queries
    print("\n=== Testing Regular Queries ===")
    params = parse_user_query("Find me videos about machine learning from last week with at least 10k views")
    print(f"Regular Search Query:")
    print(f"- Query: {params.query}")
    print(f"- Date Filter: {params.date_filter}")
    print(f"- Views Filter: {params.views_filter}")
    print(f"- Is Scheduled: {params.is_scheduled}")
    
    # Test URL analysis
    print("\n=== Testing URL Analysis ===")
    params = parse_user_query("Analyze this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(f"URL Analysis:")
    print(f"- URL: {params.url}")
    print(f"- Is Scheduled: {params.is_scheduled}")
    
    # Test scheduling queries
    print("\n=== Testing Scheduling Queries ===")
    scheduling_tests = [
        "Schedule AI news analysis every day at 9am",
        "Analyze crypto market videos weekly at 18:30",
        "Give me a monthly report about machine learning trends on the first day of each month",
        "Every week at 10am, analyze videos about tech news with at least 50k views"
    ]
    
    for test in scheduling_tests:
        params = parse_user_query(test)
        print(f"\nInput: {test}")
        print(f"- Query: {params.query}")
        print(f"- Is Scheduled: {params.is_scheduled}")
        print(f"- Frequency: {params.schedule_frequency}")
        print(f"- Preferred Time: {params.preferred_time}")
        print(f"- Analysis Type: {params.analysis_type}")
        if params.views_filter != 5000:  # Only show if different from default
            print(f"- Views Filter: {params.views_filter}")
    
    # Test edge cases
    print("\n=== Testing Edge Cases ===")
    edge_cases = [
        "Schedule a video analysis but with no specific time",  # Should default to 00:00
        "Daily AI news",  # Minimal scheduling request
        "Weekly tech updates with minimum 1M views at midnight",  # Complex scheduling with specific views
    ]
    
    for test in edge_cases:
        params = parse_user_query(test)
        print(f"\nInput: {test}")
        print(f"- Is Scheduled: {params.is_scheduled}")
        if params.is_scheduled:
            print(f"- Frequency: {params.schedule_frequency}")
            print(f"- Preferred Time: {params.preferred_time}")
        print(f"- Query: {params.query}")

