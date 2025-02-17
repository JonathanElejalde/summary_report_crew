import os
from datetime import datetime
from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, crew, task
from pathlib import Path
PROJECT_ROOT = os.getenv("PROJECT_ROOT")

from pydantic import BaseModel

class FilteredComment(BaseModel):
    text: str
    likes: int
    relevance: str
    insight: str

class FilteredComments(BaseModel):
    comments: list[FilteredComment]


@CrewBase
class VideoAnalysisCrew:
    """Video Analysis Crew for analyzing a YouTube video's content and comments"""
    
    def __init__(self, video_url: str, analysis_type: str):
        """
        Initialize the crew with all necessary data.
        
        Args:
            video_url: The URL of the YouTube video
            analysis_type: The type of analysis to perform
        """
        # Initialize LLM
        #self.llm = LLM(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"), temperature=1.5)
        self.llm = LLM(model="gpt-4o-mini")

        # Store analysis data
        self.video_url = video_url
        self.analysis_type = analysis_type
    @agent
    def manager(self) -> Agent:
        
        return Agent(
            config=self.agents_config['manager'],
            llm=self.llm,
            verbose=True
        )

    @agent
    def comment_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['comment_analyzer'],
            llm=self.llm,
            verbose=True
        )

    @agent
    def report_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['report_analyzer'],
            llm=self.llm,
            verbose=True
        )

    @agent
    def summary_analyzer(self) -> Agent:
        return Agent(
            config=self.agents_config['summary_analyzer'],
            llm=self.llm,
            verbose=True
        )

    @task
    def analyze_comments_task(self) -> Task:
        """Analyze and filter YouTube comments."""
        task_config = self.tasks_config['analyze_comments_task'].copy()
        return Task(
            config=task_config,
            agent=self.comment_analyzer(),
            output_pydantic=FilteredComments,
        )

    def _generate_output_file(self, output_type: str) -> str:
        """
        Generate output file path for analysis results.
        
        Args:
            output_type: Type of output (report/summary)
            
        Returns:
            String path to the output file
        """
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_file = Path(".") / "docs" / output_type / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        return str(output_file)

    @task
    def create_summary_task(self) -> Task:
        """Create a focused video summary."""
        task_config = self.tasks_config['create_summary_task'].copy()
        return Task(
            config=task_config,
            agent=self.summary_analyzer(),
            output_file=self._generate_output_file("summary"),
        )
    
    @task
    def create_report_task(self) -> Task:
        """Create a detailed video analysis report."""
        task_config = self.tasks_config['create_report_task'].copy()
        return Task(
            config=task_config,
            agent=self.report_analyzer(),
            output_file=self._generate_output_file("report"),
        )
    
    @crew
    def analysis_crew(self) -> Crew:
        return Crew(
            agents=[
                self.comment_analyzer(),
                self.report_analyzer() if self.analysis_type == "report" else self.summary_analyzer(),
            ],
            tasks=[
                self.analyze_comments_task(),
                self.create_report_task() if self.analysis_type == "report" else self.create_summary_task(),
            ],
            process=Process.sequential,
            #manager_llm=self.llm,
            #manager_agent=self.manager(),
            verbose=True
        )
