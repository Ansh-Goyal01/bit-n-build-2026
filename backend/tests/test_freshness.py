"""Tests for the R7 scheme-freshness monitor (pure diff logic, no network)."""

from pathlib import Path

from app.ingestion.freshness import (
    REVIEW_CRITICAL_SECTIONS,
    build_scheme_diff,
    diff_scheme_sections,
    live_rule_scheme_ids,
)
from app.ingestion.models import CorpusDoc, Reference


def _doc(sections: dict[str, str], references: list[Reference] | None = None) -> CorpusDoc:
    return CorpusDoc(
        scheme_id="pm-kisan",
        short_name="PM-KISAN",
        name="Pradhan Mantri Kisan Samman Nidhi",
        category="farmers",
        level="Central",
        ministry="Ministry of Agriculture",
        page_url="https://www.myscheme.gov.in/schemes/pm-kisan",
        references=references or [],
        fetched_at="2026-07-10",
        sections=sections,
    )


def test_identical_sections_produce_no_changes() -> None:
    # Arrange
    sections = {"eligibility": "All landholding farmer families.", "faq": "Q and A."}

    # Act
    changes = diff_scheme_sections(sections, dict(sections))

    # Assert
    assert changes == []


def test_modified_eligibility_is_review_critical() -> None:
    # Arrange
    old = {"eligibility": "Income below Rs 10,000 per month."}
    new = {"eligibility": "Income below Rs 15,000 per month."}

    # Act
    changes = diff_scheme_sections(old, new)

    # Assert
    assert len(changes) == 1
    assert changes[0].section == "eligibility"
    assert changes[0].change == "modified"
    assert changes[0].review_critical is True


def test_modified_faq_is_not_review_critical() -> None:
    # Arrange
    old = {"faq": "Old answer."}
    new = {"faq": "New answer."}

    # Act
    changes = diff_scheme_sections(old, new)

    # Assert
    assert len(changes) == 1
    assert changes[0].review_critical is False


def test_added_and_removed_sections_are_detected() -> None:
    # Arrange
    old = {"eligibility": "Rules.", "faq": "Q."}
    new = {"eligibility": "Rules.", "exclusions": "Government employees."}

    # Act
    changes = diff_scheme_sections(old, new)

    # Assert
    by_section = {change.section: change for change in changes}
    assert by_section["exclusions"].change == "added"
    assert by_section["faq"].change == "removed"


def test_fetched_at_alone_does_not_flag_a_scheme() -> None:
    # Arrange — fresh fetch always has a new fetched_at stamp
    old_doc = _doc({"eligibility": "Same text."})
    new_doc = _doc({"eligibility": "Same text."}).model_copy(update={"fetched_at": "2026-07-17"})

    # Act
    diff = build_scheme_diff(old_doc, new_doc, checkable=True)

    # Assert
    assert diff.changes == []
    assert diff.references_changed is False
    assert diff.needs_review is False


def test_critical_change_on_checkable_scheme_needs_review() -> None:
    # Arrange
    old_doc = _doc({"eligibility": "Age 60+."})
    new_doc = _doc({"eligibility": "Age 65+."})

    # Act
    diff = build_scheme_diff(old_doc, new_doc, checkable=True)

    # Assert
    assert diff.needs_review is True
    assert diff.checkable is True


def test_informational_change_alone_does_not_need_review() -> None:
    # Arrange
    old_doc = _doc({"faq": "Old.", "eligibility": "Same."})
    new_doc = _doc({"faq": "New.", "eligibility": "Same."})

    # Act
    diff = build_scheme_diff(old_doc, new_doc, checkable=True)

    # Assert
    assert diff.needs_review is False
    assert len(diff.changes) == 1


def test_reference_url_change_is_detected() -> None:
    # Arrange
    old_doc = _doc({"eligibility": "Same."}, [Reference(title="Guidelines", url="https://a.gov/1")])
    new_doc = _doc({"eligibility": "Same."}, [Reference(title="Guidelines", url="https://a.gov/2")])

    # Act
    diff = build_scheme_diff(old_doc, new_doc, checkable=False)

    # Assert
    assert diff.references_changed is True


def test_live_rule_scheme_ids_reads_yaml_filenames(tmp_path: Path) -> None:
    # Arrange
    (tmp_path / "pm-kisan.yaml").write_text("rules: []", encoding="utf-8")
    (tmp_path / "apy.yaml").write_text("rules: []", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")

    # Act
    ids = live_rule_scheme_ids(tmp_path)

    # Assert
    assert ids == {"pm-kisan", "apy"}


def test_review_critical_sections_cover_rule_bearing_content() -> None:
    # Assert — the sections rules are encoded from must all be critical
    assert {"eligibility", "exclusions", "benefits", "documents"} <= REVIEW_CRITICAL_SECTIONS
    assert "faq" not in REVIEW_CRITICAL_SECTIONS
