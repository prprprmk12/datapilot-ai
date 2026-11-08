"""Optional real inference. No implicit fallback to demo or download at import."""
from datapilot.integrations.protocol import messages_for, parse_action

class TinyAyaPolicy:
    def __init__(self, settings):
        from transformers import AutoTokenizer, AutoModelForCausalLM
        self.tokenizer = AutoTokenizer.from_pretrained(settings.model_id, token=settings.hf_token)
        self.model = AutoModelForCausalLM.from_pretrained(settings.model_id, token=settings.hf_token, device_map="auto")
        self.model.eval()

    def choose(self, question, observations):
        messages = messages_for(question, observations)
        inputs = self.tokenizer.apply_chat_template(messages, add_generation_prompt=True, tokenize=True, return_dict=True, return_tensors="pt").to(self.model.device)
        import torch
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=512, do_sample=False)
        text = self.tokenizer.decode(output[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
        return parse_action(text)
