import os
import time
import uuid
import re
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer

import pprint

# ---------------- 配置 ----------------
DOCS_PATH = "./docs"
DB_PATH = "./chroma_db"

MODEL_NAME = r"D:\workspace\huggingface\models\google\embeddinggemma-300m"

CHUNK_SIZE = 600
CHUNK_OVERLAP = 60
BATCH_SIZE = 256


# ---------------- RST 清洗 ----------------
def clean_rst(text):

    # rst anchor
    text = re.sub(r"\.\.\s_[^:]+:", "", text)

    # rst directive
    text = re.sub(r"\.\.\s.*", "", text)

    # :ref:
    text = re.sub(r":ref:`([^`]+)`", r"\1", text)

    # rst link
    text = re.sub(r"`([^`]+)`__", r"\1", text)

    # HTML
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.S)
    text = re.sub(r"<.*?>", "", text)

    # RST table cleanup
    text = re.sub(r"\|[-=+]+\|", "", text)
    text = re.sub(r"^[\|\+\-\s]+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)

    # 多空行
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)

    return text.strip()


# ---------------- RST 解析 ----------------
def parse_godot_rst(file_path):

    path = file_path.replace("\\","/")

    if "classes/" in path:
        doc_type = "api"
    elif "tutorials/" in path:
        doc_type = "tutorial"
    else:
        doc_type = "docs"


    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        class_name = "Unknown"
        filename = os.path.basename(file_path)

        # class 文档识别
        if filename.startswith("class_"):
            class_name = filename.replace("class_", "").replace(".rst.txt", "").capitalize()

        sections = []
        current_section = ""
        current_title = "Overview"


        INVALID_TITLES = [
            "Page not found",
            "Search",
        ]

        for i, line in enumerate(lines):

            if i + 1 < len(lines):

                next_line = lines[i + 1].strip()

                # RST 标题检测
                if set(next_line) in [{"="}, {"-"}, {"~"}, {"^"}] and len(next_line) > 3:
                    new_title = line.strip()

                    # 过滤无效页面
                    if any(x.lower() in new_title.lower() for x in INVALID_TITLES):
                        return []

                    if len(current_section.strip()) > 50:

                        clean_text = clean_rst(current_section)
                        if len(clean_text) < 80:
                            continue

                        sections.append({
                            "text": clean_rst(current_section),
                            "class": class_name,
                            "func": current_title,
                            "type": doc_type
                        })

                    current_title = line.strip()
                    current_section = ""
                    continue

            current_section += line

        if len(current_section.strip()) > 50:
            sections.append({
                "text": clean_rst(current_section),
                "class": class_name,
                "func": current_title,
                "type": doc_type
            })

        return sections

    except:
        return []


def worker(file_info):
    return parse_godot_rst(os.path.join(file_info[0], file_info[1]))


# ---------------- 主程序 ----------------
if __name__ == "__main__":

    start_time = time.time()

    # 1. CPU 并行解析
    file_tasks = [
        (r, f)
        for r, _, fs in os.walk(DOCS_PATH)
        for f in fs
        if f.endswith(".txt") and not f.startswith("index")
    ]

    all_sections = []

    with ProcessPoolExecutor() as executor:
        results = list(
            tqdm(
                executor.map(worker, file_tasks),
                total=len(file_tasks),
                desc="Parsing RST"
            )
        )

        all_sections = [item for sublist in results for item in sublist]

    # 2. 文本切分
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    final_texts = []
    final_metas = []

    for sec in all_sections:

        header = f"""Godot Documentation
            Type: {sec['type']}
            Class: {sec['class']}
            Section: {sec['func']}
            """

        for split in splitter.split_text(sec["text"]):

            final_texts.append(header + "\n" + split)

            final_metas.append({
                "type": sec["type"],
                "class": sec["class"],
                "section": sec["func"],
                "source": sec["class"]
            })

    print(f"✅ 解析完成：{len(final_texts)} 个切片")

    # 3. GPU 本地推理
    print("🚀 加载模型至 CUDA...")
    model = SentenceTransformer(MODEL_NAME, device="cuda")

    print(f"🔥 正在 GPU 上执行批量向量化 (Batch Size: {BATCH_SIZE})...")

    embeddings = model.encode(
        final_texts,
        batch_size=BATCH_SIZE,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # 4. 写入 Chroma
    if os.path.exists(DB_PATH):
        import shutil
        shutil.rmtree(DB_PATH)

    vectorstore = Chroma(
        persist_directory=DB_PATH,
        collection_metadata={"hnsw:space": "cosine"}
    )

    UPSERT_BATCH_SIZE = 5000
    total_slices = len(final_texts)

    print(f"📦 正在分批写入 Chroma (每批 {UPSERT_BATCH_SIZE})...")

    for i in range(0, total_slices, UPSERT_BATCH_SIZE):

        end_idx = min(i + UPSERT_BATCH_SIZE, total_slices)

        batch_ids = [str(uuid.uuid4()) for _ in range(i, end_idx)]
        batch_texts = final_texts[i:end_idx]
        batch_metas = final_metas[i:end_idx]
        batch_embeddings = embeddings[i:end_idx].tolist()

        vectorstore._collection.add(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_texts,
            metadatas=batch_metas
        )

        print(f"✅ 已写入 {end_idx}/{total_slices}...")

    total_time = time.time() - start_time

    print(f"\n✨ 任务彻底完成！总耗时: {total_time:.2f}s")
    print(f"🚀 效率: {len(final_texts)/total_time:.1f} slices/sec")