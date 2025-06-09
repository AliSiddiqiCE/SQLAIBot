from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.utilities.sql_database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
import warnings
import os
import sys
warnings.filterwarnings("ignore")

_ = load_dotenv()

# Load environment variables
DB_URL = os.getenv("DATABASE_URL", "sqlite:///example.db")

class SQLState(TypedDict):
    query: str
    sql: str
    result: str
    explanation: str
    schema: str
    error: str

# Initialize components
llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7)
db = SQLDatabase.from_uri(DB_URL)
db_chain = SQLDatabaseChain.from_llm(
    llm, db
)

# Define prompts
QUERY_PROMPT = """You are a SQL query generator. Given a natural language question, generate a SQL query that answers it.
Database schema: {schema}
Question: {query}
Generated SQL query:"""

EXPLANATION_PROMPT = """Explain the SQL query in simple terms:
Query: {sql}
Explanation:"""

ERROR_HANDLING_PROMPT = """The previous query failed with error: {error}
Please analyze the error and generate a corrected SQL query.
Database schema: {schema}
Original question: {query}
Failed query: {sql}
Corrected SQL query:"""

def get_schema() -> str:
    """Get the database schema description."""
    return db.get_table_info()

def query_node(state: SQLState) -> dict[str, str]:
    """Generate SQL query from natural language."""
    schema = state.get('schema', get_schema())
    messages = [
        SystemMessage(content=QUERY_PROMPT.format(schema=schema, query=state['query']))
    ]
    response = llm.invoke(messages)
    
    # Ensure we have a valid SQL query
    sql = response.content.strip()
    if not sql:
        return {'error': 'No SQL query generated'}
    
    # Return the SQL query
    return {'sql': sql}

def execute_node(state: SQLState) -> dict[str, str]:
    """Execute the SQL query and get results."""
    try:
        # Split SQL statements by semicolon
        statements = [stmt.strip() for stmt in state['sql'].split(';') if stmt.strip()]
        results = []
        
        # Execute each statement separately
        for stmt in statements:
            try:
                result = db_chain.run(stmt)
                results.append(result)
            except Exception as e:
                return {'error': f"Error executing statement: {stmt}\nError: {str(e)}"}
                
        return {'result': '\n'.join(results)}
    except Exception as e:
        return {'error': str(e)}

def explain_node(state: SQLState) -> dict[str, str]:
    """Generate an explanation of the query."""
    messages = [
        SystemMessage(content=EXPLANATION_PROMPT.format(sql=state['sql']))
    ]
    response = llm.invoke(messages)
    return {'explanation': response.content}

def error_handling_node(state: SQLState) -> dict[str, str]:
    """Handle query errors by generating a corrected query."""
    schema = state.get('schema', get_schema())
    messages = [
        SystemMessage(content=ERROR_HANDLING_PROMPT.format(
            error=state['error'],
            schema=schema,
            query=state['query'],
            sql=state['sql']
        ))
    ]
    response = llm.invoke(messages)
    
    # Ensure we have a valid SQL query
    sql = response.content.strip()
    if not sql:
        return {'error': 'Failed to generate corrected query'}
    
    return {'sql': sql}

def create_sql_agent() -> StateGraph:
    """Create the SQL agent graph."""
    builder = StateGraph(SQLState)
    
    # Add nodes
    builder.add_node("generate_sql", query_node)
    builder.add_node("run_query", execute_node)
    builder.add_node("explain_query", explain_node)
    builder.add_node("handle_error", error_handling_node)
    builder.add_node("final_error", lambda state: {'error': 'Final error: ' + state.get('error', 'Unknown error')})
    
    # Set entry point
    builder.set_entry_point("generate_sql")
    
    # Add edges
    builder.add_edge("generate_sql", "run_query")
    builder.add_conditional_edges("run_query", 
        lambda state: 'error' in state,
        {True: "handle_error", False: "explain_query"}
    )
    
    # Add error handling flow
    builder.add_conditional_edges("handle_error", 
        lambda state: 'error' in state,
        {True: "final_error", False: "run_query"}
    )
    
    # Add terminal edges
    builder.add_edge("explain_query", END)
    builder.add_edge("final_error", END)
    
    # Compile the graph
    return builder.compile()

def main():
    """Run the SQL agent."""
    agent = create_sql_agent()
    
    print("Welcome to the Text-to-SQL Agent!")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your question (or 'exit' to quit): ").strip()
        if query == 'quit':
            sys.exit()
        if query.lower() == 'exit':
            break
            
        try:
            # Initialize state
            state = SQLState(
                query=query,
                sql='',
                result='',
                explanation='',
                schema=get_schema(),
                error=''
            )
            
            # Run the agent
            result = agent.invoke(state)
            
            # Display results
            if result.get('sql'):
                print("\nGenerated SQL:", result['sql'])
            
            if result.get('explanation'):
                print("\nExplanation:", result['explanation'])
            
            if result.get('result'):
                print("\nResult:", result['result'])
            
            if result.get('error'):
                if result['error'] != 'Final error: ':
                    print("\nError:", result['error'])
                
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
            break

if __name__ == "__main__":
    main()
