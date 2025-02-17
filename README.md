# YouTube Video Analysis Tool 🎥

An AI-powered tool that analyzes YouTube videos by examining their transcripts and comments to provide either detailed reports or concise summaries.

## Features ✨

- 📝 Video transcript extraction (using official captions or Whisper for audio transcription)
- 💬 Comment analysis and filtering
- 📊 Two analysis types:
  - Detailed Report: Comprehensive analysis of video content and reception
  - Concise Summary: Key points and main takeaways
- 🤖 AI-powered analysis using CrewAI
- 🔍 Spam comment detection and filtering

## Prerequisites 📋

Before you begin, ensure you have the following installed:

- Python 3.9 or higher
- FFmpeg (required for Whisper audio transcription)
- Git

### Installing FFmpeg

#### Ubuntu
```bash
sudo apt update
sudo apt install ffmpeg
```

#### Windows
1. Download FFmpeg from the official website: https://ffmpeg.org/download.html
2. Extract the downloaded archive
3. Add the FFmpeg `bin` folder to your system's PATH environment variable

## Installation 🚀

1. Clone the repository:
```bash
git clone https://github.com/yourusername/youtube_agent.git
cd youtube_agent
```

2. Create and activate a virtual environment:

#### Ubuntu
```bash
python -m venv venv
source venv/bin/activate
```

#### Windows
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Edit the `.env` file and add your API keys:
- `YOUTUBE_API_KEY`: Get from [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
- `AGENTOPS_API_KEY`: Get from AgentOps dashboard
- `OPENAI_API_KEY`: Get from OpenAI dashboard

## Usage 🎮

1. Activate the virtual environment (if not already activated):

#### Ubuntu
```bash
source venv/bin/activate
```

#### Windows
```bash
venv\Scripts\activate
```

2. Run the analysis tool:
```bash
python main.py
```

3. Follow the prompts:
   - Enter a YouTube video URL
   - Choose analysis type (1 for Detailed Report, 2 for Concise Summary)

4. The tool will:
   - Extract the video transcript
   - Collect and analyze comments
   - Generate an AI analysis based on your chosen type
   - Save the analysis to the `docs` directory

## Output 📄

Analysis results are saved in the `docs` directory:
- Reports: `docs/report/YYYYMMDD_HHMMSS.md`
- Summaries: `docs/summary/YYYYMMDD_HHMMSS.md`

## License 📜

[MIT License](LICENSE)

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request. 