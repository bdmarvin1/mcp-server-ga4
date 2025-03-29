"""Google Analytics 4 client for interacting with the GA4 Data API."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (DateRange, Dimension, Metric,
                                                OrderBy, RunRealtimeReportRequest,
                                                RunRealtimeReportResponse,
                                                RunReportRequest,
                                                RunReportResponse)
from google.analytics.data_v1beta.types.analytics_data_api import GetMetadataRequest
from google.api_core.exceptions import GoogleAPIError

logger = logging.getLogger("mcp-server-ga4")

# Date range aliases
DATE_RANGE_ALIASES = {
    "today": (datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")),
    "yesterday": ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), 
                  (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")),
    "last7days": ((datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"), 
                 datetime.now().strftime("%Y-%m-%d")),
    "last30days": ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"), 
                  datetime.now().strftime("%Y-%m-%d")),
}


class GA4Client:
    """Client for interacting with the Google Analytics 4 Data API."""
    
    def __init__(self, default_property_id: Optional[str] = None):
        """
        Initialize the GA4 client.
        
        Args:
            default_property_id: Default GA4 property ID to use if not specified in requests
        """
        self.default_property_id = default_property_id
        self._executor = ThreadPoolExecutor(max_workers=5)
        self._client = None
    
    async def _get_client(self) -> BetaAnalyticsDataClient:
        """
        Get or create the GA4 API client.
        
        Returns:
            Google Analytics Data API client
        """
        if self._client is None:
            # Create client in executor to avoid blocking
            loop = asyncio.get_running_loop()
            self._client = await loop.run_in_executor(
                self._executor, BetaAnalyticsDataClient
            )
        return self._client
    
    async def verify_auth(self) -> bool:
        """
        Verify that authentication is working.
        
        Returns:
            True if authentication successful
        
        Raises:
            Exception: If authentication fails
        """
        if not self.default_property_id:
            logger.warning("No default property ID provided, skipping auth verification")
            return True
        
        # Try to get metadata to verify authentication
        client = await self._get_client()
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                self._executor,
                client.get_metadata,
                GetMetadataRequest(name=f"properties/{self.default_property_id}/metadata"),
            )
            return True
        except Exception as e:
            logger.error(f"Authentication verification failed: {e}")
            raise
    
    async def run_report(
        self,
        property_id: Optional[str] = None,
        metrics: List[str] = None,
        dimensions: Optional[List[str]] = None,
        date_range: Union[Dict[str, str], str] = "last30days",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Run a standard GA4 report.
        
        Args:
            property_id: GA4 property ID (overrides default if provided)
            metrics: List of metric names
            dimensions: List of dimension names
            date_range: Date range as dict with start_date and end_date keys, or string alias
            limit: Maximum number of rows to return
            
        Returns:
            Formatted report data
            
        Raises:
            ValueError: If invalid parameters provided
            GoogleAPIError: If API request fails
        """
        if not metrics:
            raise ValueError("At least one metric must be specified")
        
        property_id = property_id or self.default_property_id
        if not property_id:
            raise ValueError("No property ID provided")
        
        # Process date range
        if isinstance(date_range, str):
            if date_range not in DATE_RANGE_ALIASES:
                raise ValueError(
                    f"Unknown date range alias: {date_range}. "
                    f"Valid aliases: {', '.join(DATE_RANGE_ALIASES.keys())}"
                )
            start_date, end_date = DATE_RANGE_ALIASES[date_range]
        else:
            start_date = date_range.get("start_date")
            end_date = date_range.get("end_date")
            if not start_date or not end_date:
                raise ValueError("Date range must include start_date and end_date")
        
        # Build request
        request = RunReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name=metric) for metric in metrics],
            dimensions=(
                [Dimension(name=dimension) for dimension in dimensions]
                if dimensions
                else []
            ),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        
        # Execute request
        client = await self._get_client()
        loop = asyncio.get_running_loop()
        try:
            response: RunReportResponse = await loop.run_in_executor(
                self._executor, client.run_report, request
            )
            
            return self._format_report_response(response)
        except GoogleAPIError as e:
            logger.error(f"Error running report: {e}")
            raise
    
    async def run_realtime_report(
        self,
        property_id: Optional[str] = None,
        metrics: List[str] = None,
        dimensions: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Run a realtime GA4 report for the last 30 minutes.
        
        Args:
            property_id: GA4 property ID (overrides default if provided)
            metrics: List of metric names
            dimensions: List of dimension names
            limit: Maximum number of rows to return
            
        Returns:
            Formatted report data
            
        Raises:
            ValueError: If invalid parameters provided
            GoogleAPIError: If API request fails
        """
        if not metrics:
            raise ValueError("At least one metric must be specified")
        
        property_id = property_id or self.default_property_id
        if not property_id:
            raise ValueError("No property ID provided")
        
        # Build request
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            metrics=[Metric(name=metric) for metric in metrics],
            dimensions=(
                [Dimension(name=dimension) for dimension in dimensions]
                if dimensions
                else []
            ),
            limit=limit,
        )
        
        # Execute request
        client = await self._get_client()
        loop = asyncio.get_running_loop()
        try:
            response: RunRealtimeReportResponse = await loop.run_in_executor(
                self._executor, client.run_realtime_report, request
            )
            
            return self._format_report_response(response)
        except GoogleAPIError as e:
            logger.error(f"Error running realtime report: {e}")
            raise
    
    async def get_metadata(
        self,
        property_id: Optional[str] = None,
        metadata_type: str = "all",
    ) -> Dict[str, Any]:
        """
        Get metadata about available metrics and dimensions.
        
        Args:
            property_id: GA4 property ID (overrides default if provided)
            metadata_type: Type of metadata to retrieve ("metrics", "dimensions", or "all")
            
        Returns:
            Formatted metadata
            
        Raises:
            ValueError: If invalid parameters provided
            GoogleAPIError: If API request fails
        """
        property_id = property_id or self.default_property_id
        if not property_id:
            raise ValueError("No property ID provided")
        
        if metadata_type not in ("metrics", "dimensions", "all"):
            raise ValueError(
                f"Invalid metadata type: {metadata_type}. "
                f"Valid types: metrics, dimensions, all"
            )
        
        # Execute request
        client = await self._get_client()
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                self._executor,
                client.get_metadata,
                GetMetadataRequest(name=f"properties/{property_id}/metadata"),
            )
            
            result = {}
            
            if metadata_type in ("metrics", "all"):
                metrics = []
                for metric in response.metrics:
                    metrics.append({
                        "name": metric.api_name,
                        "display_name": metric.ui_name,
                        "description": metric.description,
                        "category": metric.category,
                    })
                result["metrics"] = metrics
            
            if metadata_type in ("dimensions", "all"):
                dimensions = []
                for dimension in response.dimensions:
                    dimensions.append({
                        "name": dimension.api_name,
                        "display_name": dimension.ui_name,
                        "description": dimension.description,
                        "category": dimension.category,
                    })
                result["dimensions"] = dimensions
            
            return result
        except GoogleAPIError as e:
            logger.error(f"Error getting metadata: {e}")
            raise

    def _format_report_response(
        self, response: Union[RunReportResponse, RunRealtimeReportResponse]
    ) -> Dict[str, Any]:
        """
        Format a report response into a more usable structure.
        
        Args:
            response: Report response from GA4 API
            
        Returns:
            Formatted report data
        """
        # Extract dimension and metric headers
        dimension_headers = [header.name for header in response.dimension_headers]
        metric_headers = [header.name for header in response.metric_headers]
        
        # Build rows
        rows = []
        for row in response.rows:
            row_data = {}
            
            # Add dimensions
            for i, dimension_value in enumerate(row.dimension_values):
                row_data[dimension_headers[i]] = dimension_value.value
            
            # Add metrics
            for i, metric_value in enumerate(row.metric_values):
                row_data[metric_headers[i]] = metric_value.value
            
            rows.append(row_data)
        
        # Build response
        result = {
            "dimensions": dimension_headers,
            "metrics": metric_headers,
            "rows": rows,
            "row_count": len(rows),
            "totals": [],
        }
        
        # Add totals if available
        if hasattr(response, "totals") and response.totals:
            for total_row in response.totals:
                total_data = {}
                for i, metric_value in enumerate(total_row.metric_values):
                    total_data[metric_headers[i]] = metric_value.value
                result["totals"].append(total_data)
        
        return result
    
    async def close(self):
        """Close the client and clean up resources."""
        if self._client:
            logger.debug("Closing GA4 client")
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(self._executor, self._client.close)
            except Exception as e:
                logger.error(f"Error closing GA4 client: {e}")
        
        self._executor.shutdown(wait=False)
