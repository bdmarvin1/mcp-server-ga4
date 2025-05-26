'''
# MCP Server for Google Analytics 4 (Version 0.2.1)

A Model Context Protocol (MCP) server that allows Large Language Models (LLMs) to interact with Google Analytics 4 (GA4) data through the Google Analytics Data API.

## Features

- Run standard GA4 reports with customizable dimensions, metrics, and date ranges.
- Get real-time data for the past 30 minutes.
- Retrieve metadata about available metrics and dimensions.
- Secure authentication via:
    - OAuth 2.0 access tokens (passed by an MCP controller like [typingmind-mcp](https://github.com/bdmarvin1/typingmind-mcp)).
    - Google Cloud's Application Default Credentials (ADC) as a fallback.
- Configurable for easy deployment.

## Installation

This server can be installed using `pip` or `uv` (recommended for faster environment management and execution).

### Using `uv` (Recommended)

[uv](https://github.com/astral-sh/uv) is an extremely fast Python package installer and resolver.

1.  **Install `uv`**:
    Follow the instructions on the [official `uv` installation guide](https://github.com/astral-sh/uv#installation).

2.  **Install `bdmarvin1-mcp-server-ga4` (from PyPI once published)**:
    ```bash
    uv pip install bdmarvin1-mcp-server-ga4
    ```
    To install directly from the GitHub repository (e.g., the `main` branch):
    ```bash
    uv pip install "bdmarvin1-mcp-server-ga4 @ git+https://github.com/bdmarvin1/mcp-server-ga4.git@main"
    ```
    (Note: The package name `bdmarvin1-mcp-server-ga4` is used here, but the internal script name invoked by `uv run` will still be `mcp-server-ga4` as defined in `pyproject.toml`.)


### Using `pip` (from PyPI once published)

```bash
pip install bdmarvin1-mcp-server-ga4
```

### From Source (Development)

```bash
git clone https://github.com/bdmarvin1/mcp-server-ga4.git
cd mcp-server-ga4

# Using uv (recommended for development)
uv venv 
_SCRIPT_CONTINUATION_
source .venv/bin/activate # Or .venv\Scripts\activate on Windows
# This installs the package named 'bdmarvin1-mcp-server-ga4' in editable mode with dev dependencies
uv pip install -e ".[dev]" 

# Or using pip and venv
# python -m venv .venv
# source .venv/bin/activate # Or .venv\Scripts\activate on Windows
# pip install -e ".[dev]"
```

## Authentication

This server supports two primary methods of authentication with the Google Analytics Data API:

1.  **OAuth 2.0 Access Token (Preferred when used with an MCP Controller):**
    *   When this server is managed by an OAuth-enabled MCP controller (such as [bdmarvin1/typingmind-mcp](https://github.com/bdmarvin1/typingmind-mcp)), the controller is responsible for handling the full OAuth 2.0 flow.
    *   The controller will pass a Google OAuth **access token** to this server with each tool call, under the key `__google_access_token__` in `kwargs`.
    *   If a valid `__google_access_token__` is provided, it will be used for GA4 API requests.

2.  **Application Default Credentials (ADC - Fallback/Standalone):**
    *   If no `__google_access_token__` is provided, the server falls back to ADC.
    *   Setup:
        1.  [Create a Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects).
        2.  [Enable the Google Analytics Data API](https://console.cloud.google.com/flows/enableapi?apiid=analyticsdata.googleapis.com).
        3.  Set up ADC: `gcloud auth application-default login`.
    *   See [Google Cloud Authentication documentation](https://cloud.google.com/docs/authentication/provide-credentials-adc).

**Priority:** OAuth token takes precedence over ADC.

## Usage

The server can be run using its command-line script `mcp-server-ga4` (this is the script name defined in `pyproject.toml`) or by telling `uv run` to execute the package `bdmarvin1-mcp-server-ga4`.

### Command Line with `uv run` (Recommended for direct execution)

To run the installed package `bdmarvin1-mcp-server-ga4` (which exposes the `mcp-server-ga4` script):
```bash
uv run bdmarvin1-mcp-server-ga4 -- --property-id YOUR_GA4_PROPERTY_ID 
```
(The first `--` separates `uv run` arguments from arguments for the script `mcp-server-ga4`)

To run directly from the GitHub repository (e.g., `main` branch), effectively installing and running in one step:
```bash
uv run "bdmarvin1-mcp-server-ga4 @ git+https://github.com/bdmarvin1/mcp-server-ga4.git@main" -- --property-id YOUR_GA4_PROPERTY_ID
```

### Command Line (if `mcp-server-ga4` script is in PATH)

After installation (e.g., via `uv pip install bdmarvin1-mcp-server-ga4` or `pip install bdmarvin1-mcp-server-ga4`), the `mcp-server-ga4` script should be available:
```bash
mcp-server-ga4 --property-id YOUR_GA4_PROPERTY_ID
```
Run `mcp-server-ga4 --help` for more options.

### Environment Variables

- `GA4_PROPERTY_ID`: Default GA4 property ID.

### Using with an MCP Controller (e.g., `typingmind-mcp`)

1.  **Installation for the Controller:**
    Ensure the `bdmarvin1-mcp-server-ga4` package is installed in an environment accessible to your MCP controller. For Dockerized environments (like Cloud Run):
    *   Add Python and `uv` to your Dockerfile.
    *   Install the package: `RUN uv pip install bdmarvin1-mcp-server-ga4` (or from Git for development).

2.  **Controller Configuration:**
    Configure your MCP controller to launch the `mcp-server-ga4` script. Example using `uv run`:
    ```json
    {
        "servers": {
            "ga4_oauth": {
                "command": "uv", 
                "args": ["run", "bdmarvin1-mcp-server-ga4", "--", "--property-id", "YOUR_DEFAULT_GA4_PROPERTY_ID_FOR_ADC_FALLBACK"],
            }
        }
    }
    ```

## Available Tools

When an OAuth access token is used, the `property_id` parameter is still respected. If `property_id` is omitted, the server's default `GA4_PROPERTY_ID` is used (primarily for ADC).

### `run-report`
Parameters:
- `metrics: List[str]`
- `dimensions: Optional[List[str]]`
- `date_range: Union[Dict[str, str], str]`
- `property_id: Optional[str]`
- `limit: int` (Default: 10)
- `**kwargs` (Internal: for `__google_access_token__`)

### `run-realtime-report`
Parameters:
- `metrics: List[str]`
- `dimensions: Optional[List[str]]`
- `property_id: Optional[str]`
- `limit: int` (Default: 10)
- `**kwargs`

### `get-metadata`
Parameters:
- `type: str` (Default: `"all"`. Options: `"metrics"`, `"dimensions"`, `"all"`)
- `property_id: Optional[str]`
- `**kwargs`

## Examples (Natural Language Prompts to an LLM)

(Examples remain the same, just ensure the LLM/controller is aware it can specify `property_id` if needed)

## Development

1.  Clone: `git clone https://github.com/bdmarvin1/mcp-server-ga4.git`
2.  `cd mcp-server-ga4`
3.  Create/activate venv using `uv`:
    ```bash
    uv venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    ```
4.  Install dev dependencies (installs `bdmarvin1-mcp-server-ga4` in editable mode):
    ```bash
    uv pip install -e ".[dev]"
    ```
5.  Linters/formatters: `black .`, `isort .`
6.  Tests: `pytest`

## License
MIT
'''