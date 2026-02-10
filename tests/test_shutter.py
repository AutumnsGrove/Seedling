"""Tests for shutter.py parsing functions."""

import json

import pytest

from seedling.extraction.shutter import (
    _parse_salary,
    _extract_field,
    _is_remote,
    _parse_shutter_output,
)


class TestParseSalary:
    """Tests for _parse_salary."""

    def test_parse_salary_range(self) -> None:
        """'$80,000 - $120,000' → (80000, 120000)."""
        low, high = _parse_salary("$80,000 - $120,000")
        assert low == 80000
        assert high == 120000

    def test_parse_salary_single_value(self) -> None:
        """'$95,000' → (95000, 95000)."""
        low, high = _parse_salary("$95,000")
        assert low == 95000
        assert high == 95000

    def test_parse_salary_none(self) -> None:
        """None → (None, None)."""
        low, high = _parse_salary(None)
        assert low is None
        assert high is None

    def test_parse_salary_no_numbers(self) -> None:
        """'Competitive' → (None, None)."""
        low, high = _parse_salary("Competitive")
        assert low is None
        assert high is None


class TestExtractField:
    """Tests for _extract_field."""

    def test_extract_field_found(self) -> None:
        """'Title: Software Engineer\\n...' → 'Software Engineer'."""
        text = "Title: Software Engineer\nCompany: Acme Corp\nLocation: Remote"
        result = _extract_field(text, "title")
        assert result == "Software Engineer"

    def test_extract_field_not_found(self) -> None:
        """No match → None."""
        text = "Some random text without any fields"
        result = _extract_field(text, "title")
        assert result is None


class TestIsRemote:
    """Tests for _is_remote."""

    def test_is_remote_true(self) -> None:
        """'Remote' → True."""
        assert _is_remote("Remote") is True

    def test_is_remote_false(self) -> None:
        """'Onsite - Atlanta' → False."""
        assert _is_remote("Onsite - Atlanta") is False

    def test_is_remote_unknown(self) -> None:
        """'Atlanta, GA' → None (no keyword)."""
        assert _is_remote("Atlanta, GA") is None


class TestParseShutterOutput:
    """Tests for _parse_shutter_output."""

    def test_parse_shutter_output_real_format(self) -> None:
        """Full Shutter output with 'extracted' key and nested 'prompt_injection'.

        Regression test for the JSON key bug fix (was 'text', now 'extracted').
        """
        output = {
            "extracted": (
                "Title: Senior DevOps Engineer\n"
                "Company: CloudCorp\n"
                "Location: Remote\n"
                "Salary: $130,000 - $160,000\n\n"
                "We are looking for a DevOps engineer to manage our infrastructure."
            ),
            "prompt_injection": {
                "detected": True,
                "details": "Suspicious instruction found",
            },
            "model": "accurate",
            "tokens": 450,
        }

        result = _parse_shutter_output("https://example.com/job/1", output)

        assert result.url == "https://example.com/job/1"
        assert result.title == "Senior DevOps Engineer"
        assert result.company == "CloudCorp"
        assert result.location == "Remote"
        assert result.remote is True
        assert result.salary_min == 130000
        assert result.salary_max == 160000
        assert result.pi_detected is True
        assert result.description is not None
        assert "DevOps" in result.description
