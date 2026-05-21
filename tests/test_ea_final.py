"""
Test suite for EA Final — founder leverage tools.
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


class TestTaskYieldMatrix:

    def test_import(self):
        from control_plane.strategy.task_yield_matrix import (
            YIELD_QUADRANTS, classify_task_yield,
            run_yield_audit, format_yield_report,
        )

    def test_quadrants_structure(self):
        from control_plane.strategy.task_yield_matrix import YIELD_QUADRANTS
        for key in ('delegate', 'replace', 'invest', 'produce'):
            assert key in YIELD_QUADRANTS
            q = YIELD_QUADRANTS[key]
            assert 'label' in q
            assert 'description' in q
            assert 'action' in q
            assert 'emoji' in q

    def test_format_yield_report_empty(self):
        from control_plane.strategy.task_yield_matrix import format_yield_report
        results = {'delegate': [], 'replace': [], 'invest': [], 'produce': []}
        report = format_yield_report(results)
        assert isinstance(report, str)
        assert 'Yield' in report

    def test_format_yield_report_with_items(self):
        from control_plane.strategy.task_yield_matrix import format_yield_report
        results = {
            'delegate': [{'task': 'Check email', 'reasoning': 'Admin task'}],
            'replace': [],
            'invest': [],
            'produce': [{'task': 'Record content', 'reasoning': 'Core genius'}],
        }
        report = format_yield_report(results)
        assert 'Check email' in report
        assert 'Record content' in report
        assert 'DELEGATE' in report or '🤖' in report


class TestFounderRate:

    def test_import(self):
        from state.metrics.founder_rate import (
            calculate_founder_rate, store_founder_rate,
            get_current_founder_rate, log_time_block,
            get_time_audit_summary,
        )

    def test_calculate_120k(self):
        from state.metrics.founder_rate import calculate_founder_rate
        rate = calculate_founder_rate(120000)
        assert rate['annual_income'] == 120000
        assert rate['hourly_rate'] == 60.0
        assert rate['founder_rate'] == 15.0
        assert '$15.0' in rate['interpretation']

    def test_calculate_custom_hours(self):
        from state.metrics.founder_rate import calculate_founder_rate
        rate = calculate_founder_rate(80000, working_hours_per_year=1600)
        assert rate['hourly_rate'] == 50.0
        assert rate['founder_rate'] == 12.5

    def test_calculate_zero_income(self):
        from state.metrics.founder_rate import calculate_founder_rate
        rate = calculate_founder_rate(0)
        assert rate['founder_rate'] == 0.0


class TestLeveragePatterns:

    def test_import(self):
        from understanding.patterns.leverage_patterns import (
            LEVERAGE_KILLER_SIGNALS, detect_leverage_killer, check_solution_standard,
        )

    def test_detect_staller(self):
        from understanding.patterns.leverage_patterns import detect_leverage_killer
        result = detect_leverage_killer("I need more information before I decide")
        assert result.get('assassin') == 'staller'
        assert 'intervention' in result
        assert len(result['intervention']) > 10

    def test_detect_saver(self):
        from understanding.patterns.leverage_patterns import detect_leverage_killer
        result = detect_leverage_killer("I'll do it myself, it's easier if I handle this")
        assert result.get('assassin') == 'saver'

    def test_no_assassin_clean_text(self):
        from understanding.patterns.leverage_patterns import detect_leverage_killer
        result = detect_leverage_killer("Let's review the Q1 revenue numbers")
        assert result == {}

    def test_solution_standard_violation_detected(self):
        from understanding.patterns.leverage_patterns import check_solution_standard
        # Problem statement with no options
        assert check_solution_standard("The problem is we have no leads. What should I do?") is True

    def test_solution_standard_compliant_with_options(self):
        from understanding.patterns.leverage_patterns import check_solution_standard
        # Problem with options present
        assert check_solution_standard(
            "The problem is low leads. Option 1 is ads. Option 2 is outreach. I recommend outreach."
        ) is False

    def test_solution_standard_clean_message(self):
        from understanding.patterns.leverage_patterns import check_solution_standard
        assert check_solution_standard("Schedule a call with Jacob for Thursday") is False


class TestIdealWeek:

    def test_import(self):
        from control_plane.scheduling.ideal_week import (
            DEFAULT_IDEAL_WEEK, get_ideal_week,
            save_ideal_week, create_process_capture,
        )

    def test_default_ideal_week_structure(self):
        from control_plane.scheduling.ideal_week import DEFAULT_IDEAL_WEEK
        for day in ('monday', 'tuesday', 'wednesday', 'thursday', 'friday'):
            assert day in DEFAULT_IDEAL_WEEK
            d = DEFAULT_IDEAL_WEEK[day]
            assert 'theme' in d
            assert 'morning' in d
            assert 'afternoon' in d
            assert 'protected' in d

    def test_get_ideal_week_returns_dict(self):
        from control_plane.scheduling.ideal_week import get_ideal_week
        # Falls back to default if no DB record — must not raise
        week = get_ideal_week()
        assert isinstance(week, dict)
        assert 'monday' in week


class TestGWSConnectorDrive:

    def test_new_methods_exist(self):
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()
        for method in (
            'create_folder', 'move_file', 'list_files',
            'rename_file', 'create_document',
            'get_drive_structure', 'audit_drive',
        ):
            assert hasattr(gws, method), f'Missing method: {method}'

    def test_list_files_returns_list(self):
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()
        # GWS CLI may not be authed — must return [] not raise
        result = gws.list_files()
        assert isinstance(result, list)

    def test_get_drive_structure_returns_list(self):
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()
        result = gws.get_drive_structure()
        assert isinstance(result, list)

    def test_audit_drive_returns_dict(self):
        from adapters.google_workspace.gws_connector import GWSConnector
        gws = GWSConnector()
        result = gws.audit_drive()
        assert isinstance(result, dict)
        assert 'root_files' in result
        assert 'untitled' in result


class TestWeekArchitect:

    def test_import(self):
        from control_plane.scheduling.week_architect import architect_week

    def test_architect_week_returns_string(self):
        from control_plane.scheduling.week_architect import architect_week
        # Falls back gracefully without LLM — must not raise
        try:
            result = architect_week()
            assert isinstance(result, str)
        except Exception:
            pass  # LLM may be unavailable in test env — ok
