import os
import torch
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

def build_vectorstore_from_pdfs(pdf_folder: str = "DATA", save_path: str = "vectorstore"):
    all_docs = []
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- Working on: {device.upper()} ---")

    if not os.path.exists(pdf_folder):
        print(f"❌ Folder '{pdf_folder}' not found. Please create it and add PDFs.")
        return

    # 1.PDF
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"⚠️ No PDF files found in '{pdf_folder}'.")
        return

    print(f"📚 Found {len(pdf_files)} PDF file(s). Processing...")
    for filename in pdf_files:
        loader = PyPDFLoader(os.path.join(pdf_folder, filename))
        docs = loader.load()
        all_docs.extend(docs)

    # 2. (Chunks)
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(all_docs)
    print(f"✂️ Created {len(chunks)} text chunks.")

    # 3. 
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': device}
    )

    # 4.Vectorstore
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(save_path)
    print(f"✅ Vector store saved successfully to: '{save_path}'")

if __name__ == "__main__":
    build_vectorstore_from_pdfs()