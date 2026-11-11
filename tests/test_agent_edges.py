"""Edge cases of the model/tool handshake, using an offline provider."""
import json
import unittest

from agent import run_agent
from status_tools import StatusTools
from test_lab import FakeProvider, final, tool_call


class AgentEdgeTests(unittest.TestCase):
    def test_limited_search_cannot_prove_no_historical_incidents(self):
        class LimitedTools:
            def execute(self, name, args):
                return {'provider': 'github', 'incidents': [],
                        'note': 'Chỉ tìm theo chuỗi trong 50 incident gần nhất; không tìm thấy không chứng minh không có sự cố.'}

        fake = FakeProvider([tool_call('search', 'get_status', '{"provider":"github"}'),
                             final('Không có sự cố năm 2025.'),
                             final('Không thể xác nhận danh sách đầy đủ năm 2025 vì chỉ có 50 incident gần nhất.')])
        result = run_agent('Tất cả incident năm 2025?', fake, LimitedTools())
        self.assertEqual(result['status'], 'completed')
        self.assertIn('50 incident', result['answer'])
        self.assertTrue(any(x['event'] == 'validation_search_limit' for x in result['trace']))

    def test_json_array_is_invalid_arguments_observation(self):
        fake = FakeProvider([tool_call('array', 'get_status', '[]'), final()])
        result = run_agent('status?', fake, StatusTools())
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(json.loads(fake.histories[1][-1]['content'])['error'], 'INVALID_ARGUMENTS')

    def test_all_calls_are_dispatched_even_at_step_limit(self):
        first = tool_call('one', 'get_status', '{"provider":"github"}')
        second = tool_call('two', 'get_status', '{"provider":"cloudflare"}')
        first['calls'].extend(second['calls'])
        first['message']['tool_calls'].extend(second['message']['tool_calls'])
        result = run_agent('both?', FakeProvider([first]), StatusTools(), max_steps=1)
        self.assertEqual(result['status'], 'max_steps')
        self.assertEqual([x['name'] for x in result['trace'] if x['event'] == 'tool'],
                         ['get_status', 'get_status'])

    def test_stop_with_calls_still_dispatches_tools(self):
        response = tool_call('call', 'get_status', '{"provider":"github"}')
        response['finish'] = 'stop'
        fake = FakeProvider([response, final()])
        self.assertEqual(run_agent('status?', fake, StatusTools())['status'], 'completed')
        self.assertEqual(fake.histories[1][-1]['tool_call_id'], 'call')

    def test_provider_exception_is_traced(self):
        class FailingProvider:
            def complete(self, messages, schemas):
                raise RuntimeError('provider unavailable')

        result = run_agent('status?', FailingProvider(), StatusTools())
        self.assertEqual(result['status'], 'error')
        self.assertTrue(any(x['event'] == 'error' for x in result['trace']))
