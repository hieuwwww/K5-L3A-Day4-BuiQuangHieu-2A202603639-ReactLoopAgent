"""Bonus context and retry limits for the shared agent loop."""
import json
import unittest

from agent import run_agent
from bonus.tools import BonusTools
from bonus.test_agent import ScriptedProvider, call, final


class BonusLoopLimitsTests(unittest.TestCase):
    def test_repeated_429_stops_network_retries_but_reports_observation(self):
        tools = BonusTools(scenario='rate_limit_always')
        provider = ScriptedProvider([call('a', 'get_vercel_status', {}),
                                     call('b', 'get_vercel_status', {}),
                                     call('c', 'get_vercel_status', {}), final('Chưa xác minh được Vercel.')])
        result = run_agent('Kiểm tra Vercel', provider, tools, max_steps=5)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(tools.calls[('get_vercel_status', 'vercel')], 2)
        self.assertEqual(json.loads(provider.histories[1][-1]['content'])['error'], 'RATE_LIMITED')
        self.assertEqual(json.loads(provider.histories[3][-1]['content'])['error'], 'RATE_LIMITED')

    def test_noisy_status_keeps_trace_but_not_distractors_in_model_context(self):
        tools = BonusTools(scenario='noisy')
        provider = ScriptedProvider([call('a', 'get_vercel_status', {}), final('Đã xem snapshot.')])
        result = run_agent('Kiểm tra Vercel', provider, tools)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('distractors', result['trace'][1]['result'])
        self.assertNotIn('distractors', json.loads(provider.histories[1][-1]['content']))
