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
        description="Type of analysis to perform ('report' for detailed analysis, 'summary' for concise overview)"
    )

def parse_user_query(user_input: str, model: str = "gpt-4o-mini") -> UserQueryParams:
    """
    Parse a user's natural language query into structured search parameters.
    
    Uses LangChain with `model` to extract search parameters from the user's
    input, handling various ways users might express their search intent.
    
    Args:
        user_input (str): The natural language query from the user
        model (str): The model to use for parsing (default: "gpt-4o-mini")
        
    Returns:
        UserQueryParams: Structured parameters for YouTube search and filtering
        
    Example:
        >>> params = parse_user_query("Find me videos about machine learning from last week with at least 10k views")
        >>> params.query
        'machine learning'
        >>> params.date_filter
        'week'
        >>> params.views_filter
        10000
    """
    # Initialize the parser with our Pydantic model
    parser = PydanticOutputParser(pydantic_object=UserQueryParams)
    
    # Create a prompt template
    template = """
    You are an AI assistant that extracts search parameters from user queries about YouTube videos.
    
    USER QUERY: {query}
    
    Extract the following information:
    1. The search query for YouTube (what topics/keywords to search for)
    2. A specific video URL if provided
    3. Time frame for the search (default to "24 hours" if not specified)
    4. Minimum view count for filtering (default to 5000 if not specified)
    5. Analysis type (default to "report" if not specified)
    
    If the user provides a specific YouTube URL, extract it. If they're asking for a general search, 
    identify the main topic or keywords they want to search for.
    
    For the time frame, look for mentions of "today", "this week", "this month", "this year", or specific 
    time periods. Map these to "24 hours", "week", "month", "year", etc.
    
    For view count, extract any minimum view threshold mentioned (e.g., "at least 10k views", "more than 1 million views").
    
    For analysis type, look for indications of whether the user wants a detailed report or a concise summary.
    If they mention "summary", "brief", "concise", "overview", etc., set analysis_type to "summary".
    If they mention "report", "detailed", "comprehensive", "in-depth", etc., or don't specify, set analysis_type to "report".
    
    {format_instructions}
    """
    
    # Set up the prompt with format instructions from the parser
    prompt = PromptTemplate(
        template=template,
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()}
    )
    
    # Initialize the language model
    llm = ChatOpenAI(
        model=model,
        temperature=0,
    )
    
    # Generate the formatted prompt
    formatted_prompt = prompt.format(query=user_input)
    
    # Get the response from the model
    response = llm.invoke(formatted_prompt).content
    
    # Parse the response into our Pydantic model
    try:
        return parser.parse(response)
    except Exception as e:
        # Fallback to default values if parsing fails
        print(f"Error parsing query parameters: {e}")
        return UserQueryParams(query=user_input)
    
if __name__ == "__main__":
    # Test the parser with a sample query
    params = parse_user_query("Find me videos about machine learning from last week with at least 10k views")
    print(params)
    
    # Test with a URL
    params = parse_user_query("Analyze this YouTube video: https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    print(params)
    
    # Test with a complex query
    params = parse_user_query("I want to see popular finance videos from this month with more than 100k views")
    print(params)
    
    # Test with analysis type specified
    params = parse_user_query("Give me a summary of videos about AI from this week")
    print(params)
    
    params = parse_user_query("I need a detailed report on cryptocurrency videos with at least 50k views")
    print(params)