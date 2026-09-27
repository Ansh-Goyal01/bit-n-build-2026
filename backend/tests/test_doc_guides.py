"""R4 — document how-to guides: deterministic detection of common document
types in a scheme's documents markdown. Keys are language-invariant; the
frontend renders localized guide content (where to get it, cost, time) per key.
"""

from app.rules.doc_guides import GUIDE_KEYWORDS, guide_keys_for


class TestGuideKeysFor:
    def test_empty_markdown_yields_no_keys(self):
        assert guide_keys_for("") == []

    def test_no_known_documents_yields_no_keys(self):
        assert guide_keys_for("- Letter from your employer\n- Old utility bill") == []

    def test_detects_common_documents_from_realistic_markdown(self):
        markdown = (
            "The following documents are required:\n\n"
            "- Aadhaar Card\n"
            "- Bank account passbook\n"
            "- Caste certificate (for SC/ST applicants)\n"
            "- Income certificate issued by the competent authority\n"
            "- Passport-size photograph\n"
        )
        keys = guide_keys_for(markdown)
        assert "aadhaar" in keys
        assert "bank_account" in keys
        assert "caste_certificate" in keys
        assert "income_certificate" in keys
        assert "photo" in keys

    def test_detection_is_case_insensitive(self):
        assert guide_keys_for("AADHAAR card and RATION CARD") == [
            "aadhaar",
            "ration_card",
        ]

    def test_bpl_matches_only_as_a_whole_word(self):
        assert guide_keys_for("BPL card of the family") == ["bpl_card"]
        assert guide_keys_for("a BPLXYZ reference code") == []

    def test_order_is_stable_declaration_order(self):
        markdown = "Income certificate, then Aadhaar, then land records (khatauni)."
        keys = guide_keys_for(markdown)
        # declaration order of GUIDE_KEYWORDS, not appearance order in the text
        expected = [k for k in GUIDE_KEYWORDS if k in set(keys)]
        assert keys == expected

    def test_every_guide_key_is_detectable_by_its_own_keywords(self):
        for key, keywords in GUIDE_KEYWORDS.items():
            assert guide_keys_for(f"Bring your {keywords[0]}.") == [key]


class TestPipelineWiring:
    def test_scheme_result_carries_guide_keys(self):
        from app.agent.state import SchemeResult

        result = SchemeResult(
            scheme_id="pm-kisan",
            scheme_name="PM-KISAN",
            short_name="PM-KISAN",
            verdict="eligible",
            summary="s",
            reasons=[],
            missing_info=[],
            document_guide_keys=["aadhaar", "land_records"],
        )
        assert result.document_guide_keys == ["aadhaar", "land_records"]

    def test_compose_populates_guide_keys_from_documents_section(self):
        import inspect

        from app.agent import rules_nodes

        source = inspect.getsource(rules_nodes.rules_assess_and_compose)
        assert "guide_keys_for" in source, (
            "rules_assess_and_compose must derive document_guide_keys "
            "from the documents section"
        )
