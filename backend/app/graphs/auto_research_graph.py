from typing import TypedDict, List, Annotated, Literal
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document
from app.services.llm_service import llm_service
from app.services.vector_service import vector_service
from app.services.web_search_service import web_search_service # You'll need this
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# STATE DEFINITION
# ==============================================================================

class ResearchState(TypedDict):
    goal: str                   # The user's research goal
    plan: List[str]             # Step-by-step plan
    current_step: int           # Current step index
    gathered_info: List[str]    # Accumulated knowledge
    draft_report: str           # Current draft
    critique: str               # Critique of the draft
    iteration_count: int        # Loop counter
    finished: bool              # Is the research done?

# ==============================================================================
# NODES
# ==============================================================================

def planner_node(state: ResearchState):
    """Break the goal into a research plan."""
    goal = state["goal"]
    
    prompt = f"""
    You are an expert research planner.
    Goal: {goal}
    
    Create a step-by-step plan to research this topic thoroughly.
    Include steps for:
    1. Searching web for recent info
    2. Searching internal knowledge base
    3. Synthesizing findings
    4. Writing and critiquing
    
    Output a JSON list of steps.
    """
    
    llm = llm_service.get_llm(...) # Get user's configured LLM
    response = llm.invoke(prompt)
    
    # Parse plan (pseudo-code)
    plan = parse_plan(response.content) 
    
    return {"plan": plan, "current_step": 0, "gathered_info": []}

def researcher_node(state: ResearchState):
    """Execute the current research step (Web + Vector DB)."""
    current_step_idx = state["current_step"]
    plan = state["plan"]
    
    if current_step_idx >= len(plan):
        return {"finished": True}
    
    step_instruction = plan[current_step_idx]
    
    # 1. Search Web (for public info)
    web_results = web_search_service.search(step_instruction)
    
    # 2. Search Vector DB (for private info)
    # db_results = vector_service.search(...) 
    
    # Combine findings
    findings = f"Step: {step_instruction}\nWeb Results: {web_results}\n"
    
    return {
        "gathered_info": state["gathered_info"] + [findings],
        "current_step": current_step_idx + 1
    }

def writer_node(state: ResearchState):
    """Draft the report based on gathered info."""
    goal = state["goal"]
    info = "\n\n".join(state["gathered_info"])
    
    prompt = f"""
    Goal: {goal}
    Gathered Information:
    {info}
    
    Write a comprehensive research report. Include citations.
    """
    
    llm = llm_service.get_llm(...)
    response = llm.invoke(prompt)
    
    return {"draft_report": response.content}

def critic_node(state: ResearchState):
    """Critique the draft. Decide if more research is needed."""
    draft = state["draft_report"]
    goal = state["goal"]
    
    prompt = f"""
    Goal: {goal}
    Draft: {draft}
    
    Critique this report. Is it comprehensive? Are there gaps?
    If gaps exist, suggest specific additional research steps.
    Answer 'DONE' if satisfactory, or list missing info.
    """
    
    llm = llm_service.get_llm(...)
    response = llm.invoke(prompt)
    
    finished = "DONE" in response.content.upper()
    
    return {
        "critique": response.content,
        "finished": finished,
        "iteration_count": state["iteration_count"] + 1
    }

def revise_plan_node(state: ResearchState):
    """Update the plan based on critique."""
    critique = state["critique"]
    current_plan = state["plan"]
    
    prompt = f"""
    Current Plan: {current_plan}
    Critique: {critique}
    
    Add new research steps to address the critique.
    Output updated plan.
    """
    
    llm = llm_service.get_llm(...)
    response = llm.invoke(prompt)
    
    return {"plan": parse_plan(response.content)}

# ==============================================================================
# GRAPH BUILDING
# ==============================================================================

def build_auto_research_graph():
    workflow = StateGraph(ResearchState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("writer", writer_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("reviser", revise_plan_node)
    
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "writer")
    workflow.add_edge("writer", "critic")
    
    # Conditional Edge: Done or Revise?
    workflow.add_conditional_edges(
        "critic",
        lambda s: "end" if s["finished"] or s["iteration_count"] > 3 else "revise"
    )
    
    workflow.add_edge("revise", "researcher") # Loop back to research
    workflow.add_edge("end", END)
    
    return workflow.compile()

auto_research_graph = build_auto_research_graph()