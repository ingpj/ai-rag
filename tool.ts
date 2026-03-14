import { tool } from "@opencode-ai/plugin"

export default tool({

  description:
    // "Search the official Godot 4 documentation including Node classes, GDScript syntax and engine API. Use this whenever the user asks about Godot nodes, signals, scripting or engine features.",
    `
    Search the official Godot 4 documentation.

    Use this tool whenever the user asks about:

    - Godot nodes (Node2D, CharacterBody2D, Control, etc.)
    - GDScript syntax
    - signals
    - scene tree
    - physics
    - rendering
    - engine API
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
        prompt: args.query,
        top_k: 5
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