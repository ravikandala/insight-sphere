import os
import json
import requests
from dotenv import load_dotenv
import streamlit as st
import time

# --- The Correct, Working Strands Imports ---
from strands.agent import Agent
from strands.models import BedrockModel
from pitch_generation import sales_pitch_generation
from strands.multiagent import GraphBuilder

# --- 1. Setup: Load KBs and Model ---
load_dotenv()

BEDROCK_MODEL = os.getenv("BEDROCK_MODEL")
Playbook_model = os.getenv("Playbook_model")
scraping_url = os.getenv("scraping_url")

# Fallback defaults to avoid None-related errors
if not BEDROCK_MODEL:
    BEDROCK_MODEL = "us.meta.llama3-3-70b-instruct-v1:0"
if not Playbook_model:
    Playbook_model = "us.meta.llama3-3-70b-instruct-v1:0"

def load_file(path, is_pitch=False):
    """Loads a file, creating a placeholder if it doesn't exist."""
    if not os.path.exists(path):
        placeholder = "# Sales Pitch..." if is_pitch else f"Placeholder for {os.path.basename(path)}."
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(placeholder)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def fetch_sales_kb_from_s3(company_name):
    """
    Given a company name, call an API to get a signed S3 URL,
    then download and return the file content as a string.
    """
    # 1. Call the API to get the signed S3 URL (replace with your actual API endpoint)
    api_url = f"{scraping_url}?company={company_name}"
    response = requests.get(api_url)
    response.raise_for_status()
    # print("response",response)
    signed_url = response.json().get("s3_url")
    if not signed_url:
        raise ValueError("No signed URL returned from API")

    # 2. Download the file using the signed URL
    file_response = requests.get(signed_url)
    file_response.raise_for_status()
    # print("file_response",file_response.json().get("summary"))
    content = file_response.json().get("summary")

    return content

# Usage: Replace 'AcmeCorp' with the actual company name
def run_simulation(company_name, prospect_company_name, conversation_container, technical_kb_text=None, sales_kb_text=None, prospect_kb_text=None):
    # company_name = "fissionLabs"
    # prospect_company_name = "Ul"
    sales_kb = sales_kb_text if sales_kb_text else fetch_sales_kb_from_s3(company_name)
    # Prefer uploaded Technical KB if provided; otherwise fall back to sales_kb
    technical_kb = technical_kb_text if technical_kb_text else sales_kb
    prospect_kb = prospect_kb_text if prospect_kb_text else fetch_sales_kb_from_s3(prospect_company_name)
    sales_pitch = sales_pitch_generation(sales_kb,technical_kb,prospect_kb) # Using the clean pitch file

    # Show the sales pitch before starting the conversation
    with conversation_container:
        st.markdown("## 🧾 Generated Sales Pitch")
        st.markdown(sales_pitch)
        st.divider()


    def conversation_transcript():
        # Set up the Bedrock model
        bedrock_model = BedrockModel(
            model_id=BEDROCK_MODEL,
            region_name="us-east-1",
            temperature=0.7,
        )

        # --- 2. Define the Agents (with Detailed Personas) ---

        prospect_agent = Agent(
            name="ProspectAgent",
            model=bedrock_model,
            system_prompt=f"""
            You are 'Alex', a Senior Director or a CTO at the prospect company. You are analytical, busy, and focused on ROI and implementation risk.
            Your task is to formulate the next question in a sales conversation. Ask an outstanding and realistic question from the sales pitch and prospect kb attached.
            balance between technical and sales questions.

            <BACKGROUND_DOCUMENTS>
            THE SALES PITCH YOU RECEIVED:
            ---
            {sales_pitch}
            ---

            YOUR INTERNAL COMPANY NOTES:
            ---
            {prospect_kb}
            ---
            </BACKGROUND_DOCUMENTS>

            The ongoing conversation history will be provided as your main input.

            **YOUR CURRENT TASK:**
            Based on ALL of the information above (your background documents AND the conversation history), your single objective is to generate ONE new, insightful, and challenging follow-up question.
            - Do not repeat previous questions.
            - Do not summarize the history.
            - Just ask the single new question.
            """
        )

        # MODIFIED: Router prompt is now a simple 2-way choice
        router_agent = Agent(
            name="RouterAgent",
            model=bedrock_model,
            system_prompt="""
            You are a router. Read the prospect's question. Who is best suited to answer?
            Your response MUST be ONLY the word 'Sales' for business, pricing, or relationship questions,
            or 'Technical' for feature, integration, or implementation questions.
            """
        )

        sales_agent = Agent(
            name="SalesAgent",
            model=bedrock_model,
            system_prompt=f"""
            You are 'Sarah', an engaging sales lead at Fission Labs. Your tone is confident and value-focused.

            YOUR INPUT is the full conversation history, ending with the prospect's latest question.
            YOUR TASK is to provide a direct and helpful answer to that last question, using your SALES KNOWLEDGE BASE for support.

            **RESPONSE STYLE: Your answer must be professional, confident, and concise. Aim for 2-3 short paragraphs. Get straight to the point.**
            **IMPORTANT: DO NOT repeat the prospect's question in your response. Just provide the answer.**

            Speak in terms of business outcomes: ROI, revenue growth, and risk reduction.**

            SALES KNOWLEDGE BASE:
            ---
            {sales_kb}
            ---
            """
        )

        technical_agent = Agent(
            name="TechnicalAgent",
            model=bedrock_model,
            system_prompt=f"""
            You are 'David', a solutions architect at Fission Labs, You are an expert at translating complex technology into clear business value and ROI.

            YOUR INPUT is the full conversation history, ending with the prospect's latest question.
            You MUST AVOID simply listing technologies.
            YOUR TASK is to provide a direct answer using the "Value Sandwich" method:

            1. Acknowledge the business problem behind their technical question.
            2. Briefly explain the technical approach, referencing a methodology from your TECHNICAL KNOWLEDGE BASE.
            3. Immediately pivot to the business outcome and ROI. Quantify the benefit whenever possible.

            **RESPONSE STYLE: Your answer must be professional, confident, and concise. Aim for 2-3 short paragraphs. Get straight to the point.**
            **IMPORTANT: DO NOT repeat the prospect's question in your response. Just provide the answer.**

            TECHNICAL KNOWLEDGE BASE:
            ---
            {technical_kb}
            ---
            """
        )


        # --- 3. Manually Orchestrate the Conversation in a Simple Loop ---
        print("Starting conversation simulation...")

        conversation_log = []
        max_turns = 6

        # for turn in range(max_turns):
        #     print(f"\n--- Turn {turn + 1} of {max_turns} ---")

        #     if turn == 0:
        #         context_for_prospect = "Based on the sales pitch and your internal notes, please ask your first question."
        #     else:
        #         context_for_prospect = "\n\n".join([f"{list(entry.keys())[0]}: {list(entry.values())[0]}" for entry in conversation_log])
        #     # ----------------

        #     # 1. Prospect asks a question
        #     prospect_response_obj = prospect_agent(context_for_prospect)
        #     prospect_question = prospect_response_obj.message['content'][0]['text'].strip()

        #     print(f"Prospect asks: {prospect_question}")
        #     conversation_log.append({"Prospect": prospect_question})

        #     # ... (the rest of the loop remains the same) ...
        #     router_response_obj = router_agent(prospect_question)
        #     routing_decision = router_response_obj.message['content'][0]['text'].strip().lower()
        #     print(f"Router decision: {routing_decision}")

        #     history_for_responder = "\n\n".join([f"{list(entry.keys())[0]}: {list(entry.values())[0]}" for entry in conversation_log])

        #     if "technical" in routing_decision:
        #         response_obj = technical_agent(history_for_responder)
        #         responder_answer = response_obj.message['content'][0]['text'].strip()
        #         print(f"Technical Agent responds: {responder_answer}")
        #         conversation_log.append({"Technical Agent": responder_answer})
        #     else:
        #         response_obj = sales_agent(history_for_responder)
        #         responder_answer = response_obj.message['content'][0]['text'].strip()
        #         print(f"Sales Agent responds: {responder_answer}")
        #         conversation_log.append({"Sales Agent": responder_answer})

        for turn in range(max_turns):
            # Display turn header in Streamlit
            with conversation_container:
                st.markdown(f"### 🔄 Turn {turn + 1} of {max_turns}")
                st.divider()

            if turn == 0:
                context_for_prospect = "Based on the sales pitch and your internal notes, please ask your first question."
            else:
                context_for_prospect = "\n\n".join([f"{list(entry.keys())[0]}: {list(entry.values())[0]}" for entry in conversation_log])

            # 1. Prospect asks a question
            with conversation_container:
                with st.spinner("🤔 Prospect is thinking..."):
                    prospect_response_obj = prospect_agent(context_for_prospect)
                    prospect_question = prospect_response_obj.message['content'][0]['text'].strip()

                st.markdown(f"**👤 Prospect (Alex):**")
                st.info(prospect_question)

            conversation_log.append({"Prospect": prospect_question})

            # 2. Router decision
            with conversation_container:
                with st.spinner("🔀 Routing to appropriate agent..."):
                    router_response_obj = router_agent(prospect_question)
                    routing_decision = router_response_obj.message['content'][0]['text'].strip().lower()

                if "technical" in routing_decision:
                    st.caption("↪️ *Routing to Technical Agent*")
                else:
                    st.caption("↪️ *Routing to Sales Agent*")

            history_for_responder = "\n\n".join([f"{list(entry.keys())[0]}: {list(entry.values())[0]}" for entry in conversation_log])

            # 3. Agent responds
            with conversation_container:
                if "technical" in routing_decision:
                    with st.spinner("🔧 Technical Agent (David) is responding..."):
                        response_obj = technical_agent(history_for_responder)
                        responder_answer = response_obj.message['content'][0]['text'].strip()
                    st.markdown(f"**🔧 Technical Agent (David):**")
                    st.success(responder_answer)
                    conversation_log.append({"Technical Agent": responder_answer})
                else:
                    with st.spinner("💼 Sales Agent (Sarah) is responding..."):
                        response_obj = sales_agent(history_for_responder)
                        responder_answer = response_obj.message['content'][0]['text'].strip()
                    st.markdown(f"**💼 Sales Agent (Sarah):**")
                    st.success(responder_answer)
                    conversation_log.append({"Sales Agent": responder_answer})

                st.divider()

            # Small delay for better UX
            time.sleep(0.5)

        return conversation_log, sales_kb, technical_kb, prospect_kb, sales_pitch

        # # --- 4. Save the Final Transcript ---
        # print("\n\n==========================")
        # print("✅ CONVERSATION SIMULATION COMPLETE")
        # print("==========================")

        # final_transcript_text = "\n\n".join([f"{list(entry.keys())[0]}: {list(entry.values())[0]}" for entry in conversation_log])

        # with open("conversation_transcript.json", "w", encoding="utf-8") as f:
        #     json.dump(conversation_log, f, indent=2)

        # print(final_transcript_text)
        # print("\n\n📄 Full conversation saved to 'conversation_transcript.json'")
        return conversation_log, sales_kb, technical_kb, prospect_kb, sales_pitch

    conversation_logs, sales_kb, technical_kb, prospect_kb, sales_pitch = conversation_transcript()


    with conversation_container:
        st.markdown("Generating Sales Playbook...")
        with st.spinner("Analyzing conversation and creating strategic playbook..."):
            transcript = "\n".join([f"{list(turn.keys())[0]}: {list(turn.values())[0]}" for turn in conversation_logs])
        bedrock_model = BedrockModel(
        model_id="us.anthropic.claude-opus-4-1-20250805-v1:0",
        region_name="us-east-1",
        temperature=0.3,
        max_tokens=30000
        )

        # --- 2. Define Agent Nodes ---
        conversation_analyst = Agent(
            name="ConversationAnalyst",
            model=bedrock_model,
            system_prompt="""
            You are a Forensic Sales Intelligence Analyst. You are like a detective analyzing an interrogation tape. Your mission is to dissect a sales conversation transcript and extract every piece of quantifiable evidence and psychological insight.

            Your output will be an intelligence brief for a master strategist. It must be brutally honest, data-rich, and leave no room for ambiguity.

            In the transcript Treat any expressed problem, concern, or question as an explicit pain point if it relates to the prospect's business, operations, or technology. Quote their exact words wherever possible.
            Analyze the conversation transcript you receive as input and produce a structured intelligence brief in Markdown format with these three sections:

            1. ## Key Prospect Pain Points
            - For each pain point, you MUST extract direct quotes and any associated metric (e.g., "manual reporting is slow," "37% data loss").
            - Quantify the business impact where possible, even if it's an estimate (e.g., "This likely leads to increased labor costs and delayed decision-making.").

            2. ## Customer Concerns & Objections
            - List every question, hesitation, or direct objection raised by the prospect.
            - Classify each concern as 'High Priority' (potential deal-blocker) or 'Low Priority' (request for information).

            3. ## Moments of High Interest (Buying Signals)
            - Identify the exact features, benefits, or outcomes that triggered a positive reaction or follow-up questions from the prospect.
            - Quote the prospect's words (e.g., "That's a significant value-add for our legal team.").
            """
        )


        # --- NECESSARY CHANGE 3: Providing all KBs to the final agent ---
        sales_strategist = Agent(
            name="SalesStrategist",
            model=bedrock_model,
            system_prompt=f"""
            You are a world-class sales strategist, a hybrid of a McKinsey consultant and a top-tier investment banker. Your language is sharp, confident, and relentlessly focused on financial impact. You use powerful analogies to make complex ideas simple and memorable.

            **YOUR REASONING PROCESS:**
            1.  First, you will deeply analyze the <INTELLIGENCE_BRIEF> from your analyst.
            2.  Second, for **every single point** in that brief, you will meticulously search the <BACKGROUND_REFERENCE_DOCUMENTS> to find a **specific, hard number, case study, or technical differentiator to use as 'ammunition'.**
            3.  Finally, you will construct the MASTER SALES PLAYBOOK, weaving this ammunition into a powerful, persuasive narrative.

            <INTELLIGENCE_BRIEF>
            {{analysis_report}}
            </INTELLIGENCE_BRIEF>

            <BACKGROUND_REFERENCE_DOCUMENTS>
            Original Sales Pitch:\n---\n{sales_pitch}\n---
            Prospect's Internal KB:\n---\n{prospect_kb}\n---
            Our Technical KB:\n---\n{technical_kb}\n---
            Our Sales KB:\n---\n{sales_kb}\n---
            </BACKGROUND_REFERENCE_DOCUMENTS>

            **YOUR TASK:**
            Produce a highly detailed and actionable sales playbook in markdown format with the following exhaustive sections. Translate all technical details into quantified business value.

            # ============== MASTER SALES PLAYBOOK ==============

            ## 1. EXECUTIVE SUMMARY
            - **1.1 Prospect Profile:** A detailed paragraph summarizing the prospect company, their market position, revenue, and key business priorities.
            - **1.2 Critical Pain Points:** A bulleted list of the top business challenges identified, including quantified impacts and a one line explanation of the pain point.
            - **1.3 The Winning Strategy:** A single, powerful paragraph that can be used as an 'elevator pitch' for the deal strategy, focused on a 3-phase, quantifiable plan.

            ## 2. DEEP DIVE: CONVERSATION ANALYSIS
            - **2.1 Customer Concerns:** List the specific questions and objections raised.
            - **2.2 Moments of High Interest:** Highlight the exact topics that resonated with the prospect along with justification

            ## 3. STRATEGIC GAME PLAN
            - **3.1 Key Talking Points & Value Propositions:** For each pain point, provide a specific, numbers-driven talking point that a salesperson can use (e.g., "When they mention X, you say Y to highlight Z% cost savings from our case study.").
            - **3.2 Competitive Angle:** State our key advantage over any known competitors, quantifying the difference.

            ## 4. KEY QUESTIONS & PREPARED ANSWERS
            - Predict the 5 most critical questions the prospect is likely to ask next. Preferably take it from the conversation transcript.
            - For each question, provide a concise, powerful, and business-value-focused answer a salesperson can use directly.

            ## 5. ADDRESSING CUSTOMER CONCERNS (Concerns Handling Matrix)
            - Create a table with three columns: "Prospect's Stated Concern," "The Real Underlying Issue," and "Your Recommended Response."
            - Responses must be empathetic and include quantitative proof points.

            ## 6. ACTIONABLE NEXT STEPS
            - **6.1 Primary Goal for Next Contact:** Define the single most important objective.
            - **6.2 Recommended Action:** Suggest a specific next action with a quantifiable benefit (e.g., "A 90-minute Profitability Workshop to build a custom ROI model").
            - **6.3 Sample Follow-Up Email:** Write a complete, ready-to-send draft that reinforces the key value propositions with numbers.

            # ===============================================

            **CRITICAL META-INSTRUCTION: You are not describing a plan; you are CREATING the plan. Do not write "We will provide...". You must generate the actual, complete, and detailed content for every single section.**
            """
        )



        # --- 3. Build the Graph ---
        print("Building the Strands graph...")
        builder = GraphBuilder()
        builder.add_node(conversation_analyst, "analyst_node")
        builder.add_node(sales_strategist, "strategist_node")
        builder.set_entry_point("analyst_node")
        builder.add_edge("analyst_node", "strategist_node")


        # --- 4. Compile and Run ---
        print("Compiling graph...")
        graph = builder.build()

        print("Invoking graph with transcript...")
        result = graph(transcript)


        def extract_text(message):
            content = message["content"]
            if isinstance(content, list):
                for block in content:
                    if "text" in block:
                        return block["text"].strip()
            return str(content).strip()

        final_playbook = extract_text(result.results["strategist_node"].result.message)


    # print("\n\n########################")
    # print("## Here is the Final Sales Playbook:")
    # print("########################\n")
    # print(final_playbook)

    # with open("sales_playbook.md", "w", encoding='utf-8') as f:
    #     f.write(final_playbook)

    # print("\n[SUCCESS] The playbook has been saved to sales_playbook.md")
    return conversation_logs, final_playbook, sales_pitch

# ----- Streamlit UI -----

st.set_page_config(page_title="Sales Conversation Simulator", layout="wide")

st.title("Sales Conversation Simulator & Playbook Generator")
# st.markdown("Watch AI agents engage in a realistic sales conversation in real-time")

# Two-step wizard state
if 'wizard_step' not in st.session_state:
    st.session_state['wizard_step'] = 1
if 'sales_company_name' not in st.session_state:
    st.session_state['sales_company_name'] = ''
if 'sales_kb_text' not in st.session_state:
    st.session_state['sales_kb_text'] = None
if 'technical_kb_text' not in st.session_state:
    st.session_state['technical_kb_text'] = None
if 'prospect_company_name' not in st.session_state:
    st.session_state['prospect_company_name'] = ''
if 'prospect_kb_text' not in st.session_state:
    st.session_state['prospect_kb_text'] = None
if 'start_clicked' not in st.session_state:
    st.session_state['start_clicked'] = False

def is_ready_to_start():
    return bool(st.session_state['sales_company_name'] and st.session_state['prospect_company_name'])

center_container = st.container()
with center_container:
    col_left, col_mid, col_right = st.columns([1, 2, 1])
    with col_mid:
        if st.session_state['wizard_step'] == 1:
            st.subheader("Sales Company")
            company_name = st.text_input("Sales Company Website", value=st.session_state['sales_company_name'], placeholder="https://example.com")
            st.markdown("<div style='text-align:center; color:#888'>or</div>", unsafe_allow_html=True)
            uploaded_sales_kb = st.file_uploader("Upload Sales KB (.txt, .md)", type=["txt", "md"], key="sales_kb_upload")
            sales_kb_text = st.session_state['sales_kb_text']
            if uploaded_sales_kb is not None:
                try:
                    sales_kb_text = uploaded_sales_kb.read().decode("utf-8")
                    st.caption("✅ Sales KB uploaded")
                except Exception:
                    st.warning("Could not read uploaded Sales KB.")

            uploaded_sales_tech = st.file_uploader("Upload Sales Technical Document (.txt, .md)", type=["txt", "md"], key="sales_tech_upload")
            technical_kb_text = st.session_state['technical_kb_text']
            if uploaded_sales_tech is not None:
                try:
                    technical_kb_text = uploaded_sales_tech.read().decode("utf-8")
                    st.caption("✅ Sales Technical Document uploaded")
                except Exception:
                    st.warning("Could not read Sales Technical Document.")

            st.markdown("---")
            if st.button("Next ➡️", use_container_width=True):
                st.session_state['sales_company_name'] = company_name
                st.session_state['sales_kb_text'] = sales_kb_text
                st.session_state['technical_kb_text'] = technical_kb_text
                st.session_state['wizard_step'] = 2

        elif st.session_state['wizard_step'] == 2:
            st.subheader("Prospect Company")
            prospect_name = st.text_input("Prospect Company Name or Website", value=st.session_state['prospect_company_name'], placeholder="https://prospect.com")
            st.markdown("<div style='text-align:center; color:#888'>or</div>", unsafe_allow_html=True)
            uploaded_prospect_kb = st.file_uploader("Upload Prospect KB (.txt, .md)", type=["txt", "md"], key="prospect_kb_upload")
            prospect_kb_text = st.session_state['prospect_kb_text']
            if uploaded_prospect_kb is not None:
                try:
                    prospect_kb_text = uploaded_prospect_kb.read().decode("utf-8")
                    st.caption("✅ Prospect KB uploaded")
                except Exception:
                    st.warning("Could not read uploaded Prospect KB.")

            st.markdown("---")
            back_col, start_col = st.columns(2)
            with back_col:
                if st.button("⬅️ Back", use_container_width=True):
                    st.session_state['prospect_company_name'] = prospect_name
                    st.session_state['prospect_kb_text'] = prospect_kb_text
                    st.session_state['wizard_step'] = 1
            with start_col:
                if st.button("🚀 Start Simulation", type="primary", use_container_width=True):
                    st.session_state['prospect_company_name'] = prospect_name
                    st.session_state['prospect_kb_text'] = prospect_kb_text
                    st.session_state['start_clicked'] = True

# --- SIMULATION START ---
if st.session_state['start_clicked']:
    if not is_ready_to_start():
        st.error("Please provide both Sales Company Name and Prospect Company Name before starting.")
    else:
        # Clear previous results
        st.session_state.pop('conversation_logs', None)
        st.session_state.pop('playbook', None)

        # Create container for live conversation
        conversation_container = st.container()

        with st.spinner("Generating sales conversation..."):
            # You should yield/print the conversation inside your simulation for streaming live output.
            # We'll simulate this here with a simple for-loop, but your run_simulation function needs to accept the container for true live display.

            try:
                effective_company_name = st.session_state['sales_company_name']
                effective_prospect_name = st.session_state['prospect_company_name']

                # Main simulation using stored values
                conversation_logs, final_playbook, sales_pitch = run_simulation(
                    effective_company_name,
                    effective_prospect_name,
                    conversation_container,    # Pass the container to be updated live
                    st.session_state['technical_kb_text'],
                    st.session_state['sales_kb_text'],
                    st.session_state['prospect_kb_text']
                )

                st.session_state['sales_pitch'] = sales_pitch
                st.session_state['conversation_logs'] = conversation_logs
                st.session_state['playbook'] = final_playbook

            except Exception as ex:
                st.error(f"❌ Error running simulation: {ex}")
                st.exception(ex)

            # Once out of the spinner, show completion and rest of UI
            conversation_container.success("✅ Simulation Complete!")

            st.markdown("---")
            st.markdown("## 🧾 Generated Sales Pitch")
            _pitch = st.session_state.get('sales_pitch')
            if _pitch:
                st.markdown(_pitch)
            else:
                st.info("Sales pitch not available.")

            dl1, dl2 = st.columns(2)
            with dl1:
                if _pitch:
                    st.download_button(
                        "⬇️ Download Sales Pitch",
                        _pitch.encode("utf-8"),
                        "sales_pitch.md",
                        use_container_width=True
                    )

            st.markdown("---")
            st.markdown("## 📋 Sales Playbook")
            st.markdown(st.session_state['playbook'])

            col1, col2 = st.columns(2)
            with col2:
                st.download_button(
                    "⬇️ Download Playbook",
                    st.session_state['playbook'].encode("utf-8"),
                    "sales_playbook.md",
                    use_container_width=True
                )

else:
    st.info("Configure your settings and click 'Start Simulation' to begin")

    # Show previous results if available
    if 'conversation_logs' in st.session_state and 'playbook' in st.session_state:
        st.markdown("---")
        st.markdown("## 📜 Previous Results")
        with st.expander("View Last Conversation", expanded=False):
            for turn in st.session_state['conversation_logs']:
                speaker = list(turn.keys())[0]
                message = list(turn.values())[0]
                st.markdown(f"**{speaker}:**")
                st.write(message)
                st.markdown("---")
        with st.expander("View Last Playbook", expanded=False):
            st.markdown(st.session_state['playbook'])
