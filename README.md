# InsightSphere

InsightSphere is an AI-powered sales intelligence platform that combines web scraping, multi-agent conversation simulation, and strategic playbook generation. The system consists of two main services:

- **scraping/**: A FastAPI-based service that intelligently scrapes company websites (via robots.txt/sitemaps, with robust fallbacks), summarizes content using AWS Bedrock AI models, and stores structured JSON summaries in S3 with presigned URLs.
- **streamlit/**: A comprehensive Streamlit web UI that orchestrates multiple AI agents to generate tailored sales pitches, simulate realistic sales conversations, and produce actionable Sales Playbooks.

## System Architecture

### High-Level Architecture Diagram
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           InsightSphere Platform                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐        │
│  │   Streamlit UI  │───▶│  Scraping API    │───▶│   AWS S3        │        │
│  │   (Port 8501)   │    │  (Port 8000)     │    │   (Storage)     │        │
│  │                 │    │                  │    │                 │        │
│  │ • Multi-Agent   │    │ • Web Scraping   │    │ • JSON Summaries│        │
│  │   Orchestration │    │ • Content Extract│    │ • Presigned URLs│        │
│  │ • Real-time UI  │    │ • AI Summarization│   │ • Secure Access │        │
│  │ • File Uploads  │    │ • S3 Integration │    │                 │        │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘        │
│           │                       │                       │                │
│           ▼                       ▼                       ▼                │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐        │
│  │  Strands Agents │    │  AWS Bedrock     │    │  AWS Services   │        │
│  │  Framework      │    │  AI Models       │    │  Integration    │        │
│  │                 │    │                  │    │                 │        │
│  │ • GraphBuilder  │    │ • Llama 3.3 70B  │    │ • boto3 SDK     │        │
│  │ • Agent Routing │    │ • Claude Opus 4.1│    │ • IAM Roles     │        │
│  │ • State Mgmt    │    │ • Llama 1 70B    │    │ • Region Config │        │
│  └─────────────────┘    └──────────────────┘    └─────────────────┘        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Service Architecture Details

#### Scraping Service (FastAPI)
- **Port**: 8000
- **Framework**: FastAPI with async/await support
- **Key Components**:
  - **URL Discovery Engine**: Intelligent sitemap parsing with fallback mechanisms
  - **Content Extraction**: Playwright-based dynamic content rendering
  - **AI Summarization Pipeline**: Chunked processing with context preservation
  - **S3 Integration**: Secure storage with presigned URL generation
- **API Endpoints**:
  - `GET /scrape?company={name}`: Main scraping endpoint
  - Returns: `{"s3_url": "presigned_s3_url"}`

#### Streamlit Service (Frontend)
- **Port**: 8501
- **Framework**: Streamlit with custom components
- **Key Components**:
  - **Multi-Agent Orchestrator**: Strands Agents with GraphBuilder
  - **Real-time UI**: Live conversation display with progress indicators
  - **File Management**: Upload handling for knowledge bases
  - **Export System**: Download functionality for generated content
- **Agent Workflows**:
  - **Pitch Generation**: 3-agent pipeline (Analyzer → Solver → Pitcher)
  - **Conversation Simulation**: 4-agent system with intelligent routing
  - **Playbook Creation**: 2-agent strategic analysis pipeline

### Data Flow Architecture
```
User Input → Streamlit UI → Agent Orchestration → AWS Bedrock
     ↓              ↓              ↓                    ↓
File Uploads → Knowledge Bases → Multi-Agent → AI Model Inference
     ↓              ↓              Processing           ↓
Company URLs → Scraping API → Content Processing → S3 Storage
     ↓              ↓              ↓                    ↓
Web Scraping → AI Summarization → JSON Storage → Presigned URLs
```

### Security & Access Control
- **AWS IAM**: Role-based access control for Bedrock and S3
- **Presigned URLs**: Time-limited, secure access to S3 objects
- **Environment Variables**: Secure configuration management
- **Docker Isolation**: Containerized services for deployment security

### Scalability Considerations
- **Async Processing**: Non-blocking operations for better performance
- **Chunked Processing**: Handles large documents efficiently
- **Stateless Design**: Services can be horizontally scaled
- **Caching Strategy**: S3-based caching for frequently accessed data

## AI Agents & Multi-Agent System

InsightSphere leverages a sophisticated multi-agent architecture powered by **Strands Agents** and **AWS Bedrock** to simulate realistic sales conversations and generate strategic insights.

### Sales Pitch Generation Agents
1. **ProspectAnalyzer Agent**
   - **Role**: Business analyst that identifies key business challenges from prospect information
   - **Model**: Meta Llama 3.3 70B Instruct
   - **Function**: Analyzes prospect company data to extract primary pain points and business challenges

2. **TechnicalSolver Agent**
   - **Role**: Solutions architect providing quantified solutions based on technical documentation
   - **Model**: Meta Llama 3.3 70B Instruct
   - **Function**: Maps identified pain points to specific, measurable solutions with ROI metrics

3. **SalesPitcher Agent**
   - **Role**: Senior sales executive creating persuasive sales narratives
   - **Model**: Meta Llama 3.3 70B Instruct
   - **Function**: Synthesizes analysis into executive-friendly sales pitches with quantified outcomes

### Conversation Simulation Agents
4. **ProspectAgent (Alex)**
   - **Role**: Senior Director/CTO at prospect company
   - **Personality**: Analytical, busy, ROI-focused, risk-aware
   - **Function**: Asks challenging, realistic questions during sales conversations

5. **RouterAgent**
   - **Role**: Intelligent routing system
   - **Function**: Determines whether questions should be handled by Sales or Technical agents
   - **Decision Logic**: Routes business/pricing questions to Sales, technical/implementation questions to Technical

6. **SalesAgent (Sarah)**
   - **Role**: Engaging sales lead at Fission Labs
   - **Personality**: Confident, value-focused, business-outcome oriented
   - **Function**: Handles business questions with ROI and revenue growth focus

7. **TechnicalAgent (David)**
   - **Role**: Solutions architect at Fission Labs
   - **Personality**: Expert at translating technology into business value
   - **Function**: Uses "Value Sandwich" method: acknowledges business problem → explains technical approach → pivots to quantified ROI

### Playbook Generation Agents
8. **ConversationAnalyst Agent**
   - **Role**: Forensic sales intelligence analyst
   - **Model**: Claude Opus 4.1 (for advanced analysis)
   - **Function**: Extracts pain points, concerns, and buying signals from conversation transcripts

9. **SalesStrategist Agent**
   - **Role**: World-class sales strategist (McKinsey consultant + investment banker hybrid)
   - **Model**: Claude Opus 4.1 (for strategic thinking)
   - **Function**: Creates comprehensive sales playbooks with quantified strategies and actionable next steps

### Agent Orchestration
- **Framework**: Strands Agents with GraphBuilder for multi-agent workflows
- **Communication**: Agents pass structured data between each other in defined workflows
- **State Management**: Conversation history and context maintained across agent interactions
- **Error Handling**: Robust fallbacks and error recovery mechanisms

## Technology Stack

### Core Technologies
- **Python 3.12+**: Primary development language
- **FastAPI**: High-performance web framework for the scraping API
- **Streamlit**: Interactive web UI framework for the frontend
- **Strands Agents**: Multi-agent orchestration framework
- **AWS Bedrock**: Managed AI service for large language models

### AI Models & Their Specialized Roles

#### Primary Models
- **Meta Llama 3.3 70B Instruct** (`us.meta.llama3-3-70b-instruct-v1:0`)
  - **Usage**: Primary model for conversation simulation and pitch generation agents
  - **Agents**: ProspectAgent, RouterAgent, SalesAgent, TechnicalAgent, ProspectAnalyzer, TechnicalSolver, SalesPitcher
  - **Strengths**: Excellent for conversational AI, business analysis, and structured reasoning
  - **Configuration**: Temperature 0.7 for conversations, 0.3 for analysis

- **Claude Opus 4.1** (`us.anthropic.claude-opus-4-1-20250805-v1:0`)
  - **Usage**: Advanced strategic analysis and playbook generation
  - **Agents**: ConversationAnalyst, SalesStrategist
  - **Strengths**: Superior analytical capabilities, strategic thinking, and complex reasoning
  - **Configuration**: Temperature 0.3, Max tokens 30,000 for comprehensive analysis

- **Meta Llama 1 70B Instruct** (`us.meta.llama3-1-70b-instruct-v1:0`)
  - **Usage**: Content summarization and text processing
  - **Agents**: SummarizeAgent (in scraping service)
  - **Strengths**: Efficient text summarization with context preservation
  - **Configuration**: Temperature 0.7 for balanced summarization

#### Model Selection Strategy
- **Conversational Agents**: Llama 3.3 for natural dialogue and business communication
- **Strategic Analysis**: Claude Opus 4.1 for complex reasoning and strategic planning
- **Content Processing**: Llama 1 for efficient summarization and text processing
- **Fallback Models**: System provides safe defaults if environment variables are not set

### Web Scraping & Data Processing
- **Playwright**: Browser automation for dynamic content extraction
- **BeautifulSoup4**: HTML parsing and content extraction
- **httpx**: Async HTTP client for API calls

### Cloud & Storage
- **AWS S3**: Object storage for scraped summaries and knowledge bases
- **AWS Bedrock**: AI model inference and management
- **boto3**: AWS SDK for Python

### Development & Deployment
- **Docker**: Containerization for both services
- **uvicorn**: ASGI server for FastAPI
- **python-dotenv**: Environment variable management
- **requests**: HTTP library for API communication

## Prerequisites
- Python 3.12+
- AWS account with Bedrock and S3 access
- Docker (optional for containerized runs)
- AWS CLI (for ECR/ECS workflows)

## Environment Variables
Common variables used across services (set in shell, Docker env, or .env):

- AWS_REGION: e.g. us-east-1
- S3_BUCKET: target bucket for summaries (scraping)
- BEDROCK_MODEL: model id for conversation/pitch, e.g. us.meta.llama3-3-70b-instruct-v1:0
- Playbook_model: model id for playbook generation (Streamlit)
- scraping_url: full base URL to scraping service, e.g. http://localhost:8000/scrape

Notes:
- Services provide safe fallbacks for missing model IDs, but you should set them explicitly.

## Quick Start (Local)
1) Create and activate venv, then install requirements per each service folder.
2) Start scraping API (see scraping/README.md)
3) Configure `scraping_url` in the Streamlit environment for company information
4) Start Streamlit UI (see streamlit/README.md)

## Complete System Workflow

### Phase 1: Data Collection & Processing
1. **URL Discovery & Scraping** (scraping service)
   - **Input**: Company name or website URL
   - **Process**: 
     - Reads `robots.txt` and discovers sitemaps (XML/HTML/text formats)
     - Handles sitemap indexes and gzipped sitemaps automatically
     - Falls back to homepage link extraction if no sitemaps found
     - Uses Playwright to fetch top-N pages with full JavaScript rendering
     - Extracts clean text content from each page
   - **Output**: List of discovered URLs and extracted text content

2. **AI-Powered Summarization** (scraping service)
   - **Process**:
     - Chunks large text content into manageable segments (1000 chars each)
     - Uses **SummarizeAgent** with Meta Llama 1 70B for intelligent summarization
     - Implements chain summarization to maintain context across chunks
     - Preserves key business information while reducing content size
   - **Storage**: Uploads structured JSON `{company, summary, site_urls}` to S3
   - **Output**: Presigned S3 URL for secure access to company knowledge base

### Phase 2: Sales Intelligence Generation
3. **Multi-Agent Sales Pitch Generation** (streamlit)
   - **Input**: Sales KB, Technical KB, and Prospect KB (from S3 or file uploads)
   - **Agent Workflow**:
     ```
     ProspectAnalyzer → TechnicalSolver → SalesPitcher
     ```
   - **Process**:
     - **ProspectAnalyzer**: Identifies key business challenges and pain points
     - **TechnicalSolver**: Maps pain points to quantified solutions with ROI metrics
     - **SalesPitcher**: Synthesizes analysis into executive-friendly sales narrative
   - **Output**: Comprehensive sales analysis report with competitive analysis, pain points, solutions, and executive narrative

### Phase 3: Conversation Simulation
4. **Real-time Sales Conversation** (streamlit)
   - **Setup**: Initializes 4 specialized agents with distinct personas
   - **Conversation Flow**:
     ```
     ProspectAgent (Alex) → RouterAgent → [SalesAgent (Sarah) | TechnicalAgent (David)]
     ```
   - **Process**:
     - **Turn 1-6**: Multi-turn conversation simulation
     - **ProspectAgent**: Asks challenging, realistic questions based on sales pitch and internal knowledge
     - **RouterAgent**: Intelligently routes questions to appropriate specialist
     - **SalesAgent**: Handles business/pricing questions with ROI focus
     - **TechnicalAgent**: Addresses technical questions using "Value Sandwich" method
   - **Real-time Display**: Live conversation updates in Streamlit UI with agent status indicators
   - **Output**: Complete conversation transcript with all Q&A exchanges

### Phase 4: Strategic Analysis & Playbook Creation
5. **Advanced Playbook Generation** (streamlit)
   - **Input**: Complete conversation transcript + all knowledge bases
   - **Agent Workflow**:
     ```
     ConversationAnalyst → SalesStrategist
     ```
   - **Process**:
     - **ConversationAnalyst**: Forensic analysis of conversation transcript
       - Extracts key prospect pain points with direct quotes
       - Identifies customer concerns and objections (High/Low priority)
       - Detects moments of high interest and buying signals
     - **SalesStrategist**: Creates comprehensive sales playbook
       - Executive summary with prospect profile and critical pain points
       - Deep dive conversation analysis
       - Strategic game plan with key talking points
       - Prepared answers for predicted questions
       - Concerns handling matrix
       - Actionable next steps with sample follow-up email
   - **Output**: Master Sales Playbook in markdown format

### Phase 5: Delivery & Export
6. **Results Presentation** (streamlit)
   - **Display**: All generated content in organized, downloadable format
   - **Downloads Available**:
     - Sales Pitch (markdown)
     - Sales Playbook (markdown)
     - Conversation Transcript (JSON)
   - **Features**: Real-time progress indicators, error handling, and user-friendly interface

## Docker
Both services include Dockerfiles. Build and run:

```bash
docker build -t sales_insights_scraping ./scraping
docker run -p 8000:8000 --env-file .env sales_insights_scraping

docker build -t sales_insight_streamlit ./streamlit
docker run -p 8501:8501 --env-file .env sales_insight_streamlit
```

## ECR/ECS
Push to ECR (example):

```bash
docker build --platform linux/amd64 -t sales_insight_streamlit ./streamlit
docker tag sales_insight_streamlit:latest <account>.dkr.ecr.<region>.amazonaws.com/sales-insights:latest
aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker push <account>.dkr.ecr.<region>.amazonaws.com/sales-insights:latest
```

Ensure your ECS task definition platform matches the image (amd64 vs arm64) or build multi-arch with buildx.

## Current Project Status & Running Environment

### Key Features Currently Working
✅ **Web Scraping**: Intelligent sitemap discovery and content extraction  
✅ **AI Summarization**: Chunked processing with context preservation  
✅ **Multi-Agent Conversations**: Real-time sales conversation simulation  
✅ **Strategic Playbook Generation**: Comprehensive sales intelligence reports  
✅ **File Upload Support**: Direct knowledge base uploads  
✅ **Export Functionality**: Downloadable sales pitches and playbooks  
✅ **Real-time UI**: Live conversation display with progress indicators  

### Performance Metrics
- **Scraping Speed**: ~5-10 pages per company (configurable)
- **Conversation Turns**: 6-turn realistic sales dialogues
- **Processing Time**: 2-5 minutes for complete workflow
- **Model Response Time**: 10-30 seconds per agent interaction

### Known Limitations
- **Rate Limits**: AWS Bedrock API rate limits apply
- **Content Size**: Large websites may require chunking optimization
- **Model Costs**: Usage-based pricing for Bedrock models
- **Browser Requirements**: Playwright requires compatible browser installation

## Project Structure
```
sales-insights/
├── scraping/                  # FastAPI scraping service
│   ├── main.py               # Main scraping application
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Container configuration
│   └── README.md            # Service documentation
├── streamlit/                # Streamlit frontend service
│   ├── conversation.py       # Multi-agent conversation logic
│   ├── pitch_generation.py   # Sales pitch generation
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Container configuration
│   └── README.md            # Service documentation
├── README.md                 # This comprehensive documentation
└── LICENSE                   # Project license
```

### Service Dependencies
- **scraping/**: FastAPI, Playwright, BeautifulSoup4, boto3, strands-agents
- **streamlit/**: Streamlit, strands-agents, boto3, requests, python-dotenv
- **Shared**: AWS Bedrock access, S3 bucket configuration

## Getting Started

### Quick Start (Local Development)
1. **Clone Repository**: `git clone <repository-url>`
2. **Set Environment Variables**: Configure AWS credentials and model IDs
3. **Start Scraping Service**: `cd scraping && pip install -r requirements.txt && uvicorn main:app --reload`
4. **Start Streamlit UI**: `cd streamlit && pip install -r requirements.txt && streamlit run conversation.py`
5. **Access Application**: Open `http://localhost:8501` in your browser

### Production Deployment
- **Docker**: Use provided Dockerfiles for containerized deployment
- **AWS ECS**: Deploy containers to AWS ECS with proper IAM roles
- **Load Balancing**: Configure load balancers for high availability
- **Monitoring**: Set up CloudWatch monitoring for both services

See each service's README for detailed setup and configuration instructions.
