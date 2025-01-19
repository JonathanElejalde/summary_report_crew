from typing import Any, Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MetadataExtractionInput(BaseModel):
    """Input schema for MetadataExtractionTool."""
    video_ids: list[str] = Field(
        ..., 
        description="List of YouTube video IDs to fetch metadata for"
    )

class MetadataExtractionTool(BaseTool):
    name: str = "Metadata Extraction Tool"
    description: str = "Fetches comprehensive metadata for given YouTube video IDs, including video details, captions, and comments"
    args_schema: Type[BaseModel] = MetadataExtractionInput

    def _run(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """
        Fetch metadata for given video IDs.
        Replace this with the actual metadata extraction logic.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            list: List of comprehensive video metadata including captions and comments
        """
        # Placeholder data mapping for testing
        sample_metadata = {
            "abc123": {
                "video_id": "abc123",
                "title": "Introduction to AI - Latest Developments 2024",
                "description": "Explore the latest developments in AI technology, including breakthroughs in machine learning, neural networks, and practical applications. We cover the most significant advancements from leading research institutions and tech companies.",
                "channel": {
                    "name": "TechInsights",
                    "id": "UC123456789",
                    "subscriber_count": 500000
                },
                "statistics": {
                    "views": 150000,
                    "likes": 12000,
                    "comments": 1500
                },
                "published_date": "2024-01-15",
                "duration": "PT15M30S",
                "tags": ["AI", "Machine Learning", "Technology", "Innovation"],
                "captions_available": True,
                "language": "en",
                "category": "Science & Technology",
                "captions": """
Welcome to TechInsights! Today we're exploring the latest developments in artificial intelligence as we enter 2024.

The past year has seen remarkable breakthroughs in several key areas. First, let's talk about large language models. These models have become increasingly sophisticated, with improvements in reasoning, coding abilities, and multilingual understanding.

A major advancement has been in multimodal AI systems. These new models can seamlessly work with text, images, audio, and video, opening up exciting possibilities for creative and practical applications.

We're also seeing significant progress in AI safety and alignment. Researchers have developed better methods for making AI systems more reliable and aligned with human values.

In the field of robotics, AI models are now better at understanding and manipulating real-world objects. This has led to more capable and adaptable robotic systems in manufacturing and research settings.

Looking ahead, experts predict 2024 will bring even more exciting developments in areas like scientific discovery, healthcare, and sustainable technology solutions.

Remember to subscribe for more updates on the latest in AI and technology!
""",
                "comments": [
                    {
                        "author": "AI_Enthusiast",
                        "text": "The part about multimodal AI systems was fascinating. I've been following the development of these models and their ability to understand context across different types of media is truly revolutionary.",
                        "likes": 450,
                        "timestamp": "2024-01-15T15:30:00Z"
                    },
                    {
                        "author": "TechResearcher",
                        "text": "Great overview of AI safety progress. Would love to see a deep dive into specific alignment techniques being developed.",
                        "likes": 380,
                        "timestamp": "2024-01-15T16:45:00Z"
                    },
                    {
                        "author": "RandomUser123",
                        "text": "First! Love your videos!",
                        "likes": 5,
                        "timestamp": "2024-01-15T14:00:00Z"
                    },
                    {
                        "author": "AISkeptic",
                        "text": "These developments seem overhyped. What about the risks?",
                        "likes": 25,
                        "timestamp": "2024-01-15T17:20:00Z"
                    },
                    {
                        "author": "RoboticsFan",
                        "text": "The advancements in robotics are particularly exciting. I work in manufacturing and we're already seeing the impact of these improved AI models in our automation systems.",
                        "likes": 290,
                        "timestamp": "2024-01-15T18:15:00Z"
                    }
                ]
            },
            "def456": {
                "video_id": "def456",
                "title": "Machine Learning Breakthroughs - A Deep Dive",
                "description": "A comprehensive analysis of recent machine learning breakthroughs and their implications for the future of AI. This video examines cutting-edge research and real-world applications.",
                "channel": {
                    "name": "AI Academy",
                    "id": "UC987654321",
                    "subscriber_count": 250000
                },
                "statistics": {
                    "views": 75000,
                    "likes": 6000,
                    "comments": 800
                },
                "published_date": "2024-01-10",
                "duration": "PT20M45S",
                "tags": ["Machine Learning", "Deep Learning", "AI Research", "Data Science"],
                "captions_available": True,
                "language": "en",
                "category": "Education",
                "captions": """
Hello everyone! In today's deep dive, we're examining three groundbreaking developments in machine learning that are reshaping the field.

The first breakthrough involves self-supervised learning. Recent research has shown that models can now learn more effectively from unlabeled data, dramatically reducing the need for large annotated datasets. This has huge implications for training efficiency and cost reduction.

Next, we'll explore advances in reinforcement learning. New algorithms have achieved remarkable results in complex decision-making tasks, particularly in areas like game theory and resource optimization. These improvements are already being applied in real-world scenarios from energy grid management to autonomous systems.

Finally, we're seeing exciting progress in few-shot learning capabilities. Models can now adapt to new tasks with minimal training examples, making AI systems more flexible and practical for real-world applications.

These developments are not just theoretical - they're already being implemented in various industries. Let's look at some practical examples...

Stay tuned for part two of this series where we'll explore the ethical implications of these advances.
""",
                "comments": [
                    {
                        "author": "DataScientist42",
                        "text": "The explanation of self-supervised learning was excellent. We're implementing similar techniques in our research lab and seeing promising results with much smaller datasets.",
                        "likes": 620,
                        "timestamp": "2024-01-10T12:30:00Z"
                    },
                    {
                        "author": "MLEngineer",
                        "text": "Could you elaborate more on the specific algorithms used in the reinforcement learning examples? Particularly interested in the energy grid management case.",
                        "likes": 450,
                        "timestamp": "2024-01-10T13:45:00Z"
                    },
                    {
                        "author": "SpamBot9000",
                        "text": "Check out my channel for more AI content!",
                        "likes": 0,
                        "timestamp": "2024-01-10T14:20:00Z"
                    },
                    {
                        "author": "IndustryExpert",
                        "text": "The few-shot learning applications are game-changing for smaller companies that don't have access to massive datasets. We've started implementing these techniques in our startup.",
                        "likes": 380,
                        "timestamp": "2024-01-10T15:10:00Z"
                    }
                ]
            },
            "ghi789": {
                "video_id": "ghi789",
                "title": "The Future of Artificial Intelligence",
                "description": "An exploration of where AI is headed and its potential impact on society.",
                "channel": {
                    "name": "Future Tech Today",
                    "id": "UC567890123",
                    "subscriber_count": 750000
                },
                "statistics": {
                    "views": 200000,
                    "likes": 18000,
                    "comments": 2200
                },
                "published_date": "2024-01-05",
                "duration": "PT18M15S",
                "tags": ["AI Future", "Technology Trends", "Society", "Innovation"],
                "captions_available": True,
                "language": "en",
                "category": "Science & Technology",
                "captions": """
As we look toward the future of artificial intelligence, we need to consider both its potential and challenges.

Today's discussion focuses on three key areas that will shape AI's development over the next decade. First, we'll explore the convergence of AI with other emerging technologies like quantum computing and biotechnology.

One of the most promising developments is in healthcare, where AI is beginning to revolutionize everything from drug discovery to personalized medicine. Imagine AI systems that can predict health issues before they become serious, or design targeted treatments based on your genetic profile.

Another crucial area is environmental protection. AI is already helping us model climate change, optimize renewable energy systems, and develop more sustainable manufacturing processes.

However, we must also address important challenges. Privacy concerns, algorithmic bias, and the need for transparent AI systems are all critical issues that need careful consideration.

The future of AI isn't just about technology - it's about how we choose to develop and implement these powerful tools in ways that benefit all of humanity.
""",
                "comments": [
                    {
                        "author": "HealthTechPro",
                        "text": "The healthcare applications are particularly promising. I'm a medical researcher, and we're already seeing AI accelerate our drug discovery process significantly.",
                        "likes": 890,
                        "timestamp": "2024-01-05T10:15:00Z"
                    },
                    {
                        "author": "EthicsResearcher",
                        "text": "Important points about AI transparency and bias. We need to ensure these systems are developed with strong ethical guidelines and oversight.",
                        "likes": 760,
                        "timestamp": "2024-01-05T11:30:00Z"
                    },
                    {
                        "author": "ClimateScientist",
                        "text": "The environmental applications are crucial. We're using AI models to improve our climate predictions and they're proving remarkably accurate.",
                        "likes": 680,
                        "timestamp": "2024-01-05T12:45:00Z"
                    },
                    {
                        "author": "RandomTroll",
                        "text": "AI will never replace human intelligence!",
                        "likes": 3,
                        "timestamp": "2024-01-05T13:20:00Z"
                    },
                    {
                        "author": "PrivacyAdvocate",
                        "text": "Glad you addressed the privacy concerns. We need more discussion about data protection in AI systems.",
                        "likes": 550,
                        "timestamp": "2024-01-05T14:10:00Z"
                    }
                ]
            }
        }
        
        # Return metadata for all requested video IDs
        return [sample_metadata.get(video_id, {
            "video_id": video_id,
            "title": "Video Not Found",
            "description": "No metadata available for this video ID.",
            "error": "Video not found in sample data",
            "captions_available": False,
            "captions": "",
            "comments": []
        }) for video_id in video_ids]

