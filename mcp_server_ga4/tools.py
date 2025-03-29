"""MCP tools for interacting with Google Analytics 4."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context

logger = logging.getLogger("mcp-server-ga4")


async def run_report(
    ctx: Context,
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    date_range: Union[Dict[str, str], str] = "last30days",
    property_id: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Run a standard GA4 report with configurable metrics, dimensions, and date ranges.
    
    Args:
        ctx: MCP context
        metrics: List of metric names (e.g., ["activeUsers", "sessions"])
        dimensions: List of dimension names (e.g., ["date", "country"])
        date_range: Date range in one of these formats:
            - {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
            - "last7days", "last30days", "today", "yesterday"
        property_id: GA4 property ID (overrides the default)
        limit: Number of rows to return (default: 10)
        
    Returns:
        Formatted report data
    """
    ga4_client = ctx.request_context.lifespan_context["ga4_client"]
    try:
        # Log the request
        logger.info(
            f"Running report with metrics={metrics}, dimensions={dimensions}, "
            f"date_range={date_range}, limit={limit}"
        )
        
        # Run the report
        result = await ga4_client.run_report(
            property_id=property_id,
            metrics=metrics,
            dimensions=dimensions,
            date_range=date_range,
            limit=limit,
        )
        
        # Format the response
        return _format_result_as_table(result)
    except Exception as e:
        logger.error(f"Error running report: {e}")
        return f"Error running report: {str(e)}"


async def run_realtime_report(
    ctx: Context,
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    property_id: Optional[str] = None,
    limit: int = 10,
) -> str:
    """
    Get real-time data for the past 30 minutes.
    
    Args:
        ctx: MCP context
        metrics: List of metric names (e.g., ["activeUsers", "screenPageViews"])
        dimensions: List of dimension names (e.g., ["country", "city"])
        property_id: GA4 property ID (overrides the default)
        limit: Number of rows to return (default: 10)
        
    Returns:
        Formatted report data
    """
    ga4_client = ctx.request_context.lifespan_context["ga4_client"]
    try:
        # Log the request
        logger.info(
            f"Running realtime report with metrics={metrics}, dimensions={dimensions}, "
            f"limit={limit}"
        )
        
        # Run the report
        result = await ga4_client.run_realtime_report(
            property_id=property_id,
            metrics=metrics,
            dimensions=dimensions,
            limit=limit,
        )
        
        # Format the response
        return _format_result_as_table(result)
    except Exception as e:
        logger.error(f"Error running realtime report: {e}")
        return f"Error running realtime report: {str(e)}"


async def get_metadata(
    ctx: Context,
    type: str = "all",
    property_id: Optional[str] = None,
) -> str:
    """
    Retrieve available metrics and dimensions for a GA4 property.
    
    Args:
        ctx: MCP context
        type: Type of metadata to retrieve ("metrics", "dimensions", or "all")
        property_id: GA4 property ID (overrides the default)
        
    Returns:
        Formatted metadata
    """
    ga4_client = ctx.request_context.lifespan_context["ga4_client"]
    try:
        # Log the request
        logger.info(f"Getting metadata type={type}")
        
        # Get the metadata
        result = await ga4_client.get_metadata(
            property_id=property_id,
            metadata_type=type,
        )
        
        # Format the response
        response = []
        
        if "metrics" in result:
            response.append("# Available Metrics\n")
            for metric in result["metrics"]:
                response.append(f"- **{metric['name']}**: {metric['display_name']}")
                if metric.get("description"):
                    response.append(f"  - {metric['description']}")
                response.append(f"  - Category: {metric['category']}")
                response.append("")
        
        if "dimensions" in result:
            response.append("# Available Dimensions\n")
            for dimension in result["dimensions"]:
                response.append(f"- **{dimension['name']}**: {dimension['display_name']}")
                if dimension.get("description"):
                    response.append(f"  - {dimension['description']}")
                response.append(f"  - Category: {dimension['category']}")
                response.append("")
        
        return "\n".join(response)
    except Exception as e:
        logger.error(f"Error getting metadata: {e}")
        return f"Error getting metadata: {str(e)}"


def _format_result_as_table(result: Dict[str, Any]) -> str:
    """
    Format report result as a markdown table.
    
    Args:
        result: Report result from GA4 client
        
    Returns:
        Formatted markdown table
    """
    if not result["rows"]:
        return "No data returned."
    
    # Get all columns
    columns = []
    if result["dimensions"]:
        columns.extend(result["dimensions"])
    if result["metrics"]:
        columns.extend(result["metrics"])
    
    # Build header row
    header_row = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    # Build data rows
    data_rows = []
    for row in result["rows"]:
        row_values = []
        for column in columns:
            row_values.append(str(row.get(column, "")))
        data_rows.append("| " + " | ".join(row_values) + " |")
    
    # Build totals if available
    totals_rows = []
    if result["totals"]:
        for total in result["totals"]:
            total_values = []
            for column in columns:
                # For dimension columns in totals, use empty string
                if column in result["dimensions"]:
                    total_values.append("")
                else:
                    total_values.append(str(total.get(column, "")))
            totals_rows.append("| " + " | ".join(total_values) + " |")
    
    # Combine all parts
    table = [header_row, separator] + data_rows
    
    # Add totals with a header if available
    if totals_rows:
        table.append("\n**Totals:**")
        table.append(header_row)
        table.append(separator)
        table.extend(totals_rows)
    
    return "\n".join(table)
