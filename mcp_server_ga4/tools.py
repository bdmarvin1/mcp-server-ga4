'''MCP tools for interacting with Google Analytics 4.'''

import logging
from datetime import datetime, timedelta # Not directly used here but often useful contextually
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import Context
from .ga4_client import GA4Client # Assuming GA4Client class is in ga4_client.py

from google.api_core.exceptions import GoogleAPIError, PermissionDenied, Unauthenticated

logger = logging.getLogger("mcp-server-ga4")


async def run_report(
    ctx: Context,
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    date_range: Union[Dict[str, str], str] = "last30days",
    property_id: Optional[str] = None,
    limit: int = 10,
    **kwargs: Any, 
) -> Union[str, Dict[str, Any]]: 
    """
    Run a standard GA4 report with configurable metrics, dimensions, and date ranges.
    (Full docstring as before)
    """
    ga4_client: GA4Client = ctx.request_context.lifespan_context["ga4_client"]
    access_token: Optional[str] = kwargs.get("__google_access_token__")
    user_email: Optional[str] = kwargs.get("__google_user_email__") 

    try:
        log_msg = (
            f"run_report called with: metrics={metrics}, dimensions={dimensions}, "
            f"date_range={date_range}, property_id={property_id}, limit={limit}, "
            f"token_present={'yes' if access_token else 'no'}"
        )
        if user_email:
            log_msg += f", user_email={user_email}"
        logger.info(log_msg)
        
        result = await ga4_client.run_report(
            property_id=property_id,
            metrics=metrics,
            dimensions=dimensions,
            date_range=date_range,
            limit=limit,
            access_token=access_token,
        )
        
        return _format_result_as_table(result)
    except (PermissionDenied, Unauthenticated) as e:
        logger.error(f"Authentication/Permission error in run_report for property '{property_id}': {e}")
        error_type = "permission_denied" if isinstance(e, PermissionDenied) else "unauthenticated"
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": error_type}
    except GoogleAPIError as e: 
        logger.error(f"Google API error running report for property '{property_id}': {e}")
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": "api_error"}
    except ValueError as e: 
        logger.error(f"Value error running report for property '{property_id}': {e}")
        return {"status": "error", "message": str(e), "error_type": "value_error"}
    except Exception as e:
        logger.error(f"Unexpected error running report for property '{property_id}': {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected server error occurred while running the report.", "error_type": "unexpected_server_error"}


async def run_realtime_report(
    ctx: Context,
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    property_id: Optional[str] = None,
    limit: int = 10,
    **kwargs: Any,
) -> Union[str, Dict[str, Any]]:
    ga4_client: GA4Client = ctx.request_context.lifespan_context["ga4_client"]
    access_token: Optional[str] = kwargs.get("__google_access_token__")

    try:
        logger.info(
            f"run_realtime_report called with: metrics={metrics}, dimensions={dimensions}, "
            f"property_id={property_id}, limit={limit}, "
            f"token_present={'yes' if access_token else 'no'}"
        )
        result = await ga4_client.run_realtime_report(
            property_id=property_id,
            metrics=metrics,
            dimensions=dimensions,
            limit=limit,
            access_token=access_token,
        )
        return _format_result_as_table(result)
    except (PermissionDenied, Unauthenticated) as e:
        logger.error(f"Authentication/Permission error in run_realtime_report for property '{property_id}': {e}")
        error_type = "permission_denied" if isinstance(e, PermissionDenied) else "unauthenticated"
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": error_type}
    except GoogleAPIError as e:
        logger.error(f"Google API error running realtime report for property '{property_id}': {e}")
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": "api_error"}
    except ValueError as e:
        logger.error(f"Value error running realtime report for property '{property_id}': {e}")
        return {"status": "error", "message": str(e), "error_type": "value_error"}
    except Exception as e:
        logger.error(f"Unexpected error running realtime report for property '{property_id}': {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected server error occurred while running the realtime report.", "error_type": "unexpected_server_error"}


async def get_metadata(
    ctx: Context,
    type: str = "all", 
    property_id: Optional[str] = None,
    **kwargs: Any,
) -> Union[str, Dict[str, Any]]:
    ga4_client: GA4Client = ctx.request_context.lifespan_context["ga4_client"]
    access_token: Optional[str] = kwargs.get("__google_access_token__")

    try:
        logger.info(
            f"get_metadata called with: type={type}, property_id={property_id}, "
            f"token_present={'yes' if access_token else 'no'}"
        )
        result = await ga4_client.get_metadata(
            property_id=property_id,
            metadata_type=type, 
            access_token=access_token,
        )
        
        response_parts = []
        if "metrics" in result and result["metrics"]:
            response_parts.append("# Available Metrics\n")
            for metric in result["metrics"]:
                response_parts.append(f"- **{metric.get('name', 'N/A')}** ({metric.get('display_name', 'N/A')})")
                if metric.get("description"):
                    response_parts.append(f"  - {metric['description']}")
                response_parts.append(f"  - Category: {metric.get('category', 'N/A')}\n")
        
        if "dimensions" in result and result["dimensions"]:
            response_parts.append("# Available Dimensions\n")
            for dimension in result["dimensions"]:
                response_parts.append(f"- **{dimension.get('name', 'N/A')}** ({dimension.get('display_name', 'N/A')})")
                if dimension.get("description"):
                    response_parts.append(f"  - {dimension['description']}")
                response_parts.append(f"  - Category: {dimension.get('category', 'N/A')}\n")
        
        if not response_parts:
            return "No metadata found or an issue occurred retrieving it."
            
        return "\n".join(response_parts)

    except (PermissionDenied, Unauthenticated) as e:
        logger.error(f"Authentication/Permission error in get_metadata for property '{property_id}': {e}")
        error_type = "permission_denied" if isinstance(e, PermissionDenied) else "unauthenticated"
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": error_type}
    except GoogleAPIError as e:
        logger.error(f"Google API error getting metadata for property '{property_id}': {e}")
        return {"status": "error", "message": f"GA4 API Error: {str(e)}", "error_type": "api_error"}
    except ValueError as e: 
        logger.error(f"Value error getting metadata for property '{property_id}': {e}")
        return {"status": "error", "message": str(e), "error_type": "value_error"}
    except Exception as e:
        logger.error(f"Unexpected error getting metadata for property '{property_id}': {e}", exc_info=True)
        return {"status": "error", "message": "An unexpected server error occurred while getting metadata.", "error_type": "unexpected_server_error"}


def _format_result_as_table(result: Dict[str, Any]) -> str:
    if not result or ("rows" not in result and "row_count" not in result and not result.get("metrics") and not result.get("dimensions")): # Check if result itself is empty or lacks report structure
        return "No data returned or report data is empty/invalid."
    
    if not result.get("rows") and result.get("row_count") == 0: # Explicitly no rows
         return "No data returned for the specified criteria."
    
    columns = []
    if result.get("dimensions"):
        columns.extend(result["dimensions"])
    if result.get("metrics"):
        columns.extend(result["metrics"])
    
    if not columns:
        # This case might happen if the result dict is malformed (e.g., has rows but no headers)
        # or if it's metadata that wasn't meant for table formatting by this function.
        logger.warning(f"Report data is present but has no dimension or metric columns: {result}")
        return "Report data is present but could not be formatted (no columns)."

    header_row = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    data_rows = []
    if result.get("rows"): # Ensure 'rows' key exists
        for row in result["rows"]:
            if not isinstance(row, dict):
                logger.warning(f"Skipping row with unexpected format: {row}")
                continue
            row_values = [str(row.get(column, "")) for column in columns]
            data_rows.append("| " + " | ".join(row_values) + " |")
    
    table_parts = [header_row, separator] + data_rows
    
    if result.get("totals") and isinstance(result["totals"], list):
        has_total_data = any(isinstance(total_row, dict) and total_row for total_row in result["totals"])
        if has_total_data:
            table_parts.append("\n**Totals:**")
            # table_parts.append(header_row) # Optional: re-add header for totals
            # table_parts.append(separator)  # Optional: re-add separator for totals
            for total_row in result["totals"]:
                if not isinstance(total_row, dict):
                    logger.warning(f"Skipping total_row with unexpected format: {total_row}")
                    continue
                total_values = []
                # For totals, only metric columns are typically populated.
                # Dimension columns in a 'totals' row are often context-dependent or empty.
                for column_name in columns:
                    if column_name in result.get("dimensions", []):
                        # Heuristic: if it's the first dimension column, label it "Total"
                        # This is a basic assumption and might need refinement based on GA4's actual total row structure.
                        if columns.index(column_name) == 0 and result.get("dimensions"): 
                             total_values.append("TOTALS")
                        else:
                             total_values.append("") # Empty for other dimension columns in total row
                    else: # Metric column
                        total_values.append(str(total_row.get(column_name, "")))
                table_parts.append("| " + " | ".join(total_values) + " |")
    
    return "\n".join(table_parts)

