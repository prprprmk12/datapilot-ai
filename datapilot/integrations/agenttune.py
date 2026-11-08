"""Verified public factory boundary; installed separately in a training environment."""
def create_training_job(dataset, tools, output_dir, model="CohereLabs/tiny-aya-global", max_steps=10, reward=None):
    from agenttune.core.backend_factory import create_agentic_trainer
    return create_agentic_trainer(
        algorithm="grpo", model=model, train_dataset=dataset, tools=tools,
        reward_funcs=[reward if reward is not None else answer_reward], output_dir=str(output_dir), max_steps=max_steps,
        per_device_train_batch_size=2, gradient_accumulation_steps=1,
        num_generations=2, max_steps_per_turn=3, use_vllm=False,
        peft_config=dict(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM"),
        report_to="none",
    )

def answer_reward(completions, answer=None, **kwargs):
    # Starter exact-answer reward only. Not an execution correctness/safety metric.
    def text(c):
        return str(c[-1].get("content", "")) if isinstance(c, list) and c else str(c)
    return [float(text(c).strip() == str(answer[i]).strip()) if answer else 0.0 for i,c in enumerate(completions)]
