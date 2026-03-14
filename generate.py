import os
from bs4 import BeautifulSoup
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# ---------------- 配置 ----------------
DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"
OLLAMA_EMB_MODEL = "embeddinggemma:300m-qat-q4_0"
CHUNK_SIZE = 600   # 稍微调小一点，保证 embedding 质量
CHUNK_OVERLAP = 60

embeddings = OllamaEmbeddings(model=OLLAMA_EMB_MODEL)

# ---------------- 增强版 HTML 解析 ----------------
def parse_godot_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
    
    # 移除脚本和样式，避免干扰
    for script in soup(["script", "style"]):
        script.decompose()

    # 获取类名 (通常在 <title> 或 <h1>)
    class_name = None
    h1 = soup.find("h1")
    if h1:
        class_name = h1.get_text().strip()

    # 策略：将内容按 section (h2/h3) 组合，而不是每个 p 标签一个 chunk
    # 这样能保留方法描述和代码块的关联性
    content_list = []
    current_section = ""
    current_func = "Overview"

    # 只抓取主要内容区域 (Sphinx 文档通常在 role="main" 或 class="body")
    main_content = soup.find("div", {"role": "main"}) or soup.body
    
    if main_content:
        for tag in main_content.find_all(["h2", "h3", "p", "pre", "div"]):
            if tag.name in ["h2", "h3"]:
                # 当遇到新的标题时，保存旧的内容并开始新的
                if len(current_section.strip()) > 50: # 避免存太短的碎块
                    content_list.append({
                        "text": current_section,
                        "class_name": class_name,
                        "func_name": current_func
                    })
                current_func = tag.get_text().strip()
                current_section = f"### {current_func}\n" # 保持 Markdown 风格
            elif tag.name in ["p", "pre"] or (tag.name == "div" and "highlight" in tag.get("class", [])):
                current_section += tag.get_text(separator="\n") + "\n"

        # 别忘了最后一个 section
        if current_section:
            content_list.append({
                "text": current_section,
                "class_name": class_name,
                "func_name": current_func
            })

    return content_list

# ---------------- 运行逻辑 ----------------
all_sections = []
for root, _, files in os.walk(DOCS_PATH):
    for file in files:
        if file.endswith(".html") and not file.startswith("index"):
            all_sections.extend(parse_godot_html(os.path.join(root, file)))

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n### ", "\n\n", "\n", " ", ""]
)

documents = []
for sec in tqdm(all_sections, desc="Processing Godot Docs"):
    splits = text_splitter.split_text(sec["text"])
    for split in splits:
        # 核心修正：确保这里的 Key 与你 FastAPI 检索脚本中的一致
        documents.append(Document(
            page_content=f"Class: {sec['class_name']}\nSection: {sec['func_name']}\n\n{split}",
            metadata={
                "source": os.path.basename(sec['class_name'] or "unknown"),
                "class": sec['class_name'], # 对应你 API 里的 class_name
                "method": sec['func_name']   # 对应你 API 里的 method
            }
        ))

# 清理旧数据并重新生成
if os.path.exists(DB_PATH):
    import shutil
    shutil.rmtree(DB_PATH)

vectorstore = Chroma.from_documents(
    documents=documents, 
    embedding=embeddings, 
    persist_directory=DB_PATH,
    collection_metadata={"hnsw:space": "cosine"} # 使用余弦相似度更直观
)

print(f"✅ 成功处理 {len(documents)} 个知识切片！")