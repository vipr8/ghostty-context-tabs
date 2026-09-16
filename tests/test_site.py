import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BEACON_SOURCE = "https://static.cloudflareinsights.com/beacon.min.js"
ANALYTICS_TOKEN = "9b7f49f0dc4f45a9b8809a57d0349642"


class PublishedSiteTests(unittest.TestCase):
    def test_every_html_page_has_the_labs_analytics_beacon(self):
        pages = sorted(DOCS.rglob("*.html"))
        self.assertTrue(pages, "No published HTML pages found")

        for page in pages:
            with self.subTest(page=page.relative_to(ROOT)):
                html = page.read_text(encoding="utf-8")
                self.assertEqual(html.count(BEACON_SOURCE), 1)
                self.assertEqual(html.count(ANALYTICS_TOKEN), 1)
                self.assertLess(html.index(BEACON_SOURCE), html.index("</body>"))

    def test_home_page_discloses_the_website_analytics_boundary(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn("Cloudflare Web Analytics", html)
        self.assertIn("PRIVACY.md", html)
        self.assertIn("installed Context Tabs tool remains telemetry-free", html)


if __name__ == "__main__":
    unittest.main()
