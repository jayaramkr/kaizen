import json
from unittest.mock import MagicMock, patch

import pytest

from altk_evolve.schema.tips import SubtaskSegment

pytestmark = pytest.mark.unit

MESSAGES = [{"role": "user", "content": "Do something"}, {"role": "assistant", "content": "Step 1 done"}]

VALID_SEGMENTATION_JSON = json.dumps(
    {
        "subtasks": [
            {"generalized_description": "Authenticate with service", "start_step": 1, "end_step": 2, "purpose": "Get access"},
            {"generalized_description": "Retrieve data", "start_step": 3, "end_step": 5, "purpose": "Fetch records"},
        ]
    }
)


def _mock_completion(content: str) -> MagicMock:
    resp = MagicMock()
    resp.choices[0].message.content = content
    return resp


@patch("altk_evolve.llm.tips.segmentation.completion")
@patch("altk_evolve.llm.tips.segmentation.get_supported_openai_params", return_value=[])
@patch("altk_evolve.llm.tips.segmentation.supports_response_schema", return_value=False)
def test_segment_trajectory_returns_subtasks(mock_schema, mock_params, mock_completion):
    mock_completion.return_value = _mock_completion(VALID_SEGMENTATION_JSON)

    from altk_evolve.llm.tips.segmentation import segment_trajectory

    result = segment_trajectory(MESSAGES)

    assert len(result) == 2
    assert isinstance(result[0], SubtaskSegment)
    assert result[0].generalized_description == "Authenticate with service"
    assert result[0].start_step == 1
    assert result[0].end_step == 2
    assert result[1].generalized_description == "Retrieve data"


@patch("altk_evolve.llm.tips.segmentation.completion")
@patch("altk_evolve.llm.tips.segmentation.get_supported_openai_params", return_value=[])
@patch("altk_evolve.llm.tips.segmentation.supports_response_schema", return_value=False)
def test_segment_trajectory_returns_empty_on_llm_failure(mock_schema, mock_params, mock_completion):
    mock_completion.side_effect = Exception("LLM unavailable")

    from altk_evolve.llm.tips.segmentation import segment_trajectory

    result = segment_trajectory(MESSAGES)

    assert result == []


@patch("altk_evolve.llm.tips.segmentation.completion")
@patch("altk_evolve.llm.tips.segmentation.get_supported_openai_params", return_value=[])
@patch("altk_evolve.llm.tips.segmentation.supports_response_schema", return_value=False)
def test_segment_trajectory_retries_on_parse_failure(mock_schema, mock_params, mock_completion):
    bad = _mock_completion("not valid json at all")
    good = _mock_completion(VALID_SEGMENTATION_JSON)
    mock_completion.side_effect = [bad, bad, good]

    from altk_evolve.llm.tips.segmentation import segment_trajectory

    result = segment_trajectory(MESSAGES)

    assert len(result) == 2
    assert mock_completion.call_count == 3


@patch("altk_evolve.llm.tips.segmentation.completion")
@patch("altk_evolve.llm.tips.segmentation.get_supported_openai_params", return_value=[])
@patch("altk_evolve.llm.tips.segmentation.supports_response_schema", return_value=False)
def test_segment_trajectory_returns_empty_after_max_retries(mock_schema, mock_params, mock_completion):
    mock_completion.return_value = _mock_completion("not valid json at all")

    from altk_evolve.llm.tips.segmentation import segment_trajectory

    result = segment_trajectory(MESSAGES)

    assert result == []
    assert mock_completion.call_count == 3
