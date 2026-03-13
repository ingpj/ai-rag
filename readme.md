# 使用 langchian 仅制作 godot4 离线 html docs 制作 rag ，embeding 使用本地 ollama 加载
- 给我制作流程
- 给我示例代码 

## 依赖库:
- langchain
- chromadb
- ollama
- beautifulsoup4
- lxml
- tqdm

## 要求:
- Metadata 强化：记录类名、函数名、模块路径，便于检索。
- 自定义 Splitter：针对 class、func 等 API 单位分块，而非单纯长度。
- 多层 Chunking：
    - 第一层按类/方法
    - 第二层按段落或代码块
- RAG Prompt：
    - 附加 source 信息
    - 用于生成带引用的回答
以及 考虑 API-aware chunking

## docs 结构:
├── _downloads
│   ├── 0e9010cdc7bfae0d0bed55a967d66e0b
├── _images
├── _sources
│   ├── about
│   ├── classes
│   ├── community
│   │   └── asset_library
│   ├── engine_details
│   │   ├── architecture
│   │   ├── class_reference
│   │   ├── development
│   │   │   ├── compiling
│   │   │   ├── configuring_an_ide
│   │   │   ├── debugging
│   │   │   │   └── vulkan
│   │   │   └── profiling
│   │   ├── editor
│   │   ├── engine_api
│   │   └── file_formats
│   ├── getting_started
│   │   ├── first_2d_game
│   │   ├── first_3d_game
│   │   ├── introduction
│   │   └── step_by_step
│   └── tutorials
│       ├── 2d
│       ├── 3d
│       │   ├── global_illumination
│       │   ├── particles
│       │   └── procedural_geometry
│       ├── animation
│       ├── assets_pipeline
│       │   ├── escn_exporter
│       │   └── importing_3d_scenes
│       ├── audio
│       ├── best_practices
│       ├── editor
│       ├── export
│       ├── i18n
│       ├── inputs
│       ├── io
│       ├── math
├── _static
│   ├── css
│   │   └── fonts
│   ├── fonts
│   │   ├── Lato
│   │   └── RobotoSlab
│   └── js
├── about
├── classes
├── community
│   └── asset_library
├── engine_details
│   ├── architecture
│   ├── class_reference
│   ├── development
│   │   ├── compiling
│   │   ├── configuring_an_ide
│   │   ├── debugging
│   │   │   └── vulkan
│   │   └── profiling
│   ├── editor
│   ├── engine_api
│   └── file_formats
├── getting_started
│   ├── first_2d_game
│   ├── first_3d_game
│   ├── introduction
│   └── step_by_step
└── tutorials
    ├── 2d
    ├── 3d
    │   ├── global_illumination
    │   ├── particles
    │   └── procedural_geometry
    ├── animation
    ├── assets_pipeline
    │   ├── escn_exporter
    │   └── importing_3d_scenes
    ├── audio
    ├── best_practices
    ├── editor
    ├── export