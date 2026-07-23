# Model routing

`config/litellm.yaml` is derived from the current model catalog in [`docs/can-use-models-list.md`](can-use-models-list.md).

The upstream service is exposed as an OpenAI-compatible endpoint through `ICA_BASE` / `ICA_KEY`, so LiteLLM model identifiers use the `openai/<upstream-model-id>` provider prefix.

## Current alias strategy

| Alias | Upstream model | Best use |
| --- | --- | --- |
| `claude-sonnet-5` | `gpt-5.6-terra-dzus` | Default Claude Code-compatible balanced reasoning/coding alias. |
| `claude-sonnet-4-5` | `gpt-5.6-terra-dzus` | Backward-compatible Sonnet alias. |
| `claude-opus-4-8` | `gpt-5.5-gus` | Strong multi-step/deep work. |
| `claude-opus-4-5` | `gpt-5.5-gus` | Backward-compatible Opus alias. |
| `claude-haiku-4-5` | `gpt-5.6-luna-dzus` | Fast, lightweight, cost-efficient tasks. |
| `gpt-best` | `gpt-5.5-gus` | Highest-capability custom alias. |
| `gpt-coding` | `gpt-5.6-terra-dzus` | Balanced coding and productivity. |
| `gpt-fast` | `gpt-5.6-luna-dzus` | Fast and cost-efficient requests. |
| `gpt-multimodal` | `gpt-4o` | Natural multimodal tasks. |
| `gpt-4o` | `gpt-4o` | Direct GPT-4o alias. |
| `gemini` | `gemini-3.1-pro-preview` | Long-context/pro analysis. |
| `gemini-fast` | `gemini-3.5-flash` | Fast Gemini/global fallback. |
| `llama` | `meta-llama/llama-4-maverick-17b-128e-instruct-fp8` | Long guided tasks and OSS-style fallback. |
| `granite` | `ibm/granite-4-h-small` | Small, stable, fast fallback. |
| `gemma` | `gemma-4-26b-a4b-it` | Google/Gemma preview experimentation. |

## Fallback principles

- Each user-facing alias is explicitly present in `model_list` so `/v1/models` shows the names clients should use.
- Claude-compatible coding aliases prefer Terra/GPT-5.5 first, then Gemini/Llama for long-context recovery.
- Fast aliases prefer Luna, Gemini Flash, then Granite.
- Multimodal aliases prefer GPT-4o, then Gemini, then GPT-best.
- Preview/experimental aliases have conservative fallbacks to stable fast models.

## Health-check notes

LiteLLM `/health` probes every configured alias/deployment. When several aliases point to the same upstream model, a transient or upstream-specific probe issue may show one alias as unhealthy while the same upstream model is healthy through another alias. In that case, validate both:

- `/health` endpoint availability via `wait-for-health.sh`
- `/v1/models` alias exposure via `status.sh`

Do not remove useful client-facing aliases only to deduplicate health probes unless the user explicitly asks for fewer aliases.

## Updating routing when the catalog changes

1. Update `docs/can-use-models-list.md` with the latest catalog.
2. Map each new model by its description, not just by name.
3. Update `config/litellm.yaml` aliases and fallbacks.
4. Update this document and the README alias list.
5. Validate on a non-conflicting port with real local credentials:

```bash
ENV_FILE=.env.local LITELLM_PORT=4001 ./deploy/scripts/start.sh
ENV_FILE=.env.local LITELLM_PORT=4001 TIMEOUT_SECONDS=180 ./deploy/scripts/wait-for-health.sh
ENV_FILE=.env.local LITELLM_PORT=4001 ./deploy/scripts/status.sh
ENV_FILE=.env.local LITELLM_PORT=4001 ./deploy/scripts/stop.sh
```

6. Generate a review report:

```bash
make review-report REPORT_FILE=docs/reports/model-routing-update.md
```
