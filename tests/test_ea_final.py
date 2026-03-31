"""
Test suite for EA Final — Dan Martell framework tools.
Run: python3 -m pytest /opt/OS/tests/test_ea_final.py -v
"""

import sys
sys.path.insert(0, '/opt/OS')

from dotenv import load_dotenv
load_dotenv('/opt/OS/eos_ai/.env')
load_dotenv('/opt/OS/13_Scripts/.env')

import pytest


class TestDripMatrix:

    def test_import(self):
        from eos_ai.drip_matrix import (
            DRIP_QUADRANTS, classify_task_drip,
            run_drip_audit, format_drip_report,
        )

    def test_quadrants_structure(self):
        from eos_ai.drip_matrix import DRIP_QUADRANTS
        for key in ('delegate', 'replace', 'invest', 'produce'):
            assert key in DRIP_QUADRANTS
            q = DRIP_QUADRANTS[key]
            assert 'label' in q
            assert 'description' in q
            assert 'action' in q
            assert 'emoji' in q

    def test_format_drip_report_empty(self):
        from eos_ai.drip_matrix import format_drip_report
        results = {'delegate': [], 'replace': [], 'invest': [], 'produce': []}
        report = format_drip_report(results)
        assert isinstance(report, str)
        assert 'DRIP' in report

    def test_format_drip_report_with_items(self):
        from eos_ai.drip_matrix import format_drip_report
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
        from eos_ai.buyback_rate import (
            calculate_buyback_rate, store_buyback_rate,
            get_current_buyback_rate, log_time_block,
            get_time_audit_summary,
        )

    def test_calculate_120k(self):
        from eos_ai.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(120000)
        assert rate['annual_income'] == 120000
        assert rate['hourly_rate'] == 60.0
        assert rate['buyback_rate'] == 15.0
        assert '$15.0' in rate['interpretation']

    def test_calculate_custom_hours(self):
        from eos_ai.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(80000, working_hours_per_year=1600)
        assert rate['hourly_rate'] == 50.0
        assert rate['buyback_rate'] == 12.5

    def test_calculate_zero_income(self):
        from eos_ai.buyback_rate import calculate_buyback_rate
        rate = calculate_buyback_rate(0)
        assert rate['buyback_rate'] == 0.0
