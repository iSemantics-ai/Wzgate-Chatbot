"""
this file contains the main graph of the chatbot
main graph is the parent graph that contains the subgraphs
the subgraphs are the RAG and the UNITS subgraphs
the main graph is responsible for routing the user input to the proper subgraph
and then routing the output of the subgraph to the END node
"""
import os
import asyncio
from langgraph.graph import StateGraph, END
from typing import List, TypedDict
from langchain_openai import ChatOpenAI
from core import settings
from .RAG_subgraph import RAGChatbotGraph, initialize_chatbot as initialize_rag, RAGChatbotState,RAGChatbot
from .units_subgraph import UnitsChatbotGraph, UnitsChatbotState
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import trim_messages
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.store.memory import InMemoryStore
from format import classifier_prompt
from core import settings

#set enviroment variables
os.environ["LANGCHAIN_TRACING_V2"] = settings.LANGCHAIN_TRACING_V2
os.environ["LANGSMITH_PROJECT"] = settings.LANGSMITH_PROJECT
os.environ["LANGCHAIN_ENDPOINT"] = settings.LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY

# Define the MemorySaver and trimmer.
memory = MemorySaver()
if not hasattr(memory, "messages"):
    memory.messages = []  
trimmer = trim_messages(strategy="last", max_tokens=7, token_counter=len)
user_memory_store = InMemoryStore()

# Define a helper function to create unique keys for the user’s chat history.
def get_memory_key(user_id: str, category: str) -> str:
    return f"{user_id}_{category}"

# Define the Parent Graph State.
# We mark total=False so that extra keys are allowed—but list keys we want to persist.
# --------------------------------------------------------------------------
class ChatbotState(TypedDict, total=False):
    user_input: str
    question: str               # Add this so that the RAG adapter’s "question" key is preserved.
    last_chatbot: str | None    # will be set to "UNITS" or "RAG"
    bot_response: str | None    # will be set to the response from the subgraph.
    chat_history: List          # list of messages (HumanMessage, AIMessage, etc.)
    rag_chat_history: List      # list of messages (HumanMessage, AIMessage, etc.)
    units_chat_history: List    # list of messages (HumanMessage, AIMessage, etc.)
    lang: str                   # This key is needed by the Units and RAG adapters.


# Create a classifier LLM and prompt for routing.
# --------------------------------------------------------------------------
classifier_llm = ChatOpenAI(
    model=settings.MODEL_NAME,
    temperature=0,
    openai_api_key=settings.OPENAI_API_KEY
)

        
def classify_query(state: ChatbotState) -> dict:
    """
    this function classifies the query and routes it to the proper subgraph.
    """
    last_user_message = state["user_input"]

    chat_history = state.get("chat_history", [])
    if not chat_history:  # if the list is empty
        last_messages = ["No previous messages. This is the start of the conversation."]
    else:
        # Apply the trimmer to keep only the most recent 4 messages.
        trimmed_messages = trimmer.invoke(chat_history)
        last_messages = [f"{msg.type.capitalize()}: {msg.content}" for msg in trimmed_messages]

    # Combine the messages into one string for context.
    combined_history = "\n".join(last_messages)
    # Call the classifier LLM with the prompt and context.
    response = classifier_llm.invoke(classifier_prompt(combined_history, last_user_message, state.get("last_chatbot", "UNITS")))

    classification = response.content.strip()
    
    # Default to the previous chatbot if the classification is not clearly "UNITS" or "RAG".
    if classification not in ["UNITS", "RAG"]:
        classification = state.get("last_chatbot", "UNITS")

    return {"last_chatbot": classification, "bot_response": None}


# Adapter node: Convert parent state into the UNITS subgraph’s state.
# --------------------------------------------------------------------------
def units_adapter(state: ChatbotState) -> UnitsChatbotState:
    return {
        "user_input": state["user_input"],
        "extracted_info": None,
        "conversation_summary": None,
        "bot_response": None,
        "chat_history": state["chat_history"],  # Passing the shared MemorySaver
        "lang": "ar" if any(0x0600 <= ord(c) <= 0x06FF for c in state["user_input"]) else "en",
        "units_chat_history":state["units_chat_history"],
        "should_complete": False,
    }



# Adapter node: Convert parent state into the RAG subgraph’s state.
# --------------------------------------------------------------------------
def rag_adapter(state: ChatbotState) -> RAGChatbotState:
    return {
        "question": state["user_input"],
        "context": [],
        "answer": None,
        "chat_history": state["chat_history"],
        "rag_chat_history":state["rag_chat_history"],  # Passing the shared MemorySaver
        "redifined_question": state.get("redifined_question", None),
        "bot_response": None,
        "lang": "ar" if any(0x0600 <= ord(c) <= 0x06FF for c in state["user_input"]) else "en",
    }


# Adapter node: Convert the UNITS subgraph’s output back to the parent’s state.
# --------------------------------------------------------------------------
def units_output_adapter(units_state: UnitsChatbotState) -> dict:
    return {"bot_response": units_state.get("bot_response", ""), "last_chatbot": "UNITS"}


# Adapter node: Convert the RAG subgraph’s output back to the parent’s state.
# --------------------------------------------------------------------------
def rag_output_adapter(rag_state: RAGChatbotState) -> dict:
    return {"bot_response": rag_state.get("bot_response", ""), "last_chatbot": "RAG"}


# Instantiate the subgraph classes and compile their graphs.
# --------------------------------------------------------------------------
units_chatbot = UnitsChatbotGraph()
rag_chatbot   = RAGChatbotGraph()

# Compile the subgraphs.
# --------------------------------------------------------------------------
compiled_units = units_chatbot.compiled_graph  
compiled_rag   = rag_chatbot.compiled_graph      

# Build the Parent Graph.
# --------------------------------------------------------------------------
chatbot_graph = StateGraph(ChatbotState)
chatbot_graph.set_entry_point("classifier")

#The classifier node (classifies the query)
# --------------------------------------------------------------------------
chatbot_graph.add_node("classifier", classify_query)

#Based on classification, route to the proper adapter.
def route_based_on_classification(state: ChatbotState):
    if state.get("last_chatbot") == "UNITS":
        return "units_adapter"
    elif state.get("last_chatbot") == "RAG":
        return "rag_adapter"
    return state.get("last_chatbot", "units_adapter")

#Conditional edges: route based on the classification.
chatbot_graph.add_conditional_edges(
    "classifier",
    route_based_on_classification,
    {"units_adapter": "units_adapter", "rag_adapter": "rag_adapter"}
)

#Adapter nodes: convert the parent's state into the subgraph input.
chatbot_graph.add_node("units_adapter", units_adapter)
chatbot_graph.add_node("rag_adapter", rag_adapter)

#Add the compiled subgraphs directly as nodes.
chatbot_graph.add_node("units_subgraph", compiled_units)
chatbot_graph.add_node("rag_subgraph", compiled_rag)

# Adapter nodes: convert the subgraph output back to the parent state.
chatbot_graph.add_node("units_output", units_output_adapter)
chatbot_graph.add_node("rag_output", rag_output_adapter)

# Connect adapter nodes to the corresponding subgraphs.
chatbot_graph.add_edge("units_adapter", "units_subgraph")
chatbot_graph.add_edge("rag_adapter", "rag_subgraph")

# Connect subgraphs to their output adapters.
chatbot_graph.add_edge("units_subgraph", "units_output")
chatbot_graph.add_edge("rag_subgraph", "rag_output")

# send the output adapters to END.
chatbot_graph.add_edge("units_output", END)
chatbot_graph.add_edge("rag_output", END)
compiled_parent = chatbot_graph.compile(checkpointer=memory, store=user_memory_store)

rag_class= RAGChatbot()

# Draw the complete (nested) graph 
# compiled_parent.get_graph(xray=1).draw_mermaid_png(output_file_path="main_graph_final.png")

# Define the chatbot interface.
async def chatbot_interface(input_text: str, user_id: str, history: list = None) -> dict:
    """
    this function is the main interface for the chatbot
    input_text: the user input
    user_id: the user id
    history: the chat history
    
    return: the chatbot response
    """
    # Use our helper to create unique keys.
    chat_key = get_memory_key(user_id, "chat_history")
    rag_key = get_memory_key(user_id, "rag_chat_history")
    units_key = get_memory_key(user_id, "units_chat_history")
    
    # Retrieve histories.
    chat_history_mem = user_memory_store.get(chat_key, chat_key)
    rag_history_mem = user_memory_store.get(rag_key, rag_key)
    units_history_mem = user_memory_store.get(units_key, units_key)
    
    chat_history = chat_history_mem.value if chat_history_mem else []
    rag_chat_history = rag_history_mem.value if rag_history_mem else []
    units_chat_history = units_history_mem.value if units_history_mem else []
    
    # If initial history is provided and no history stored, use it.
    if not chat_history and history:
        for m in history:
            if m.get("role") == "user":
                chat_history.append(HumanMessage(content=m.get("content")))
            elif m.get("role") == "ai":
                chat_history.append(AIMessage(content=m.get("content")))
    
    config = {"configurable": {"thread_id": user_id, "user_id": user_id}}
    
    initial_state = {
        "user_input": input_text,
        "question": None,
        "last_chatbot": None,
        "bot_response": None,
        "chat_history": chat_history,
        "rag_chat_history": rag_chat_history,
        "units_chat_history": units_chat_history,
        "lang": "ar" if any(0x0600 <= ord(c) <= 0x06FF for c in input_text) else "en",
        "redifined_question": "",
    }
    
    final_response = None
    async for output in compiled_parent.astream(initial_state, config=config):
        if "units_output" in output:
            final_response = output["units_output"].get("bot_response")
        elif "rag_output" in output:
            final_response = output["rag_output"].get("bot_response")
    
    if not final_response:
        return {"text": "Sorry, I couldn't process your request."}
    
    # After processing, update the store.
    new_state = compiled_parent.get_state(config)
    if new_state:
        user_memory_store.put(chat_key, chat_key, new_state.values.get("chat_history", []))
        user_memory_store.put(rag_key, rag_key, new_state.values.get("rag_chat_history", []))
        user_memory_store.put(units_key, units_key, new_state.values.get("units_chat_history", []))
    
    return {"text": final_response}


async def main():
    await initialize_rag()  

if __name__ == "__main__":
    asyncio.run(main())

