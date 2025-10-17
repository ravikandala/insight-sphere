import os
import asyncio
import json
import uuid
from typing import List
import re
import requests
from bs4 import BeautifulSoup
from newspaper import Article
import boto3
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import sys
from strands.agent import Agent
from strands.models import BedrockModel
import xml.etree.ElementTree as ET
import httpx
from urllib.parse import urljoin, urlparse
import gzip
import io

load_dotenv()

# Environment Variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL")

if not S3_BUCKET or not BEDROCK_MODEL:
    raise ValueError("Environment variables S3_BUCKET and BEDROCK_MODEL must be set.")

if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# AWS Clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
bedrock_runtime = boto3.client("bedrock-runtime", region_name="us-east-1")

messages = [
    {
        "role": "user",
        "content": [{"text": "Summarize this text for me."}]
    }
]


# Set up the Bedrock model (define once, not inside functions)
bedrock_model = BedrockModel(
    model_id="us.meta.llama3-1-70b-instruct-v1:0",  # ✅ check your model id
    region_name="us-east-1",
    temperature=0.7,
)

def chunk_text(text: str, chunk_size: int = 1000) -> List[str]:
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

def summarize_chunk(chunk, prev_summary=None):
    # system_prompt = "You are a helpful summarization assistant."
    system_prompt = (
        "You are a careful summarization assistant. When given a previous running summary "
        "and a new chunk of text, you MUST produce an updated cumulative summary that "
        "retains all key points from the previous summary while integrating any new, "
        "non-duplicative information from the new chunk. Do not drop earlier points. "
        "If the new chunk adds nothing new, return the previous summary unchanged."
    )

    if prev_summary is None:
        messages = [
            {
                "role": "user",
                # "content": [{"text": f"Summarize the following text:\n\n{chunk}"}]
                "content": [{"text": (
                    "Summarize the following text into a concise summary capturing all key points.\n\n"
                    f"Text:\n{chunk}\n\n"
                    "Your output must be a self-contained summary."
                )}]
            }
        ]
    else:
        messages = [
            {
                "role": "user",
                # "content": [{"text": f"Given the previous summary:\n{prev_summary}\n\n"
                #                  f"Summarize the following additional text and integrate it:\n{chunk}"}]
                "content": [{"text": (
                    "You are updating a running summary.\n\n"
                    f"Previous summary (must be fully preserved unless contradicted):\n{prev_summary}\n\n"
                    f"New chunk of text to integrate:\n{chunk}\n\n"
                    "Task: Produce an UPDATED cumulative summary that (1) keeps all prior key points,"
                    " (2) integrates any new information, and (3) removes duplicates."
                )}]
            }
        ]

    summarize_agent = Agent(
        name="summarizeAgent",
        model=bedrock_model,
        system_prompt=system_prompt,  # must be string, not messages
        messages=messages
    )

    result = summarize_agent()  # call without extra prompt argument
    return result.output_text if hasattr(result, "output_text") else str(result)



def chain_summarize(text: str, chunk_size: int = 1000) -> str:
    summary = None
    for chunk in chunk_text(text, chunk_size):
        summary = summarize_chunk(chunk, summary)
    return summary

def upload_json_to_s3(data: dict, prefix: str = "summary") -> str:
    file_name = f"{prefix}_{uuid.uuid4().hex}.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=file_name,
        Body=json.dumps(data, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": file_name},
        ExpiresIn=3600,
    )
    return url

def _normalize_base_url(company_name: str) -> str:
    parsed = urlparse(company_name)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    # assume bare domain
    return f"https://{company_name.strip('/')}"


async def _fetch_text(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(url, timeout=20.0)
        resp.raise_for_status()
        # handle gzipped sitemaps explicitly when served with gzip content-type
        content_type = resp.headers.get("content-type", "").lower()
        if "application/x-gzip" in content_type or url.endswith(".gz"):
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(resp.content)) as gz:
                    return gz.read().decode("utf-8", errors="ignore")
            except Exception:
                return resp.text
        return resp.text
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""


def _same_domain(url: str, base_url: str) -> bool:
    try:
        return urlparse(url).netloc == urlparse(base_url).netloc
    except Exception:
        return True


def _extract_urls_from_html(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url + "/", href)
        if abs_url.startswith("http") and _same_domain(abs_url, base_url):
            urls.append(abs_url)
    return urls


def _extract_urls_from_text(text: str) -> List[str]:
    urls: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("sitemap:"):
            # skip sitemap declarations here; they are handled separately
            continue
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
    return urls


async def _collect_from_sitemap(client: httpx.AsyncClient, sitemap_url: str, base_url: str, limit: int, collected: List[str]) -> None:
    if len(collected) >= limit:
        return
    text = await _fetch_text(client, sitemap_url)
    if not text:
        return

    # Try XML first
    try:
        root = ET.fromstring(text)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        # sitemap index
        sitemap_elems = list(root.findall(".//sm:sitemap/sm:loc", ns))
        if sitemap_elems:
            for elem in sitemap_elems:
                if len(collected) >= limit:
                    break
                child_url = elem.text.strip() if elem.text else ""
                if child_url:
                    await _collect_from_sitemap(client, child_url, base_url, limit, collected)
            return
        # urlset
        url_elems = list(root.findall(".//sm:url/sm:loc", ns))
        if url_elems:
            for elem in url_elems:
                if len(collected) >= limit:
                    break
                loc = elem.text.strip() if elem.text else ""
                if loc and _same_domain(loc, base_url):
                    collected.append(loc)
            return
    except ET.ParseError:
        pass

    # If not XML or failed, try HTML extraction
    html_urls = _extract_urls_from_html(text, base_url)
    if html_urls:
        for u in html_urls:
            if len(collected) >= limit:
                break
            collected.append(u)
        return

    # Finally, treat as plaintext list of URLs
    text_urls = _extract_urls_from_text(text)
    for u in text_urls:
        if len(collected) >= limit:
            break
        if _same_domain(u, base_url):
            collected.append(u)


async def fetch_company_site_urls(company_name: str, num_urls: int = 10) -> List[str]:
    """Discover up to num_urls pages using robots.txt and sitemaps (XML, HTML, or text)."""
    base_url = _normalize_base_url(company_name)
    robots_url = f"{base_url}/robots.txt"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        robots_text = await _fetch_text(client, robots_url)
        sitemap_links: List[str] = []

        if robots_text:
            # Prefer explicit Sitemap: directives
            for line in robots_text.splitlines():
                if line.lower().startswith("sitemap:"):
                    link = line.split(":", 1)[1].strip()
                    if link:
                        sitemap_links.append(link)
            # Also fallback to regex for any links containing 'sitemap'
            if not sitemap_links:
                sitemap_links = re.findall(r"https?://[^\s'\"]*sitemap[^\s'\"]*", robots_text, flags=re.IGNORECASE)

        if not sitemap_links:
            # No sitemap found; fallback to base_url homepage and HTML crawl for links
            homepage_html = await _fetch_text(client, base_url)
            urls = _extract_urls_from_html(homepage_html, base_url)
            # Deduplicate while preserving order
            seen = set()
            deduped = []
            for u in urls:
                if u not in seen:
                    seen.add(u)
                    deduped.append(u)
                if len(deduped) >= num_urls:
                    break
            return deduped or [base_url]

        collected: List[str] = []
        for sm in sitemap_links:
            if len(collected) >= num_urls:
                break
            await _collect_from_sitemap(client, sm, base_url, num_urls, collected)

        # Deduplicate and cap
        seen = set()
        result: List[str] = []
        for u in collected:
            if u not in seen:
                seen.add(u)
                result.append(u)
            if len(result) >= num_urls:
                break
        return result or [base_url]

async def fetch_page_content(url: str) -> str:
    """Fetch full HTML using Playwright for individual articles."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            content = await page.content()
            await browser.close()
            return content
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return ""

async def scrape_and_summarize(company_name: str, num_pages: int = 5):
    # Step 1: Get URLs from the company's sitemap (robots.txt)
    site_urls = await fetch_company_site_urls(company_name, num_pages)  # returns list of URLs
    print("site_urls", site_urls)

    # Step 2: Scrape content from each URL
    website_texts = ""
    for url in site_urls:
        page_html = await fetch_page_content(url)  # fetch HTML for each URL
        page_soup = BeautifulSoup(page_html, "html.parser")
        main_text = page_soup.get_text(separator="\n", strip=True)
        website_texts += main_text[:2000] + "\n\n"  # limit each page's text to 2000 chars

    # Step 3: Summarize all collected website text
    final_summary = chain_summarize(website_texts)
    print("final_summaryjfdjwfbjekrbfj0000", final_summary)

    # Step 4: Save to S3 and return URL
    data_to_save = {
        "company_name": company_name,
        "summary": final_summary,
        "site_urls": site_urls  # include URLs for reference
    }
    s3_url = upload_json_to_s3(data_to_save)
    return s3_url



# FastAPI App
app = FastAPI(title="Scraper-Summarizer API")

@app.get("/scrape")
async def scrape_endpoint(company: str = Query(..., description="Company name to scrape")):
    try:
        s3_url = await scrape_and_summarize(company)
        return {"s3_url": s3_url}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
