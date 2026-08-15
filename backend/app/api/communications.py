from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database.connection import get_db
from app.models.models import Email, Meeting, ChatSession, WorkflowRun, AgentLog, Employee
from app.schemas.schemas import EmailResponse, MeetingResponse, ChatSessionResponse, WorkflowRunResponse
from app.middleware.rbac import get_current_user
from app.agents.graph import agent_graph
from app.agents.guardrails import AIGuardrails
from app.agents.memory import short_term_memory, long_term_memory

router = APIRouter(prefix="/api/communications", tags=["Communication & AI Sessions"])

@router.get("/emails", response_model=List[EmailResponse])
def get_emails(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve emails sent or received by the current employee."""
    emails = db.query(Email).filter(
        (Email.sender_id == current_user.employee_id) |
        (Email.receiver_id == current_user.employee_id)
    ).order_by(Email.sent_at.desc()).offset(skip).limit(limit).all()
    return emails

@router.get("/meetings", response_model=List[MeetingResponse])
def get_meetings(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """Retrieve meetings organized by the current employee or related to their projects."""
    # Find employee's assigned projects
    project_ids = [pm.project_id for pm in current_user.project_memberships]
    
    meetings = db.query(Meeting).filter(
        (Meeting.organizer_id == current_user.employee_id) |
        (Meeting.project_id.in_(project_ids))
    ).order_by(Meeting.meeting_date.desc()).offset(skip).limit(limit).all()
    return meetings

@router.get("/chats", response_model=List[ChatSessionResponse])
def get_chat_sessions(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100)
):
    """List AI assistant chat sessions for the current user."""
    sessions = db.query(ChatSession).filter(
        ChatSession.employee_id == current_user.employee_id
    ).order_by(ChatSession.started_at.desc()).offset(skip).limit(limit).all()
    return sessions

@router.get("/chats/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Retrieve a detailed chat session including its AI agent workflows and agent logs."""
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.employee_id == current_user.employee_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )
    return session

@router.post("/chats", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    title: str = Query(..., description="Title of the new chat session"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """Create a new AI agent chat session."""
    session = ChatSession(
        employee_id=current_user.employee_id,
        session_title=title,
        status="active"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

@router.post("/chats/{session_id}/message", response_model=WorkflowRunResponse)
def send_chat_message(
    session_id: int,
    message: str = Query(..., description="Message content sent to the AI Agent"),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_user)
):
    """
    Send a message to the AI agent. Executes the compiled LangGraph multi-agent flow:
    Runs safety checks, loads memory history, traverses the agent graph nodes,
    writes audit logs/traces to Postgres, and indexes long-term decisions.
    """
    session = db.query(ChatSession).filter(
        ChatSession.session_id == session_id,
        ChatSession.employee_id == current_user.employee_id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found."
        )

    # 1. Run Input Guardrails
    is_safe, error_msg = AIGuardrails.check_input(message)
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # 2. Retrieve history and construct initial state
    history = short_term_memory.get_history(session_id)
    
    user_role = current_user.role.role_name if current_user.role else "Employee"
    user_context = {
        "employee_id": current_user.employee_id,
        "role": user_role,
        "department_id": current_user.department_id
    }
    
    # Structure messages: history + new user prompt
    messages_payload = [{"role": m["role"], "content": m["content"]} for m in history]
    messages_payload.append({"role": "user", "content": message})
    
    initial_state = {
        "messages": messages_payload,
        "user_context": user_context,
        "retrieved_context": [],
        "agent_trace": []
    }
    
    # 3. Invoke compiled multi-agent state graph
    try:
        final_state = agent_graph.invoke(initial_state)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI Agent Graph execution failed: {e}"
        )

    # Extract final text output
    assistant_msgs = [m for m in final_state.get("messages", []) if m.get("role") == "assistant"]
    final_answer = assistant_msgs[-1]["content"] if assistant_msgs else "No agent output was generated."

    # 4. Save short-term memory
    short_term_memory.add_message(session_id, "user", message)
    short_term_memory.add_message(session_id, "assistant", final_answer)

    # 5. Persist Workflow Run
    last_trace = final_state.get("agent_trace", [{}])[-1]
    final_score = last_trace.get("confidence_score", 0.95) if last_trace else 0.95
    
    workflow = WorkflowRun(
        session_id=session_id,
        workflow_name=f"Enterprise QA: {message[:30]}...",
        status="completed",
        confidence_score=round(float(final_score), 2),
        final_output=final_answer,
        completed_at=datetime.utcnow()
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # 6. Save observability Agent Logs
    for trace in final_state.get("agent_trace", []):
        log = AgentLog(
            workflow_id=workflow.workflow_id,
            agent_name=trace.get("agent", "UnknownAgent"),
            task_description=trace.get("task_description") or "Executed step",
            input_data=str(trace.get("input_data", ""))[:500],
            output_data=str(trace.get("output_data", ""))[:1500],
            execution_time_ms=trace.get("latency_ms", 100),
            confidence_score=round(float(trace.get("confidence_score", 0.90)), 2)
        )
        db.add(log)
    db.commit()
    db.refresh(workflow)
    
    # 7. Check for decisions to index in long-term memory
    long_term_memory.auto_detect_and_index(session_id, current_user.employee_id, message, final_answer)
    
    return workflow
