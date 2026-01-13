"""
LangGraph-based ReAct Agent for intelligent query routing.
Uses LangGraph for state management and control flow.
"""

import logging
from typing import Annotated, Literal, TypedDict, Callable, Optional
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import Tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: list  # Conversation history
    query: str  # Current user query
    needs_retrieval: bool  # Whether to retrieve from knowledge base
    retrieved_context: str  # Context from retrieval
    final_answer: str  # Final answer to return
    iterations: int  # Number of reasoning steps
    tools_used: list[str]  # Tools that were called


class LangGraphRAGAgent:
    """
    LangGraph-based agent that intelligently routes queries.
    
    Flow:
    1. Analyze query → Decide if retrieval needed
    2. If needed → Retrieve from knowledge base
    3. Generate final answer with or without context
    """
    
    def __init__(
        self,
        llm,
        rag_system,
        max_iterations: int = 5,
        status_callback: Optional[Callable] = None
    ):
        """
        Args:
            llm: LangChain-compatible LLM
            rag_system: RAG system for retrieval
            max_iterations: Max reasoning steps
            status_callback: Function for status updates
        """
        self.llm = llm
        self.rag_system = rag_system
        self.max_iterations = max_iterations
        self.status_callback = status_callback
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _emit_status(self, message: str, level: str = "info"):
        """Emit status update."""
        if self.status_callback:
            self.status_callback(message, level)
        # logger.info(message)
    
    def _build_graph(self) -> StateGraph:
        """Build the agent workflow graph."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze", self._analyze_query)
        workflow.add_node("retrieve", self._retrieve_knowledge)
        workflow.add_node("answer", self._generate_answer)
        
        # Add edges
        workflow.set_entry_point("analyze")
        
        # Conditional routing after analysis
        workflow.add_conditional_edges(
            "analyze",
            self._should_retrieve,
            {
                "retrieve": "retrieve",
                "answer": "answer"
            }
        )
        
        # After retrieval, go to answer
        workflow.add_edge("retrieve", "answer")
        
        # After answer, end
        workflow.add_edge("answer", END)
        
        return workflow.compile()
    
    async def _analyze_query(self, state: AgentState) -> AgentState:
        """Analyze if query needs knowledge base retrieval."""
        self._emit_status("🔍 Analyzing query...", "thought")
        
        query = state["query"]
        
        # Use LLM to classify
        system_prompt = """You are a query analyzer. Determine if the user's question requires retrieving information from a knowledge base.

Questions that NEED retrieval:
- Specific facts about companies, products, events, people in documents
- Financial data, statistics, metrics
- Technical specifications or details
- "What did X say/do/announce?"
- queries that explicitly ask to use the knowledge base "ex: use the docs..."
- Questions about specific entities or events

Questions that DON'T need retrieval:
- Greetings (hi, hello, how are you)
- Requests for clarification
- Meta questions about the system itself

Respond with ONLY "YES" or "NO"."""

        prompt = f"{system_prompt}\n\nQuestion: {query}\n\nNeeds retrieval?"
        
        try:
            # Get LLM decision
            response = await self.llm.generate(prompt, temperature=0, max_tokens=10)
            needs_retrieval = "yes" in response.lower()
            
            decision = "RETRIEVE from knowledge base" if needs_retrieval else "ANSWER directly"
            self._emit_status(f"💡 Decision: {decision}", "action")
            
            state["needs_retrieval"] = needs_retrieval
            state["iterations"] = state.get("iterations", 0) + 1
            
        except Exception as e:
            logger.error(f"Error analyzing query: {e}", exc_info=True)
            # Default to retrieval on error
            state["needs_retrieval"] = True
            self._emit_status(f"⚠️ Analysis error, defaulting to retrieval", "warning")
        
        return state
    
    async def _retrieve_knowledge(self, state: AgentState) -> AgentState:
        """Retrieve relevant knowledge from RAG system."""
        self._emit_status("📚 Retrieving from knowledge base...", "tool")
        
        query = state["query"]
        
        try:
            # Use RAG system to retrieve
            results = await self.rag_system.retrieve(query)
            
            if not results:
                context = "No relevant documents found in knowledge base."
                self._emit_status("⚠️ No relevant documents found", "warning")
            else:
                # Format context from retrieved chunks
                chunks_text = []
                for i, chunk in enumerate(results, 1): # Show all retrieved
                    text = chunk.get('chunk_text', '')
                    source = chunk.get('doc_id', 'unknown')
                    score = chunk.get('fusion_score', chunk.get('relevance_score', chunk.get('similarity_score', 0)))
                    chunks_text.append(f"[Source {i}] (score: {score:.3f})\n{text}")
                
                context = "\n\n".join(chunks_text)
                self._emit_status(f"✓ Retrieved {len(results)} chunks", "observation")
            
            state["retrieved_context"] = context
            state["tools_used"] = state.get("tools_used", []) + ["retrieve_knowledge"]
            state["iterations"] = state.get("iterations", 0) + 1
            
        except Exception as e:
            logger.error(f"Error retrieving knowledge: {e}", exc_info=True)
            state["retrieved_context"] = f"Error retrieving knowledge: {str(e)}"
            self._emit_status(f"❌ Retrieval error: {str(e)}", "error")
        
        return state
    
    async def _generate_answer(self, state: AgentState) -> AgentState:
        """Generate final answer with or without retrieved context."""
        self._emit_status("💭 Generating answer...", "tool")
        
        query = state["query"]
        context = state.get("retrieved_context", "")
        needs_retrieval = state.get("needs_retrieval", False)
        
        try:
            if needs_retrieval and context:
                # Answer with retrieved context
                prompt = f"""Answer the user's question based on the provided context from the knowledge base.

Context:
{context}

Question: {query}

Instructions:
- Use ONLY information from the context above
- Be specific and cite relevant details
- If the context doesn't contain the answer, say so clearly
- Keep the answer concise but complete

Answer:"""
            else:
                # Answer without context (general knowledge)
                prompt = f"""Answer the user's question using your general knowledge.

Question: {query}

Answer:"""
            
            answer = await self.llm.generate(prompt, temperature=0.7, max_tokens=500)
            
            state["final_answer"] = answer.strip()
            state["tools_used"] = state.get("tools_used", []) + ["generate_answer"]
            state["iterations"] = state.get("iterations", 0) + 1
            
            self._emit_status("✅ Answer generated", "success")
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}", exc_info=True)
            state["final_answer"] = f"I encountered an error generating the answer: {str(e)}"
            self._emit_status(f"❌ Generation error: {str(e)}", "error")
        
        return state
    
    def _should_retrieve(self, state: AgentState) -> Literal["retrieve", "answer"]:
        """Decide next step based on analysis."""
        return "retrieve" if state.get("needs_retrieval", False) else "answer"
    
    async def run(self, query: str) -> dict:
        """
        Run the agent on a query.
        
        Returns:
            Dict with answer, tools_used, iterations, etc.
        """
        start_time = datetime.now()
        
        # Initialize state
        initial_state = AgentState(
            messages=[],
            query=query,
            needs_retrieval=False,
            retrieved_context="",
            final_answer="",
            iterations=0,
            tools_used=[]
        )
        
        try:
            # Run the graph
            final_state = await self.graph.ainvoke(initial_state)
            
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'answer': final_state.get('final_answer', 'No answer generated'),
                'tools_used': final_state.get('tools_used', []),
                'iterations': final_state.get('iterations', 0),
                'duration_ms': duration,
                'success': True,
                'needs_retrieval': final_state.get('needs_retrieval', False)
            }
            
        except Exception as e:
            logger.error(f"Error running agent: {e}", exc_info=True)
            duration = (datetime.now() - start_time).total_seconds() * 1000
            
            return {
                'answer': f"I encountered an error: {str(e)}",
                'tools_used': [],
                'iterations': 0,
                'duration_ms': duration,
                'success': False,
                'error': str(e)
            }
