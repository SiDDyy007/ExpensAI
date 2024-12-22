import getpass
from dotenv import load_dotenv
from typing import List, Dict, Any
from pydantic import BaseModel, Field
import os
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from pdf_extractor import getExpenseJSON
from langchain_community.vectorstores import Pinecone
from pinecone import Pinecone as PineconeClient
from langchain_pinecone import PineconeVectorStore
from langchain_pinecone import PineconeEmbeddings

memory = MemorySaver()


load_dotenv()
claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
pinecone_api_key = os.environ.get("PINECONE_API_KEY")

# Initialize Pinecone (assuming it's already set up)
pc = PineconeClient(pinecone_api_key)
pinecone_index = pc.Index("multilingual-e5-large")
# vectorstore = Pinecone(pinecone_index, embedding_function, "text")
embeddings = PineconeEmbeddings(model="multilingual-e5-large")
vectorstore = PineconeVectorStore(index=pinecone_index, embedding=embeddings)

llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")

# State definition
class ProcessorState(BaseModel):
    statements: List[str] = Field(default_factory=list)
    transactions: List[Dict] = Field(default_factory=list)
    categorized_charges: Dict[str, List] = Field(default_factory=dict)
    new_observations: List[str] = Field(default_factory=list)
    current_balance: float = Field(default=0.0)
    confirmed: bool = Field(default=False)


# Function to process statements
def process_statements(state: ProcessorState) -> ProcessorState:
    '''Process statements and extract transactions'''
    state.transactions = getExpenseJSON()[:3]
    # print(state.transactions, " ----- ", type(state.transactions))
    # print(vectorstore.similarity_search("Apple"))
    return state

class transaction(BaseModel):
    """Code output"""
    name: Annotated[str, ..., "The name of the charge"]
    description: Annotated[str, ..., "The description of the charge"]
    charge: Annotated[str, ...,"Charge Amount"]





# Function to check charges against vector DB and get user clarification
def categorize_charges(state: ProcessorState) -> dict:
    # print("Categorizing charges...", state)
    messages = [SystemMessage(
        content="You are a helpful Expense manager assistant! Your name is ExpensAI. Your job to help users manage their expenses by categorizing their credit card charges according to them. Keep your responses clear and concise."
    )]
    for transaction in state.transactions:
        # Search vector DB for similar charges
        results = vectorstore.similarity_search(transaction['description'])
        # print("resuts ", results)
        results = None
        if not results:
            print("No results boss")
            user_input = input(f"I noticed a new charge: {transaction['description']} "
                                f"for {transaction['amount']}. Could you tell me what "
                                f"category this falls under using a number only? (\n1. Utilities \n2. Grocery \n3. Fun \n4. Investment \n5. Bill payments)")
            if user_input == '1':
                category = "utilities"
            elif user_input == '2':
                category = "grocery"
            elif user_input == '3':
                category = "fun"
            elif user_input == '4':
                category = "investment"
            elif user_input == "5":
                category = "bill payments"
            else:
                category = "other"
            # New charge type found - ask for clarification
            create_description_message = [HumanMessage(content=f"There is a new type of charge/refund in my statement for {transaction['description']} and amount {transaction['amount']}. "
                                            f"This falls under the category {category}. Please craft a small description for this charge/refund type in 1-2 sentences for future references for such type of charges/refunds.")]
            
            structured_llm = llm.with_structured_output(transaction)
            # response = structured_llm.invoke(messages + create_description_message)
            response = structured_llm.invoke("I have a charge from Amazon for $100 as a new charge type. This falls under the category of shopping.")
            category = response.content

            print("Response from LLM ", response.content)
            
            # Store new charge type in vector DB
            vectorstore.add_texts(
                texts=[transaction['description']],
                metadatas=[{"category": category}]
            )
            
            state.new_observations.append(f"New charge type: {transaction['description']} - {category}")
        else:
            category = results[0].metadata['category']
            
        # Group charges by category
        if category not in state.categorized_charges:
            state.categorized_charges[category] = []
        state.categorized_charges[category].append(transaction)
    
    return state


# Build the graph
def build_credit_card_processor() -> StateGraph:
    workflow = StateGraph(ProcessorState)
    
    # Add nodes
    workflow.add_node("process_statements", process_statements)
    workflow.add_node("categorize_charges", categorize_charges)
    # workflow.add_node("confirm_balance", confirm_balance)
    # workflow.add_node("update_sheets", update_sheets)
    # workflow.add_node("generate_report", generate_report)
    
    # Add edges
    workflow.add_edge("process_statements", "categorize_charges")
    # workflow.add_edge("categorize_charges", "confirm_balance")
    
    # # Conditional edge based on balance confirmation
    # workflow.add_conditional_edges(
    #     "confirm_balance",
    #     lambda x: "update_sheets" if x.confirmed else "process_statements",
    #     {
    #         "update_sheets": "update_sheets",
    #         "process_statements": "process_statements"
    #     }
    # )
    
    # workflow.add_edge("update_sheets", "generate_report")
    # workflow.add_edge("generate_report", END)
    
    # Set entry point
    workflow.set_entry_point("process_statements")

    workflow.add_edge("categorize_charges", END)
    
    return workflow

# Main execution
def main():
    # Initialize the graph
    app = build_credit_card_processor()

    app = app.compile()
    
    # Get initial user input
    messages = [
        HumanMessage(content="Hello! Please provide your credit card statements that you'd like me to process.")
    ]
    response = llm.invoke(messages)
    
    # Create initial state
    initial_state = ProcessorState(statements=[response.content])
    
    # Run the graph
    for output in app.stream(initial_state):
        if "process_statements" in output:
            print("Processing statements...")
        elif "categorize_charges" in output:
            print("Categorizing charges...")
        elif "confirm_balance" in output:
            print("Confirming balance...")
        elif "update_sheets" in output:
            print("Updating Google Sheets...")
        elif "generate_report" in output:
            print("Generating final report...")
            print(output["generate_report"].report)

if __name__ == "__main__":
    main()