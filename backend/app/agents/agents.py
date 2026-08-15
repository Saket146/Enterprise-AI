import logging
import time
import re
import json
from typing import Dict, Any, List

from app.agents.state import AgentState
from app.agents.tools import ControlledTools
from app.agents.guardrails import AIGuardrails
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class AgentNodes:
    """
    State Graph nodes for each of the 11 agents in the LangGraph workflow.
    Fitted with latency timers, token estimators, and safety checks.
    """

    @staticmethod
    def planner_node(state: AgentState) -> Dict[str, Any]:
        """Planner Agent: Classify user intent and route query to domain experts."""
        start_time = time.time()
        last_message = state["messages"][-1]["content"]
        
        logger.info(f"Planner Agent mapping query routing: '{last_message[:50]}'")
        
        # Build prompt for Planner
        prompt = f"""
        You are the Planner Agent for an Enterprise Operating System.
        Your job is to classify the user request and select the single most appropriate executor agent.
        Available Agents:
        - 'hr': Handles employee database lookup, manager hierarchies, and HR policy manual searches.
        - 'finance': Handles corporate budget checks, allocated vs approved funds, and fiscal sheets.
        - 'sales': Handles client profiles, industry details, and contracts documents.
        - 'engineering': Handles project statuses, pending tasks, milestones, and technical docs.
        - 'analytics': Handles raw read-only SQL queries on the relational database.
        - 'document': Handles document content parsing and text matching in file catalogs.
        - 'retrieval': Fallback agent for general knowledge queries matching Qdrant vector spaces.

        Select the agent. Respond in raw JSON format with fields:
        "next_agent": "<agent_name>",
        "reasoning": "<brief explanation>"

        User Request: "{last_message}"
        """
        
        system_instruction = "You are an orchestration router. You must respond ONLY with a raw JSON object."
        llm_response = llm_service.generate(prompt, system_instruction=system_instruction, max_tokens=100)
        
        # Parse output
        next_agent = "retrieval"
        reasoning = "Fallback semantic vector indexing."
        try:
            # Clean json formatting marks if any
            clean_json = re.sub(r"```json|```", "", llm_response).strip()
            data = json.loads(clean_json)
            next_agent = data.get("next_agent", "retrieval").lower()
            reasoning = data.get("reasoning", "")
        except Exception as e:
            logger.warning(f"Planner LLM output parsing failed, using heuristic router: {e}")
            fallback_route = llm_service.parse_routing(last_message, [])
            next_agent = fallback_route["next_agent"]
            reasoning = fallback_route["reasoning"]

        # Validate agent name
        valid_agents = ["retrieval", "hr", "finance", "sales", "engineering", "analytics", "document"]
        if next_agent not in valid_agents:
            next_agent = "retrieval"

        latency = int((time.time() - start_time) * 1000)
        tokens = (len(prompt) + len(llm_response)) // 4
        
        trace = {
            "agent": "PlannerAgent",
            "task_description": f"Classified query routing to '{next_agent.upper()}'. Reason: {reasoning}",
            "input_data": last_message,
            "output_data": f"Route: {next_agent}. Explanation: {reasoning}",
            "latency_ms": latency,
            "confidence_score": 0.98,
            "tokens_used": tokens
        }

        return {
            "current_agent": "PlannerAgent",
            "next_agent": next_agent,
            "agent_trace": [trace]
        }

    @staticmethod
    def retrieval_node(state: AgentState) -> Dict[str, Any]:
        """Retrieval Agent: Perform vector hybrid lookup across global databases."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        
        logger.info("Retrieval Agent running global hybrid retrieval...")
        
        # Global search
        rag_hits = rag_service.global_search(query, limit=2)
        
        flat_contexts = []
        for col, hits in rag_hits.items():
            for h in hits:
                flat_contexts.append({
                    "source": h["source"],
                    "text": h["text"],
                    "score": h["score"]
                })
                
        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "RetrievalAgent",
            "task_description": f"Queried Qdrant & Neo4j. Fetched {len(flat_contexts)} contexts.",
            "input_data": query,
            "output_data": f"Found {len(flat_contexts)} matching text blocks across collections.",
            "latency_ms": latency,
            "confidence_score": 0.95,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "RetrievalAgent",
            "retrieved_context": flat_contexts,
            "agent_trace": [trace]
        }

    @staticmethod
    def hr_node(state: AgentState) -> Dict[str, Any]:
        """HR Agent: Execute HR tool calls or lookup company policies."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]
        
        logger.info("HR Agent processing request...")
        
        # Decide if seeking an employee ID or checking generic policies
        emp_ids = re.findall(r"\b\d+\b", query)
        retrieved = []
        
        if emp_ids:
            emp_id = int(emp_ids[0])
            details = ControlledTools.get_employee_details(emp_id, user_context)
            if details.get("success"):
                retrieved.append({
                    "source": f"Postgres database: employees table (ID {emp_id})",
                    "text": f"Employee Profile Details: Name: {details['name']}, Email: {details['email']}, Status: {details['employment_status']}, Role: {details['role']}, Dept: {details['department']}, Manager: {details['manager']}, Office: {details['office_location']}."
                })
            else:
                retrieved.append({
                    "source": "Postgres database: employees (unauthorized)",
                    "text": f"Error: {details.get('error')}"
                })
        else:
            # Policy search
            policy_res = ControlledTools.search_hr_policy(query, user_context)
            for hit in policy_res.get("results", []):
                retrieved.append({
                    "source": hit["source"],
                    "text": hit["text"]
                })

        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "HRAgent",
            "task_description": "Executed HR database lookup or search HR policy manuals.",
            "input_data": query,
            "output_data": f"Retrieved {len(retrieved)} facts on employee profile or leave guidelines.",
            "latency_ms": latency,
            "confidence_score": 0.92,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "HRAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def finance_node(state: AgentState) -> Dict[str, Any]:
        """Finance Agent: Verify budgets and financial allocations."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]
        
        logger.info("Finance Agent processing budget queries...")
        
        ids = re.findall(r"\b\d+\b", query)
        retrieved = []
        
        if ids:
            dept_id = int(ids[0])
            budget_res = ControlledTools.get_budget_information(dept_id, user_context)
            if budget_res.get("success"):
                fiscal_details = ", ".join([f"Year {f['fiscal_year']}: Allocated {f['allocated']}, Approved {f['approved']}" for f in budget_res['fiscal_runs']])
                fact = f"Department budget for {budget_res['department_name']} (Total: {budget_res['total_budget']}). Breakdown: {fiscal_details}."
                retrieved.append({
                    "source": f"Postgres database: budgets table (Dept {dept_id})",
                    "text": fact
                })
            else:
                retrieved.append({
                    "source": f"Postgres database: budgets (Dept {dept_id})",
                    "text": f"Error: {budget_res.get('error')}"
                })
        else:
            # Query vector DB policies for financial rules
            hits = rag_service.search_collection(query, collection_name="policies", limit=2)
            for h in hits:
                retrieved.append({"source": h["source"], "text": h["text"]})

        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "FinanceAgent",
            "task_description": "Queried corporate financial budgets.",
            "input_data": query,
            "output_data": f"Retrieved budget allocation status. Factual results size: {len(retrieved)}",
            "latency_ms": latency,
            "confidence_score": 0.94,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "FinanceAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def sales_node(state: AgentState) -> Dict[str, Any]:
        """Sales Agent: Retrieve contract parameters and client accounts."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        
        logger.info("Sales Agent searching client directories...")
        
        # Retrieve client contract documents from Qdrant
        hits = rag_service.search_collection(query, collection_name="documents", limit=3)
        retrieved = []
        for h in hits:
            if "contract" in h["text"].lower() or "client" in h["text"].lower() or "agreement" in h["text"].lower():
                retrieved.append({
                    "source": h["source"],
                    "text": h["text"]
                })
                
        # If nothing matches contracts, just return top hits
        if not retrieved:
            retrieved = [{"source": h["source"], "text": h["text"]} for h in hits[:2]]

        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "SalesAgent",
            "task_description": "Searched Qdrant vector documents for client contracts.",
            "input_data": query,
            "output_data": f"Collected {len(retrieved)} contract references.",
            "latency_ms": latency,
            "confidence_score": 0.90,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "SalesAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def engineering_node(state: AgentState) -> Dict[str, Any]:
        """Engineering Agent: Collect project status, tasks and milestones."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]
        
        logger.info("Engineering Agent inspecting project board status...")
        
        ids = re.findall(r"\b\d+\b", query)
        retrieved = []
        
        if ids:
            proj_id = int(ids[0])
            status_res = ControlledTools.get_project_status(proj_id, user_context)
            task_res = ControlledTools.get_pending_tasks(proj_id, user_context)
            
            if status_res.get("success"):
                retrieved.append({
                    "source": f"Postgres database: projects table (ID {proj_id})",
                    "text": f"Project {status_res['name']} ({status_res['code']}) is {status_res['status']} with priority {status_res['priority']}. Manager: {status_res['manager']}. Budget: {status_res['budget']}."
                })
            else:
                retrieved.append({
                    "source": f"Postgres: projects (ID {proj_id})",
                    "text": f"Error: {status_res.get('error')}"
                })
                
            if task_res.get("success"):
                taskList = ", ".join([f"{t['title']} ({t['status']} - Assignee: {t['assignee']})" for t in task_res['tasks']])
                retrieved.append({
                    "source": f"Postgres database: tasks table (Project {proj_id})",
                    "text": f"Pending Tasks: {taskList or 'None'}"
                })
        else:
            # Query documents collection in Qdrant for technical manual files
            hits = rag_service.search_collection(query, collection_name="documents", limit=2)
            for h in hits:
                retrieved.append({"source": h["source"], "text": h["text"]})

        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "EngineeringAgent",
            "task_description": "Fetched project status and task allocations.",
            "input_data": query,
            "output_data": f"Extracted task list details. Factual count: {len(retrieved)}",
            "latency_ms": latency,
            "confidence_score": 0.93,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "EngineeringAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def analytics_node(state: AgentState) -> Dict[str, Any]:
        """Analytics Agent: Synthesize read-only SQL queries on Postgres database."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]
        
        logger.info("Analytics Agent analyzing SQL generation requirements...")
        
        # Build prompt for LLM to write a SELECT query
        prompt = f"""
        You are the SQL Analytics Agent. You convert user questions into read-only SQL SELECT queries.
        Database tables available:
        - departments (department_id, department_name, department_code, location, budget)
        - employees (employee_id, first_name, last_name, email, phone, gender, hire_date, department_id, role_id, manager_id, employment_status, salary, office_location)
        - projects (project_id, project_name, project_code, status, budget, priority)
        - tasks (task_id, project_id, assigned_to, title, status, priority, estimated_hours, actual_hours)
        - roles (role_id, role_name, role_level)
        - policies (policy_id, department_id, policy_name, version, description)
        - budgets (budget_id, department_id, project_id, fiscal_year, allocated_amount, approved_amount)
        
        Output ONLY the SQL SELECT statement. Do not add markdown formatting or explanations.
        
        User Request: "{query}"
        """
        
        sql_query = ""
        # Clean regex check in case LLM is mocked
        sql_match = re.search(r"\bselect\b[\s\S]+", query, re.IGNORECASE)
        if sql_match:
            sql_query = sql_match.group(0)
        else:
            llm_sql = llm_service.generate(prompt, max_tokens=150)
            # Remove sql markdown formatting
            sql_query = re.sub(r"```sql|```", "", llm_sql).strip()
            
        retrieved = []
        if sql_query.lower().startswith("select"):
            db_res = ControlledTools.execute_authorized_sql(sql_query, user_context)
            if db_res.get("success"):
                rows_text = json.dumps(db_res.get("rows", []))
                retrieved.append({
                    "source": f"SQL query: '{sql_query}'",
                    "text": f"SQL Output Row Results: {rows_text[:1500]}"
                })
            else:
                retrieved.append({
                    "source": f"SQL Execution Error: '{sql_query}'",
                    "text": f"Database reported: {db_res.get('error')}"
                })
        else:
            retrieved.append({
                "source": "Analytics Agent",
                "text": "Failed to translate query to a secure SQL SELECT statement."
            })
            
        latency = int((time.time() - start_time) * 1000)
        tokens = (len(prompt) + len(sql_query)) // 4
        
        trace = {
            "agent": "AnalyticsAgent",
            "task_description": f"Translated text to Cypher SQL: '{sql_query[:60]}...'. Executed on database engine.",
            "input_data": query,
            "output_data": f"Rows fetched: {len(retrieved)}",
            "latency_ms": latency,
            "confidence_score": 0.95,
            "tokens_used": tokens
        }
        
        return {
            "current_agent": "AnalyticsAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def document_node(state: AgentState) -> Dict[str, Any]:
        """Document Agent: Match and parse file documents inside Qdrant."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        
        logger.info("Document Agent searching document registries...")
        
        hits = rag_service.search_collection(query, collection_name="documents", limit=3)
        retrieved = [{"source": h["source"], "text": h["text"]} for h in hits]
        
        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "DocumentAgent",
            "task_description": "Scanned file document vector text embeddings.",
            "input_data": query,
            "output_data": f"Extracted {len(retrieved)} text chunks.",
            "latency_ms": latency,
            "confidence_score": 0.91,
            "tokens_used": len(query) // 4
        }
        
        return {
            "current_agent": "DocumentAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def report_generator_node(state: AgentState) -> Dict[str, Any]:
        """Report Generator Agent: Structure gathered context into a unified report draft."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        contexts = state.get("retrieved_context", [])
        
        logger.info("Report Generator synthesizing responses...")
        
        if not contexts:
            draft = "No retrieved context was loaded to answer the query."
        else:
            # Build synthesis prompt
            context_block = ""
            for idx, c in enumerate(contexts):
                context_block += f"Source: {c.get('source')}\n{c.get('text')}\n\n"
                
            prompt = f"""
            You are the Report Generator Agent. Synthesize a professional, comprehensive, and clear markdown report answering the user query based ONLY on the retrieved contexts below.
            Always list the sources used at the end of the document.
            
            User Query: "{query}"
            
            Retrieved Contexts:
            {context_block}
            """
            
            system_instruction = "You are a report writer. Synthesize information accurately, avoid speculation, and formats as clean Markdown."
            draft = llm_service.generate(prompt, system_instruction=system_instruction, max_tokens=1200)

        latency = int((time.time() - start_time) * 1000)
        tokens = len(prompt) // 4 if contexts else 0
        
        trace = {
            "agent": "ReportGeneratorAgent",
            "task_description": "Synthesized markdown report combining database entries and vector hits.",
            "input_data": f"Context size: {len(contexts)} objects.",
            "output_data": f"Draft length: {len(draft)} chars.",
            "latency_ms": latency,
            "confidence_score": 0.96,
            "tokens_used": tokens
        }
        
        return {
            "current_agent": "ReportGeneratorAgent",
            "report_content": draft,
            "agent_trace": [trace]
        }

    @staticmethod
    def critic_node(state: AgentState) -> Dict[str, Any]:
        """Critic Agent: Quality evaluation step checking completeness and accuracy."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        report = state.get("report_content", "")
        
        logger.info("Critic Agent evaluating report quality...")
        
        prompt = f"""
        You are the Critic Agent. Evaluate if the draft report below fully answers the user request: "{query}".
        Check for any gaps or formatting issues.
        If the report is accurate and answers the request, respond with "APPROVED".
        If it needs adjustments, write a descriptive feedback note explaining what needs to be changed.
        
        Draft Report:
        {report}
        """
        
        system_instruction = "You are a quality assurance inspector. Be critical and verify that all parts of the user request are covered."
        evaluation = llm_service.generate(prompt, system_instruction=system_instruction, max_tokens=150)
        
        approved = "approved" in evaluation.lower()
        feedback = "" if approved else evaluation.strip()
        
        latency = int((time.time() - start_time) * 1000)
        tokens = (len(prompt) + len(evaluation)) // 4
        
        trace = {
            "agent": "CriticAgent",
            "task_description": f"Evaluated report draft completeness. Approved: {approved}.",
            "input_data": f"Report size: {len(report)} chars.",
            "output_data": f"Evaluation output: {evaluation}",
            "latency_ms": latency,
            "confidence_score": 0.97,
            "tokens_used": tokens
        }
        
        return {
            "current_agent": "CriticAgent",
            "critic_feedback": feedback,
            "agent_trace": [trace]
        }

    @staticmethod
    def verification_node(state: AgentState) -> Dict[str, Any]:
        """Verification Agent: Scrub PII and execute factual correctness hallucination check."""
        start_time = time.time()
        report = state.get("report_content", "")
        contexts = state.get("retrieved_context", [])
        
        logger.info("Verification Agent scrubbing PII and checking factual accuracy...")
        
        # Scrub PII
        scrubbed_report = AIGuardrails.filter_pii(report)
        
        # Run hallucination verification
        is_valid_facts, score = AIGuardrails.prevent_hallucination(scrubbed_report, contexts)
        
        final_answer = scrubbed_report
        if not is_valid_facts:
            final_answer += f"\n\n> ⚠️ *Warning: Factual accuracy of some numbers/metrics in this response could not be fully verified against databases (Fact check score: {int(score*100)}%).*"
            
        latency = int((time.time() - start_time) * 1000)
        
        trace = {
            "agent": "VerificationAgent",
            "task_description": f"Verified factual metrics against context. Score: {int(score*100)}%. Scrubbed email/phone PII patterns.",
            "input_data": f"Report size: {len(report)} chars.",
            "output_data": f"Safety audited and cleared report.",
            "latency_ms": latency,
            "confidence_score": round(score, 2),
            "tokens_used": len(report) // 4
        }
        
        return {
            "current_agent": "VerificationAgent",
            "messages": [{"role": "assistant", "content": final_answer}],
            "agent_trace": [trace]
        }
