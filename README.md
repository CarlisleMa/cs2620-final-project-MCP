# CS2620 Final Project - MCP (Multi-Service Client Platform)

A distributed system with multiple microservices including calendar, todo, and weather services.

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
- [Environment Setup](#environment-setup)
- [Running the Services](#running-the-services)
- [API Services](#api-services)

## Overview

This project implements a distributed system with multiple microservices communicating via gRPC. The system includes:

- Calendar Service (appointment management with Google Calendar integration)
- Todo Service (task management with SQLite persistence)
- Weather Service (weather data retrieval with WeatherAPI.com integration)

The system includes multiple API integrations:
- The Weather Service integrates with WeatherAPI.com to provide real-time weather data.
- The Calendar Service can integrate with Google Calendar for real appointment management.
- The Todo Service uses SQLite for persistent storage of tasks.

## Project Structure

```
├── client/               # Client-side code
├── server/               # Server-side code
│   ├── calendar_server.py   # Calendar service
│   ├── todo_server.py       # Todo service
│   ├── weather_server.py    # Weather service with Weather API integration
│   └── weather_service.py   # Weather service implementation
├── protocol_pb2.py       # gRPC protocol definitions (compiled)
├── protocol_pb2_grpc.py  # gRPC service stubs (compiled)
├── run_servers.py        # Script to run all servers
└── .env.example          # Example environment variables configuration
```

## Requirements

- Python 3.7+
- gRPC and Protocol Buffers
- Requests library (for API calls)
- python-dotenv (for environment variable management)

## Installation

1. Clone the repository:

```bash
git clone https://github.com/CarlisleMa/cs2620-final-project-MCP.git
cd cs2620-final-project-MCP
```

2. Install the required packages:

```bash
pip install grpcio grpcio-tools protobuf requests python-dotenv
```

## Environment Setup

This project requires environment variables for the Weather API integration and Google Calendar integration. Here's how to set them up:

### Environment Variables

- `WEATHER_API_KEY`: Your API key for WeatherAPI.com (required for real weather data)
- `USE_GOOGLE_CALENDAR`: Set to 'true' to enable Google Calendar integration (defaults to 'false')
- `WEATHER_SERVER_PORT`: Port for the weather server (defaults to 50052)

### Using a .env File (Recommended)

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file** and replace the placeholder values with your actual API keys and configuration.

3. **Install python-dotenv** to load variables from the .env file:
   ```bash
   pip install python-dotenv
   ```

4. The system will automatically load these variables if python-dotenv is installed.

### Setting Environment Variables Manually

#### On macOS/Linux

**For the current terminal session only:**
```bash
export WEATHER_API_KEY=your_api_key_here
```

**To make it permanent:**
1. Edit your shell configuration file (`~/.bash_profile`, `~/.bashrc`, or `~/.zshrc`):
   ```bash
   echo 'export WEATHER_API_KEY=your_api_key_here' >> ~/.bashrc
   ```
2. Reload your shell configuration:
   ```bash
   source ~/.bashrc   # or source ~/.zshrc for Zsh
   ```

#### On Windows

**For the current Command Prompt session only:**
```cmd
set WEATHER_API_KEY=your_api_key_here
```

**For the current PowerShell session only:**
```powershell
$env:WEATHER_API_KEY = "your_api_key_here"
```

**To make it permanent via GUI:**
1. Search for "Edit environment variables for your account" in the Start menu
2. Click "New" to add a new variable
3. Enter "WEATHER_API_KEY" for the name and your API key for the value
4. Click "OK" to save

### Getting a Weather API Key

1. Sign up for an account at [weatherapi.com](https://www.weatherapi.com/)
2. After signing in, go to your Dashboard
3. Copy your API key from the dashboard
4. Set it in your environment as described above

## Running the Services

### Run All Services at Once

To start all services (Calendar, Todo, and Weather):

```bash
python3 run_servers.py
```

This will start:
- Weather Server on port 50052
- Todo Server on port 50053
- Calendar Server on port 50054

### Run Individual Services

To run specific services individually:

```bash
# Run the Weather Service
python3 -m server.weather_server

# Run the Todo Service
python3 -m server.todo_server

# Run the Calendar Service
python3 -m server.calendar_server
```

## Running the Client

After starting the services, you can run the client application to interact with all three services. The client provides an interactive interface to view weather, manage tasks, schedule events, and generate daily agendas.

### Interactive Agenda Client

```bash
python3 -m client.agenda_client
```

This will start an interactive terminal interface with the following commands:

- `agenda` - Display your daily agenda (combines weather, tasks, and events)
- `add event` - Add a calendar event
- `add task` - Add a todo task
- `weather [location]` - Get weather for a specific location
- `exit` - Exit the application

### Programmatic Usage

You can also use the client API programmatically in your own Python code:

```python
from client.agenda_client import AgendaClient

# Initialize the client with your credentials
client = AgendaClient(client_id="your_client_id", api_key="your_api_key")

# Generate an agenda
agenda = client.generate_daily_agenda()
print(agenda)

# Get weather for a location
weather = client.get_weather("London")
print(weather)

# Add a task
client.add_task(
    "Complete project",
    "Finish the distributed system project",
    "2025-05-01",
    "high"
)
```

## Google Calendar Integration

This project supports integration with Google Calendar, allowing you to manage real calendar events instead of using the mock implementation. 

### Setting Up Google Calendar Credentials

1. **Create a Google Cloud Project:**
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project from the dropdown menu
   - Name your project (e.g., "Distributed System Calendar")

2. **Enable the Google Calendar API:**
   - Navigate to "APIs & Services" > "Library"
   - Search for "Google Calendar API" and click on it
   - Click "Enable"

3. **Set Up OAuth Consent Screen:**
   - Go to "APIs & Services" > "OAuth consent screen"
   - Select "External" as the user type
   - Fill in required fields (app name, support email, developer contact)
   - Add the scope: `https://www.googleapis.com/auth/calendar`
   - Add your email as a test user

4. **Create OAuth Credentials:**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Choose "Desktop app" and give it a name
   - Download the JSON file

5. **Configure Your Application:**
   - Create a `credentials` directory in your project root:
     ```bash
     mkdir -p credentials
     ```
   - Rename the downloaded file to `credentials.json` and move it to the `credentials/` directory
   - Add `USE_GOOGLE_CALENDAR=true` to your `.env` file

> **Important Security Note:** Never commit your credentials files to version control! The `credentials/` directory and JSON files are already in the `.gitignore` file to prevent accidental commits.

For more detailed instructions, see the [Google Calendar Setup Guide](docs/google_calendar_setup.md).

The system will automatically detect and use Google Calendar if properly configured, or fall back to the mock implementation if not.

## API Services

### Weather Service

The Weather Service provides current weather and forecast data. It integrates with Weather API for real data but falls back to mock data if the API key is not configured or if there's an API error.

**Key Methods:**
- `get_current_weather`: Get current weather for a location
- `get_forecast`: Get a multi-day weather forecast for a location

### Todo Service

The Todo Service allows for task management with persistent storage using SQLite:

**Key Methods:**
- Task creation, retrieval, updating, and deletion
- Task listing and filtering

**Persistence:**
- Tasks are stored in a SQLite database located in the `data/todo.db` file
- Data persists between server restarts
- Automatic database creation and initialization

### Calendar Service

The Calendar Service manages appointments and events:

**Key Methods:**
- Event creation, retrieval, updating, and deletion
- Calendar views and scheduling