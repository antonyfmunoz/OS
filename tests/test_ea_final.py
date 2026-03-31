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
