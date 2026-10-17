import pytest
from founderreach.validation.deduplicator import Deduplicator

def test_url_canonicalization():
    dedup = Deduplicator()
    url1 = "https://news.ycombinator.com/item?id=12345&utm_source=twitter&utm_medium=social"
    url2 = "https://news.ycombinator.com/item?id=12345"
    assert dedup.canonicalize_url(url1) == dedup.canonicalize_url(url2)

def test_content_hashing():
    dedup = Deduplicator()
    text1 = "How do you check in on parents? "
    text2 = "how do   you check in on parents?"
    assert dedup.get_content_hash(text1) == dedup.get_content_hash(text2)

def test_duplicate_rejection():
    dedup = Deduplicator()
    url = "https://news.ycombinator.com/item?id=8888"
    text = "Unique discussion about elderly family care in Bangalore."
    
    assert dedup.is_duplicate(url, text) is False
    assert dedup.is_duplicate(url, text) is True
