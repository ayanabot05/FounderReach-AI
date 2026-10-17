from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator

def utc_now():
    return datetime.now(timezone.utc)

class ProductProfile(BaseModel):
    name: str = Field(..., description="Product name (e.g. AYANA)")
    website: str = Field(..., description="Product website URL")
    description: str = Field(..., description="Clear explanation of the product and what it does")
    target_audiences: List[str] = Field(default_factory=list, description="Target customer personas (e.g. NRIs with parents in India)")
    target_markets: List[str] = Field(default_factory=list, description="Target countries or regions (e.g. India, USA, Global)")
    keywords: List[str] = Field(default_factory=list, description="Core search keywords")
    pain_points: List[str] = Field(default_factory=list, description="Specific problems the product solves")
    negative_keywords: List[str] = Field(default_factory=list, description="Irrelevant keywords to filter out")
    max_actionable_age_days: int = Field(default=90, description="Strict freshness gate: maximum age in days for actionable outreach")

class DiscussionItem(BaseModel):
    id: str = Field(..., description="Platform-unique identifier")
    platform: str = Field(..., description="Platform name (e.g. Hacker News, Reddit)")
    original_url: str = Field(..., description="Direct permalink to discussion or comment")
    title: Optional[str] = Field(None, description="Discussion title / thread title")
    author: Optional[str] = Field(None, description="Username or author name")
    text: str = Field(..., description="Full text of the discussion/comment")
    created_at: Optional[datetime] = Field(None, description="Publication timestamp")
    raw_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw platform payload for auditing")

class ScoreBreakdown(BaseModel):
    problem_fit: float = Field(..., ge=0, le=30, description="Max 30: Does discussion match pain points solved?")
    customer_fit: float = Field(..., ge=0, le=20, description="Max 20: Does author fit target audience?")
    expressed_intent: float = Field(..., ge=0, le=20, description="Max 20: Active solution seeker vs passive mention")
    recency: float = Field(..., ge=0, le=15, description="Max 15: Freshness and actionability")
    evidence_quality: float = Field(..., ge=0, le=15, description="Max 15: Specificity and verifiable context")
    total_score: float = Field(..., ge=0, le=100, description="Total 100-point score")
    justification: Dict[str, str] = Field(default_factory=dict, description="Transparent justification for each subscore")

class SourceVerification(BaseModel):
    verified: bool = Field(..., description="Whether live URL and content were successfully verified (SOURCE_VERIFIED)")
    http_status: Optional[int] = Field(None, description="HTTP status code received")
    verified_url: str = Field(..., description="Verified canonical URL")
    evidence_excerpt: str = Field(..., description="Exact verifiable excerpt found in the live content")
    checked_at: datetime = Field(default_factory=utc_now, description="Timestamp of live verification check")
    verification_notes: Optional[str] = Field(None, description="Details or warnings from the verification attempt")

class CustomerOpportunity(BaseModel):
    id: str = Field(..., description="Unique opportunity ID (hash of source ID and product)")
    product_name: str = Field(..., description="Associated product")
    platform: str = Field(..., description="Hacker News, Reddit, etc.")
    original_url: str = Field(..., description="Verified original URL")
    discussion_date: Optional[str] = Field(None, description="Formatted date of discussion")
    author: Optional[str] = Field(None, description="Author identifier")
    
    # Validation Machine Enhancements (CEO Directive)
    classification: Literal["ACTIONABLE_OPPORTUNITY", "RESEARCH_INSIGHT", "IRRELEVANT"] = Field(
        default="RESEARCH_INSIGHT",
        description="Explicit separation of actionable outreach vs research insight vs irrelevant"
    )
    source_status: Literal["SOURCE_VERIFIED", "SOURCE_UNVERIFIED"] = Field(
        default="SOURCE_UNVERIFIED",
        description="Confirms live HTTP 200 and excerpt presence"
    )
    intent_status: Literal["CUSTOMER_INTENT_VERIFIED", "CUSTOMER_INTENT_UNVERIFIED"] = Field(
        default="CUSTOMER_INTENT_UNVERIFIED",
        description="Confirms author explicitly expressed direct customer problem or intent"
    )
    direct_problem_evidence: Optional[str] = Field(
        None,
        description="Verbatim sentence proving the customer problem exists (no loose inference)"
    )
    rejection_reasons: List[str] = Field(
        default_factory=list,
        description="Explicit reasons if not classified as an actionable opportunity"
    )
    
    customer_problem: str = Field(..., description="Succinct synthesis of the customer's stated problem")
    why_relevant: str = Field(..., description="Explicit explanation of why the product is relevant to this discussion")
    evidence_excerpt: str = Field(..., description="Exact quote verified from original discussion")
    score: ScoreBreakdown = Field(..., description="Transparent 100-point score")
    suggested_response: str = Field(default="", description="Draft only for verified actionable records; human approval required")
    verification: SourceVerification = Field(..., description="Source verification status and audit trail")
    feedback: Optional[str] = Field(None, description="User feedback: 'relevant', 'irrelevant', or None")
    feedback_notes: Optional[str] = Field(None, description="Founder notes on opportunity quality")
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def withhold_unapproved_drafts(self):
        if (self.classification != "ACTIONABLE_OPPORTUNITY" or
            self.source_status != "SOURCE_VERIFIED" or
            self.intent_status != "CUSTOMER_INTENT_VERIFIED" or
            not self.verification.verified):
            self.suggested_response = ""
        return self
