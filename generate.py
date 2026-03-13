import os
from bs4 import BeautifulSoup
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings

# ---------- 配置 ----------
DOCS_PATH = "./_sources"
DB_PATH = "./chroma_db"

# Ollama 本地 embedding
embeddings = OllamaEmbeddings(model="ggml-ollama")  # 替换成本地模型名称

# ---------- 解析 HTML ----------
def parse_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
    
    # 获取标题/类名
    class_name = soup.find("h1")
    class_name = class_name.text.strip() if class_name else None

    # 提取方法名和段落
    chunks = []
    for tag in soup.find_all(["h2", "h3", "p", "pre"]):
        if tag.name in ["h2", "h3"]:  # 方法/函数名
            func_name = tag.text.strip()
            current_text = ""
        elif tag.name in ["p", "pre"]:
            current_text = tag.get_text(separator="\n").strip()
            if current_text:
                chunks.append({
                    "text": current_text,
                    "class_name": class_name,
                    "func_name": func_name if 'func_name' in locals() else None,
                    "module_path": os.path.relpath(file_path, DOCS_PATH)
                })
    return chunks

# ---------- 遍历文档 ----------
all_docs = []
for root, dirs, files in os.walk(DOCS_PATH):
    for file in files:
        if file.endswith(".html"):
            file_path = os.path.join(root, file)
            all_docs.extend(parse_html(file_path))

# ---------- 自定义 Splitter（段落 + 代码块） ----------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=50,
)

documents = []
for doc in tqdm(all_docs):
    splits = text_splitter.split_text(doc["text"])
    for split in splits:
        documents.append(Document(
            page_content=split,
            metadata={
                "class_name": doc["class_name"],
                "func_name": doc["func_name"],
                "module_path": doc["module_path"]
            }
        ))

# ---------- 存入 ChromaDB ----------
vectorstore = Chroma.from_documents(documents, embeddings, persist_directory=DB_PATH)
vectorstore.persist()
print("✅ 文档已入库")