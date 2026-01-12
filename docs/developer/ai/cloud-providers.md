# Cloud AI Providers

Using OpenAI and other cloud APIs for AI inference.

## Overview

Cloud providers are an alternative to local Ollama for users who:
- Have limited hardware (< 8GB RAM)
- Want higher quality models (GPT-4, Claude)
- Need faster inference than CPU-only local models

**Privacy note**: When using cloud providers, the text being processed is sent to the provider's servers. Your knowledge base, connections, and conversation history remain local.

## Supported Providers

| Provider | Models | Best For |
|----------|--------|----------|
| **OpenAI** | GPT-4o, GPT-4o-mini, text-embedding-3-small | Primary recommendation |
| **Anthropic** | Claude 3.5 Sonnet, Claude 3 Haiku | Quality-focused users |
| **Google** | Gemini 1.5 Flash, Gemini 1.5 Pro | Budget-conscious users |

### Why OpenAI First

OpenAI is the primary cloud provider because:
- Most mature API with best documentation
- Widest model selection
- Most users already have API keys
- Best price/performance for embeddings

Other providers are supported via LiteLLM but OpenAI is the default recommendation.

## Architecture

We use [LiteLLM](https://github.com/BerriAI/litellm) to provide a unified interface:

```
┌─────────────────────────────────────────────────────────────┐
│                    CloudProvider                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                    LiteLLM                           │    │
│  │  • Unified API for all providers                     │    │
│  │  • Automatic retries                                 │    │
│  │  • Cost tracking                                     │    │
│  │  • Runs locally (bundled with app)                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│           ┌───────────────┼───────────────┐                 │
│           ▼               ▼               ▼                 │
│      ┌─────────┐    ┌──────────┐    ┌─────────┐            │
│      │ OpenAI  │    │Anthropic │    │ Google  │            │
│      └─────────┘    └──────────┘    └─────────┘            │
└─────────────────────────────────────────────────────────────┘
```

**Why LiteLLM over direct API calls?**
- Single interface for all providers
- Automatic fallback between providers
- Built-in cost tracking
- No external service dependency (runs locally)

## Setup

### API Key Configuration

```
┌─────────────────────────────────────────────────────────────┐
│  Cloud AI Configuration                                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  OpenAI                                                      │
│  [sk-proj-••••••••••••••••••••]         ✓ Connected         │
│                                                              │
│  Get your API key at: https://platform.openai.com/api-keys  │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  Anthropic (Optional)                                        │
│  [Not configured]                            [Add Key]       │
│                                                              │
│  Google (Optional)                                           │
│  [Not configured]                            [Add Key]       │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│                                                              │
│  [Test Connection]                                           │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Key Storage

API keys are stored securely in the OS keychain:
- macOS: Keychain Access
- Windows: Credential Manager
- Linux: Secret Service (libsecret)

```python
import keyring

def store_api_key(provider: str, key: str) -> None:
    keyring.set_password("cortex", f"{provider}_api_key", key)

def get_api_key(provider: str) -> str | None:
    return keyring.get_password("cortex", f"{provider}_api_key")
```

**Never** store API keys in:
- Plain text files
- SQLite database
- Environment variables (for desktop app)

## Implementation

### Provider Class

```python
from litellm import acompletion, aembedding

class CloudProvider(AIProvider):
    def __init__(self, config: CloudConfig):
        self.embedding_model = config.embedding_model  # e.g., "text-embedding-3-small"
        self.chat_model = config.chat_model  # e.g., "gpt-4o-mini"

        # Set API keys from keychain
        os.environ["OPENAI_API_KEY"] = get_api_key("openai")

    async def embed(self, text: str) -> list[float]:
        response = await aembedding(
            model=self.embedding_model,
            input=[text]
        )
        return response.data[0]["embedding"]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await aembedding(
            model=self.embedding_model,
            input=texts
        )
        return [item["embedding"] for item in response.data]

    async def chat(
        self,
        messages: list[dict],
        system: str | None = None
    ) -> str:
        if system:
            messages = [{"role": "system", "content": system}] + messages

        response = await acompletion(
            model=self.chat_model,
            messages=messages
        )
        return response.choices[0].message.content

    async def stream_chat(
        self,
        messages: list[dict],
        system: str | None = None
    ) -> AsyncIterator[str]:
        if system:
            messages = [{"role": "system", "content": system}] + messages

        response = await acompletion(
            model=self.chat_model,
            messages=messages,
            stream=True
        )
        async for chunk in response:
            if content := chunk.choices[0].delta.content:
                yield content
```

### Model Selection

```python
# Recommended models by task
CLOUD_MODELS = {
    "embedding": {
        "openai": "text-embedding-3-small",  # 1536 dims, $0.02/1M tokens
        "google": "text-embedding-004",       # 768 dims
    },
    "chat": {
        "openai": "gpt-4o-mini",              # Fast, cheap, good quality
        "anthropic": "claude-3-haiku-20240307", # Fast, good at following instructions
        "google": "gemini-1.5-flash",         # Cheapest option
    },
    "chat_premium": {
        "openai": "gpt-4o",                   # Best OpenAI model
        "anthropic": "claude-3-5-sonnet-20241022", # Best for complex tasks
        "google": "gemini-1.5-pro",           # Best Google model
    }
}
```

## Cost Tracking

### Per-Request Tracking

```python
from litellm import completion_cost

async def chat_with_cost(self, messages: list) -> tuple[str, float]:
    response = await acompletion(
        model=self.chat_model,
        messages=messages
    )
    cost = completion_cost(completion_response=response)
    return response.choices[0].message.content, cost
```

### Monthly Usage Display

```
┌─────────────────────────────────────────────────────────────┐
│  Cloud AI Usage This Month                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Embeddings                                                  │
│  1,247 requests • ~2.1M tokens • $0.04                      │
│                                                              │
│  Chat (gpt-4o-mini)                                         │
│  89 requests • ~180K tokens • $0.03                         │
│                                                              │
│  ─────────────────────────────────────────────────────────  │
│  Total estimated cost: $0.07                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Cost Estimation

| Operation | Model | Cost per 1M tokens | Typical per item |
|-----------|-------|-------------------|------------------|
| Embedding | text-embedding-3-small | $0.02 | $0.0001 |
| Extraction | gpt-4o-mini | $0.15 input, $0.60 output | $0.001 |
| Chat query | gpt-4o-mini | $0.15 input, $0.60 output | $0.0005 |
| Chat query | gpt-4o | $2.50 input, $10.00 output | $0.01 |

**Typical monthly costs:**
- Light usage (50 items/month, 20 queries): ~$0.10
- Medium usage (100 items/month, 50 queries): ~$0.25
- Heavy usage (200 items/month, 100 queries): ~$0.50

## Error Handling

### Rate Limiting

```python
from litellm.exceptions import RateLimitError

async def embed_with_retry(self, text: str) -> list[float]:
    for attempt in range(3):
        try:
            return await self.embed(text)
        except RateLimitError:
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
    raise RateLimitError("Rate limited after 3 attempts")
```

### Invalid API Key

```python
from litellm.exceptions import AuthenticationError

async def validate_api_key(provider: str, key: str) -> bool:
    try:
        # Make a minimal API call to verify key works
        await aembedding(
            model=CLOUD_MODELS["embedding"][provider],
            input=["test"]
        )
        return True
    except AuthenticationError:
        return False
```

### Provider Unavailable

```python
# Fallback chain
async def embed_with_fallback(self, text: str) -> list[float]:
    providers = ["openai", "google", "anthropic"]

    for provider in providers:
        if not get_api_key(provider):
            continue
        try:
            return await self._embed_with_provider(provider, text)
        except Exception as e:
            logger.warning(f"{provider} failed: {e}")
            continue

    raise AllProvidersFailedError("No cloud providers available")
```

## Hybrid Mode

When hybrid mode is enabled:

1. **Embeddings**: Use configured provider (usually local for speed)
2. **Simple extraction**: Use local model
3. **Complex queries**: Use cloud model
4. **Fallback**: If local fails, try cloud

```python
class HybridProvider(AIProvider):
    def __init__(self, local: OllamaProvider, cloud: CloudProvider):
        self.local = local
        self.cloud = cloud

    async def embed(self, text: str) -> list[float]:
        # Always use local for embeddings (consistency)
        return await self.local.embed(text)

    async def chat(self, messages: list, system: str | None = None) -> str:
        try:
            return await self.local.chat(messages, system)
        except Exception:
            # Fallback to cloud
            return await self.cloud.chat(messages, system)
```

## Security Considerations

### What Gets Sent

When using cloud providers, only the following is transmitted:
- Text content being embedded or analyzed
- Chat messages and system prompts

**Never sent:**
- Your full knowledge base
- Connection graphs
- Conversation history (only current query)
- Local file paths or metadata

### Minimizing Data Exposure

```python
# Chunk text to send only what's needed
async def analyze_item(self, item: Item) -> Analysis:
    # Only send summary, not full content
    text_to_analyze = item.title + "\n" + item.summary[:1000]
    return await self.cloud.extract(text_to_analyze)
```

## Related Documentation

- [AI Overview](./overview.md) - Provider architecture
- [Ollama Integration](./ollama.md) - Local AI alternative
- [Embeddings](./embeddings.md) - Vector embedding strategy
