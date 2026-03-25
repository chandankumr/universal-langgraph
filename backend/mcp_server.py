#!/usr/bin/env python3
"""
MCP Server for Universal LangGraph RAG System
"""

import os
import sys
import asyncio

# ✅ CRITICAL: Suppress ALL stdout except JSON-RPC
class StdoutSuppressor:
    def __init__(self):
        self._stdout = sys.__stdout__
    def write(self, _):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False
    @property
    def buffer(self):
        return self._stdout.buffer

sys.stdout = StdoutSuppressor()

from dotenv import load_dotenv
backend_dir = os.path.dirname(os.path.abspath(__file__))

# ✅ CRITICAL: Hardcode your exact database URL (from your working test)
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/langgraph-postgres"
os.environ["CHROMA_PERSIST_DIR"] = "/Users/chandankumar/Documents/universal-langgraph/universal-langgraph/backend/data/chroma_db"
os.environ["GROQ_API_KEY"] = ""  # key
os.environ["OLLAMA_MODEL"] = "llama3.1:8b"
os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

# Now load .env as backup
load_dotenv(os.path.join(backend_dir, '.env'))

def log_debug(message):
    print(f"🔍 {message}", file=sys.stderr, flush=True)

def log_error(message):
    print(f"❌ {message}", file=sys.stderr, flush=True)

log_debug(f"DATABASE_URL: {os.getenv('DATABASE_URL')}")
log_debug(f"CHROMA_PERSIST_DIR: {os.getenv('CHROMA_PERSIST_DIR')}")

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

sys.path.insert(0, backend_dir)

# ✅ Suppress SQLAlchemy logging
import logging
logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

from app.database import SessionLocal
from app.graphs.rag_graph import rag_graph

app = Server("langgraph-rag-server")

def get_db_session():
    return SessionLocal()

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_knowledge_base",
            description="Search the internal knowledge base (technical documentation, manuals, PDFs) and get answers with citations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all documents currently indexed in the knowledge base",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    log_debug(f"Tool called: {name}")
    
    try:
        if name == "list_documents":
            db = get_db_session()
            
            from app.models import Document
            docs = db.query(Document).limit(10).all()
            log_debug(f"Found {len(docs)} documents")
            
            if not docs:
                return [TextContent(type="text", text="No documents indexed. Upload at http://localhost:3000/documents")]
            
            doc_list = "\n".join([f"- {doc.filename} ({doc.chunk_count} chunks)" for doc in docs])
            return [TextContent(type="text", text=f"Indexed Documents:\n{doc_list}")]
            
        elif name == "query_knowledge_base":
            query = arguments.get("query", "")
            if not query:
                return [TextContent(type="text", text="Error: No query provided")]
            
            db = get_db_session()
            from app.models import Document
            doc_count = db.query(Document).count()
            log_debug(f"Database has {doc_count} documents")
            
            if doc_count == 0:
                return [TextContent(type="text", text="Knowledge base is empty. Upload documents at http://localhost:3000/documents")]

            inputs = {
                "messages": [{"role": "user", "content": query}],
                "question": query,
                "answer": "",
                "router_decision": "",
                "documents": []
            }
            config = {"configurable": {"thread_id": "mcp-query"}}
            
            result = rag_graph.invoke(inputs, config)
            answer = result.get("answer", "No answer found")
            docs_count = len(result.get("documents", []))
            
            return [TextContent(type="text", text=f"Answer: {answer}\n\n(Sources: {docs_count} chunks)")]
            
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        import traceback
        log_error(f"Error: {traceback.format_exc()}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]

async def main():
    log_debug("Starting MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())






















# #!/usr/bin/env python3
# """
# MCP Server for Universal LangGraph RAG System
# """

# import os
# import sys
# import asyncio
# import io
# from contextlib import redirect_stdout, redirect_stderr

# # ✅ CRITICAL: Suppress ALL stdout except JSON-RPC
# class StdoutSuppressor:
#     def __init__(self):
#         self._stdout = sys.__stdout__
#     def write(self, _):
#         pass
#     def flush(self):
#         pass
#     def isatty(self):
#         return False
#     @property
#     def buffer(self):
#         return self._stdout.buffer

# # Redirect all stdout to null (only stderr will show logs)
# sys.stdout = StdoutSuppressor()

# # Now load .env
# from dotenv import load_dotenv
# backend_dir = os.path.dirname(os.path.abspath(__file__))
# env_path = os.path.join(backend_dir, '.env')
# load_dotenv(env_path)

# # ✅ All logging MUST go to stderr
# def log_debug(message):
#     print(f"🔍 {message}", file=sys.stderr, flush=True)

# def log_error(message):
#     print(f"❌ {message}", file=sys.stderr, flush=True)

# log_debug(f"Loading .env from: {env_path}")

# from mcp.server import Server
# from mcp.server.stdio import stdio_server
# from mcp.types import Tool, TextContent

# # Add backend to path
# sys.path.insert(0, backend_dir)

# # ✅ Suppress SQLAlchemy logging
# import logging
# logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
# logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

# from app.database import SessionLocal
# from app.graphs.rag_graph import rag_graph

# app = Server("langgraph-rag-server")

# def get_db_session():
#     return SessionLocal()

# @app.list_tools()
# async def list_tools():
#     log_debug("Listing tools")
#     return [
#         Tool(
#             name="query_knowledge_base",
#             description="Search the internal knowledge base (technical documentation, manuals, PDFs) and get answers with citations.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "query": {"type": "string", "description": "The search query"}
#                 },
#                 "required": ["query"]
#             }
#         ),
#         Tool(
#             name="list_documents",
#             description="List all documents currently indexed in the knowledge base",
#             inputSchema={"type": "object", "properties": {}, "required": []}
#         )
#     ]

# @app.call_tool()
# async def call_tool(name: str, arguments: dict):
#     log_debug(f"Tool called: {name}")
    
#     try:
#         if name == "query_knowledge_base":
#             query = arguments.get("query", "")
#             if not query:
#                 return [TextContent(type="text", text="Error: No query provided")]
            
#             db = get_db_session()
#             from app.models import Document
#             doc_count = db.query(Document).count()
#             log_debug(f"Found {doc_count} documents")
            
#             if doc_count == 0:
#                 return [TextContent(type="text", text="The knowledge base is empty. Please upload documents at http://localhost:3000/documents")]

#             inputs = {
#                 "messages": [{"role": "user", "content": query}],
#                 "question": query,
#                 "answer": "",
#                 "router_decision": "",
#                 "documents": []
#             }
#             config = {"configurable": {"thread_id": "mcp-query"}}
            
#             result = rag_graph.invoke(inputs, config)
#             answer = result.get("answer", "No answer found")
#             docs_count = len(result.get("documents", []))
            
#             return [TextContent(type="text", text=f"Answer: {answer}\n\n(Sources: {docs_count} chunks)")]
            
#         elif name == "list_documents":
#             db = get_db_session()
#             from app.models import Document
#             docs = db.query(Document).limit(10).all()
            
#             if not docs:
#                 return [TextContent(type="text", text="No documents indexed. Upload at http://localhost:3000/documents")]
            
#             doc_list = "\n".join([f"- {doc.filename} ({doc.chunk_count} chunks)" for doc in docs])
#             return [TextContent(type="text", text=f"Indexed Documents:\n{doc_list}")]
            
#         else:
#             return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
#     except Exception as e:
#         import traceback
#         log_error(f"Error: {traceback.format_exc()}")
#         return [TextContent(type="text", text=f"Error: {str(e)}")]

# async def main():
#     log_debug("Starting MCP Server...")
#     log_debug(f"DB: {os.getenv('DATABASE_URL', 'NOT SET')[:30]}...")
    
#     async with stdio_server() as (read_stream, write_stream):
#         await app.run(read_stream, write_stream, app.create_initialization_options())

# if __name__ == "__main__":
#     asyncio.run(main())





















# #!/usr/bin/env python3
# """
# MCP Server for Universal LangGraph RAG System
# Exposes RAG query capability as a tool for AI assistants
# """

# import os
# import sys
# import asyncio
# from dotenv import load_dotenv

# # ✅ CRITICAL: Explicitly load .env from the backend directory
# backend_dir = os.path.dirname(os.path.abspath(__file__))
# env_path = os.path.join(backend_dir, '.env')
# print(f"🔍 Loading .env from: {env_path}", file=sys.stderr)
# load_dotenv(env_path)

# # Verify critical vars are loaded
# if not os.getenv("DATABASE_URL"):
#     print("❌ ERROR: DATABASE_URL not found!", file=sys.stderr)
# if not os.getenv("CHROMA_PERSIST_DIR"):
#     print("❌ ERROR: CHROMA_PERSIST_DIR not found!", file=sys.stderr)

# from mcp.server import Server
# from mcp.server.stdio import stdio_server
# from mcp.types import Tool, TextContent
# from sqlalchemy.orm import Session
# from app.database import SessionLocal, vector_db
# from app.graphs.rag_graph import rag_graph

# # Add backend to path
# sys.path.insert(0, backend_dir)

# # Initialize MCP Server
# app = Server("langgraph-rag-server")

# # Store active DB session
# db_session = None

# def get_db():
#     global db_session
#     if db_session is None:
#         db_session = SessionLocal()
#     return db_session

# @app.list_tools()
# async def list_tools():
#     """List available tools for AI assistants."""
#     return [
#         Tool(
#             name="query_knowledge_base",
#             description="Search the internal knowledge base (technical documentation, manuals, PDFs) and get answers with citations. Use this for questions about Java programming, technical concepts, or uploaded documents.",
#             inputSchema={
#                 "type": "object",
#                 "properties": {
#                     "query": {
#                         "type": "string",
#                         "description": "The search query or question to answer from the knowledge base"
#                     }
#                 },
#                 "required": ["query"]
#             }
#         ),
#         Tool(
#             name="list_documents",
#             description="List all documents currently indexed in the knowledge base",
#             inputSchema={
#                 "type": "object",
#                 "properties": {},
#                 "required": []
#             }
#         )
#     ]

# @app.call_tool()
# async def call_tool(name: str, arguments: dict):
#     """Execute tool calls from AI assistants."""
#     # ✅ DEBUG: Log environment details
#     print(f"🔍 MCP Tool Called: {name}")
#     print(f"📡 DB URL: {os.getenv('DATABASE_URL')}")
#     print(f"📂 Chroma Dir: {os.getenv('CHROMA_PERSIST_DIR')}")
    
#     try:
#         if name == "query_knowledge_base":
#             query = arguments.get("query", "")
#             if not query:
#                 return [TextContent(type="text", text="Error: No query provided")]
            
#             db = get_db()
            
#             # ✅ DEBUG: Check document count explicitly
#             from app.models import Document
#             doc_count = db.query(Document).count()
#             print(f"✅ DB Connected. Found {doc_count} documents in Postgres.")
            
#             if doc_count == 0:
#                 return [TextContent(type="text", text="Error: Database connection successful, but NO documents found. Please check CHROMA_PERSIST_DIR and DATABASE_URL in claude_desktop_config.json.")]

#             inputs = {
#                 "messages": [{"role": "user", "content": query}],
#                 "question": query,
#                 "answer": "",
#                 "router_decision": "",
#                 "documents": []
#             }
#             config = {"configurable": {"thread_id": "mcp-query"}}
            
#             result = rag_graph.invoke(inputs, config)
#             answer = result.get("answer", "No answer found")
#             docs_count = len(result.get("documents", []))
            
#             response = f"Answer: {answer}\n\n(Sources consulted: {docs_count} document chunks)"
#             return [TextContent(type="text", text=response)]
            
#         elif name == "list_documents":
#             db = get_db()
#             from app.models import Document
#             docs = db.query(Document).limit(10).all()
            
#             if not docs:
#                 return [TextContent(type="text", text=f"No documents indexed yet. (DB Connected: True, Count: 0)")]
            
#             doc_list = "\n".join([f"- {doc.filename} ({doc.chunk_count} chunks)" for doc in docs])
#             return [TextContent(type="text", text=f"Indexed Documents:\n{doc_list}")]
            
#         else:
#             return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
#     except Exception as e:
#         import traceback
#         error_detail = traceback.format_exc()
#         print(f"❌ Error: {error_detail}")
#         return [TextContent(type="text", text=f"Error executing tool: {str(e)}")]

# # @app.call_tool()
# # async def call_tool(name: str, arguments: dict):
# #     """Execute tool calls from AI assistants."""
# #     try:
# #         if name == "query_knowledge_base":
# #             query = arguments.get("query", "")
# #             if not query:
# #                 return [TextContent(type="text", text="Error: No query provided")]
            
# #             # Execute RAG query
# #             db = get_db()
# #             inputs = {
# #                 "messages": [{"role": "user", "content": query}],
# #                 "question": query,
# #                 "answer": "",
# #                 "router_decision": "",
# #                 "documents": []
# #             }
# #             config = {"configurable": {"thread_id": "mcp-query"}}
            
# #             # Get answer from LangGraph
# #             result = rag_graph.invoke(inputs, config)
# #             answer = result.get("answer", "No answer found")
# #             docs_retrieved = len(result.get("documents", []))
            
# #             response = f"Answer: {answer}\n\nSources consulted: {docs_retrieved} document chunks"
# #             return [TextContent(type="text", text=response)]
            
# #         elif name == "list_documents":
# #             # List documents from database
# #             db = get_db()
# #             from app.models import Document
# #             docs = db.query(Document).limit(10).all()
            
# #             if not docs:
# #                 return [TextContent(type="text", text="No documents indexed yet")]
            
# #             doc_list = "\n".join([f"- {doc.filename} ({doc.chunk_count} chunks)" for doc in docs])
# #             return [TextContent(type="text", text=f"Indexed Documents:\n{doc_list}")]
            
# #         else:
# #             return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
# #     except Exception as e:
# #         return [TextContent(type="text", text=f"Error: {str(e)}")]

# async def main():
#     """Run the MCP server."""
#     print("🚀 Starting LangGraph RAG MCP Server...")
#     print("📡 Listening for MCP connections...")
#     async with stdio_server() as (read_stream, write_stream):
#         await app.run(
#             read_stream,
#             write_stream,
#             app.create_initialization_options()
#         )

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())