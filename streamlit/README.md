# Streamlit UI

Streamlit web app to:
1) Collect Sales/Prospect inputs (website or uploads)
2) Generate a Sales Pitch using Bedrock
3) Simulate a conversation via Strands Agents
4) Produce a Sales Playbook

## Environment Variables
- BEDROCK_MODEL: model id for agents (e.g., us.meta.llama3-3-70b-instruct-v1:0)
- Playbook_model: model id for playbook (optional; fallback provided)
- scraping_url: scraping API base (e.g., http://localhost:8000/scrape)

## Local Run
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export BEDROCK_MODEL=<model-id> scraping_url=http://localhost:8000/scrape
streamlit run conversation.py
```

## Docker
```bash
docker build -t sales_insight_streamlit .
docker run -p 8501:8501 --env-file ../.env sales_insight_streamlit
# Or set env inline and ensure 0.0.0.0 binding
# CMD already uses: --server.address 0.0.0.0 --server.port 8501
```

## ECR/ECS
- Build for amd64 on Apple Silicon:
```bash
docker build --platform linux/amd64 -t sales_insight_streamlit .
```
- Tag/push to ECR and use ECS task definition matching platform.

## Usage
1) Sales company page: enter website or upload Sales KB + technical doc
2) Prospect page: enter website or upload Prospect KB, then Start Simulation
3) The app renders the Sales Pitch first, streams the conversation, and finally shows the Playbook with downloads.
