from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Depends, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import uvicorn
from contextlib import asynccontextmanager
import os
import uuid
from langchain_core.messages import HumanMessage, AIMessage
from core import settings
from routers import user_memory_store, get_memory_key, chatbot_interface
from routers import global_rag_chatbot
from routers import initialize_rag

# Define your API key (in production, load this securely from environment variables or a secrets vault)
API_KEY = settings.APP_API_KEY

def verify_api_key(app_api_key: str = Header(...)):
    """
    Dependency function to verify the API key sent in the request header.
    """
    if app_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return app_api_key

# Initialize the RAG chatbot
async def initialize_chatbot():
    await initialize_rag()  


# Data Models
class ChatRequest(BaseModel):
    user_id: str
    input: str
    chat_history: Optional[List[dict]] = Field(
        default=None,
        description="""
A list of messages. Each message is a dict with:
- **role**: "user" or "ai"
- **content**: The text content of the message
"""
    )
    return_history: bool = Field(
        default=False,
        description="Set to True if you want the endpoint to return the chat history in the response."
    )

class Message(BaseModel):
    role: str
    content: str

class ChatResponse(BaseModel):
    text: str
    need_history: bool = False
    chat_history: Optional[List[Message]] = None

def serialize_history(messages: List) -> List[Message]:
    serialized = []
    for msg in messages:
        if isinstance(msg, dict):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
        elif isinstance(msg, HumanMessage):
            role = "user"
            content = msg.content
        elif isinstance(msg, AIMessage):
            role = "ai"
            content = msg.content
        else:
            role = "unknown"
            content = str(msg)
        serialized.append(Message(role=role, content=content))
    return serialized

# Run initialization at startup (this runs before the app is created)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await initialize_chatbot()
    yield
    # Shutdown (optional)
    print("Shutting down...")

# initialize the FastAPI app
app = FastAPI(
    title="Wzgate Chatbot API",
    version="1.2",
    lifespan=lifespan,
    description="""
**Wzgate Chatbot**

This application serves as the central orchestrator for a real estate chatbot, efficiently managing user interactions by directing them to specialized subcomponents.

**Architecture Overview:**

- **Main Graph:** Acts as the parent structure, encompassing all functionalities and routing mechanisms.
- **Retrieval-Augmented Generation (RAG) Subgraph:** Integrates external real estate data to provide users with accurate and contextually relevant information.
- **UNITS Subgraph:** Manages functionalities related to real estate units, including property listings, availability, and detailed unit information.

**Operational Flow:**

1. **Input Handling:** The main graph receives and analyzes user inputs.
2. **Routing:** Based on the analysis, inputs are directed to the appropriate subgraph (either RAG or UNITS).
3. **Processing:** The selected subgraph processes the input and generates a response.
4. **Output Delivery:** The main graph routes the subgraph's output to the END node, delivering the final response to the user.

This modular design ensures that user queries are addressed efficiently and accurately, leveraging specialized subgraphs for optimal performance.
"""
)


# --------------------- Endpoint 1: Chatbot Endpoint ---------------------
@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest, api_key: str = Depends(verify_api_key)):
    """
    Processes a chat request.

    **Request Body:**
    - **user_id**: A unique identifier for the user.
    - **input**: The user's message.
    - **chat_history (optional)**: A list of dictionaries, where each dictionary represents a message with:
      - **role**: Must be either "user" or "ai".
      - **content**: The message text.
    - **return_history** (bool, optional): Set to True to include the updated chat history in the response.

      
    **Response:**
    - **text**: The chatbot's reply.
    - **need_history**: A flag indicating if the chat history is required.
    - **chat_history**: The updated chat history (returned only if 'return_history' is True).

    **Authentication:** Requires a valid API key in the 'app-api-key' header.
    """
    if not request.input:
        raise HTTPException(status_code=400, detail="Input message is required")
    if not request.user_id:
        raise HTTPException(status_code=400, detail="User ID is required")
    
    chat_key = get_memory_key(request.user_id, "chat_history")
    
    # If the user sends an empty chat_history list, delete their existing chat history.
    if request.chat_history == []:
        await user_memory_store.adelete(chat_key, chat_key)  # Delete existing history if it exists
        await user_memory_store.adelete(get_memory_key(request.user_id, "rag_chat_history"), get_memory_key(request.user_id, "rag_chat_history"))  # Delete existing history if it exists
        await user_memory_store.adelete(get_memory_key(request.user_id, "units_chat_history"), get_memory_key(request.user_id, "units_chat_history"))  # Delete existing history if it exists
        
    # Check if history exists.
    chat_history_mem = await user_memory_store.aget(chat_key, chat_key)
    need_history = chat_history_mem is None
    if need_history and request.chat_history:
        messages = []
        for m in request.chat_history:
            if m.get("role") == "user":
                messages.append(HumanMessage(content=m.get("content")))
            elif m.get("role") == "ai":
                messages.append(AIMessage(content=m.get("content")))
        user_memory_store.put(chat_key, chat_key, messages)
    
    try:
        result = await chatbot_interface(request.input, request.user_id, request.chat_history or [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {e}")
    
    bot_response = result.get("text", "Sorry, no response generated.")

    history_payload = None
    if request.return_history:
            if chat_history_mem:
                history_payload = serialize_history(chat_history_mem.value)
        
        
    return ChatResponse(text=bot_response, need_history=need_history, chat_history=history_payload)


# --- Endpoint 2: Upload DOCX File to Update Vector Store ---------------------------------------------------------------------
@app.post("/upload", response_model=dict)
async def upload_file(file: UploadFile = File(...), api_key: str = Depends(verify_api_key)):
    """
    Updates the vector store using an uploaded DOCX file.

    **Request:**
    - **file**: A DOCX file sent via form-data.

    **Response:**
    - **message**: A confirmation message.

    **Authentication:** Requires a valid API key in the 'x-api-key' header.
    """
    # Create a temporary directory to store the uploaded file.
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Generate a unique filename to avoid collisions.
    file_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(temp_dir, file_name)
    
    try:
        # Save the uploaded file to the temporary location.
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Call the RAG subgraph function to update the vector store with the new DOCX.
        await global_rag_chatbot.update_vector_store_with_docx(file_path)
        response_message = f"FAISS index updated and saved to {settings.FAISS_INDEX_PATH}."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File processing error: {e}")
    finally:
        # Remove the temporary file to avoid storage buildup.
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return JSONResponse(content={"message": response_message})

# --- Endpoint 3: Get Vector Store File Info ---
@app.get("/vector_store_info", response_model=dict)
async def get_vector_store_info(api_key: str = Depends(verify_api_key)):
    """      
    Retrieves information about the vector store.

    **Response:**
    - **num_files**: Number of files in the vector store.
    - **filenames**: A list of filenames in the vector store.

    **Authentication:** Requires a valid API key in the 'x-api-key' header.
    
    """
    try:
        num_files, filenames = await global_rag_chatbot.get_vector_store_file_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving vector store info: {e}")
    return JSONResponse(content={"num_files": num_files, "filenames": filenames})


# --- Endpoint 4: Create New Vector Store from Drive ---------------------------------------------------------------------

@app.post("/create_vector_store_from_drive", response_model=dict)
async def create_vector_store_from_drive(drive_link: str = Form(...), credentials_file: UploadFile = File(...), api_key: str = Depends(verify_api_key),background_tasks: BackgroundTasks = BackgroundTasks):
    """
    Creates a new vector store from files in a specified Google Drive folder.

    **Request (form-data):**
    - **drive_link**: A URL to the Google Drive folder.
    - **credentials_file**: A JSON file containing service account credentials.
    
    **How to Create Your Credentials File for Google Drive:**
        1. **Go to the Google Cloud Console**  
        Visit [console.cloud.google.com](https://console.cloud.google.com/) and select or create a new project.
        2. **Enable the Drive API**  
        In your project, go to **APIs & Services** → **Library**, then search for and enable the **Google Drive API**.
        3. **Create a Service Account**  
        Navigate to **APIs & Services** → **Credentials**, click **Create Credentials** → **Service Account**, and follow the prompts.
        4. **Generate a Key**  
        Once your service account is created, click on it. Under **Keys**, click **Add Key** → **Create new key** → **JSON**. A JSON file with your credentials will download.
        5. **Grant Access**  
        Share the target Google Drive folder with your service account’s email address to allow it to access the files.

    **Response:**
    - **message**: A confirmation message indicating the creation of the new FAISS index.

    **Authentication:** Requires a valid API key in the 'x-api-key' header.
    """
    # Create a temporary directory to store the credentials file.
    temp_dir = "temp_creds"
    os.makedirs(temp_dir, exist_ok=True)
    creds_file_name = f"{uuid.uuid4()}_{credentials_file.filename}"
    creds_file_path = os.path.join(temp_dir, creds_file_name)
    
    try:
        with open(creds_file_path, "wb") as f:
            content = await credentials_file.read()
            f.write(content)
        
        # Call the function to create a new vector store from the drive.
        # await global_rag_chatbot.create_new_vector_store_from_drive(drive_link, creds_file_path)
        # make it a background task to avoid timeout
        background_tasks.add_task(
        global_rag_chatbot.create_new_vector_store_from_drive,
        drive_link,
        creds_file_path
        )
        response_message = "New FAISS index created from drive and saved."
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating new vector store: {e}")
    
    return JSONResponse(content={"message": "Task scheduled. Processing in background."})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
