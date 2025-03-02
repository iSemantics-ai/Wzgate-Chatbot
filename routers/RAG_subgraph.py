"""
this file contains the RAG subgraph that is used to generate answers to user questions based on a given context.
RAG subgraph is a sequence of two nodes:
1. retrieve_context: Extracts context from the vector store.
2. generate_answer: Generates an answer using the retrieved context.
and returns the final state upon reaching END.
"""
import asyncio
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_openai.chat_models import ChatOpenAI
from core import settings
import tempfile
import os
import io
import re
import shutil
from services import SemanticChunkingService
from services import FAISSIndexService
from format import  get_system_prompt_rag, get_redefined_question_prompt 
from langchain.docstore.document import Document
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload


async def download_docx_files_from_drive(
    drive_link: str, 
    credentials_file: str, 
    download_dir: str = None
) -> List[str]:
    """
    Asynchronously downloads all DOCX files from a Google Drive folder.
    
    Parameters:
        drive_link (str): Google Drive folder URL (e.g., 
            "https://drive.google.com/drive/folders/<folder_id>").
        credentials_file (str): Path to your service account credentials JSON file.
        download_dir (str, optional): Local directory where files will be saved.
            If None, a temporary directory is created.
    
    Returns:
        List[str]: A list of local file paths for the downloaded DOCX files.
    """
    
    def sync_download() -> List[str]:
        match = re.search(r'folders/([a-zA-Z0-9_-]+)', drive_link)
        if not match:
            raise ValueError("Invalid drive folder link format.")
        folder_id = match.group(1)
        
        local_dir = download_dir or tempfile.mkdtemp()
        
        # Set up credentials and build the Drive service.
        scopes = ['https://www.googleapis.com/auth/drive.readonly']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        service = build('drive', 'v3', credentials=creds)
        
        # Query for DOCX files in the folder.
        query = (
            f"'{folder_id}' in parents and "
            "mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'"
        )
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        
        downloaded_paths = []
        for file in files:
            file_id = file.get('id')
            file_name = file.get('name')
            local_path = os.path.join(local_dir, file_name)
            
            request = service.files().get_media(fileId=file_id)
            with io.FileIO(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    print(f"Downloading {file_name}: {int(status.progress() * 100)}%.")
            
            downloaded_paths.append(local_path)
        
        return downloaded_paths

    # Offload the synchronous download operation to a separate thread.
    return await asyncio.to_thread(sync_download)

# ------- RAGChatbot Class (for setup and chain creation)
# --------------------------------------------------------------------------

class RAGChatbot:
    def __init__(self):
        # Initialize the semantic chunking and FAISS services.
        self.semantic_service = SemanticChunkingService()
        self.faiss_service = FAISSIndexService()
        
        # Initialize the LLM models for the RAG chatbot.
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.5
        )
        self.llm_refined_query = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.2
        )
        self.vector_store = None


    async def setup(self, directory_path: str):
        """Process documents, create/load the FAISS index, and initialize retrieval."""
        import os

        if not os.path.exists(settings.FAISS_INDEX_PATH):
            print("🔍 Creating FAISS index...")
            documents = await self.semantic_service.process_directory(directory_path)
            print(f"📄 Processed {len(documents)} documents.")
            if not documents:
                print("❌ No documents found! Check your directory path.")
                return
            self.semantic_service.save_documents_to_json(documents, directory_path + ".json")
            await self.faiss_service.create_faiss_index(documents)
            self.vector_store = self.faiss_service.vector_store


        else:
            print("📥 Loading FAISS index...")
            self.vector_store = self.faiss_service.load_index()

        print("✅ FAISS index ready.")

    async def update_vector_store_with_docx(self,file_path: str):
        # Process the DOCX file asynchronously to produce Document objects.
            new_documents = await asyncio.to_thread(self.semantic_service.process_file, file_path)
            
            print(" 📩 Updating existing FAISS index with new document...")
            texts = [doc.page_content for doc in new_documents]
            metadatas = [doc.metadata for doc in new_documents]
            await self.vector_store.aadd_texts(texts, metadatas=metadatas)
            self.vector_store.save_local(settings.FAISS_INDEX_PATH)
            print(f"FAISS index updated and saved to {settings.FAISS_INDEX_PATH}.")    

    async def get_vector_store_file_info(self) -> tuple[int, list[str]]:
        """
        function to get the number of unique files in the vector store and their filenames.
        Returns:
        Count the unique files in the vector store and return a tuple:
        (number_of_unique_files, list_of_file_names)
        based on the 'filename' key in each document's metadata.
        """
        if self.vector_store is None:
            print("Vector store is not initialized.")
            return 0, []
        
        try:
            docs = await asyncio.to_thread(lambda: list(self.vector_store.docstore._dict.values()))
        except AttributeError:
            print("Vector store does not expose a 'docstore' attribute.")
            return 0, []
        
        filenames = []
        for doc in docs:
            metadata = getattr(doc, "metadata", {})
            if "filename" in metadata:
                filenames.append(metadata["filename"])
        
        unique_filenames = list(set(filenames))
        return len(unique_filenames), unique_filenames
    
    
    async def create_new_vector_store_from_drive(self, drive_link: str, credentials_file: str):
        """
        function to create a new vector store from the files in the Google Drive folder specified by the drive_link.
        Asynchronously downloads DOCX files from the provided Google Drive folder link,
        processes each file to perform semantic chunking, deletes any existing FAISS index,
        and then creates a completely new FAISS vector store from the processed documents.
        
        Parameters:
            drive_link (str): The URL of the Google Drive folder.
            credentials_file (str): Path to your service account credentials JSON file.
        """
        #Download DOCX files from the drive.
        docx_paths = await download_docx_files_from_drive(drive_link, credentials_file)
        if not docx_paths:
            print("No DOCX files found at the provided drive link.")
            return

        #Process each DOCX file concurrently (perform semantic chunking service)
        tasks = [
            asyncio.to_thread(self.semantic_service.process_file, file_path)
            for file_path in docx_paths
        ]
        results = await asyncio.gather(*tasks)
        # Flatten the list of lists into one list of Document objects
        new_documents = [doc for docs in results for doc in docs]
        if not new_documents:
            print("No documents were processed from the downloaded files.")
            return

        # Delete any existing FAISS index folder to start fresh
        if os.path.exists(settings.FAISS_INDEX_PATH):
            shutil.rmtree(settings.FAISS_INDEX_PATH)
            print(f"Deleted existing FAISS index at {settings.FAISS_INDEX_PATH}.")

        #Create a new FAISS index using the processed documents
        await self.faiss_service.create_faiss_index(new_documents)
        self.vector_store = self.faiss_service.vector_store
        print(f"New FAISS index created and saved to {settings.FAISS_INDEX_PATH}.")
        

# Initialize the global RAG chatbot instance.
global_rag_chatbot = RAGChatbot()

# --- Define the RAG Subgraph State 
# --------------------------------------------------------------------------
class RAGChatbotState(TypedDict):
    question: str
    redifined_question: str | None
    context: List[Document]  # List of retrieved Document objects.
    answer: str | None
    chat_history: list   # General conversation history
    rag_chat_history: list    # RAG-specific conversation history 
    bot_response: str | None
    lang: str | None

# Node: generate context query
# --- Define generate context query Node 
# --------------------------------------------------------------------------
async def generate_context_query(state: RAGChatbotState) -> str:
    """
    Function to Generate a concise, refined query that encapsulates both the current question
    and the key points from the conversation history. This query will then be used
    to retrieve context from the vector store.
    """
    # Combine the conversation history into a single string.
    if state.get("rag_chat_history"):
        last_messages = state["rag_chat_history"][-10:]
        history_str = "\n".join(
            f'{msg["role"]}: {msg["content"]}'
            if isinstance(msg, dict) and "role" in msg and "content" in msg
            else str(msg)
            for msg in last_messages
        )
    else:
        history_str = "No previous history."

    # Generate a refined query based on the conversation history and the current question to make it more specific.
    prompt = get_redefined_question_prompt(history_str,state['question'])
    response = await asyncio.to_thread(global_rag_chatbot.llm_refined_query.invoke, prompt)
    state['redifined_question'] = response.content.strip()

    return state['redifined_question']


# Node: retrieve context
# --- Define retrieve context Node 
# --------------------------------------------------------------------------
async def retrieve_context(state: RAGChatbotState) -> RAGChatbotState:
    """
    Function to retrieve context from the FAISS vector store using a refined query that is
    generated based on both the current question and the conversation history.
    """
    if "rag_chat_history" not in state:
        state["rag_chat_history"] = []  

    # Append the current question to the RAG-specific chat history.
    state["rag_chat_history"].append({"role": "user", "content":state["question"]})

    if global_rag_chatbot.vector_store is None:
        state["context"] = []  
    else:
        # First, generate a refined retrieval query based on the conversation history.
        refined_query = await generate_context_query(state)
                
        # Use the refined query to search the vector store.
        docs_retrieved = global_rag_chatbot.vector_store.similarity_search(refined_query, k=10)
        
        # Update the state with the retrieved context.
        state["context"] = docs_retrieved
        
        # Also update the overall chat history.
        state["chat_history"].append({"role": "user", "content": state["question"]})
    
    return state


# Node: generate answer
# --- Define the RAG Subgraph Nodes ---
async def generate_answer(state: RAGChatbotState) -> RAGChatbotState:
    """
    This node builds a prompt using the retrieved context and the question.
    It then calls the LLM to generate an answer.
    The answer is stored in the 'answer' field and also as 'bot_response'.
    """
    if state.get("context"):
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
    else:
        docs_content = "No context was retrieved."

    if state.get("rag_chat_history"):
        last_messages = state["rag_chat_history"][-10:]
        history_str = "\n".join(
            f'{msg["role"]}: {msg["content"]}'
            if isinstance(msg, dict) and "role" in msg and "content" in msg
            else str(msg)
            for msg in last_messages
        )
    else:
        history_str = "No previous history."

    # RAG prompt based on language that includes the system prompt, the question, and the context and also the history
  
    prompt_text = get_system_prompt_rag(state['lang'], state['question'],docs_content,history_str,state.get('redifined_question', '')) 
    response = await asyncio.to_thread(global_rag_chatbot.llm.invoke, prompt_text)
    state["answer"] = response.content
    state["bot_response"] = response.content
    state["chat_history"].append({"role": "ai", "content": response.content})
    state["rag_chat_history"].append({"role": "ai", "content": response.content})
    return state

# --- Compile the RAG Chatbot Subgraph ---
def compile_rag_chatbot_graph() -> StateGraph:
    """
    The subgraph is built as a sequence of two nodes:
    1. retrieve_context: Extracts context from the vector store.
    2. generate_answer: Generates an answer using the retrieved context.
    """
    # Create a graph that passes the state through both nodes in sequence.
    graph = StateGraph(RAGChatbotState)
    # Here we add the nodes in sequence.
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_answer", generate_answer)
    # Set the entry point to "retrieve_context".
    graph.set_entry_point("retrieve_context")
    # Connect retrieve_context to generate_answer.
    graph.add_edge("retrieve_context", "generate_answer")
    # Connect generate_answer to END.
    graph.add_edge("generate_answer", END)
    return graph.compile()

# --- RAGChatbotGraph Class ---
class RAGChatbotGraph:
    def __init__(self):
        self.compiled_graph = compile_rag_chatbot_graph()

    async def run(self, state: RAGChatbotState) -> RAGChatbotState:
        async for output in self.compiled_graph.astream(state):
            final_state = output  # Final state upon reaching END.
        return final_state

# --- RAG Interface ---
async def rag_interface(question: str, user_id: str, history: Optional[List[dict]] = None) -> dict:
    from main_graph import user_memory_store, get_memory_key

    # Build unique keys for chat history and rag-specific history.
    chat_key = get_memory_key(user_id, "chat_history")
    rag_key = get_memory_key(user_id, "rag_chat_history")
    
    # Retrieve stored histories.
    stored_chat = user_memory_store.get(chat_key, chat_key)
    stored_rag = user_memory_store.get(rag_key, rag_key)
    chat_history = stored_chat.value if stored_chat else []
    rag_chat_history = stored_rag.value if stored_rag else []
    
    if not chat_history and history:
        for m in history:
            if m.get("role") == "user":
                chat_history.append(HumanMessage(content=m.get("content")))
            elif m.get("role") == "ai":
                chat_history.append(AIMessage(content=m.get("content")))
    
    # Build the initial state for the RAG subgraph.
    state = {
        "question": question,
        "redifined_question": None,
        "context": [],
        "answer": None,
        "chat_history": chat_history,
        "rag_chat_history": rag_chat_history,
        "bot_response": None,
        "lang": "ar" if any(0x0600 <= ord(c) <= 0x06FF for c in question) else "en"
    }
    
    # Run the RAG subgraph.
    final_state = await RAGChatbotGraph().run(state)
    
    # Update the store with the new conversation histories.
    user_memory_store.put(chat_key, chat_key, final_state.get("chat_history", []))
    user_memory_store.put(rag_key, rag_key, final_state.get("rag_chat_history", []))
    
    # Return the answer (bot_response) and the updated chat history.
    return {
        "text": final_state.get("bot_response", "No response generated."),
        "chat_history": final_state.get("chat_history", [])
    }

# --- RAG Interface (Synchronous Wrapper) ---
def sync_rag_interface(question: str, user_id: str, history: Optional[List[dict]] = None):
    return asyncio.run(rag_interface(question, user_id, history))
    
# --- Initialize the RAG Chatbot ---
async def initialize_chatbot():
    await global_rag_chatbot.setup(settings.SOURCE_DATA)
    print(" 📚 RAG chatbot initialized.")