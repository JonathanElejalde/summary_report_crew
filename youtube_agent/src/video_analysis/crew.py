from crewai import Agent, Task, Crew, Process, LLM
from crewai.project import CrewBase, agent, crew, task
from langchain_community.llms import Ollama
from src.video_analysis.tools.youtube_search_tool import YouTubeSearchTool
from src.video_analysis.tools.metadata_extraction_tool import MetadataExtractionTool

@CrewBase
class VideoAnalysisCrew:
    """Video Analysis Crew for processing and analyzing YouTube videos"""

    def __init__(self):
        #self.llm = LLM(model="ollama/phi4", base_url="http://localhost:11434")
        self.llm = LLM(model="deepseek/deepseek-chat", api_key="sk-d07cc60c0b8b4dfabf65e32b94c2b361", temperature=1.5)
        # Initialize tools
        self.youtube_search = YouTubeSearchTool()
        self.metadata_extraction = MetadataExtractionTool()

    @agent
    def query_processor(self) -> Agent:
        return Agent(
            config=self.agents_config["query_processor"],
            tools=[self.youtube_search, self.metadata_extraction],
            llm=self.llm,
            verbose=True
        )

    @agent
    def comment_filter(self) -> Agent:
        return Agent(
            config=self.agents_config["comment_filter"],
            llm=self.llm,
            verbose=True
        )

    @agent
    def caption_summarizer(self) -> Agent:
        return Agent(
            config=self.agents_config["caption_summarizer"],
            llm=self.llm,
            verbose=True
        )

    @agent
    def final_report_generator(self) -> Agent:
        return Agent(
            config=self.agents_config["final_report_generator"],
            llm=self.llm,
            verbose=True
        )

    @task
    def video_query_task(self) -> Task:
        return Task(
            config=self.tasks_config["video_query_task"],
            agent=self.query_processor()
        )

    @task
    def comment_filter_task(self) -> Task:
        return Task(
            config=self.tasks_config["comment_filter_task"],
            agent=self.comment_filter(),
            context=[self.video_query_task()],
            async_execution=True
        )

    @task
    def caption_summarization_task(self) -> Task:
        return Task(
            config=self.tasks_config["caption_summarization_task"],
            agent=self.caption_summarizer(),
            context=[self.video_query_task()],
            async_execution=True
        )

    @task
    def final_report_task(self) -> Task:
        return Task(
            config=self.tasks_config["final_report_task"],
            agent=self.final_report_generator(),
            context=[self.comment_filter_task(), self.caption_summarization_task()]
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[
                self.query_processor(),
                self.comment_filter(),
                self.caption_summarizer(),
                self.final_report_generator()
            ],
            tasks=[
                self.video_query_task(),
                self.comment_filter_task(),
                self.caption_summarization_task(),
                self.final_report_task()
            ],
            process=Process.hierarchical,
            verbose=True,
            manager_llm=self.llm
        )
