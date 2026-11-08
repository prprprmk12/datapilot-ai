"""Public AuditKIT APIs only; no invented agent metric classes."""
def evaluate_answers(inputs, targets, predictions):
    import auditkit as ak
    if not (len(inputs) == len(targets) == len(predictions)):
        raise ValueError("Mismatched sample lengths")
    samples = [ak.Sample(input=x, target=y, actual_output=z) for x,y,z in zip(inputs,targets,predictions)]
    return ak.evaluate(samples, model="precomputed", scorers=["exact_match"])

def load_training_episodes(path):
    from auditkit.agent_eval import episodes_from_agenttune
    return episodes_from_agenttune(str(path))

def evaluate_episode(question, response, expected_rows, reference_turns):
    """Score a recorded run; SQL rows are the oracle, prose cannot establish success."""
    import json
    from fastapi.encoders import jsonable_encoder
    from auditkit.agent_eval import (
        AgentCase, AgentEvalRunner, AgentEvalSpec, FinalStateAssertion,
        episode_from_openai_messages,
    )
    messages = [{"role": "user", "content": question}]
    for i, step in enumerate(response["trace"]):
        messages.append({"role": "assistant", "content": None, "tool_calls": [
            {"id": str(i), "type": "function", "function": {
                "name": step["name"], "arguments": json.dumps(step["arguments"])}}
        ]})
        messages.append({"role": "tool", "tool_call_id": str(i),
                         "content": json.dumps(jsonable_encoder(step["output"]))})
    messages.append({"role": "assistant", "content": response["answer"]})
    episode = episode_from_openai_messages(messages, case_id="sql-001", final_answer=response["answer"])
    episode.final_state = {"rows": jsonable_encoder(response["result"]["rows"]) if response["result"] else None}
    case = AgentCase(id="sql-001", task=question, category="tool_use",
                     allowed_tools=["list_tables", "describe_table", "get_relationships", "execute_sql"],
                     reference_turns=reference_turns,
                     outcome=FinalStateAssertion("rows", equals=jsonable_encoder(expected_rows)))
    return AgentEvalRunner().run(AgentEvalSpec(
        cases=[case], mode="recorded", episodes=[episode],
        scorers=["tool_call_f1", "tool_call_validity"], trials=1))
