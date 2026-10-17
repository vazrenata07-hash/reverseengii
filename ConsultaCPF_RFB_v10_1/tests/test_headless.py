import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from browser_mode import browser_args, check_headless_progress, HeadlessNeedsWindow
from wifi_networks import validate_settings
class Tests(unittest.TestCase):
    def test_headless_flag_and_viewport(self):
        args=browser_args('edge',9333,'profile','https://example.test',True)
        self.assertIn('--headless=new',args);self.assertIn('--window-size=1280,900',args)
        self.assertNotIn('--new-window',args);self.assertEqual(args[-1],'https://example.test')
    def test_visible_mode_uses_window(self):
        args=browser_args('edge',9333,'profile','url',False)
        self.assertIn('--new-window',args);self.assertNotIn('--headless=new',args)
    def test_unreleased_verification_stops_after_30_seconds(self):
        check_headless_progress(True,100,False,False,129.99)
        with self.assertRaises(HeadlessNeedsWindow):check_headless_progress(True,100,False,False,130)
    def test_ready_token_or_submitted_query_does_not_timeout(self):
        check_headless_progress(True,100,True,False,1000)
        check_headless_progress(True,100,False,True,1000)
    def test_visible_mode_has_no_headless_deadline(self):
        check_headless_progress(False,100,False,False,1000)
    def test_settings_default_is_visible_and_flag_is_preserved(self):
        self.assertFalse(validate_settings({})['headless'])
        self.assertTrue(validate_settings({'headless':True})['headless'])
        with self.assertRaises(ValueError):validate_settings({'headless':'false'})
if __name__=='__main__':unittest.main()
