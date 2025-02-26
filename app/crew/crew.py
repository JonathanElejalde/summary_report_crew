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
    
    def __init__(self, video_url: str, analysis_type: str, video_metadata: dict = None):
        """
        Initialize the crew with all necessary data.
        
        Args:
            video_url: The URL of the YouTube video
            analysis_type: The type of analysis to perform
            video_metadata: Optional metadata about the video
        """
        # Initialize LLM
        #self.llm = LLM(model="deepseek/deepseek-chat", api_key=os.getenv("DEEPSEEK_API_KEY"), temperature=1.5)
        self.llm = LLM(model="gpt-4o-mini")

        # Store analysis data
        self.video_url = video_url
        self.analysis_type = analysis_type
        self.video_metadata = video_metadata or {}
        self.output_file_path = None
        
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
        # Create a safe filename that includes video title if available
        if self.video_metadata and 'title' in self.video_metadata:
            # Remove invalid characters and limit length
            safe_title = "".join(c for c in self.video_metadata['title'] if c.isalnum() or c in " -_").strip()
            safe_title = safe_title[:50]  # Limit length
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{safe_title}.md"
        else:
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        output_file = Path(".") / "docs" / output_type / filename
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Store the output file path for later reference
        self.output_file_path = str(output_file)
        
        return self.output_file_path

    @task
    def create_summary_task(self) -> Task:
        """Create a focused video summary."""
        task_config = self.tasks_config['create_summary_task'].copy()
        
        # Add video metadata to the task context
        task_config['description'] = task_config['description'].format(
            video_url=self.video_url,
            video_title=self.video_metadata.get('title', 'Unknown Title'),
            video_creator=self.video_metadata.get('creator', 'Unknown Creator'),
            video_duration=self.video_metadata.get('duration', 'Unknown Duration'),
            transcript="{transcript}",
            comments="{comments}",
        )
        
        return Task(
            config=task_config,
            agent=self.summary_analyzer(),
            output_file=self._generate_output_file("summary"),
        )
    
    @task
    def create_report_task(self) -> Task:
        """Create a detailed video analysis report."""
        task_config = self.tasks_config['create_report_task'].copy()
        
        # Add video metadata to the task context
        task_config['description'] = task_config['description'].format(
            video_url=self.video_url,
            video_title=self.video_metadata.get('title', 'Unknown Title'),
            video_creator=self.video_metadata.get('creator', 'Unknown Creator'),
            video_duration=self.video_metadata.get('duration', 'Unknown Duration'),
            transcript="{transcript}",
            comments="{comments}",
        )
        
        return Task(
            config=task_config,
            agent=self.report_analyzer(),
            output_file=self._generate_output_file("report"),
        )
    
    @crew
    def analysis_crew(self) -> Crew:
        """
        Create the analysis crew with appropriate agents and tasks.
        
        When analysis_type is "report", includes both summary and report tasks.
        When analysis_type is "summary", includes only the summary task.
        
        Returns:
            Crew: Configured crew for video analysis
        """
        if self.analysis_type == "report":
            # For reports, include both summary and report agents/tasks
            return Crew(
                agents=[
                    self.comment_analyzer(),
                    self.summary_analyzer(),
                    self.report_analyzer(),
                ],
                tasks=[
                    self.analyze_comments_task(),
                    self.create_summary_task(),
                    self.create_report_task(),
                ],
                process=Process.sequential,
                verbose=True
            )
        else:
            # For summaries, include only summary agent/task
            return Crew(
                agents=[
                    self.comment_analyzer(),
                    self.summary_analyzer(),
                ],
                tasks=[
                    self.analyze_comments_task(),
                    self.create_summary_task(),
                ],
                process=Process.sequential,
                verbose=True
            )
