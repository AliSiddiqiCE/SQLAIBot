from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_community.database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
import os
import warnings
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
    llm=llm,
    database=db,
    verbose=True
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
    return {'sql': response.content}

def execute_node(state: SQLState) -> dict[str, str]:
    """Execute the SQL query and get results."""
    try:
        result = db_chain.run(state['sql'])
        return {'result': result}
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
    return {'sql': response.content}

def create_sql_agent() -> StateGraph[SQLState]:
    """Create the SQL agent graph."""
    builder = StateGraph(SQLState)
    
    # Add nodes
    builder.add_node("query", query_node)
    builder.add_node("execute", execute_node)
    builder.add_node("explain", explain_node)
    builder.add_node("error_handling", error_handling_node)
    
    # Set entry point
    builder.set_entry_point("query")
    
    # Add edges
    builder.add_edge("query", "execute")
    builder.add_conditional_edges("execute", 
        lambda state: state.get('error'),
        {True: "error_handling", False: "explain"}
    )
    builder.add_edge("error_handling", "execute")
    
    # Compile the graph
    return builder.compile()

def main():
    """Run the SQL agent."""
    agent = create_sql_agent()
    
    print("Welcome to the Text-to-SQL Agent!")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nEnter your question (or 'exit' to quit): ")
        if query.lower() == 'exit':
            break
            
        # Initialize state
        state = {
            'query': query,
            'schema': get_schema()
        }
        
        # Run the agent
        result = agent.invoke(state)
        
        # Display results
        print("\nGenerated SQL:", result.get('sql', 'N/A'))
        print("\nExplanation:", result.get('explanation', 'N/A'))
        print("\nResult:", result.get('result', 'N/A'))
        if 'error' in result:
            print("\nError:", result['error'])

if __name__ == "__main__":
    main() 

REFLECTION_PROMPT = """You are a teacher grading an essay submission. \
Generate critique and recommendations for the user's submission. \
Provide detailed recommendations, including requests for length, depth, style, etc."""

RESEARCH_PLAN_PROMPT = """You are a researcher charged with providing information that can \
be used when writing the following essay. Generate a list of search queries that will gather \
any relevant information. Only generate 3 queries max."""

RESEARCH_CRITIQUE_PROMPT = """You are a researcher charged with providing information that can \
be used when making any requested revisions (as outlined below). \
Generate a list of search queries that will gather any relevant information. Only generate 3 queries max."""


class Queries(BaseModel):
    queries: List[str]

def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=PLAN_PROMPT), 
        HumanMessage(content=state['task'])
    ]
    response = model.invoke(messages)
    return {"plan": response.content}

def research_plan_node(state: AgentState):
    queries = model.with_structured_output(Queries).invoke([
        SystemMessage(content=RESEARCH_PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ])
    content = state['content'] or []
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            content.append(r['content'])
    return {"content": content}

def generation_node(state: AgentState):
    content = "\n\n".join(state['content'] or [])
    user_message = HumanMessage(
        content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}")
    messages = [
        SystemMessage(
            content=WRITER_PROMPT.format(content=content)
        ),
        user_message
        ]
    response = model.invoke(messages)
    return {
        "draft": response.content, 
        "revision_number": state.get("revision_number", 1) + 1
    }

def reflection_node(state: AgentState):
    messages = [
        SystemMessage(content=REFLECTION_PROMPT), 
        HumanMessage(content=state['draft'])
    ]
    response = model.invoke(messages)
    return {"critique": response.content}

def research_critique_node(state: AgentState):
    queries = model.with_structured_output(Queries).invoke([
        SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
        HumanMessage(content=state['critique'])
    ])
    content = state['content'] or []
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            content.append(r['content'])
    return {"content": content}

def should_continue(state):
    if state["revision_number"] > state["max_revisions"]:
        return END
    return "reflect"

builder = StateGraph(AgentState)

builder.add_node("planner", plan_node)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_plan", research_plan_node)
builder.add_node("research_critique", research_critique_node)

builder.set_entry_point("planner")

builder.add_conditional_edges(
    "generate", 
    should_continue, 
    {END: END, "reflect": "reflect"}
)


builder.add_edge("planner", "research_plan")
builder.add_edge("research_plan", "generate")

builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")

graph = builder.compile(checkpointer=memory)

