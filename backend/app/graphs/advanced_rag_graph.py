# backend/app/graphs/advanced_rag_graph.py
from langgraph.graph import StateGraph, END, START
from typing import List, TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph.message import add_messages

class AdvancedRAGState(TypedDict):
    messages: Annotated[List[dict], add_messages]
    original_question: str
    decomposed_questions: List[str]  # Multi-hop breakdown
    current_hop: int
    all_retrieved_docs: List[dict]
    intermediate_answers: List[str]
    final_answer: str
    reasoning_trace: str
    confidence_score: float

def decompose_question_node(state: AdvancedRAGState):
    """Break complex question into multiple sub-questions (Karpathy-style reasoning)."""
    question = state["original_question"]
    
    prompt = f"""
    Break this complex question into 2-4 simpler sub-questions that need to be answered sequentially.
    Each sub-question should build on previous answers.
    
    Question: {question}
    
    Output format (JSON):
    {{
        "sub_questions": ["question 1", "question 2", ...],
        "reasoning": "Why these sub-questions are needed"
    }}
    """
    
    response = llm.invoke(prompt)
    # Parse JSON response
    decomposed = parse_json_response(response)
    
    return {
        "decomposed_questions": decomposed["sub_questions"],
        "reasoning_trace": decomposed["reasoning"],
        "current_hop": 0
    }

def multi_hop_retrieval_node(state: AdvancedRAGState):
    """Execute retrieval for each hop, using previous answers as context."""
    current_hop = state["current_hop"]
    decomposed = state["decomposed_questions"]
    
    if current_hop >= len(decomposed):
        return {"current_hop": current_hop}  # All hops complete
    
    # Get current sub-question
    sub_question = decomposed[current_hop]
    
    # Add previous answers as context
    previous_context = "\n".join(state["intermediate_answers"])
    
    if previous_context:
        enhanced_query = f"""
        Previous findings:
        {previous_context}
        
        Current question: {sub_question}
        """
    else:
        enhanced_query = sub_question
    
    # Retrieve documents
    docs = vector_service.search(enhanced_query, k=3)
    
    return {
        "all_retrieved_docs": state["all_retrieved_docs"] + [docs],
        "current_hop": current_hop + 1
    }

def synthesize_answer_node(state: AdvancedRAGState):
    """Combine all intermediate answers into final response."""
    all_docs = state["all_retrieved_docs"]
    intermediate = state["intermediate_answers"]
    original_question = state["original_question"]
    reasoning = state["reasoning_trace"]
    
    prompt = f"""
    Original Question: {original_question}
    
    Reasoning Process:
    {reasoning}
    
    Intermediate Findings:
    {chr(10).join(intermediate)}
    
    All Retrieved Context:
    {all_docs}
    
    Synthesize a comprehensive final answer that addresses the original question
    using all the intermediate findings. Show your reasoning trace.
    
    Final Answer:
    """
    
    response = llm.invoke(prompt)
    
    # Calculate confidence score based on document quality
    confidence = calculate_confidence(all_docs, response)
    
    return {
        "final_answer": response.content,
        "confidence_score": confidence,
        "messages": [AIMessage(content=response.content)]
    }

def should_continue_hops(state: AdvancedRAGState):
    """Decide if more hops are needed."""
    if state["current_hop"] < len(state["decomposed_questions"]):
        return "continue"
    return "synthesize"

# Build Multi-Hop Graph
def build_advanced_rag_graph():
    workflow = StateGraph(AdvancedRAGState)
    
    workflow.add_node("decompose", decompose_question_node)
    workflow.add_node("retrieve_hop", multi_hop_retrieval_node)
    workflow.add_node("synthesize", synthesize_answer_node)
    
    workflow.add_edge(START, "decompose")
    workflow.add_edge("decompose", "retrieve_hop")
    
    workflow.add_conditional_edges(
        "retrieve_hop",
        should_continue_hops,
        {
            "continue": "retrieve_hop",
            "synthesize": "synthesize"
        }
    )
    
    workflow.add_edge("synthesize", END)
    
    return workflow.compile()

advanced_rag_graph = build_advanced_rag_graph()