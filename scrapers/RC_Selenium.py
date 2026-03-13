from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import time
import re
from typing import List
try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None
import csv
import os
import sys


def extract_titles_from_html_komparify(html: str) -> List[str]:
    """Extract titles from Komparify actor page HTML using BeautifulSoup.

    Looks for divs with class 'play-tt' (the structure you attached) and also
    anchors with entertainment/movie links as a fallback.
    """
    if BeautifulSoup is None:
        raise RuntimeError('BeautifulSoup is not available; install beautifulsoup4')

    soup = BeautifulSoup(html, 'html.parser')
    titles = set()

    # Primary: div.play-tt
    for d in soup.find_all('div', class_=lambda c: c and 'play-tt' in c):
        t = d.get_text(strip=True)
        if t:
            titles.add(t)

    # Secondary: anchor hrefs to entertainment/movie or /entertainment/show
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/entertainment/movie/' in href or '/entertainment/show/' in href:
            txt = a.get_text(strip=True)
            if txt:
                titles.add(txt)

    # Normalize titles (strip trailing years in parentheses)
    year_re = re.compile(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$")
    normalized = sorted({year_re.sub('', t).strip() for t in titles if t and len(t) > 1})
    return normalized


def save_titles_csv(titles: List[str], path: str) -> None:
    """Save titles to a CSV file with a single column 'title'."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['title'])
        for t in titles:
            writer.writerow([t])


def get_rajiv_chilaka_titles(url: str = None, headless: bool = True, timeout: int = 15, debug: bool = False) -> List[str]:
    """Scrape Komparify actor page for Rajiv Chilaka and return titles.

    If Selenium element scraping yields nothing it falls back to parsing page_source
    with BeautifulSoup using Komparify-specific heuristics.
    """
    options = webdriver.ChromeOptions()
    if headless:
        # New headless flag available in newer Chrome; fallback will still work
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        try:
            from webdriver_manager.chrome import ChromeDriverManager

            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        except Exception as e:
            raise RuntimeError("Could not start Chrome webdriver: " + str(e))

    try:
        if debug:
            print('driver started')
        if not url:
            url = "https://www.komparify.com/entertainment/actor/rajiv-chilaka1?srsltid=AfmBOopvkpkGYmAScL1IOmhle5m_Tf8Ja86a7MD8FEOTpFx99_9HiCt4"
        if debug:
            print('navigating to', url)
        driver.get(url)

        # Debug info about the loaded page
        if debug:
            try:
                print('current_url:', driver.current_url)
                print('page title:', driver.title)
                print('page_source length:', len(driver.page_source))
            except Exception:
                print('could not read page metadata')

        wait = WebDriverWait(driver, timeout)

        # Try to dismiss common cookie/popups quickly
        cookie_selectors = [
            "//button[contains(., 'Accept') or contains(., 'I Agree') or contains(., 'Allow') ]",
            "//a[contains(., 'Accept') or contains(., 'Agree') or contains(., 'Allow') ]",
        ]
        for sel in cookie_selectors:
            try:
                btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, sel)))
                btn.click()
                time.sleep(0.3)
                break
            except Exception:
                if debug:
                    print('cookie selector failed:', sel)

        # Perform multiple scrolls with pauses to allow lazy-loaded content to appear
        try:
            for y in (600, 1200, 1800, 2400):
                driver.execute_script(f"window.scrollTo(0, {y});")
                time.sleep(1.0)
        except Exception:
            # ignore scroll issues
            time.sleep(1.0)

        try:
            search_root = wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        except Exception:
            try:
                search_root = driver.find_element(By.CSS_SELECTOR, "div.wraplist")
            except Exception:
                search_root = driver.find_element(By.TAG_NAME, "body")

        if debug:
            try:
                print('search_root tag:', search_root.tag_name)
            except Exception:
                print('search_root obtained')

        titles = set()

        # Candidate XPaths tuned for Komparify structure (div.play-tt etc.)
        candidate_selectors = [
            ".//div[contains(@class,'play-tt')]",
            ".//a[contains(@href, '/entertainment/movie/') or contains(@href, '/entertainment/show/')]",
            ".//div[contains(@class,'playlist')]//a//div[contains(@class,'play-tt')]",
            ".//a//div[contains(@class,'play-tt')]",
            ".//h3|.//h2|.//h4|.//span[contains(@class,'title') or contains(@class,'card-title')]",
        ]

        found = []
        for sel in candidate_selectors:
            try:
                els = search_root.find_elements(By.XPATH, sel)
            except Exception:
                els = []
            if debug:
                print(f"selector '{sel}' found {len(els)} elements")
            found.extend(els)

        for el in found:
            try:
                t = (el.get_attribute('alt') or el.get_attribute('title') or el.text or el.get_attribute('aria-label') or '').strip()
                if not t and el.tag_name.lower() == 'a':
                    t = (el.text or el.get_attribute('title') or '').strip()
                if not t:
                    continue
                if len(t) < 2:
                    continue
                low = t.lower()
                if any(x in low for x in ['see more', 'watch', 'play', 'episode', 'season', 'more', 'back']):
                    continue
                titles.add(t)
            except Exception:
                if debug:
                    print('error processing element')

        # Normalize titles (strip trailing years)
        year_re = re.compile(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$")
        normalized = {year_re.sub('', t).strip() for t in titles}

        # Save page_source when debugging to inspect what loaded
        if debug:
            try:
                with open('rc_debug_page.html', 'w', encoding='utf-8') as fh:
                    fh.write(driver.page_source)
                print('Wrote rc_debug_page.html (debug)')
            except Exception:
                print('Could not write debug page file')

        # Always attempt BeautifulSoup parsing of page_source as a supplementary source
        if BeautifulSoup is not None:
            try:
                bs_titles = extract_titles_from_html_komparify(driver.page_source)
                if bs_titles:
                    normalized.update(bs_titles)
                    if debug:
                        print(f'BeautifulSoup supplemental found {len(bs_titles)} titles')
            except Exception:
                if debug:
                    print('BeautifulSoup supplemental parsing failed')

        normalized_list = sorted(t for t in normalized if t)
        return normalized_list
    finally:
        driver.quit()


if __name__ == "__main__":
    # CLI: --html-file <path> and --out <path> and --url <actor page>
    out_path = 'rc_titles.csv'
    html_file = None
    url = None
    headless = True
    debug = False
    if '--html-file' in sys.argv:
        i = sys.argv.index('--html-file')
        if i + 1 < len(sys.argv):
            html_file = sys.argv[i + 1]
    if '--out' in sys.argv:
        i = sys.argv.index('--out')
        if i + 1 < len(sys.argv):
            out_path = sys.argv[i + 1]
    if '--url' in sys.argv:
        i = sys.argv.index('--url')
        if i + 1 < len(sys.argv):
            url = sys.argv[i + 1]
    if '--no-headless' in sys.argv:
        headless = False
    if '--debug' in sys.argv:
        debug = True

    try:
        if html_file:
            if BeautifulSoup is None:
                print('BeautifulSoup not installed. Run: pip install beautifulsoup4')
                sys.exit(1)
            with open(html_file, 'rb') as f:
                raw = f.read()
            html = None
            for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1'):
                try:
                    html = raw.decode(enc)
                    break
                except Exception:
                    html = None
            if html is None:
                html = raw.decode('latin-1', errors='replace')
            titles = extract_titles_from_html_komparify(html)
        else:
            titles = get_rajiv_chilaka_titles(url=url, headless=headless, debug=debug)

        # Filter out titles ending with 'credits' or obvious non-title fragments
        filtered = [t for t in titles if not t.strip().lower().endswith('credits')]

        save_titles_csv(filtered, out_path)
        print(f"Found {len(titles)} works (before filter). {len(filtered)} written to {out_path}.")
        for t in filtered:
            print(t)
    except Exception as exc:
        # Print a full traceback to help debugging when running in the terminal
        import traceback

        print('Error running script:')
        traceback.print_exc()
        sys.exit(2)
