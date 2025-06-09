# Text-to-SQL Agent

An interactive agent that converts natural language queries into SQL queries using LangGraph and LangChain.

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

3. Set up your database connection:
- Update the `db_url` in `text_to_sql_agent.py` to point to your database
- Supported databases: SQLite, PostgreSQL, MySQL, etc.

## Usage

Run the agent:
```bash
python text_to_sql_agent.py
```

The agent will start an interactive session where you can ask natural language questions about your database. Type 'exit' to quit.

## Features

- Natural language to SQL conversion
- Interactive query interface
- Error handling and feedback
- Built with LangGraph for efficient processing
