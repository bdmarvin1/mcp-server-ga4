'''Google Analytics 4 client for interacting with the GA4 Data API.'''

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
from google.oauth2 import credentials as google_credentials # Alias to avoid confusion


logger = logging.getLogger("mcp-server-ga4")

# Date range aliases
DATE_RANGE_ALIASES = {
    "today": (datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")),
    "yesterday": ((datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"), 
                  (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")),
    "last7days": ((datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"), # Corrected: 7 days including today means 6 days ago to today
                 datetime.now().strftime("%Y-%m-%d")),
    "last30days": ((datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d"), # Corrected: 30 days including today means 29 days ago to today
                  datetime.now().strftime("%Y-%m-%d")),
}


class GA4Client:
    '''Client for interacting with the Google Analytics 4 Data API.'''
    
    def __init__(self, default_property_id: Optional[str] = None):
        '''
        Initialize the GA4 client.
        
        Args:
            default_property_id: Default GA4 property ID to use if not specified in requests
        '''
        self.default_property_id = default_property_id
        self._executor = ThreadPoolExecutor(max_workers=5)
        # self._client is the ADC-based default client
        self._client: Optional[BetaAnalyticsDataClient] = None
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)


    async def _get_adc_client(self) -> BetaAnalyticsDataClient:
        '''
        Get or create the default GA4 API client using Application Default Credentials.
        '''
        if self._client is None:
            logger.info("Initializing default ADC-based BetaAnalyticsDataClient.")
            self._client = await self._loop.run_in_executor(
                self._executor, BetaAnalyticsDataClient
            )
        return self._client

    async def _get_token_based_client(self, access_token: str) -> BetaAnalyticsDataClient:
        '''
        Create a new GA4 API client using a provided OAuth access token.
        '''
        logger.info("Initializing token-based BetaAnalyticsDataClient.")
        try:
            creds = google_credentials.Credentials(token=access_token)
            token_client = await self._loop.run_in_executor(
                self._executor, BetaAnalyticsDataClient, creds
            )
            return token_client
        except Exception as e: 
            logger.error(f"Failed to create token-based client: {e}")
            raise GoogleAPIError(f"Failed to initialize client with provided token: {e}")

    
    async def verify_auth(self) -> bool:
        '''
        Verify that authentication is working using the default ADC client.
        '''
        if not self.default_property_id:
            logger.warning("No default property ID provided, skipping auth verification")
            return True
        
        logger.info("Verifying authentication using default ADC client.")
        client = await self._get_adc_client() 
        try:
            # For get_metadata, the 'name' parameter is the full resource name.
            metadata_resource_name = f"properties/{self.default_property_id}/metadata"
            await self._loop.run_in_executor(
                self._executor,
                client.get_metadata, 
                name=metadata_resource_name 
            )
            logger.info("Default ADC authentication verification successful.")
            return True
        except Exception as e:
            logger.error(f"Default ADC authentication verification failed: {e}")
            raise
    
    async def run_report(
        self,
        property_id: Optional[str] = None,
        metrics: List[str] = None,
        dimensions: Optional[List[str]] = None,
        date_range: Union[Dict[str, str], str] = "last30days",
        limit: int = 10,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not metrics:
            raise ValueError("At least one metric must be specified")
        
        prop_id = property_id or self.default_property_id
        if not prop_id:
            raise ValueError("No property ID provided (neither specific nor default).")

        if access_token:
            logger.debug(f"run_report for {prop_id} using token-based client.")
            client = await self._get_token_based_client(access_token)
        else:
            logger.debug(f"run_report for {prop_id} using ADC-based client.")
            client = await self._get_adc_client()
        
        if isinstance(date_range, str):
            if date_range not in DATE_RANGE_ALIASES:
                raise ValueError(
                    f"Unknown date range alias: {date_range}. "
                    f"Valid aliases: { cultivo}
            start_date, end_date = DATE_RANGE_ALIASES[date_range]
        elif isinstance(date_range, dict):
            start_date = date_range.get("start_date")
            end_date = date_range.get("end_date")
            if not start_date or not end_date:
                raise ValueError("Date range dict must include start_date and end_date")
        else:
            raise ValueError("Invalid date_range format. Must be string alias or dict.")
        
        request = RunReportRequest(
            property=f"properties/{prop_id}",
            metrics=[Metric(name=metric) for metric in metrics],
            dimensions=(
                [Dimension(name=dimension) for dimension in dimensions]
                if dimensions
                else []
            ),
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        
        try:
            response: RunReportResponse = await self._loop.run_in_executor(
                self._executor, client.run_report, request
            )
            return self._format_report_response(response)
        except GoogleAPIError as e:
            logger.error(f"Error running report for property {prop_id}: {e}")
            raise 
    
    async def run_realtime_report(
        self,
        property_id: Optional[str] = None,
        metrics: List[str] = None,
        dimensions: Optional[List[str]] = None,
        limit: int = 10,
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not metrics:
            raise ValueError("At least one metric must be specified")
        
        prop_id = property_id or self.default_property_id
        if not prop_id:
            raise ValueError("No property ID provided (neither specific nor default).")

        if access_token:
            logger.debug(f"run_realtime_report for {prop_id} using token-based client.")
            client = await self._get_token_based_client(access_token)
        else:
            logger.debug(f"run_realtime_report for {prop_id} using ADC-based client.")
            client = await self._get_adc_client()
        
        request = RunRealtimeReportRequest(
            property=f"properties/{prop_id}",
            metrics=[Metric(name=metric) for metric in metrics],
            dimensions=(
                [Dimension(name=dimension) for dimension in dimensions]
                if dimensions
                else []
            ),
            limit=limit,
        )
        
        try:
            response: RunRealtimeReportResponse = await self._loop.run_in_executor(
                self._executor, client.run_realtime_report, request
            )
            return self._format_report_response(response)
        except GoogleAPIError as e:
            logger.error(f"Error running realtime report for property {prop_id}: {e}")
            raise
    
    async def get_metadata(
        self,
        property_id: Optional[str] = None,
        metadata_type: str = "all",
        access_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        prop_id = property_id or self.default_property_id
        if not prop_id:
            raise ValueError("No property ID provided (neither specific nor default).")
        
        if metadata_type not in ("metrics", "dimensions", "all"):
            raise ValueError(
                f"Invalid metadata type: {metadata_type}. "
                f"Valid types: metrics, dimensions, all"
            )
        
        if access_token:
            logger.debug(f"get_metadata for {prop_id} using token-based client.")
            client = await self._get_token_based_client(access_token)
        else:
            logger.debug(f"get_metadata for {prop_id} using ADC-based client.")
            client = await self._get_adc_client()
        
        try:
            metadata_request_name = f"properties/{prop_id}/metadata"
            # The client.get_metadata method expects 'name' as a keyword argument for the request.
            response = await self._loop.run_in_executor(
                self._executor,
                client.get_metadata, 
                name=metadata_request_name
            )
            
            result = {}
            if metadata_type in ("metrics", "all"):
                metrics_data = []
                for metric_item in response.metrics:
                    metrics_data.append({
                        "name": metric_item.api_name,
                        "display_name": metric_item.ui_name,
                        "description": metric_item.description,
                        "category": metric_item.category,
                    })
                result["metrics"] = metrics_data
            
            if metadata_type in ("dimensions", "all"):
                dimensions_data = []
                for dimension_item in response.dimensions:
                    dimensions_data.append({
                        "name": dimension_item.api_name,
                        "display_name": dimension_item.ui_name,
                        "description": dimension_item.description,
                        "category": dimension_item.category,
                    })
                result["dimensions"] = dimensions_data
            return result
        except GoogleAPIError as e:
            logger.error(f"Error getting metadata for property {prop_id}: {e}")
            raise

    def _format_report_response(
        self, response: Union[RunReportResponse, RunRealtimeReportResponse]
    ) -> Dict[str, Any]:
        dimension_headers = [header.name for header in response.dimension_headers]
        metric_headers = [header.name for header in response.metric_headers]
        
        rows = []
        for row_obj in response.rows:
            row_data = {}
            for i, dimension_value in enumerate(row_obj.dimension_values):
                row_data[dimension_headers[i]] = dimension_value.value
            for i, metric_value in enumerate(row_obj.metric_values):
                row_data[metric_headers[i]] = metric_value.value
            rows.append(row_data)
        
        result = {
            "dimensions": dimension_headers,
            "metrics": metric_headers,
            "rows": rows,
            "row_count": response.row_count if hasattr(response, 'row_count') and response.row_count is not None else len(rows),
            "totals": [],
        }
        
        if hasattr(response, "totals") and response.totals:
            for total_row in response.totals:
                total_data = {}
                for i, metric_value in enumerate(total_row.metric_values):
                    if i < len(metric_headers):
                        total_data[metric_headers[i]] = metric_value.value
                if total_data:
                    result["totals"].append(total_data)
        return result
    
    async def close(self):
        """Close the client and clean up resources."""
        if self._client:
            logger.debug("Closing default ADC GA4 client")
            try:
                await self._loop.run_in_executor(self._executor, self._client.close)
            except Exception as e:
                logger.error(f"Error closing default ADC GA4 client: {e}")
        
        logger.info("Shutting down GA4Client ThreadPoolExecutor.")
        self._executor.shutdown(wait=True)
        logger.info("GA4Client resources (executor) shut down.")

