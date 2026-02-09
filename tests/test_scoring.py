"""Tests for the scoring module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from seedling.scoring.scorer import (
    CANDIDATE_PROFILE,
    JobScorer,
    ScoredJob,
    quick_reject_job,
    score_job,
)


class TestScoredJob:
    """Tests for the ScoredJob dataclass."""

    def test_scored_job_creation(self) -> None:
        """Test creating a ScoredJob."""
        scored = ScoredJob(
            url="https://example.com/job",
            match_score=85,
            category="tech-devops",
            score_breakdown={"skill_match": 90, "growth": 80, "logistics": 85, "compensation": 75, "ease": 95},
            score_summary="Great match for your DevOps skills",
            quick_reject_reason=None,
            passed_quick_reject=True,
        )

        assert scored.match_score == 85
        assert scored.category == "tech-devops"
        assert scored.passed_quick_reject is True
        assert scored.quick_reject_reason is None

    def test_scored_job_rejected(self) -> None:
        """Test creating a rejected ScoredJob."""
        scored = ScoredJob(
            url="https://example.com/job",
            match_score=0,
            category="tech-devops",
            score_breakdown={},
            score_summary="",
            quick_reject_reason="Requires 5+ years experience",
            passed_quick_reject=False,
        )

        assert scored.passed_quick_reject is False
        assert scored.quick_reject_reason == "Requires 5+ years experience"


class TestJobScorer:
    """Tests for the JobScorer class."""

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock OpenAI response."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "PASS"
        return response

    @pytest.fixture
    def scorer(self) -> JobScorer:
        """Create a JobScorer without a real client."""
        # Create a scorer without passing http_client to avoid validation
        scorer = JobScorer.__new__(JobScorer)
        scorer.client = MagicMock()
        scorer.model = "moonshotai/kimi-k2.5"
        scorer.tech_threshold = 60
        scorer.serving_threshold = 50
        return scorer

    @pytest.mark.asyncio
    async def test_quick_reject_pass(self, scorer: JobScorer, mock_response: MagicMock) -> None:
        """Test quick reject when job passes."""
        mock_response.choices[0].message.content = "PASS"
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        passed, reason = await scorer.quick_reject("Python developer position")

        assert passed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_quick_reject_reject_with_reason(self, scorer: JobScorer) -> None:
        """Test quick reject when job is rejected."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "REJECT: Requires 5+ years experience"
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        passed, reason = await scorer.quick_reject("Senior Python developer")

        assert passed is False
        assert reason == "Requires 5+ years experience"

    @pytest.mark.asyncio
    async def test_quick_reject_unknown_format(self, scorer: JobScorer) -> None:
        """Test quick reject with unknown response format."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Some unexpected response"
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        passed, reason = await scorer.quick_reject("Job description")

        assert passed is False
        assert reason == "Unknown reason"

    @pytest.mark.asyncio
    async def test_score_tech_job_success(self, scorer: JobScorer) -> None:
        """Test scoring a tech job successfully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {"score": 85, "category": "tech-devops", "breakdown": {"skill_match": 90, "growth": 80, "logistics": 85, "compensation": 75, "ease": 95}, "summary": "Great match for your DevOps skills"}
        '''
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await scorer.score_tech_job("Looking for a DevOps engineer with Python and AWS experience")

        assert result.match_score == 85
        assert result.category == "tech-devops"
        assert result.passed_quick_reject is True
        assert "DevOps" in result.score_summary

    @pytest.mark.asyncio
    async def test_score_tech_job_parse_error(self, scorer: JobScorer) -> None:
        """Test scoring with JSON parse error falls back."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid response format"
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await scorer.score_tech_job("Python developer")

        assert result.match_score == 50  # Fallback value
        assert result.category == "tech-devops"
        assert "Could not parse" in result.score_summary

    @pytest.mark.asyncio
    async def test_score_serving_job_success(self, scorer: JobScorer) -> None:
        """Test scoring a serving job successfully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {"score": 75, "category": "serving", "breakdown": {"location": 80, "schedule": 70, "pay": 75, "vibe": 75}, "summary": "Good serving position in Atlanta"}
        '''
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await scorer.score_serving_job("Server position at local restaurant")

        assert result.match_score == 75
        assert result.category == "serving"
        assert result.score_breakdown["location"] == 80

    @pytest.mark.asyncio
    async def test_score_job_tech_category(self, scorer: JobScorer) -> None:
        """Test score_job dispatches to tech scoring."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"score": 80, "category": "tech-fullstack", "breakdown": {}, "summary": "Full stack match"}'
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await scorer.score_job("Full stack developer", "tech-fullstack")

        assert result.category == "tech-fullstack"

    @pytest.mark.asyncio
    async def test_score_job_serving_category(self, scorer: JobScorer) -> None:
        """Test score_job dispatches to serving scoring."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"score": 70, "category": "serving", "breakdown": {}, "summary": "Good serving job"}'
        scorer.client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await scorer.score_job("Restaurant server", "serving")

        assert result.category == "serving"


class TestCandidateProfile:
    """Tests for the candidate profile."""

    def test_candidate_profile_contains_key_skills(self) -> None:
        """Test that profile contains expected skills."""
        assert "Python" in CANDIDATE_PROFILE
        assert "TypeScript" in CANDIDATE_PROFILE
        assert "Cloudflare" in CANDIDATE_PROFILE

    def test_candidate_profile_contains_education(self) -> None:
        """Test that profile contains education info."""
        assert "Kennesaw State" in CANDIDATE_PROFILE
        assert "Information Technology" in CANDIDATE_PROFILE


class TestConvenienceFunctions:
    """Tests for the convenience functions."""

    @pytest.mark.asyncio
    async def test_quick_reject_job_function(self) -> None:
        """Test the quick_reject_job convenience function."""
        with patch(
            "seedling.scoring.scorer.JobScorer",
            return_value=MagicMock(
                quick_reject=AsyncMock(return_value=(True, None))
            ),
        ):
            passed, _ = await quick_reject_job(
                "Python developer position",
                api_key="test-key",
            )

            assert passed is True

    @pytest.mark.asyncio
    async def test_score_job_function(self) -> None:
        """Test the score_job convenience function."""
        with patch(
            "seedling.scoring.scorer.JobScorer",
            return_value=MagicMock(
                score_job=AsyncMock(
                    return_value=ScoredJob(
                        url="",
                        match_score=85,
                        category="tech-devops",
                        score_breakdown={},
                        score_summary="Good match",
                    )
                )
            ),
        ):
            result = await score_job(
                "DevOps position",
                api_key="test-key",
                category="tech-devops",
            )

            assert result.match_score == 85
