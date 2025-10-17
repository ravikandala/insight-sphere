import os
from dotenv import load_dotenv

# --- Strands Imports (Updated for Bedrock) ---
from strands.agent import Agent
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
import requests

# --- 1. Setup: Load KBs and Set Up Bedrock Model (CHANGED) ---
load_dotenv()

def load_file(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(f"This is a placeholder for {os.path.basename(path)}.")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()



# # Usage: Replace 'AcmeCorp' with the actual company name
# company_name = "fissionLabs"
# prospect_company_name = "Ul"
# sales_kb = fetch_sales_kb_from_s3(company_name)
# print("sales_kb",sales_kb)
# technical_kb = sales_kb #load_file("kb_data/fission_technical_kb.md")
# prospect_kb = fetch_sales_kb_from_s3(prospect_company_name)

# Change from GeminiModel to BedrockModel
# The AWS keys are found automatically from your .env file.
def sales_pitch_generation(sales_kb,technical_kb,prospect_kb):
    bedrock_model = BedrockModel(
        model_id="us.meta.llama3-3-70b-instruct-v1:0",
        region_name="us-east-1",
        temperature=0.3,
    )

    # --- 2. Define the Agent Nodes (Logic is Unchanged) ---
    prospect_analyzer = Agent(
        name="ProspectAnalyzer",
        model=bedrock_model,
        system_prompt=f"""
    You are a business analyst. Your job is to read the following prospect information and identify **the key business challenges**.

    PROSPECT INFORMATION:
    ---
    {prospect_kb}
    ---

    Instructions:
    - Provide a concise bulleted list of the primary challenges.
    - Group related challenges under high-level categories if possible.
    - Focus on business impact, not technical details.
    - Keep it readable for non-technical executives.
    """
    )


    technical_solver = Agent(
        name="TechnicalSolver",
        model=bedrock_model,
        system_prompt=f"""
    You are a solutions architect. You will receive a list of a prospect's pain points. Your job is to provide **specific, quantified solutions** based on our technical documentation.

    OUR TECHNICAL DOCUMENTATION:
    ---
    {technical_kb}
    ---

    Instructions:
    - Do NOT restate the pain points.
    - For each pain point, write a clear solution in business terms.
    - Include metrics and numbers whenever possible (e.g., % reduction in workload, improvement in efficiency, cost savings).
    - Solutions must be concise, actionable, and easily understood by business stakeholders.
    - This output will be passed to the next agent, so avoid unnecessary repetition or verbose explanations.
    """
    )


    sales_pitcher = Agent(
        name="SalesPitcher",
        model=bedrock_model,
        system_prompt=f"""
    You are a senior sales executive, expert in communicating business value.

    You will receive a dossier containing:
    - Competitive research
    - Quantified solutions for the prospect's pain points

    Your task is to create a **high-quality, persuasive sales analysis report in Markdown** with four sections:

    1. **Competitive Analysis**
    - Summarize the market context and key differentiators of the prospect.
    2. **Identified Pain Points**
    - Provide a **brief summary only** (2-3 sentences max) of the main challenges.
    3. **Proposed Solutions**
    - Present the solutions received from the previous agent.
    - Focus on business impact and quantified outcomes.
    - Avoid repeating the full pain point text.
    4. **Executive Sales Narrative**
    - Write a **multi-paragraph persuasive narrative**.
    - Weave the quantified solutions naturally into the text.
    - Highlight cost savings, efficiency improvements, ROI, risk reduction, and customer impact.
    - Do NOT repeat sections 1-3 verbatim.

    Guidelines:
    - Translate technical solutions into **business outcomes** understandable by non-technical stakeholders.
    - Avoid technical jargon, model names, or implementation details.
    - Emphasize metrics, KPIs, and measurable benefits wherever possible.
    - Keep the tone professional, persuasive, and executive-friendly.

    Use these guides for context:
    PROSPECT INFO:
    ---
    {prospect_kb}
    ---
    SALES GUIDE:
    ---
    {sales_kb}
    ---
    """
    )


    # --- 3. Build the Graph ---
    print("Building the graph...")
    builder = GraphBuilder()

    # --- THE FIX: The Agent OBJECT must be the first argument ---
    builder.add_node(prospect_analyzer, "prospect_analyzer_node")
    builder.add_node(technical_solver, "technical_solver_node")
    builder.add_node(sales_pitcher, "sales_pitcher_node")
    # -------------------------------------------------------------

    # Now that nodes are registered correctly, use the STRING IDs for the entry point and edges
    builder.set_entry_point("prospect_analyzer_node")
    builder.add_edge("prospect_analyzer_node", "technical_solver_node")
    builder.add_edge("technical_solver_node", "sales_pitcher_node")

    # --- 4. Compile and Run ---
    print("Compiling graph...")
    graph = builder.build()

    print("Invoking graph...")
    initial_task = "Analyze the provided prospect information."
    result = graph(initial_task)

    print("\n\n==========================")
    print("✅ PIPELINE COMPLETE")
    print("==========================")

    def extract_text(message):
        """
        Safely extract text from a Strands message object.
        Handles cases where content is a list or a single string.
        """
        content = message.get("content", "")
        if isinstance(content, list):
            # Concatenate all 'text' fields if multiple blocks exist
            texts = []
            for block in content:
                if isinstance(block, dict) and "text" in block:
                    texts.append(block["text"].strip())
                elif isinstance(block, str):
                    texts.append(block.strip())
            return "\n".join(texts)
        elif isinstance(content, str):
            return content.strip()
        else:
            return str(content)

    pain_points = extract_text(result.results["prospect_analyzer_node"].result.message)
    solutions   = extract_text(result.results["technical_solver_node"].result.message)
    final_pitch = extract_text(result.results["sales_pitcher_node"].result.message)


    markdown_report = f"""
    # Sales Analysis Report

    ---

    ## 🔬 Identified Pain Points
    {pain_points}

    ---

    ## 💡 Proposed Solutions
    {solutions}

    ---

    ## 👔 Final Sales Pitch
    {final_pitch}
    """

    # with open("sales_pitch.md", "w", encoding="utf-8") as f:
    #     f.write(markdown_report)

    # print(markdown_report)
    # print("\n\n📄 Full analysis saved to 'sales_pitch.md'")

    return markdown_report
