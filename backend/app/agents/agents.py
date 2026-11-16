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
from app.services.sql_retriever import postgres_retriever
from app.services.answer_composer import compose_answer, context_for_prompt
from app.security.permissions import Perm, can

logger = logging.getLogger(__name__)


def _vector_hits(query: str, collection: str, user_context: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
    """Qdrant (+ Neo4j) hits for one collection, restricted to what the user may read."""
    hits = rag_service.search_collection(query, collection_name=collection, limit=limit, user_context=user_context)
    return [{"source": h["source"], "text": h["text"], "score": h.get("score")} for h in hits if h.get("text")]


def _merge(*groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Concatenate context lists, dropping exact duplicates."""
    seen, merged = set(), []
    for group in groups:
        for ctx in group or []:
            key = (ctx.get("source"), ctx.get("text"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(ctx)
    return merged

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
        - 'analytics': Handles structured counts, aggregates, and raw read-only SQL queries on the relational database.
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
        """Retrieval Agent: Hybrid lookup across PostgreSQL tables, Qdrant collections and the Neo4j graph."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]

        logger.info("Retrieval Agent running global hybrid retrieval...")

        # 1. Structured facts from the PostgreSQL tables (source of truth, RBAC-filtered)
        sql_contexts = postgres_retriever.search(query, user_context, limit=6)

        # 2. Semantic hits from Qdrant / Neo4j when those stores are available
        rag_hits = rag_service.global_search(query, limit=2, user_context=user_context)
        vector_contexts = []
        for col, hits in rag_hits.items():
            for h in hits:
                if h.get("text"):
                    vector_contexts.append({"source": h["source"], "text": h["text"], "score": h["score"]})

        flat_contexts = _merge(sql_contexts, vector_contexts)
        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "RetrievalAgent",
            "task_description": (
                f"Queried PostgreSQL ({len(sql_contexts)} facts) and Qdrant/Neo4j ({len(vector_contexts)} chunks)."
            ),
            "input_data": query,
            "output_data": f"Found {len(flat_contexts)} matching context blocks.",
            "latency_ms": latency,
            "confidence_score": 0.95 if flat_contexts else 0.5,
            "tokens_used": len(query) // 4
        }

        return {
            "current_agent": "RetrievalAgent",
            "retrieved_context": flat_contexts,
            "agent_trace": [trace]
        }

    @staticmethod
    def hr_node(state: AgentState) -> Dict[str, Any]:
        """HR Agent: Employee directory lookups (by name or id) and HR policy search."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]

        logger.info("HR Agent processing request...")

        # Employees named in the question, or referenced as "employee 42" / "my manager".
        # Field-level RBAC (salary, phone, date of birth) is applied inside the retriever.
        retrieved = postgres_retriever.search(query, user_context, domains=("employees",), limit=4)

        wants_policy = bool(re.search(r"polic|handbook|leave|vacation|benefit|sick|guideline|conduct|remote work|recruit", query.lower()))
        if wants_policy or not retrieved:
            policy_res = ControlledTools.search_hr_policy(query, user_context)
            # Keep the structured fields (title, version, owner) so the answer can present them properly
            retrieved = _merge(retrieved, [
                {k: v for k, v in hit.items() if k not in ("id", "metadata")}
                for hit in policy_res.get("results", []) if hit.get("text")
            ])

        if not retrieved:
            retrieved = postgres_retriever.search(query, user_context, domains=("departments",), limit=3)

        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "HRAgent",
            "task_description": "Executed HR database lookup or search HR policy manuals.",
            "input_data": query,
            "output_data": f"Retrieved {len(retrieved)} facts on employee profile or leave guidelines.",
            "latency_ms": latency,
            "confidence_score": 0.92 if retrieved else 0.5,
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

        # Departments named in the question ("Finance", "department 5", "my department").
        # Budget figures are only included for finance roles / the user's own department.
        retrieved = postgres_retriever.search(query, user_context, domains=("departments",), limit=4)

        if not retrieved and re.search(r"budget|allocat|approved|spend|fiscal|fund", query.lower()):
            retrieved = postgres_retriever.run("budget_overview", user_context)

        if not retrieved or "polic" in query.lower():
            # Financial rules live in the policies table / collection
            retrieved = _merge(
                retrieved,
                postgres_retriever.search(query, user_context, domains=("policies",), limit=2),
                _vector_hits(query, "policies", user_context, limit=2),
            )

        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "FinanceAgent",
            "task_description": "Queried corporate financial budgets.",
            "input_data": query,
            "output_data": f"Retrieved budget allocation status. Factual results size: {len(retrieved)}",
            "latency_ms": latency,
            "confidence_score": 0.94 if retrieved else 0.5,
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
        user_context = state["user_context"]

        logger.info("Sales Agent searching client directories...")

        # Clients named in the question; otherwise a portfolio overview.  Both require sales:read.
        retrieved = postgres_retriever.search(query, user_context, domains=("clients",), limit=4)
        if not retrieved:
            retrieved = postgres_retriever.run("sales_overview", user_context)

        # Contract documents are only added for roles that may read client data
        if can(user_context, Perm.SALES_READ):
            doc_hits = _merge(
                postgres_retriever.search(query, user_context, domains=("documents",), limit=2),
                _vector_hits(query, "documents", user_context, limit=3),
            )
            relevant = [h for h in doc_hits if re.search(r"contract|client|agreement", (h["text"] or "").lower())]
            retrieved = _merge(retrieved, relevant or doc_hits[:2])

        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "SalesAgent",
            "task_description": "Searched PostgreSQL client/contract tables and contract documents.",
            "input_data": query,
            "output_data": f"Collected {len(retrieved)} contract references.",
            "latency_ms": latency,
            "confidence_score": 0.90 if retrieved else 0.5,
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
        q_lower = query.lower()

        logger.info("Engineering Agent inspecting project board status...")

        # Projects referenced by id ("project 12"), code ("PRJ-2026-00012"), name, or "my projects".
        # Access is limited to project-oversight roles, the project manager and people working on it.
        retrieved = postgres_retriever.search(query, user_context, domains=("projects",), limit=8)

        if re.search(r"\bmy (?:open |pending |current )?tasks?\b|assigned to me", q_lower):
            retrieved = _merge(retrieved, postgres_retriever.run("my_tasks", user_context))

        if not retrieved and re.search(r"\bprojects?\b|portfolio", q_lower):
            retrieved = postgres_retriever.run("project_overview", user_context)

        if not retrieved:
            # Technical documentation
            retrieved = _merge(
                postgres_retriever.search(query, user_context, domains=("documents",), limit=3),
                _vector_hits(query, "documents", user_context, limit=2),
            )

        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "EngineeringAgent",
            "task_description": "Fetched project status and task allocations.",
            "input_data": query,
            "output_data": f"Extracted task list details. Factual count: {len(retrieved)}",
            "latency_ms": latency,
            "confidence_score": 0.93 if retrieved else 0.5,
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
        You are the SQL Analytics Agent. You convert user questions into ONE read-only PostgreSQL SELECT query.
        Database tables available:
        - departments (department_id, department_name, department_code, location, budget)
        - roles (role_id, role_name, role_level)
        - employees (employee_id, first_name, last_name, email, gender, hire_date, department_id, role_id, manager_id, employment_status, salary, office_location)
        - projects (project_id, project_name, project_code, client_id, department_id, project_manager_id, status, start_date, end_date, budget, priority)
        - tasks (task_id, project_id, assigned_to, title, status, priority, due_date, estimated_hours, actual_hours)
        - milestones (milestone_id, project_id, milestone_name, due_date, completion_date, status)
        - clients (client_id, company_name, industry, client_size, country, city, contract_value, status)
        - contracts (contract_id, client_id, contract_number, contract_title, contract_type, start_date, end_date, contract_value, status)
        - policies (policy_id, department_id, policy_name, version, effective_date, description)
        - documents (document_id, project_id, department_id, title, document_type)
        - budgets (budget_id, department_id, project_id, fiscal_year, allocated_amount, approved_amount)

        Rules: a single SELECT statement, no comments, no semicolons, never select password columns,
        add LIMIT 50 when listing rows. Output ONLY the SQL. Do not add markdown formatting or explanations.

        User Request: "{query}"
        """

        sql_query = ""
        sql_origin = "user"
        # A user may type a SELECT directly; it passes through the same guardrails
        sql_match = re.search(r"\bselect\b[\s\S]+", query, re.IGNORECASE)
        if sql_match:
            sql_query = sql_match.group(0)
        else:
            sql_origin = "llm"
            llm_sql = llm_service.generate(prompt, max_tokens=200)
            # Remove sql markdown formatting
            sql_query = re.sub(r"```sql|```", "", llm_sql or "").strip()
            if not sql_query.lower().startswith(("select", "with")):
                # No usable SQL from the model: fall back to the built-in question templates
                sql_origin = "template"
                sql_query = postgres_retriever.template_sql(query) or ""

        retrieved = []
        row_count = 0
        if sql_query.lower().startswith(("select", "with")):
            # RBAC + SQL guardrails are enforced inside the tool
            db_res = ControlledTools.execute_authorized_sql(sql_query, user_context)
            if db_res.get("success"):
                row_count = db_res.get("row_count", 0)
                rows = db_res.get("rows", [])
                rows_text = json.dumps(rows, default=str)
                # The SQL itself stays in the audit trace; the answer and its sources never show it.
                retrieved.append({
                    "source": "PostgreSQL analytics (calculated from company tables)",
                    "text": f"Calculated result ({row_count} rows): {rows_text[:3000]}",
                    "score": 1.0,
                    "pii_cleared": True,
                    "kind": "sql",
                    "label": "Company database (calculated)",
                    "columns": db_res.get("columns", []),
                    "rows": rows,
                    "filters": postgres_retriever.describe_filters(query) if sql_origin == "template" else "",
                    "sql": sql_query,
                })
            else:
                error = db_res.get("error", "")
                if error.startswith("Unauthorized"):
                    message = error.replace("Unauthorized: ", "", 1)
                    retrieved.append({
                        "source": "PostgreSQL analytics (blocked by access control)",
                        "text": f"Access denied: {message}",
                        "score": 1.0, "denied": True, "pii_cleared": True,
                        "kind": "denied", "label": "Access control",
                        "body": message[:1].upper() + message[1:],
                    })
                elif error.startswith("Query Violation"):
                    reason = error.replace("Query Violation: ", "", 1)
                    retrieved.append({
                        "source": "PostgreSQL analytics (blocked by guardrail)",
                        "text": f"The request was blocked by a data-safety rule: {reason}",
                        "score": 1.0, "pii_cleared": True,
                        "kind": "summary", "label": "Data-safety rules", "no_source": True,
                        "body": f"I can't run that request. It was blocked by a data-safety rule: {reason}",
                    })
                else:
                    logger.warning(f"Analytics query failed: {error}")
                    retrieved.append({
                        "source": "PostgreSQL analytics (execution error)",
                        "text": "The calculation could not be completed.",
                        "score": 1.0, "pii_cleared": True,
                        "kind": "summary", "label": "Analytics", "no_source": True,
                        "body": "I couldn't complete that calculation. Try rephrasing it as a count, total or average.",
                    })
        else:
            # Not expressible as SQL: answer from normal retrieval instead of failing
            retrieved = postgres_retriever.search(query, user_context, limit=5)
            if not retrieved:
                retrieved.append({
                    "source": "Analytics Agent",
                    "text": "The question could not be translated into a calculation.",
                    "kind": "summary", "label": "Analytics", "no_source": True, "pii_cleared": True,
                    "body": (
                        "I couldn't work out how to calculate that. I can count, total or average "
                        "employees, projects, tasks, clients, contracts, policies and budgets - for example "
                        "\"How many employees are in Finance?\" or \"Projects by status\"."
                    ),
                })

        latency = int((time.time() - start_time) * 1000)
        tokens = (len(prompt) + len(sql_query)) // 4

        trace = {
            "agent": "AnalyticsAgent",
            "task_description": "Translated the question into a read-only database query and ran it through the SQL guardrails.",
            "input_data": query,
            # The generated SQL is kept here for the audit trail only; the chat UI does not display it
            "output_data": f"Rows fetched: {row_count}. Query origin: {sql_origin}. Query: {sql_query[:1200]}",
            "latency_ms": latency,
            "confidence_score": 0.95 if row_count else 0.6,
            "tokens_used": tokens
        }

        return {
            "current_agent": "AnalyticsAgent",
            "retrieved_context": retrieved,
            "agent_trace": [trace]
        }

    @staticmethod
    def document_node(state: AgentState) -> Dict[str, Any]:
        """Document Agent: Match documents in the PostgreSQL catalogue and in Qdrant."""
        start_time = time.time()
        query = state["messages"][-1]["content"]
        user_context = state["user_context"]

        logger.info("Document Agent searching document registries...")

        retrieved = _merge(
            postgres_retriever.search(query, user_context, domains=("documents",), limit=3),
            _vector_hits(query, "documents", user_context, limit=3),
        )

        latency = int((time.time() - start_time) * 1000)

        trace = {
            "agent": "DocumentAgent",
            "task_description": "Searched the documents table and document vector embeddings.",
            "input_data": query,
            "output_data": f"Extracted {len(retrieved)} text chunks.",
            "latency_ms": latency,
            "confidence_score": 0.91 if retrieved else 0.5,
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
        
        user_context = state.get("user_context", {})
        prompt = ""
        fallback_contexts: List[Dict[str, Any]] = []
        if not contexts:
            # The routed specialist found nothing: try every PostgreSQL domain before giving up
            fallback_contexts = postgres_retriever.search(query, user_context, limit=6)
            contexts = fallback_contexts
        written_by = "composer"
        if not contexts:
            draft = compose_answer(query, [])
        else:
            # Short-term memory (Redis): the previous turns of this chat session
            history = state["messages"][:-1][-6:]
            history_lines = []
            for m in history:
                flat = re.sub(r"\s+", " ", str(m.get("content", "")))[:300]
                history_lines.append(f"{m.get('role', 'user')}: {flat}")
            history_block = "\n".join(history_lines) or "(no earlier messages)"

            prompt = f"""
            Answer the user's question using ONLY the numbered facts below. They were already filtered to what the user's job role ("{user_context.get('role', 'Employee')}") may see.

            How to write the answer:
            - Start with the direct answer in the first sentence. Write like a helpful colleague, not a report.
            - Keep it short. Use a markdown table only when comparing several rows, and bullet points only for lists.
            - Use **bold** for the key figure or name. No headings for short answers.
            - Never mention SQL, queries, table or column names, databases, vector stores, agents or how the data was retrieved.
            - Do not add a "Sources" section; the application shows sources separately.
            - If a fact says "Access denied" or that something is restricted, say plainly that the user doesn't have permission for that part. Never guess restricted or missing data.
            - If the facts do not answer the question, say so in one sentence.

            Conversation so far:
            {history_block}

            User question: "{query}"

            Facts:
            {context_for_prompt(contexts)}
            """

            system_instruction = (
                "You are the company's internal assistant. You answer accurately from the facts you are given, "
                "in clear conversational Markdown, and you never reveal technical internals."
            )
            draft = llm_service.generate(prompt, system_instruction=system_instruction, max_tokens=1200, strict=True)
            if draft:
                written_by = "language model"
            else:
                # No model configured, or the model call failed: write the answer deterministically
                draft = compose_answer(query, contexts)

        latency = int((time.time() - start_time) * 1000)
        tokens = (len(prompt) + len(draft)) // 4 if contexts else 0
        
        trace = {
            "agent": "ReportGeneratorAgent",
            "task_description": f"Wrote the answer from the retrieved facts ({written_by}).",
            "input_data": f"Context size: {len(contexts)} objects.",
            "output_data": f"Draft length: {len(draft)} chars.",
            "latency_ms": latency,
            "confidence_score": 0.96,
            "tokens_used": tokens
        }
        
        return {
            "current_agent": "ReportGeneratorAgent",
            "report_content": draft,
            "retrieved_context": fallback_contexts,
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
        
        # Scrub PII. Values that came from permission-checked database tools were
        # already authorised for this user and are kept; everything else is redacted.
        allowed_text = AIGuardrails.collect_allowed_pii(contexts)
        scrubbed_report = AIGuardrails.filter_pii(report, allowed_text)

        # Run hallucination verification
        user_messages = [m for m in state.get("messages", []) if m.get("role") == "user"]
        question = user_messages[-1]["content"] if user_messages else ""
        is_valid_facts, score = AIGuardrails.prevent_hallucination(scrubbed_report, contexts, question)

        final_answer = scrubbed_report
        if not is_valid_facts:
            final_answer += "\n\n*Note: I couldn't fully verify some of the figures in this answer against the source data, so please double-check them.*"
            
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
