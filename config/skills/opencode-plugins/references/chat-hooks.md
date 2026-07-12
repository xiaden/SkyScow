# Chat & LLM Hooks

Hooks for intercepting and modifying the LLM chat lifecycle — messages, parameters, headers, system prompts, and completions.

---

## Table of Contents

- [chat.message](#chatmessage)
- [chat.params](#chatparams)
- [chat.headers](#chatheaders)
- [experimental.chat.messages.transform](#experimentalchatmessagestransform)
- [experimental.chat.system.transform](#experimentalchatsystemtransform)
- [experimental.text.complete](#experimentaltextcomplete)

---

## chat.message

Called when a new user message is received. Modify the message or its parts before processing.

```typescript
"chat.message": async (input, output) => {
  // input.sessionID, input.agent?, input.model?, input.messageID?, input.variant?
  // output.message — UserMessage object
  // output.parts  — Part[] array (text, tool calls, etc.)

  // Append a system hint to every message
  output.parts.push({ type: "text", text: "(Remember: use TypeScript conventions)" })
}
```

---

## chat.params

Modify LLM parameters (temperature, topP, topK, maxOutputTokens) before each API call.

```typescript
"chat.params": async (input, output) => {
  // input.sessionID, input.agent, input.model, input.provider, input.message
  // output.temperature, output.topP, output.topK, output.maxOutputTokens, output.options

  // Force deterministic output
  output.temperature = 0.0
  output.topP = 1.0

  // Pass extra provider-specific options
  output.options.reasoning_effort = "high"
}
```

### Provider Context

The `input.provider` object includes:
- `source`: `"env" | "config" | "custom" | "api"`
- `info`: Provider metadata
- `options`: Provider-specific configuration

---

## chat.headers

Inject custom HTTP headers into LLM provider API requests.

```typescript
"chat.headers": async (input, output) => {
  // input.sessionID, input.agent, input.model, input.provider, input.message
  // output.headers — Record<string, string>

  output.headers["X-Custom-Tracking"] = input.sessionID
  output.headers["Helicone-Auth"] = `Bearer ${process.env.HELICONE_API_KEY}`
}
```

Common use cases: logging/tracing (Helicone), custom auth, rate-limit headers.

---

## experimental.chat.messages.transform

Transform the full message list before it's sent to the LLM. Use for filtering, reordering, or injecting synthetic messages.

```typescript
"experimental.chat.messages.transform": async (input, output) => {
  // output.messages — Array of { info: Message, parts: Part[] }

  // Remove tool results that contain secrets
  output.messages = output.messages.filter(msg => {
    const text = msg.parts.map(p => p.type === "text" ? p.text : "").join("")
    return !text.includes("API_KEY")
  })
}
```

---

## experimental.chat.system.transform

Modify the system prompt lines before they're assembled. Each string in the `system` array becomes one line.

```typescript
"experimental.chat.system.transform": async (input, output) => {
  // input.sessionID?, input.model
  // output.system — string[]

  // Inject custom system prompt instructions
  output.system.push("Always respond in TypeScript.", "Prefer arrow functions over function declarations.")
}
```

---

## experimental.text.complete

Intercept text completion results. Fires during streaming text completion.

```typescript
"experimental.text.complete": async (input, output) => {
  // input.sessionID, input.messageID, input.partID
  // output.text — the completion text

  // Strip trailing whitespace from all completions
  output.text = output.text.trimEnd()
}
```
