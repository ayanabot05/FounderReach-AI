import pytest
from founderreach.connectors.hackernews import HackerNewsConnector
from founderreach.connectors.reddit import RedditConnector
from founderreach.profiles import load_profile

AYANA_PROFILE = load_profile("ayana")

def test_reddit_connector_disabled_by_policy():
    reddit = RedditConnector()
    assert reddit.is_enabled() is False
    assert reddit.search(AYANA_PROFILE) == []

def test_hackernews_connector_enabled():
    hn = HackerNewsConnector()
    assert hn.is_enabled() is True
    # Test HTML entity cleaning
    html_sample = "<p>My parents&#39; house is far away. <a href=\"http://test.com\">Link</a></p>"
    cleaned = hn._clean_html(html_sample)
    assert "<p>" not in cleaned
    assert "parents'" in cleaned
    assert "Link" in cleaned
