from unittest.mock import patch

from django.test import Client, TestCase


class AgentChatApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)

    @patch("app_agent_uma.views.run_agent_native_function_calling", return_value="測試回覆")
    def test_chat_view_accepts_json_post(self, mocked_agent_call):
        response = self.client.post(
            "/agent/chat/",
            data='{"message":"哈囉成田路"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], "測試回覆")
        mocked_agent_call.assert_called_once()

    def test_chat_view_rejects_empty_json_message(self):
        response = self.client.post(
            "/agent/chat/",
            data='{"message":"   "}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.json())

    def test_base_template_includes_vrm_assistant_dom(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="ai-vrm-assistant-root"')
        self.assertContains(response, "app_dashboard/js/ai-vrm-assistant.js")
