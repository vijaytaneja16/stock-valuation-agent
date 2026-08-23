"""SEC EDGAR client -- used ONLY for qualitative text (Item 1 Business,
Item 3 Legal Proceedings, MD&A), not for structured financials. XBRL tagging
consistency across filers is poor enough that it's not worth the parsing
effort when FMP/Finnhub cover the numbers cleanly.

SEC requires a descriptive User-Agent header on every request -- set
SEC_EDGAR_USER_AGENT in your .env to "Your Name your.email@example.com".
Docs: https://www.sec.gov/os/webmaster-faq#developers
"""
from __future__ import annotations

import os
import time

import requests

from stock_agent.data.cache import cached_fetch

FULL_TEXT_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
TICKER_LOOKUP_URL = "https://www.sec.gov/files/company_tickers.json"


class EdgarClient:
    def __init__(self, user_agent: str | None = None):
        self.headers = {
            "User-Agent": user_agent or os.environ["SEC_EDGAR_USER_AGENT"],
        }
        self._ticker_to_cik: dict[str, str] | None = None

    def _get(self, url: str, params: dict | None = None):
        # SEC asks for no more than ~10 requests/second; we're nowhere near
        # that for this use case, but a small delay is good etiquette.
        time.sleep(0.2)
        resp = requests.get(url, headers=self.headers, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json()

    def _load_ticker_map(self):
        if self._ticker_to_cik is None:
            data = self._get(TICKER_LOOKUP_URL)
            self._ticker_to_cik = {
                row["ticker"].upper(): str(row["cik_str"]).zfill(10)
                for row in data.values()
            }
        return self._ticker_to_cik

    def get_cik(self, ticker: str) -> str:
        return self._load_ticker_map()[ticker.upper()]

    def get_filings_list(self, ticker: str, form_types: tuple[str, ...] = ("10-K", "10-Q", "8-K")):
        """Recent filing metadata (accession numbers, dates, form types)."""
        def fetch():
            cik = self.get_cik(ticker)
            data = self._get(SUBMISSIONS_URL.format(cik=cik))
            recent = data.get("filings", {}).get("recent", {})
            filings = []
            for i, form in enumerate(recent.get("form", [])):
                if form in form_types:
                    filings.append({
                        "form": form,
                        "filingDate": recent["filingDate"][i],
                        "accessionNumber": recent["accessionNumber"][i],
                        "primaryDocument": recent["primaryDocument"][i],
                    })
            return filings
        return cached_fetch(ticker, "edgar_filings_list", "current", fetch)

    def get_filing_document_url(self, ticker: str, accession_number: str, primary_document: str) -> str:
        cik = self.get_cik(ticker).lstrip("0")
        acc_no_dashes = accession_number.replace("-", "")
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{primary_document}"

    def full_text_search(self, query: str, ticker: str | None = None, forms: str | None = None):
        """Search filing text for phrases -- e.g. 'cyclical', 'competitive
        pressure', 'goodwill impairment'. Good for the callout-hunting steps
        in the qualitative section of the spec.
        """
        params = {"q": query}
        if ticker:
            params["ciks"] = self.get_cik(ticker)
        if forms:
            params["forms"] = forms
        return self._get(FULL_TEXT_SEARCH_URL, params=params)
