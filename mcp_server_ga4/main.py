'''MCP server for Google Analytics 4 (GA4).'''

import argparse
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from dotenv import load_dotenv
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

from .ga4_client import GA4Client
from .tools import get_metadata, run_realtime_report, run_report

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp-server-ga4")

# Load environment variables from .env file if it exists
load_dotenv()


@asynccontextmanager
async def lifespan(server: FastMCP):
    '''
    Manage server lifecycle and resources.
    '''
    property_id = os.environ.get("GA4_PROPERTY_ID")
    if property_id:
        logger.info(f"Using property ID from environment: {property_id}")
    else:
        logger.warning("No default property ID provided")
    
    ga4_client = GA4Client(default_property_id=property_id)
    
    try:
        await ga4_client.verify_auth()
        logger.info("Google Analytics authentication successful")
        yield {"ga4_client": ga4_client}
    except Exception as e:
        logger.error(f"Error initializing GA4 client: {e}")
        yield {"ga4_client": ga4_client}
    finally:
        await ga4_client.close()
        logger.info("GA4 client closed")

# --- CUSTOM SCHEMA DEFINITIONS (NOW WITH additionalProperties FOR KWARGS) ---
run_report_custom_input_schema = {
    "type": "object",
    "title": "run_reportArguments",
    "properties": {
        "metrics":     {"title": "Metrics",     "description": "List of metrics to fetch (e.g., 'activeUsers', 'sessions').", "type": "array", "items": {"type": "string"}},
        "dimensions":  {"title": "Dimensions",  "description": "List of dimensions to group by (e.g., 'date', 'country').", "default": None, "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]},
        "date_range":  {"title": "Date Range",  "description": "Date range for the report (e.g., 'last30days' or {'start_date': 'YYYY-MM-DD', 'end_date': 'YYYY-MM-DD'}).", "default": "last30days", "anyOf": [{"type": "object", "additionalProperties": {"type": "string"}}, {"type": "string"}]},
        "property_id": {"title": "Property Id", "description": "GA4 Property ID (e.g., '123456789').", "default": None, "anyOf": [{"type": "string"}, {"type": "null"}]},
        "limit":       {"title": "Limit",       "description": "Maximum number of rows to return in the report.", "type": "integer", "default": 10},
        "kwargs":      {"title": "Kwargs",      "description": "Additional keyword arguments for the report.", "type": "object", "additionalProperties": True } # <<< MODIFIED
    },
    "required": ["metrics", "kwargs"]
}

run_realtime_report_custom_input_schema = {
    "type": "object",
    "title": "run_realtime_reportArguments",
    "properties": {
        "metrics":     {"title": "Metrics",     "description": "List of metrics for the realtime report (e.g., 'activeUsers').", "type": "array", "items": {"type": "string"}},
        "dimensions":  {"title": "Dimensions",  "description": "List of dimensions for the realtime report (e.g., 'country', 'city').", "default": None, "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]},
        "property_id": {"title": "Property Id", "description": "GA4 Property ID (e.g., '123456789').", "default": None, "anyOf": [{"type": "string"}, {"type": "null"}]},
        "limit":       {"title": "Limit",       "description": "Maximum number of rows to return in the realtime report.", "type": "integer", "default": 10},
        "kwargs":      {"title": "Kwargs",      "description": "Additional keyword arguments for the realtime report.", "type": "object", "additionalProperties": True } # <<< MODIFIED
    },
    "required": ["metrics", "kwargs"]
}

get_metadata_custom_input_schema = {
    "type": "object",
    "title": "get_metadataArguments",
    "properties": {
        "type":        {"title": "Type",        "description": "Type of metadata to retrieve ('all', 'metrics', or 'dimensions').", "default": "all", "type": "string"},
        "property_id": {"title": "Property Id", "description": "GA4 Property ID (e.g., '123456789').", "default": None, "anyOf": [{"type": "string"}, {"type": "null"}]},
        "kwargs":      {"title": "Kwargs",      "description": "Additional keyword arguments.", "type": "object", "additionalProperties": True } # <<< MODIFIED
    },
    "required": ["kwargs"]
}
# --- END OF CUSTOM SCHEMA DEFINITIONS ---

def create_server(property_id: Optional[str] = None) -> FastMCP:
    if property_id:
        os.environ["GA4_PROPERTY_ID"] = property_id
    
    server = FastMCP(
        "GA4",
        dependencies=["google-analytics-data>=0.16.0", "mcp>=1.0.0"],
        lifespan=lifespan,
    )
    
    server.tool(
        annotations=ToolAnnotations(inputSchema=run_report_custom_input_schema)
    )(run_report)
    
    server.tool(
        annotations=ToolAnnotations(inputSchema=run_realtime_report_custom_input_schema)
    )(run_realtime_report)
    
    server.tool(
        annotations=ToolAnnotations(inputSchema=get_metadata_custom_input_schema)
    )(get_metadata)
    
    return server

async def async_main():
    parser = argparse.ArgumentParser(description="MCP server for Google Analytics 4")
    parser.add_argument(
        "--property-id",
        help="Default Google Analytics 4 property ID",
        default=os.environ.get("GA4_PROPERTY_ID"),
    )
    parser.add_argument(
        "--transport",
        help="Transport to use (stdio, sse, or streamable-http)",
        choices=["stdio", "sse", "streamable-http"], 
        default="stdio",
    )
    parser.add_argument(
        "--port", help="Port for SSE/HTTP transport", type=int, default=8000
    )
    parser.add_argument(
        "--host", help="Host for SSE/HTTP transport", default="localhost"
    )
    parser.add_argument(
        "--debug", help="Enable debug logging", action="store_true"
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    server = create_server(args.property_id)
    
    if args.transport == "stdio":
        logger.info("Starting server with stdio transport")
        await server.run_stdio_async()
    else: 
        logger.info(f"Starting server with {args.transport} transport on http://{args.host}:{args.port}")
        await server.run_http_async(transport=args.transport, host=args.host, port=args.port)

def main():
    asyncio.run(async_main())

if __name__ == "__main__":
    main()
