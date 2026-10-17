"""Invented test data only; never derived from a client profile or label file."""
from founderreach.models import ProductProfile


def care_profile() -> ProductProfile:
    return ProductProfile(
        identifier="ayana", name="Synthetic Care", confirmed=True,
        website="https://care-fixture.example.com/",
        description="A fictional service for families coordinating elder-care check-ins.",
        target_audiences=["NRI families with elderly parents in India"],
        target_markets=["India", "USA"],
        keywords=["parents medicine reminders", "elderly parent check in calls", "NRI parent care"],
        pain_points=["daily medicine reminders for parents", "regular check in calls",
                     "emergency reassurance for families"],
        customer_fit_signals=["NRI", "elderly parents", "parents live alone"],
        problem_patterns=[r"elderly parents", r"medicine reminders?",
                          r"check[ -]?in calls?|check in on", r"mother.*medicine|mom.*medication"],
        direct_problem_patterns=[r"my mother.*medicine", r"my mom.*medication",
                                 r"I worry.*emergency"],
        disqualifying_patterns=[r"boomer parents", r"help with kids", r"webhook|meta api"],
        negative_keywords=["compiler", "airline", "spam"],
    )


CARE_SYNTHETIC_LABELS = [
    {"id": "care_pos_1", "source": "Synthetic", "url": "https://example.com/fixture/1",
     "label": "POTENTIAL_CUSTOMER_INTENT",
     "text": "I am an NRI. My elderly parents live alone in India. How do people handle daily medicine reminders and regular check in calls?"},
    {"id": "care_pos_2", "source": "Synthetic", "url": "https://example.com/fixture/2",
     "label": "POTENTIAL_CUSTOMER_INTENT",
     "text": "I worry because my parents live alone. I need a reliable medicine reminder and a check in call."},
    {"id": "care_neg_1", "source": "Synthetic", "url": "https://example.com/fixture/3",
     "label": "NOT_CUSTOMER_INTENT", "text": "Airline route scheduling algorithms are interesting."},
]
