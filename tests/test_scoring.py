"""Tests for the scoring module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seedling.scoring.scorer import JobScorer, ScoredJob


class TestJobScorer:
    """Tests for the JobScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a JobScorer with patched AsyncOpenAI."""
        with patch("seedling.scoring.scorer.AsyncOpenAI") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client
            s = JobScorer(api_key="test-key")
            yield s, mock_client

    @pytest.mark.asyncio
    async def test_quick_reject_pass(self, scorer, mock_openai_response) -> None:
        """Test quick reject when job passes."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response("PASS")

        passed, reason = await s.quick_reject("Python developer position")
        assert passed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_quick_reject_reject_with_reason(self, scorer, mock_openai_response) -> None:
        """Test quick reject when job is rejected."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "REJECT: Requires 5+ years experience"
        )

        passed, reason = await s.quick_reject("Senior Python developer")
        assert passed is False
        assert reason == "Requires 5+ years experience"

    @pytest.mark.asyncio
    async def test_quick_reject_unknown_format(self, scorer, mock_openai_response) -> None:
        """Test quick reject with unknown response format."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Some unexpected response"
        )

        passed, reason = await s.quick_reject("Job description")
        assert passed is False
        assert reason == "Unknown reason"

    @pytest.mark.asyncio
    async def test_quick_reject_none_content(self, scorer) -> None:
        """LLM returns None content — graceful fallback."""
        s, mock_client = scorer
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = response

        passed, reason = await s.quick_reject("Some job")
        assert passed is False
        assert "empty" in reason.lower()

    @pytest.mark.asyncio
    async def test_quick_reject_empty_string(self, scorer, mock_openai_response) -> None:
        """LLM returns empty string — explicit rejection instead of 'Unknown reason'."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response("")

        passed, reason = await s.quick_reject("Some job")
        assert passed is False
        assert "empty" in reason.lower()

    @pytest.mark.asyncio
    async def test_quick_reject_whitespace_only(self, scorer, mock_openai_response) -> None:
        """LLM returns only whitespace — treated as empty."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response("   \n  ")

        passed, reason = await s.quick_reject("Some job")
        assert passed is False
        assert "empty" in reason.lower()

    @pytest.mark.asyncio
    async def test_score_tech_job_success(self, scorer, mock_openai_response) -> None:
        """Test scoring a tech job successfully."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            '{"score": 85, "category": "tech-devops", '
            '"breakdown": {"skill_match": 90, "growth": 80, "logistics": 85, "compensation": 75, "ease": 95}, '
            '"summary": "Great match for your DevOps skills"}'
        )

        result = await s.score_tech_job("DevOps engineer with Python and AWS")
        assert result.match_score == 85
        assert result.category == "tech-devops"
        assert "DevOps" in result.score_summary

    @pytest.mark.asyncio
    async def test_score_tech_job_parse_error(self, scorer, mock_openai_response) -> None:
        """Test scoring with JSON parse error falls back."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            "Invalid response format"
        )

        result = await s.score_tech_job("Python developer")
        assert result.match_score == 0
        assert "Could not parse" in result.score_summary

    @pytest.mark.asyncio
    async def test_score_serving_job_success(self, scorer, mock_openai_response) -> None:
        """Serving breakdown keys: location, schedule, pay, vibe."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            '{"score": 75, "category": "serving", '
            '"breakdown": {"location": 80, "schedule": 70, "pay": 75, "vibe": 75}, '
            '"summary": "Good serving position in Atlanta"}'
        )

        result = await s.score_serving_job("Server position at local restaurant")
        assert result.match_score == 75
        assert result.category == "serving"
        assert result.score_breakdown["location"] == 80
        assert result.score_breakdown["schedule"] == 70
        assert result.score_breakdown["pay"] == 75
        assert result.score_breakdown["vibe"] == 75

    @pytest.mark.asyncio
    async def test_score_tech_job_json_embedded_in_text(
        self, scorer, mock_openai_response
    ) -> None:
        """JSON wrapped in LLM prose is still parsed correctly."""
        s, mock_client = scorer
        mock_client.chat.completions.create.return_value = mock_openai_response(
            'Here is my analysis:\n'
            '{"score": 72, "category": "tech-fullstack", '
            '"breakdown": {"skill_match": 80, "growth": 60, "logistics": 70, "compensation": 65, "ease": 85}, '
            '"summary": "Solid full stack role"}\n'
            'Hope that helps!'
        )

        result = await s.score_tech_job("Full stack developer position")
        assert result.match_score == 72
        assert result.category == "tech-fullstack"

    @pytest.mark.asyncio
    async def test_score_job_dispatches_correctly(
        self, scorer, mock_openai_response
    ) -> None:
        """score_job dispatches to tech or serving based on category."""
        s, mock_client = scorer

        # Tech dispatch
        mock_client.chat.completions.create.return_value = mock_openai_response(
            '{"score": 80, "category": "tech-devops", "breakdown": {}, "summary": "Tech match"}'
        )
        tech_result = await s.score_job("DevOps position", "tech-devops")
        assert tech_result.category == "tech-devops"

        # Serving dispatch
        mock_client.chat.completions.create.return_value = mock_openai_response(
            '{"score": 70, "category": "serving", "breakdown": {}, "summary": "Serving match"}'
        )
        serving_result = await s.score_job("Restaurant server", "serving")
        assert serving_result.category == "serving"

    @pytest.mark.asyncio
    async def test_scorer_uses_correct_model_and_temperature(self, scorer) -> None:
        """Verify LLM call params (model, temperature)."""
        s, mock_client = scorer

        # Set up response for quick_reject
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "PASS"
        mock_client.chat.completions.create.return_value = response

        await s.quick_reject("Some job")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "deepseek/deepseek-v3.2"
        assert call_kwargs.kwargs["temperature"] == 0.1
