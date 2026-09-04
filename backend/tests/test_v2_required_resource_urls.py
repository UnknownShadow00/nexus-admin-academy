"""A required resource must be openable, or the content load fails.

Progression counts a required resource as done only once the student opens
and completes it, and the presentation layer renders anything that is not an
absolute http(s) URL as no link at all. A required resource with an empty or
malformed URL is therefore a permanent deadlock: Continue points at it, and
there is nothing to click. Today's content happens to have none — this makes
that a rule rather than an accident.

Optional resources stay lenient on purpose; they never block anything.
"""

import pytest

from app.models.certification import LearningResource, LearningResourceLink
from app.services.v2_content_loader import (
    ContentValidationError,
    load_all,
    load_resources,
    valid_external_url,
)

LESSON_LINK = "lesson.aplus.core1.networking_fundamentals.tcp_udp_ports"


@pytest.mark.parametrize(
    "url",
    ["https://example.com/guide", "http://example.com/a?b=c#d"],
)
def test_absolute_http_urls_are_valid(url):
    assert valid_external_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        None, "", "   ",
        "example.com/guide",        # no scheme
        "https://",                 # no host
        "/relative/path",
        "ftp://example.com/file",
        "javascript:alert(1)",
        "mailto:someone@example.com",
    ],
)
def test_unopenable_urls_are_rejected(url):
    assert valid_external_url(url) is False


def _resource_yaml(tmp_path, *, url, required):
    body = [
        "resources:",
        "  - resource_key: res.test.required_url",
        '    title: "Fixture resource"',
        "    resource_type: reference",
        '    provider: "Fixture"',
    ]
    if url is not None:
        body.append(f'    url: "{url}"')
    body += [
        "    certification_version: comptia_aplus_220-1201",
        "    permission_status: owned",
        "    active: true",
        "    links:",
        "      - module_key: module.aplus.core1.networking_fundamentals",
        f"        required: {'true' if required else 'false'}",
        "        order: 1",
    ]
    path = tmp_path / "fixture-resources.yaml"
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return str(path)


@pytest.mark.parametrize(
    "url",
    [None, "", "example.com/no-scheme", "/relative", "ftp://example.com/x"],
    ids=["missing", "empty", "no-scheme", "relative", "wrong-scheme"],
)
def test_a_required_resource_without_a_usable_url_is_refused(db, tmp_path, url):
    load_all(db)
    with pytest.raises(ContentValidationError) as excinfo:
        load_resources(db, _resource_yaml(tmp_path, url=url, required=True))
    assert "required resource needs a valid" in str(excinfo.value)
    assert "blocks progression" in str(excinfo.value)


def test_a_required_resource_with_a_valid_url_loads(db, tmp_path):
    load_all(db)
    load_resources(db, _resource_yaml(tmp_path, url="https://example.com/ok", required=True))
    row = db.query(LearningResource).filter_by(resource_key="res.test.required_url").one()
    assert row.url == "https://example.com/ok"
    link = db.query(LearningResourceLink).filter_by(resource_id=row.id).one()
    assert link.is_required is True


def test_an_optional_resource_may_still_have_no_url(db, tmp_path):
    """Optional resources never block progression, so they stay lenient."""
    load_all(db)
    load_resources(db, _resource_yaml(tmp_path, url=None, required=False))
    row = db.query(LearningResource).filter_by(resource_key="res.test.required_url").one()
    assert row.url is None


def test_promoting_an_urlless_resource_to_required_is_refused(db, tmp_path):
    """The block applies on re-load, not just first import."""
    load_all(db)
    load_resources(db, _resource_yaml(tmp_path, url=None, required=False))
    with pytest.raises(ContentValidationError):
        load_resources(db, _resource_yaml(tmp_path, url=None, required=True))


def test_the_shipped_content_has_no_unopenable_required_resource(db):
    """Regression guard on the real content, not just a fixture."""
    from app.services.v2_content_loader import load_module

    load_module(db, commit=False)
    offenders = [
        resource.resource_key
        for link, resource in db.query(LearningResourceLink, LearningResource)
        .join(LearningResource, LearningResource.id == LearningResourceLink.resource_id)
        .filter(LearningResourceLink.is_required.is_(True))
        .all()
        if not valid_external_url(resource.url)
    ]
    assert offenders == []
    db.rollback()
