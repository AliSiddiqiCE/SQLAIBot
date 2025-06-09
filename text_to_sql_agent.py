import os
from langchain_community import OpenAI
from langchain_community.database import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langgraph import Graph
from dotenv import load_dotenv

# Load environment variables
_ = load_dotenv()

class TextToSQLAgent:
    def __init__(self, db_url):
        self.db_url = db_url
        self.llm = OpenAI(temperature=0.7)
        self.db = SQLDatabase.from_uri(db_url)
        self.db_chain = SQLDatabaseChain.from_llm(
            llm=self.llm,
            database=self.db,
            verbose=True
        )

    def create_graph(self):
        # Create a LangGraph instance
        graph = Graph()
        
        # Define nodes
        @graph.add_node()
        def process_query(query: str) -> str:
            """Process the user's natural language query and return SQL results."""
            try:
                # Run the query through the SQL chain
                result = self.db_chain.run(query)
                return result
            except Exception as e:
                return f"Error processing query: {str(e)}"

        return graph

    def run(self, query):
        """Run a query through the agent."""
        graph = self.create_graph()
        return graph.invoke(query)

def main():
    # Example usage
    # Replace with your actual database URL
    db_url = "sqlite:///example.db"  # Change this to your actual database URL
    
    agent = TextToSQLAgent(db_url)
    
    print("Welcome to the Text-to-SQL Agent!")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nAsk a question about your database: ")
        if query.lower() == 'exit':
            break
            
        result = agent.run(query)
        print("\nResult:", result)

if __name__ == "__main__":
    main()
