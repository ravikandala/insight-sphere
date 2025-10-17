# Scraping Service (FastAPI)

This service scrapes a company's website using robots.txt and sitemaps (XML/HTML/text, with sitemap index recursion and gzip support), extracts top N URLs, fetches page content via Playwright (Chromium), summarizes with Bedrock, and uploads a JSON summary to S3 with a presigned URL.

## Endpoints
- GET /scrape?company=<domain-or-host>
  - Returns: { "s3_url": "<presigned-url>" }

## Environment Variables
- AWS_REGION: default us-east-1
- S3_BUCKET: required
- BEDROCK_MODEL: required (e.g., us.meta.llama3-3-70b-instruct-v1:0)

## Local Run
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```


## Docker
```bash
docker build -t sales_insights_scraping .
docker run -p 8000:8000 -e AWS_REGION=us-east-1 -e S3_BUCKET=<bucket> -e BEDROCK_MODEL=<model-id> sales_insights_scraping
```

## Notes
- If robots.txt has no sitemaps, falls back to homepage link extraction.
- Limits to top N URLs requested (default 10).
- Handles sitemap indexes and HTML/text sitemaps.
