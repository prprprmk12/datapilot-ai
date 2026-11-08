"""Real inference through the documented OpenAI-compatible llama.cpp/vLLM endpoint."""
import httpx
from datapilot.integrations.protocol import messages_for, parse_action, action_schema

class ModelUnavailable(RuntimeError):
    pass

class ModelAPIPolicy:
    def __init__(self, settings, transport=None):
        self.settings=settings
        self.transport=transport

    def choose(self, question, observations):
        headers={"Authorization": "Bearer " + self.settings.model_api_key} if self.settings.model_api_key else {}
        try:
            with httpx.Client(base_url=self.settings.model_base_url.rstrip("/")+"/", timeout=self.settings.model_timeout_seconds,
                              headers=headers, transport=self.transport, follow_redirects=False) as client:
                body={
                    "model":self.settings.model_id,"messages":messages_for(question,observations),
                    "temperature":0,"max_tokens":self.settings.model_max_tokens,"stream":False,
                }
                if self.settings.model_constrained_json:
                    schema=action_schema(observations)
                    if self.settings.model_schema_style=="json_schema":   # формат, который документирует vLLM
                        body["response_format"]={"type":"json_schema","json_schema":{"name":"datapilot_action","schema":schema}}
                    else:
                        body["response_format"]={"type":"json_object","schema":schema}
                response=client.post("chat/completions",json=body)
                response.raise_for_status()
                payload=response.json()
        except httpx.TimeoutException as exc:
            raise ModelUnavailable("Model inference timed out. On CPU, wait for the model to warm up or increase MODEL_TIMEOUT_SECONDS.") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelUnavailable("Model server is unavailable. Check MODEL_BASE_URL, model loading and credentials.") from exc
        try:
            text=payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelUnavailable("Model server returned an unsupported response") from exc
        return parse_action(text)
