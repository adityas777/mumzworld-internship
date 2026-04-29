"""
schema.py - Pydantic models for the Moms Verdict Engine.
Defines strict input/output contracts with validation logic.
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class VerdictOutput(BaseModel):
    """
    Structured output schema for the verdict engine.
    All fields are validated; nulls are allowed when data is insufficient.
    """

    verdict_en: Optional[str] = Field(
        None,
        description="One-sentence English verdict summarizing the product.",
        max_length=300,
    )
    verdict_ar: Optional[str] = Field(
        None,
        description="One-sentence Arabic verdict — natural, not a direct translation.",
        max_length=300,
    )
    pros: list[str] = Field(
        default_factory=list,
        description="List of positive aspects mentioned in reviews.",
    )
    cons: list[str] = Field(
        default_factory=list,
        description="List of negative aspects mentioned in reviews.",
    )
    common_issues: list[str] = Field(
        default_factory=list,
        description="Recurring problems or complaints across multiple reviews.",
    )
    sentiment_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Overall sentiment: 0 = very negative, 1 = very positive.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence in the verdict. Lowered when reviews conflict or are sparse.",
    )
    should_buy: Optional[bool] = Field(
        None,
        description="Buy recommendation. Null if data is insufficient or too contradictory.",
    )

    @field_validator("pros", "cons", "common_issues", mode="before")
    @classmethod
    def deduplicate_lists(cls, v):
        """Remove duplicate entries while preserving order."""
        if not isinstance(v, list):
            return v
        seen = set()
        result = []
        for item in v:
            normalized = item.strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                result.append(item.strip())
        return result

    @model_validator(mode="after")
    def validate_should_buy_consistency(self):
        """
        If confidence is very low, should_buy should be null.
        If sentiment is extreme, should_buy should align.
        """
        if self.confidence < 0.2:
            self.should_buy = None
        return self

    model_config = {"str_strip_whitespace": True}


class ReviewInput(BaseModel):
    """Input model for a batch of product reviews."""

    product_name: Optional[str] = Field(None, description="Optional product name for context.")
    reviews: list[str] = Field(
        ...,
        min_length=1,
        description="List of raw review texts.",
    )

    @field_validator("reviews", mode="before")
    @classmethod
    def filter_empty_reviews(cls, v):
        """Strip and remove blank reviews."""
        if not isinstance(v, list):
            raise ValueError("reviews must be a list")
        filtered = [r.strip() for r in v if isinstance(r, str) and r.strip()]
        if not filtered:
            raise ValueError("At least one non-empty review is required.")
        return filtered
