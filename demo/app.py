import os
import sys
from pathlib import Path
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Add parent dir to sys.path so we can import src and ingest
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent.absolute()
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from src.store import EmbeddingStore
from src.embeddings import OPENAI_EMBEDDING_MODEL, OpenAIEmbedder
from src.chunking import FixedSizeChunker, SentenceChunker, RecursiveChunker, ChunkingStrategyComparator
from src.agent import KnowledgeBaseAgent
from ingest import load_documents, chunk_document

load_dotenv(parent_dir / ".env", override=False)

app = Flask(__name__, static_folder='static')

# Global state to hold the RAG system
class DemoState:
    def __init__(self):
        self.data_dir = parent_dir / "data" / "k3_vinuni"
        self.embedder_type = "openai"
        self.chunker_type = "fixed" # fixed, sentence, recursive
        self.chunk_size = 500
        self.overlap = 50
        self.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)
        self.chat_model = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        self.embedder = None
        self.chunker = FixedSizeChunker(chunk_size=self.chunk_size, overlap=self.overlap)
        self.store = None
        self.agent = None
        self.documents = []
        self.ready = False
        self.error = None
        self.init_system()

    def get_embedder(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or your shell environment.")
        return OpenAIEmbedder(model_name=self.embedding_model)

    def get_llm(self):
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env or your shell environment.")

        from openai import OpenAI

        client = OpenAI()

        def openai_llm(prompt: str) -> str:
            response = client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a precise RAG assistant. Answer only from the provided context. "
                            "If the context is insufficient, say the answer is not available in the knowledge base."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""

        return openai_llm
        
    def get_chunker(self):
        if self.chunker_type == "fixed":
            return FixedSizeChunker(chunk_size=self.chunk_size, overlap=self.overlap)
        elif self.chunker_type == "sentence":
            return SentenceChunker(max_sentences_per_chunk=3)
        elif self.chunker_type == "recursive":
            return RecursiveChunker(chunk_size=self.chunk_size)
        return FixedSizeChunker(chunk_size=self.chunk_size, overlap=self.overlap)

    def init_system(self):
        self.ready = False
        self.error = None
        try:
            self.embedder = self.get_embedder()
            self.chunker = self.get_chunker()
            self.documents = load_documents(self.data_dir)

            chunk_docs = []
            for doc in self.documents:
                chunk_docs.extend(chunk_document(doc, self.chunker))

            self.store = EmbeddingStore(collection_name="demo_kb", embedding_fn=self.embedder)
            self.store.add_documents(chunk_docs)
            self.agent = KnowledgeBaseAgent(store=self.store, llm_fn=self.get_llm())
            self.ready = True
        except Exception as exc:
            self.store = None
            self.agent = None
            self.error = str(exc)

state = DemoState()

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        if 'chunker_type' in data: state.chunker_type = data['chunker_type']
        if 'chunk_size' in data: state.chunk_size = int(data['chunk_size'])
        if 'overlap' in data: state.overlap = int(data['overlap'])
        
        # Re-initialize with new config
        state.init_system()
        
    return jsonify({
        "embedder_type": state.embedder_type,
        "embedding_model": state.embedding_model,
        "chat_model": state.chat_model,
        "chunker_type": state.chunker_type,
        "chunk_size": state.chunk_size,
        "overlap": state.overlap,
        "store_size": state.store.get_collection_size() if state.store else 0,
        "document_count": len(state.documents),
        "ready": state.ready,
        "error": state.error
    })

@app.route('/api/documents', methods=['GET'])
def get_documents():
    docs = [{"id": d.id, "metadata": d.metadata, "content_preview": d.content[:150] + "..."} for d in state.documents]
    return jsonify({"documents": docs})

@app.route('/api/query', methods=['POST'])
def search_query():
    if not state.ready:
        return jsonify({"error": state.error or "RAG system is not ready"}), 503

    data = request.json
    query = data.get('query', '')
    top_k = int(data.get('top_k', 3))
    metadata_filter = data.get('filter', None)
    
    if metadata_filter and not any(metadata_filter.values()):
        metadata_filter = None
    elif metadata_filter:
        metadata_filter = {k: v for k, v in metadata_filter.items() if v}
        
    try:
        results = state.store.search_with_filter(query, top_k=top_k, metadata_filter=metadata_filter)
        return jsonify({"results": results})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

@app.route('/api/chat', methods=['POST'])
def chat():
    if not state.ready:
        return jsonify({"error": state.error or "RAG system is not ready"}), 503

    data = request.json
    question = data.get('question', '')
    top_k = int(data.get('top_k', 3))
    
    try:
        results = state.store.search(question, top_k=top_k)
        answer = state.agent.answer(question, top_k=top_k)
        return jsonify({
            "answer": answer,
            "sources": results
        })
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

@app.route('/api/compare', methods=['POST'])
def compare_chunking():
    data = request.json
    text = data.get('text', '')
    chunk_size = int(data.get('chunk_size', 200))
    
    comparator = ChunkingStrategyComparator()
    comparison = comparator.compare(text, chunk_size=chunk_size)
    return jsonify(comparison)

if __name__ == '__main__':
    # Ensure data directory exists
    if not state.data_dir.exists():
        print(f"Warning: Data directory {state.data_dir} does not exist. Creating it.")
        state.data_dir.mkdir(parents=True, exist_ok=True)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
