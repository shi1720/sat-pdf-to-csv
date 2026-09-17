"""Offline regressions for legacy provider functions.

Load the unmodified function AST without executing Streamlit UI, Firebase startup,
or environment credential checks. Requests are replaced at the network boundary;
the real function still builds the payload, parses responses and handles errors.
"""
import ast
import asyncio
import inspect
import logging
import os
from pathlib import Path
import time
import typing
import unittest
from unittest.mock import AsyncMock, Mock, patch
from claude_config import get_claude_model

SOURCE = 'sat_question_processor.py'
FUNCTION = 'call_claude_api'

class ProviderError(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code


def load_provider():
    tree = ast.parse(Path(SOURCE).read_text())
    selected = [node for node in tree.body if
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == FUNCTION
                or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'MODEL_NAME' for t in node.targets)]
    assert any(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in selected)
    transport = Mock()
    namespace = dict(vars(typing), get_claude_model=get_claude_model,
                     requests=transport, os=os, HTTPException=ProviderError,
                     logger=Mock(), logging=Mock(), st=Mock(),
                     time=Mock(), asyncio=Mock(sleep=AsyncMock()),
                     API_URL='https://api.anthropic.com/v1/messages',
                     CLAUDE_API_URL='https://api.anthropic.com/v1/messages',
                     API_KEY='offline-secret', HEADERS={'x-api-key': 'offline-secret'},
                     CLAUDE_HEADERS={'x-api-key': 'offline-secret'})
    exec(compile(ast.Module(body=selected, type_ignores=[]), SOURCE, 'exec'), namespace)
    return namespace[FUNCTION], transport, namespace


def invoke(function):
    names = list(inspect.signature(function).parameters)
    args = [[{'role': 'user', 'content': 'offline fixture'}]] if names[0] == 'messages' else ['offline fixture']
    if 'api_key' in names: args.append('offline-secret')
    result = function(*args)
    return asyncio.run(result) if inspect.isawaitable(result) else result


class ClaudeRequestTests(unittest.TestCase):
    def test_default_and_custom_model_preserve_request_and_response(self):
        for override, expected in [('', 'claude-sonnet-4-6'), ('  test-model  ', 'test-model')]:
            with self.subTest(model=expected), patch.dict(os.environ, {'ANTHROPIC_MODEL': override, 'ANTHROPIC_FALLBACK_MODEL': ''}):
                function, transport, namespace = load_provider()
                transport.post.return_value = Mock(status_code=200, json=lambda: {'content': [{'text': 'provider answer'}]})
                self.assertEqual(invoke(function), 'provider answer')
                payload = transport.post.call_args.kwargs['json']
                self.assertEqual(payload['model'], expected)
                self.assertEqual(payload['max_tokens'], 8192)
                self.assertEqual(payload['temperature'], 0.2)
                self.assertEqual(payload['messages'], [{'role': 'user', 'content': 'offline fixture'}])
                self.assertEqual(transport.post.call_args.kwargs['headers']['x-api-key'], 'offline-secret')
                self.assertNotIn('offline-secret', str(namespace['logger'].mock_calls))

    def test_provider_error_does_not_become_a_success(self):
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': '', 'ANTHROPIC_FALLBACK_MODEL': ''}):
            function, transport, _ = load_provider()
            response = Mock(status_code=503, text='unavailable', json=lambda: {'content': [{'text': 'provider answer'}]})
            response.raise_for_status.side_effect = RuntimeError('unavailable')
            transport.post.return_value = response
            try:
                self.assertIsNone(invoke(function))
            except ProviderError:
                pass
            self.assertGreaterEqual(transport.post.call_count, 1)
            self.assertLessEqual(transport.post.call_count, 5)

    def test_blank_configuration_and_fallback(self):
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': '  ', 'ANTHROPIC_FALLBACK_MODEL': ''}):
            self.assertEqual(get_claude_model(), 'claude-sonnet-4-6')
            self.assertEqual(get_claude_model(fallback=True), 'claude-sonnet-4-6')
        with patch.dict(os.environ, {'ANTHROPIC_MODEL': 'primary', 'ANTHROPIC_FALLBACK_MODEL': ' fallback '}):
            self.assertEqual(get_claude_model(), 'primary')
            self.assertEqual(get_claude_model(fallback=True), 'fallback')

if __name__ == '__main__':
    unittest.main()
