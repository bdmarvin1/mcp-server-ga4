# MCP Server for Google Analytics 4

A Model Context Protocol (MCP) server that allows Large Language Models (LLMs) to interact with Google Analytics 4 (GA4) data through the Google Analytics Data API.

## Features

- Run standard GA4 reports with customizable dimensions, metrics, and date ranges
- Get real-time data for the past 30 minutes
- Retrieve metadata about available metrics and dimensions
- Secure authentication using Google Cloud's Application Default Credentials
- Configurable for easy deployment via [Smithery](https://smithery.ai)

## Installation

### Using pip

```bash
pip install mcp-server-ga4
```

### From source

```bash
git clone https://github.com/yourusername/mcp-server-ga4.git
cd mcp-server-ga4
pip install -e .
```

## Authentication

This server uses Google Cloud's Application Default Credentials (ADC) for authentication. Before using the server, you'll need to:

1. [Create a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects)
2. [Enable the Google Analytics Data API](https://console.cloud.google.com/flows/enableapi?apiid=analyticsdata.googleapis.com)
3. Set up authentication:

```bash
gcloud auth application-default login
```

For more details, see the [Google Cloud Authentication documentation](https://cloud.google.com/docs/authentication/provide-credentials-adc).

## Usage

### Command Line

Start the server with your GA4 property ID:

```bash
mcp-server-ga4 --property-id YOUR_GA4_PROPERTY_ID
```

The server will use the standard MCP stdio transport by default.

### Environment Variables

You can also set configuration via environment variables:

- `GA4_PROPERTY_ID`: Your Google Analytics 4 property ID

### Using with Claude Desktop

1. Install the server globally: `pip install mcp-server-ga4`
2. Set up your Google Cloud authentication: `gcloud auth application-default login`
3. Edit your Claude Desktop configuration:

```json
{
    "mcpServers": {
        "ga4": {
            "command": "mcp-server-ga4",
            "args": ["--property-id", "YOUR_GA4_PROPERTY_ID"]
        }
    }
}
```

## Available Tools

### run-report

Runs a standard GA4 report with configurable metrics, dimensions, and date ranges.

Parameters:
- `property_id` (optional): GA4 property ID (overrides the default)
- `metrics`: List of metric names (e.g., ["activeUsers", "sessions"])
- `dimensions` (optional): List of dimension names (e.g., ["date", "country"])
- `date_range`: Date range in one of these formats:
  - `{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}`
  - `"last7days"`, `"last30days"`, `"today"`, `"yesterday"`
- `limit` (optional): Number of rows to return (default: 10)

### run-realtime-report

Gets real-time data for the past 30 minutes.

Parameters:
- `property_id` (optional): GA4 property ID (overrides the default)
- `metrics`: List of metric names (e.g., ["activeUsers", "screenPageViews"])
- `dimensions` (optional): List of dimension names (e.g., ["country", "city"])
- `limit` (optional): Number of rows to return (default: 10)

### get-metadata

Retrieves available metrics and dimensions for a GA4 property.

Parameters:
- `property_id` (optional): GA4 property ID (overrides the default)
- `type` (optional): Type of metadata to retrieve (`"metrics"`, `"dimensions"`, or `"all"`, default: `"all"`)

## Examples

### Running a standard report

```
What were the top 5 countries by active users in the last 30 days?
```

### Checking real-time data

```
How many users are currently active on the site?
```

### Getting metadata information

```
What metrics are available for me to query in GA4?
```

## Development

1. Clone the repository
2. Install development dependencies: `pip install -e ".[dev]"`
3. Run tests: `pytest`

## License

MIT
