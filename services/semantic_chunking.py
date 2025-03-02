"""
this service is responsible for chunking the text into Semantic parts for processing and embedding
and saving the documents into a json file to be used by the faiss index service
"""
import os
import re
import json
from langchain_experimental.text_splitter import SemanticChunker
from langchain_community.document_loaders import Docx2txtLoader
# from langchain_community.embeddings import OpenAIEmbeddings
from core import settings
import asyncio
from langchain_openai import OpenAIEmbeddings
#--- Define the SemanticChunkingService class ---
class SemanticChunkingService:
    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY, model=settings.EMBEDDING_MODEL)
        self.chunker = SemanticChunker(self.embeddings_model, 
                                       breakpoint_threshold_type="gradient", 
                                       breakpoint_threshold_amount=settings.BREAKPOINT_THRESHOLD,
                                       number_of_chunks=None,
                                       min_chunk_size=settings.MIN_CHUNK_SIZE)

    def clean_text(self, text):
        """Clean text by removing non-printable characters and normalizing whitespace."""
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def process_file(self,filepath):
        """ Process a single file to calculate chunks and create documents. """
        loader = Docx2txtLoader(filepath)
        raw_docs = loader.load()
        full_text = "\n".join([doc.page_content for doc in raw_docs])

        word_count = len(full_text.split())
        avg_chunk_size = 80  # words
        n_chunks = max(1, word_count // avg_chunk_size)
        print(f"Processing {filepath} with {word_count} words and {n_chunks} chunks.")

        self.chunker.number_of_chunks = n_chunks
        filename = os.path.basename(filepath).split(".")[0]#[:-5]
        documents = self.chunker.create_documents([full_text], metadatas=[{"filename": filename}])
        for doc in documents:
            doc.page_content = self.clean_text(doc.page_content)  
            # add metadata into page content
            doc.page_content = f"this data is from {doc.metadata['filename']} source and the content is {doc.page_content}"
        return documents
    

    async def process_directory(self,directory):
            """ Process each DOCX file in the directory asynchronously. """
            tasks = [asyncio.to_thread(self.process_file, os.path.join(directory, filename))
                    for filename in os.listdir(directory) if filename.endswith('.docx')]
            documents_lists = await asyncio.gather(*tasks)
            all_documents = [doc for sublist in documents_lists for doc in sublist]  # Flatten
            return all_documents
    
    async def process_directory(self,directory):
            """ Process each DOCX file in the directory asynchronously. """
            tasks = [asyncio.to_thread(self.process_file, os.path.join(directory, filename))
                    for filename in os.listdir(directory) if filename.endswith('.docx')]
            documents_lists = await asyncio.gather(*tasks)
            all_documents = [doc for sublist in documents_lists for doc in sublist]  # Flatten
            return all_documents
        
    def save_documents_to_json(self,documents, filename):                                    
        """ Save a list of Document objects to a JSON file. """
        docs_dict = [{'content': doc.page_content, 'metadata': doc.metadata} for doc in documents]
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(docs_dict, f, indent=4, ensure_ascii=False)
