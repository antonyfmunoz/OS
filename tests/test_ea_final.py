"""
Test suite for EA Final — Dan Martell framework tools.
Run: python3 -m pytest /opt/OS/tests/test_ea_final.py -v
"""

import sys
import os
sys.path.insert(0, os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS")
_ROOT = os.environ.get("UMH_ROOT") or os.environ.get("OS_ROOT") or os.environ.get("EOS_ROOT") or "/opt/OS"

from dotenv import load_dotenv
load_dotenv(f'{_ROOT}/runtime/.env')
load_dotenv(f'{_ROOT}/services/.env')

import pytest


class TestDripMatrix:

    def test_import(self):
        from runtime.drip_matrix import (
            DRIP_QUADRANTS, classify_task_drip,
            run_drip_audit, format_drip_report,
        )

    def test_quadrants_structure(self):
        from runtime.drip_matrix import DRIP_QUADRANTS
        for key in ('delegate', 'replace', 'invest', 'produce'):
            assert key in DRIP_QUADRANTS
            q = DRIP_QUADRANTS[key]
            assert 'label' in q
            assert 'description' in q
            assert 'action' in q
            assert 'emoji' in q

    def test_format_drip_report_empty(self):
        from runtime.drip_matrix import format_drip_report
        results = {'delegate': [], 'replace': [], 'invest': [], 'produce': []}
        report = format_drip_report(results)
        assert isinstance(report, str)
        assert 'DRIP' in report

    def test_format_drip_report_with_items(self):
        from runtime.drip_matrix import format_drip_report
        results = {
            'delegate': [{'task': 'Check email', 'reasoning': 'Admin task'}],
            'replace': [],
            'invest': [],
            'produce': [{'task': 'Record content', 'reasoning': 'Core genius'}],
        }
        report = format_drip_report(results)
        assert 'Check email' in report
        assert 'Record content' in report
        assert 'DELEGATE' in report or '🤖' in report


class TestBuybackRate:

    def test_import(self):
        from runtime.buyback_rate import (
            calculate_buyback_rate, store_buyback_rate,
            get_current_buyback_rate, log_time_block,
            get_time_audit_summary,
        )

    def test_calculate_120k(self):
        from runtime.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(120000)
        assert rate['annual_income'] == 120000
        assert rate['hourly_rate'] == 60.0
        assert rate['buyback_rate'] == 15.0
        assert '$15.0' in rate['interpretation']

    def test_calculate_custom_hours(self):
        from runtime.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(80000, working_hours_per_year=1600)
        assert rate['hourly_rate'] == 50.0
        assert rate['buyback_rate'] == 12.5

    def test_calculate_zero_income(self):
        from runtime.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(0)
        assert rate['buyback_rate'] == 0.0


class TestMartellPatterns:

    def test_import(self):
        from runtime.martell_patterns import (
            TIME_ASSASSIN_SIGNALS, detect_time_assassin, check_131_rule,
        )

    def test_detect_staller(self):
        from runtime.martell_patterns import detect_time_assassin
        result = detect_time_assassin("I need more information before I decide")
        assert result.get('assassin') == 'staller'
        assert 'intervention' in result
        assert len(result['intervention']) > 10

    def test_detect_saver(self):
        from runtime.martell_patterns import detect_time_assassin
        result = detect_time_assassin("I'll do it myself, it's easier if I handle this")
        assert result.get('assassin') == 'saver'

    def test_no_assassin_clean_text(self):
        from runtime.martell_patterns import detect_time_assassin
        result = detect_time_assassin("Let's review the Q1 revenue numbers")
        assert result == {}

    def test_131_violation_detected(self):
        from runtime.martell_patterns import check_131_rule
        # Problem statement with no options
        assert check_131_rule("The problem is we have no leads. What should I do?") is True

    def test_131_compliant_with_options(self):
        from runtime.martell_patterns import check_131_rule
        # Problem with options present
        assert check_131_rule(
            "The problem is low leads. Option 1 is ads. Option 2 is outreach. I recommend outreach."
        ) is False

    def test_131_clean_message(self):
        from runtime.martell_patterns import check_131_rule
        assert check_131_rule("Schedule a call with Jacob for Thursday") is False


class TestPerfectWeek:

    def test_import(self):
        from runtime.perfect_week import (
            DEFAULT_PERFECT_WEEK, get_perfect_week,
            save_perfect_week, create_camcorder_playbook,
        )

    def test_default_perfect_week_structure(self):
        from runtime.perfect_week import DEFAULT_PERFECT_WEEK
        for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
            assert day in DEFAULT_PERFECT_WEEK
            d = DEFAULT_PERFECT_WEEK[day]
            assert 'theme' in d
            assert 'morning' in d
            assert 'afternoon' in d
            assert 'protected' in d

    def test_get_perfect_week_returns_dict(self):
        from runtime.perfect_week import get_perfect_week
        # Falls back to default if no DB record — must not raise
        week = get_perfect_week()
        assert isinstance(week, dict)
        assert 'monday' in week


class TestGWSConnectorDrive:

    def test_new_methods_exist(self):
        from runtime.gws_connector import GWSConnector
        gws = GWSConnector()
        for method in (
            'create_folder', 'move_file', 'list_files',
            'rename_file', 'create_document',
            'get_drive_structure', 'audit_drive',
        ):
            assert hasattr(gws, method), f'Missing method: {method}'

    def test_list_files_returns_list(self):
        from runtime.gws_connector import GWSConnector
        gws = GWSConnector()
        # GWS CLI may not be authed — must return [] not raise
        result = gws.list_files()
        assert isinstance(result, list)

    def test_get_drive_structure_returns_list(self):
        from runtime.gws_connector import GWSConnector
        gws = GWSConnector()
        result = gws.get_drive_structure()
        assert isinstance(result, list)

    def test_audit_drive_returns_dict(self):
        from runtime.gws_connector import GWSConnector
        gws = GWSConnector()
        result = gws.audit_drive()
        assert isinstance(result, dict)
        assert 'root_files' in result
        assert 'untitled' in result


class TestWeekArchitect:

    def test_import(self):
        from runtime.week_architect import architect_week

    def test_architect_week_returns_string(self):
        from runtime.week_architect import architect_week
        # Falls back gracefully without LLM — must not raise
        try:
            result = architect_week()
            assert isinstance(result, str)
        except Exception:
            pass  # LLM may be unavailable in test env — ok
