# Advanced Modular Real Estate Chatbot

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Architecture](#architecture)
   - [Main Graph](#main-graph)
   - [UNITS Subgraph](#units-subgraph)
   - [RAG Subgraph](#rag-subgraph)
4. [Installation & Setup](#installation--setup)
5. [Usage](#usage)

---

## Overview

This repository contains an **Advanced Modular Real Estate Chatbot** designed and developed by **iSemantics-ai** for **Wzgate**. It handles both property-specific inquiries and broader real estate questions. Leveraging state-of-the-art Large Language Models (LLMs) and a FAISS vector store for context retrieval, the chatbot intelligently routes user queries between two specialized subgraphs:

- **UNITS Subgraph:** Manages property-specific interactions (e.g., requesting location, budget, bedrooms).
- **RAG Subgraph:** Addresses general real estate questions using retrieval-augmented generation (RAG) with external document search.

By combining asynchronous state graphs, memory management, and retrieval-based techniques, this system delivers nuanced, context-rich answers.

---

## Key Features

1. **Dual-Routing System**\
   A classifier LLM analyzes the user’s query and routes it to:

   - **UNITS** (property-specific requirements), or
   - **RAG** (general real estate questions).

2. **Modular Architecture**\
   Implemented with **LangGraph**, allowing each subgraph (UNITS and RAG) to be independently updated or replaced.

3. **Advanced Retrieval Mechanism**\
   A **FAISS** vector store is used for fast, context-based searches. Documents are chunked and embedded for efficient retrieval.

4. **Persistent Conversation Memory**\
   Memory is stored per user, maintaining conversation context and preventing data leakage.

5. **Asynchronous Design**\
   Node execution and LLM calls run asynchronously, improving performance and responsiveness.

6. **Enhanced Observability**\
   Integrates logging, debugging, and support for advanced monitoring (e.g., via LangSmith).

---

## Architecture

### Main Graph

- **Role:** The orchestrator that classifies queries and routes them to the appropriate subgraph (UNITS or RAG).
- **Functions:**
  - **Classifier LLM:** Decides if the user question is property-specific or more general.
  - **Adapter Nodes:** Converts parent graph state into subgraph-friendly data structures and vice versa.

### UNITS Subgraph

- **Focus:** Handles property-specific conversations.
- **Key Nodes:**
  1. **language:** Detects language and greets the user if the conversation is starting.
  2. **conversation:** Manages back-and-forth Q&A for property requirements.
  3. **completion & check\_complete:** Determines if enough info has been collected to summarize.
  4. **branch:** Either extracts final property details or prompts the user for additional info.

### RAG Subgraph

- **Focus:** Addresses broader real estate questions using retrieval-augmented generation.
- **Key Nodes:**
  1. **retrieve\_context:** Uses a refined query to retrieve relevant documents from the FAISS index.
  2. **generate\_answer:** Builds a final LLM prompt including the user’s question, conversation history, and retrieved documents, then generates a response.

---

## Installation & Setup

1. **Clone the Repository:**

   ```bash
   git clone https://github.com/iSemantics-ai/Wzgate-Chatbot.git
   ```

2. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

   Ensure Python 3.9+ (or the version specified in `requirements.txt`).

3. **Configure Environment:**

   - Set environment variables (e.g. `OPENAI_API_KEY`) in your shell or a `.env` file.
   - Adjust settings in `core/settings.py` to match your environment (model names, FAISS index paths, etc.).

4. **Initialize or Load FAISS Index:**

   - If needed, call `initialize_chatbot()` (in `RAG_subgraph.py`) or run the relevant code to build the FAISS index from your documents.

---

## Usage

1. **Running the Chatbot:**

   - Integrate `chatbot_interface` from **main\_graph** into your server (e.g. FastAPI or Streamlit).
   - Provide user inputs, user IDs, and optional conversation history.

2. **Property Queries (UNITS):**

   - Focus on property-specific info (location, budget, bedrooms).
   - The classifier automatically directs these to the UNITS subgraph.

3. **General Questions (RAG):**

   - For broad real estate questions, the classifier routes them to RAG for context retrieval.



All rights are reserved by **iSemantics-ai**. This project is provided for Wzgate under the conditions that all copyrights belong to **iSemantics-ai**.

---

**Thank you for exploring the Advanced Modular Real Estate Chatbot!**\
Feel free to open an issue or a pull request if you have questions or suggestions.

