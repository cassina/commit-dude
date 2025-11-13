import pytest
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT
from commit_dude.llm import ChatCommitDude
from commit_dude.settings import commit_dude_logger

logger = commit_dude_logger(__name__)

@pytest.mark.langsmith
def test_commit_dude_output_llm_as_judge():
    """Evaluate only the LLM output (no trajectory)."""

    # Run the actual model
    dude = ChatCommitDude(validate_api_key=True)
    diff = "diff --git a/main.py b/main.py\n- print('debug')\n+ logger.info('debug')"
    result = dude.invoke(diff)

    # Build a minimal evaluation input: just one assistant message
    outputs = [
        {
            "role": "assistant",
            "content": f"{result.agent_response}\n\n{result.commit_message}"
        }
    ]

    # Create the evaluator (no reference trajectory)
    evaluator = create_trajectory_llm_as_judge(
        model="openai:o3-mini",
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )

    # Run evaluation
    evaluation = evaluator(outputs=outputs)
    logger.info(f"Evaluation result: {evaluation}")
    assert evaluation["score"]
