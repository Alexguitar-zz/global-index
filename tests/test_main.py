import unittest
from unittest.mock import patch, MagicMock, call

import main


class TestCreateChromeOptions(unittest.TestCase):
    @patch("main.Options")
    def test_returns_options_with_expected_arguments(self, mock_options_cls):
        mock_opts = MagicMock()
        mock_options_cls.return_value = mock_opts

        result = main.create_chrome_options()

        self.assertIs(result, mock_opts)
        expected_args = [
            "--headless",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ]
        for arg in expected_args:
            mock_opts.add_argument.assert_any_call(arg)

        # Verify user-agent is set
        ua_calls = [
            c
            for c in mock_opts.add_argument.call_args_list
            if "user-agent=" in str(c)
        ]
        self.assertEqual(len(ua_calls), 1)

    @patch("main.Options")
    def test_add_argument_called_five_times(self, mock_options_cls):
        mock_opts = MagicMock()
        mock_options_cls.return_value = mock_opts

        main.create_chrome_options()

        self.assertEqual(mock_opts.add_argument.call_count, 5)


class TestCreateDriver(unittest.TestCase):
    @patch("main.ChromeDriverManager")
    @patch("main.Service")
    @patch("main.webdriver.Chrome")
    def test_creates_driver_with_default_options(
        self, mock_chrome, mock_service, mock_cdm
    ):
        mock_cdm_instance = MagicMock()
        mock_cdm.return_value = mock_cdm_instance
        mock_cdm_instance.install.return_value = "/path/to/chromedriver"
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        with patch("main.create_chrome_options") as mock_create_opts:
            mock_opts = MagicMock()
            mock_create_opts.return_value = mock_opts

            driver = main.create_driver()

            mock_create_opts.assert_called_once()
            mock_service.assert_called_once_with("/path/to/chromedriver")
            mock_chrome.assert_called_once_with(
                service=mock_service_instance, options=mock_opts
            )

    @patch("main.ChromeDriverManager")
    @patch("main.Service")
    @patch("main.webdriver.Chrome")
    def test_creates_driver_with_custom_options(
        self, mock_chrome, mock_service, mock_cdm
    ):
        mock_cdm_instance = MagicMock()
        mock_cdm.return_value = mock_cdm_instance
        mock_cdm_instance.install.return_value = "/path/to/chromedriver"
        custom_opts = MagicMock()

        with patch("main.create_chrome_options") as mock_create_opts:
            driver = main.create_driver(options=custom_opts)

            mock_create_opts.assert_not_called()
            mock_chrome.assert_called_once()
            _, kwargs = mock_chrome.call_args
            self.assertIs(kwargs["options"], custom_opts)


class TestDismissAds(unittest.TestCase):
    @patch("main.time.sleep")
    @patch("main.webdriver.ActionChains")
    def test_sends_escape_and_runs_script(self, mock_action_chains, mock_sleep):
        mock_driver = MagicMock()
        mock_chain = MagicMock()
        mock_action_chains.return_value = mock_chain
        mock_chain.send_keys.return_value = mock_chain

        main.dismiss_ads(mock_driver)

        mock_action_chains.assert_called_once_with(mock_driver)
        mock_chain.send_keys.assert_called_once()
        mock_chain.perform.assert_called_once()
        mock_sleep.assert_called_once_with(1)
        mock_driver.execute_script.assert_called_once_with(main.AD_REMOVAL_SCRIPT)


class TestSwitchToHalfYearView(unittest.TestCase):
    @patch("main.time.sleep")
    @patch("main.webdriver.ActionChains")
    def test_sends_180d_and_enter(self, mock_action_chains, mock_sleep):
        mock_driver = MagicMock()
        mock_chain = MagicMock()
        mock_action_chains.return_value = mock_chain
        mock_chain.send_keys.return_value = mock_chain

        main.switch_to_half_year_view(mock_driver)

        mock_action_chains.assert_called_once_with(mock_driver)
        self.assertEqual(mock_chain.send_keys.call_count, 2)
        mock_chain.perform.assert_called_once()
        mock_sleep.assert_called_once_with(12)


class TestPrepareChart(unittest.TestCase):
    @patch("main.switch_to_half_year_view")
    @patch("main.dismiss_ads")
    @patch("main.time.sleep")
    def test_navigates_and_prepares(
        self, mock_sleep, mock_dismiss, mock_switch
    ):
        mock_driver = MagicMock()
        url = "https://example.com/chart"

        main.prepare_chart(mock_driver, url)

        mock_driver.get.assert_called_once_with(url)
        mock_sleep.assert_called_once_with(18)
        mock_dismiss.assert_called_once_with(mock_driver)
        mock_switch.assert_called_once_with(mock_driver)

    @patch("main.switch_to_half_year_view")
    @patch("main.dismiss_ads")
    @patch("main.time.sleep")
    def test_custom_load_wait(self, mock_sleep, mock_dismiss, mock_switch):
        mock_driver = MagicMock()

        main.prepare_chart(mock_driver, "https://example.com", load_wait=5)

        mock_sleep.assert_called_once_with(5)

    @patch("main.switch_to_half_year_view")
    @patch("main.dismiss_ads")
    @patch("main.time.sleep")
    def test_handles_ad_dismissal_error(
        self, mock_sleep, mock_dismiss, mock_switch
    ):
        mock_driver = MagicMock()
        mock_dismiss.side_effect = Exception("popup error")

        # Should not raise
        main.prepare_chart(mock_driver, "https://example.com")

        mock_driver.get.assert_called_once()
        mock_switch.assert_not_called()


class TestTakeScreenshot(unittest.TestCase):
    def test_returns_base64_screenshot(self):
        mock_driver = MagicMock()
        mock_driver.get_screenshot_as_base64.return_value = "abc123base64"

        result = main.take_screenshot(mock_driver)

        self.assertEqual(result, "abc123base64")
        mock_driver.get_screenshot_as_base64.assert_called_once()


class TestSendScreenshot(unittest.TestCase):
    @patch("main.requests.post")
    def test_posts_payload_to_gas_url(self, mock_post):
        mock_response = MagicMock()
        mock_post.return_value = mock_response

        result = main.send_screenshot(
            "https://gas.example.com/exec", "Test Chart", "imgdata"
        )

        mock_post.assert_called_once_with(
            "https://gas.example.com/exec",
            json={"name": "Test Chart", "image_data": "imgdata"},
        )
        self.assertIs(result, mock_response)


class TestCaptureAndSend(unittest.TestCase):
    @patch("main.send_screenshot")
    @patch("main.take_screenshot")
    @patch("main.prepare_chart")
    @patch("main.create_driver")
    def test_processes_all_charts(
        self, mock_create_driver, mock_prepare, mock_screenshot, mock_send
    ):
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        mock_screenshot.return_value = "b64img"
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_send.return_value = mock_response

        charts = {
            "Chart A": "https://example.com/a",
            "Chart B": "https://example.com/b",
        }

        main.capture_and_send(
            gas_url="https://gas.test/exec", target_charts=charts
        )

        self.assertEqual(mock_prepare.call_count, 2)
        self.assertEqual(mock_screenshot.call_count, 2)
        self.assertEqual(mock_send.call_count, 2)
        mock_driver.quit.assert_called_once()

    @patch("main.send_screenshot")
    @patch("main.take_screenshot")
    @patch("main.prepare_chart")
    def test_uses_injected_driver(
        self, mock_prepare, mock_screenshot, mock_send
    ):
        mock_driver = MagicMock()
        mock_screenshot.return_value = "b64"
        mock_send.return_value = MagicMock(text="ok")
        charts = {"C": "https://example.com/c"}

        main.capture_and_send(
            gas_url="https://gas.test/exec",
            target_charts=charts,
            driver=mock_driver,
        )

        # Injected driver should NOT be quit by capture_and_send
        mock_driver.quit.assert_not_called()

    @patch("main.send_screenshot")
    @patch("main.take_screenshot")
    @patch("main.prepare_chart")
    @patch("main.create_driver")
    def test_exits_on_exception(
        self, mock_create_driver, mock_prepare, mock_screenshot, mock_send
    ):
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        mock_prepare.side_effect = RuntimeError("browser crash")

        with self.assertRaises(SystemExit) as ctx:
            main.capture_and_send(
                gas_url="https://gas.test/exec",
                target_charts={"X": "https://example.com/x"},
            )

        self.assertEqual(ctx.exception.code, 1)
        mock_driver.quit.assert_called_once()

    @patch("main.send_screenshot")
    @patch("main.take_screenshot")
    @patch("main.prepare_chart")
    @patch("main.create_driver")
    def test_defaults_to_module_constants(
        self, mock_create_driver, mock_prepare, mock_screenshot, mock_send
    ):
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        mock_screenshot.return_value = "b64"
        mock_send.return_value = MagicMock(text="ok")

        main.capture_and_send()

        self.assertEqual(mock_prepare.call_count, len(main.TARGET_CHARTS))
        for chart_name in main.TARGET_CHARTS:
            mock_send.assert_any_call(main.GAS_URL, chart_name, "b64")
        mock_driver.quit.assert_called_once()

    @patch("main.send_screenshot")
    @patch("main.take_screenshot")
    @patch("main.prepare_chart")
    @patch("main.create_driver")
    def test_quits_driver_even_on_send_error(
        self, mock_create_driver, mock_prepare, mock_screenshot, mock_send
    ):
        mock_driver = MagicMock()
        mock_create_driver.return_value = mock_driver
        mock_screenshot.return_value = "b64"
        mock_send.side_effect = ConnectionError("network down")

        with self.assertRaises(SystemExit):
            main.capture_and_send(
                gas_url="https://gas.test/exec",
                target_charts={"Y": "https://example.com/y"},
            )

        mock_driver.quit.assert_called_once()


class TestConstants(unittest.TestCase):
    def test_gas_url_is_https(self):
        self.assertTrue(main.GAS_URL.startswith("https://"))

    def test_target_charts_non_empty(self):
        self.assertGreater(len(main.TARGET_CHARTS), 0)

    def test_target_charts_values_are_urls(self):
        for name, url in main.TARGET_CHARTS.items():
            self.assertTrue(
                url.startswith("https://"), f"{name} URL doesn't start with https://"
            )

    def test_ad_removal_script_is_valid_js_string(self):
        self.assertIn("querySelectorAll", main.AD_REMOVAL_SCRIPT)
        self.assertIn("remove()", main.AD_REMOVAL_SCRIPT)


if __name__ == "__main__":
    unittest.main()
