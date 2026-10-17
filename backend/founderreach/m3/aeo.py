"""Question and direct-answer analysis grounded in M2 observations."""
from __future__ import annotations

import re
from pydantic import BaseModel, Field

from founderreach.evidence import EvidenceObservation
from founderreach.models import ProductProfile
from founderreach.m3.site import SiteAudit, SitePage, tokens


def normalized_tokens(text: str) -> set[str]:
    base = tokens(text)
    result = set()
    for word in base:
        if word.endswith("ies") and len(word) > 5:
            word = word[:-3] + "y"
        elif word.endswith("ing") and len(word) > 6:
            word = word[:-3]
        elif word.endswith("ed") and len(word) > 5:
            word = word[:-2]
        elif word.endswith("s") and len(word) > 5:
            word = word[:-1]
        if word.endswith("er") and len(word) > 6:
            word = word[:-2]
        result.add(word)
    return result


def similarity(left: str, right: str) -> float:
    a, b = normalized_tokens(left), normalized_tokens(right)
    return len(a & b) / len(a | b) if a and b else 0.0


class QuestionCluster(BaseModel):
    intent_key: str
    representative_question: str
    observation_ids: list[str]
    provenance_labels: list[str]
    evidence_state: str
    matching_page: str | None = None
    direct_answer_observed: bool = False
    faq_suitable: bool = False
    priority: float = Field(ge=0, le=1)


class AEOFinding(BaseModel):
    code: str
    question: str
    affected_url: str | None = None
    observation_ids: list[str]
    observed_evidence: str
    recommendation: str
    confidence: float = Field(ge=0, le=1)
    limitations: str


class AEOReport(BaseModel):
    business_id: str
    clusters: list[QuestionCluster] = Field(default_factory=list)
    findings: list[AEOFinding] = Field(default_factory=list)
    excluded_observation_ids: list[str] = Field(default_factory=list)


def _answer_present(page: SitePage, question: str) -> bool:
    question_terms = normalized_tokens(question)
    for paragraph in page.paragraphs:
        shared = question_terms & normalized_tokens(paragraph)
        # A short repeated heading or keyword is not a direct answer.
        if len(paragraph) >= 50 and len(shared) >= 2 and len(shared) / max(1, len(question_terms)) >= 0.2:
            return True
    return False


def _polarity(statement: str) -> tuple[frozenset[str], bool] | None:
    low = statement.lower()
    if not re.search(r"\b(?:is|are|supports?|offers?|provides?|available|can)\b", low):
        return None
    negative = bool(re.search(r"\b(?:not|never|cannot|can't|does not|do not|no)\b", low))
    words = normalized_tokens(re.sub(r"\b(?:not|never|cannot|can't|does|do|no)\b", " ", low))
    return (frozenset(words), negative) if len(words) >= 3 else None


class AEOEngine:
    def analyze(self, profile: ProductProfile, observations: list[EvidenceObservation],
                site: SiteAudit) -> AEOReport:
        if not profile.confirmed or site.business_id != profile.identifier:
            raise PermissionError("AEO requires one confirmed business and its site audit")
        report = AEOReport(business_id=profile.identifier)
        eligible = []
        for observation in observations:
            if observation.business_id != profile.identifier:
                raise PermissionError("Cross-business evidence is not allowed")
            if observation.kind not in ("customer_question", "customer_need", "complaint") or observation.relevance_state == "rejected":
                continue
            state = observation.current_verification_state()
            if state == "verified" and observation.may_support("research"):
                eligible.append(observation)
            elif observation.provenance == "founder_attested" and observation.verification_state == "attested":
                eligible.append(observation)
            else:
                report.excluded_observation_ids.append(observation.observation_id)
        groups: list[list[EvidenceObservation]] = []
        for observation in sorted(eligible, key=lambda x: x.observation_id):
            question = observation.claim if "?" in observation.claim else observation.excerpt
            match = next((group for group in groups if similarity(question,
                         group[0].claim if "?" in group[0].claim else group[0].excerpt) >= 0.35), None)
            if match is None:
                groups.append([observation])
            else:
                match.append(observation)
        for group in groups:
            representative = group[0].claim if "?" in group[0].claim else group[0].excerpt
            words = sorted(normalized_tokens(representative))
            intent_key = "-".join(words[:8]) or group[0].observation_id
            candidates = [(max([similarity(representative, page.title + " " + " ".join(h[1] for h in page.headings))]
                               + [similarity(representative, paragraph) for paragraph in page.paragraphs]), page)
                          for page in site.pages if "noindex" not in page.robots_meta
                          and "noindex" not in page.x_robots_tag]
            score, best = max(candidates, key=lambda x: x[0]) if candidates else (0.0, None)
            matching = best if score >= 0.24 else None
            direct = _answer_present(matching, representative) if matching else False
            all_verified = all(x.current_verification_state() == "verified" for x in group)
            state = "source_verified" if all_verified else "founder_attested_alternative"
            priority = min(1.0, 0.5 + min(0.2, len(group) * 0.05) +
                           (0.1 if any(x.freshness_state == "timely" for x in group) else 0) +
                           (0.1 if not matching else 0)) if all_verified else 0.25
            cluster = QuestionCluster(intent_key=intent_key, representative_question=representative,
                observation_ids=[x.observation_id for x in group],
                provenance_labels=sorted({x.provenance for x in group}), evidence_state=state,
                matching_page=matching.url if matching else None, direct_answer_observed=direct,
                faq_suitable="?" in representative and direct, priority=priority)
            report.clusters.append(cluster)
            if not matching or not direct:
                report.findings.append(AEOFinding(code="missing_page" if not matching else "missing_direct_answer",
                    question=representative, affected_url=matching.url if matching else None,
                    observation_ids=cluster.observation_ids,
                    observed_evidence="; ".join(x.excerpt[:160] for x in group),
                    recommendation=("Research a single answer-first page for this observed question" if not matching
                                    else "Add a concise, supported answer before detailed explanation"),
                    confidence=0.8 if all_verified else 0.4,
                    limitations="Evidence count is not demand volume; attestation is not independent verification"))
            elif "?" in representative and not any("FAQPage" in str(value) for value in matching.jsonld):
                report.findings.append(AEOFinding(code="faq_schema_suitability", question=representative,
                    affected_url=matching.url, observation_ids=cluster.observation_ids,
                    observed_evidence="Question and direct answer observed on page",
                    recommendation="Review whether FAQ structured data accurately reflects visible content",
                    confidence=0.65, limitations="Markup does not guarantee search display"))
            self._assess_claims(report, group, matching)
        return report

    @staticmethod
    def _assess_claims(report: AEOReport, group: list[EvidenceObservation], page: SitePage | None):
        if not page:
            return
        claims = [x.claim for x in group]
        for paragraph in page.paragraphs:
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                signature = _polarity(sentence)
                if signature and any((other := _polarity(claim)) and
                                     len(signature[0] & other[0]) / max(1, len(signature[0] | other[0])) >= 0.5
                                     and signature[1] != other[1] for claim in claims):
                    report.findings.append(AEOFinding(code="contradictory_answer", question=group[0].claim,
                        affected_url=page.url, observation_ids=[x.observation_id for x in group],
                        observed_evidence=sentence[:200], recommendation="Resolve the conflicting statement before drafting",
                        confidence=0.75, limitations="Rule-based contradiction check requires human review"))
            if re.search(r"\b(?:guaranteed|always|\d+%|24/7)\b", paragraph.lower()) and not any(
                    similarity(paragraph, claim) >= 0.55 for claim in claims):
                report.findings.append(AEOFinding(code="unsupported_answer_claim", question=group[0].claim,
                    affected_url=page.url, observation_ids=[x.observation_id for x in group],
                    observed_evidence=paragraph[:200], recommendation="Supply independent support or soften the claim",
                    confidence=0.7, limitations="Keyword-based claim screen; human factual review required"))
