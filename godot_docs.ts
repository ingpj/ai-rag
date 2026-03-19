import { tool } from "@opencode-ai/plugin"

function rewriteQuery(q: string) {

  // 尝试保留 类名 + 方法名组合
  const apiMatch = q.match(/[A-Z][A-Za-z0-9_]*(?:\s+[a-z_][A-Za-z0-9_]*)?/)
  return apiMatch ? apiMatch[0] : q
}

export default tool({

  description: `
    Search the official Godot Engine documentation.

    IMPORTANT:

    Convert the user question into a SHORT API search query.

    Examples:

    User: How to add child node?
    Query: Node add_child

    User: How to move CharacterBody3D?
    Query: CharacterBody3D move_and_slide

    User: How to use TileMapLayer?
    Query: TileMapLayer
  `,

  args: {
    query: tool.schema.string().describe(
      "Godot 4 technical question or API keyword"
    )
  },



  async execute(args) {

    const res = await fetch("http://127.0.0.1:8000/retrieve", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },

      
      body: JSON.stringify({
        prompt: rewriteQuery(args.query),
        top_k: 7
      })
    })

    if (!res.ok) {
      return `RAG server error: ${res.status}`
    }

    const docs = await res.json()

    if (!docs.length) {
      return "No relevant Godot documentation found."
    }

    return docs.map((d:any)=>
        `Source: ${d.source}
        Class: ${d.class ?? "unknown"}
        Score: ${d.score}

        ${d.content}`
    ).join("\n\n---\n\n")
  }

})
