from mcp.server import Server
from mcp.server.stdio import stdio_server
from app.graphs.rag_graph import rag_graph

server = Server("amd-ai-agent")

@server.tool("query_knowledge_base")
async def query_kb(question: str) -> str:
    """Query the enterprise knowledge base using LangGraph."""
    result = rag_graph.invoke({"question": question})
    return result["answer"]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())