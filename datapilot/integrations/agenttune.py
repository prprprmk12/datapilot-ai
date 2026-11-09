"""Verified public factory boundary; installed separately in a training environment."""
def create_training_job(dataset, tools, output_dir, model="CohereLabs/tiny-aya-global", max_steps=10, reward=None, **overrides):
    from agenttune.core.backend_factory import create_agentic_trainer
    config = dict(
        per_device_train_batch_size=1, gradient_accumulation_steps=4,   # 4 генерации на шаг; микробатч 1 экономит память на логитах
        num_generations=4, max_steps_per_turn=6, use_vllm=False,
        model_init_kwargs={"dtype": "float16"}, fp16=True, gradient_checkpointing=True,
        logging_steps=1, save_steps=20, save_total_limit=2, log_completions=False,
    )
    config.update(overrides)
    return create_agentic_trainer(
        algorithm="grpo", model=model, train_dataset=dataset, tools=tools,
        reward_funcs=[reward if reward is not None else answer_reward], output_dir=str(output_dir), max_steps=max_steps,
        peft_config=dict(r=16, lora_alpha=32, target_modules="all-linear", task_type="CAUSAL_LM"),
        report_to="none", **config,
    )

def answer_reward(completions, answer=None, **kwargs):
    # Starter exact-answer reward only. Not an execution correctness/safety metric.
    def text(c):
        return str(c[-1].get("content", "")) if isinstance(c, list) and c else str(c)
    return [float(text(c).strip() == str(answer[i]).strip()) if answer else 0.0 for i,c in enumerate(completions)]
