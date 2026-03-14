from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
import traceback

app = FastAPI(
    title="Godot4 Document Retriever",
    description="RAG service for Godot 4 official documentation",
    version="1.0"
)

# ---------------- 配置 ----------------

DB_PATH = "./chroma_db"
EMB_MODEL = "embeddinggemma:300m-qat-q4_0"

# ---------------- 初始化 ----------------

embeddings = OllamaEmbeddings(model=EMB_MODEL)

vectorstore = Chroma(
    persist_directory=DB_PATH,
    embedding_function=embeddings
)

# ---------------- 数据模型 ----------------

class QueryRequest(BaseModel):

    prompt: str = Field(
        ...,
        description="Godot 4 technical question or API keyword"
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of retrieved documents"
    )


class DocumentResponse(BaseModel):

    content: str
    source: Optional[str] = None
    class_name: Optional[str] = None
    method: Optional[str] = None
    score: float


# ---------------- API ----------------

@app.post(
    "/retrieve",
    response_model=List[DocumentResponse],
    summary="Retrieve Godot documentation chunks"
)
async def retrieve_docs(request: QueryRequest):

    try:

        test_emb = embeddings.embed_query("test")
        print(f"Embedding type: {type(test_emb)}, Length: {len(test_emb)}")


        print(f"\nQuery: {request.prompt}")
        print(f"TopK: {request.top_k}")

        # 向量搜索
        results = vectorstore.similarity_search_with_score(
            request.prompt,
            k=request.top_k
        )

        docs = []

        for doc, score in results:

            docs.append(
                DocumentResponse(
                    content=doc.page_content,
                    source=doc.metadata.get("source"),
                    class_name=doc.metadata.get("class"),
                    method=doc.metadata.get("method"),
                    score=float(score)
                )
            )

        print(f"Returned docs: {len(docs)}")

        print(docs)

        return docs

    except Exception as e:
            traceback.print_exc() # 这会在终端打印详细的错误路径
            raise HTTPException(status_code=500, detail=str(e)
        )


# ---------------- 健康检查 ----------------

@app.get("/health")
def health_check():

    return {
        "status": "ok",
        "vector_db": DB_PATH,
        "embedding_model": EMB_MODEL
    }


# ---------------- 启动 ----------------

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )