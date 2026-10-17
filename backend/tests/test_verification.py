import pytest
from unittest.mock import patch, MagicMock
from founderreach.validation.verifier import SourceVerifier

def test_source_verifier_success():
    verifier = SourceVerifier()
    mock_ctx = MagicMock()
    mock_ctx.status = 200
    mock_ctx.read.return_value = b"<html><body>My mother forgot her medicine in India.</body></html>"
    
    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = mock_ctx

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        res = verifier.verify_source("https://news.ycombinator.com/item?id=123", "My mother forgot her medicine in India.")
        assert res.verified is True
        assert res.http_status == 200

def test_source_verifier_missing_excerpt():
    verifier = SourceVerifier()
    mock_ctx = MagicMock()
    mock_ctx.status = 200
    mock_ctx.read.return_value = b"<html><body>Unrelated content about web design and CSS.</body></html>"

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = mock_ctx

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        res = verifier.verify_source("https://news.ycombinator.com/item?id=124", "Completely different text that does not exist.")
        assert res.verified is False

def test_source_verifier_404_failure():
    verifier = SourceVerifier()
    mock_ctx = MagicMock()
    mock_ctx.status = 404

    mock_urlopen = MagicMock()
    mock_urlopen.__enter__.return_value = mock_ctx

    with patch("urllib.request.urlopen", return_value=mock_urlopen):
        res = verifier.verify_source("https://news.ycombinator.com/item?id=999", "Some excerpt")
        assert res.verified is False
        assert res.http_status == 404
