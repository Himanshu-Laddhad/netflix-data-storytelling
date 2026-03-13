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


def extract_titles_from_html(html: str) -> List[str]:
    """Extract titles from Plex DetailsCreditsTable HTML using BeautifulSoup.

    Looks for tables with class containing 'DetailsCreditsTable_table' and
    collects anchor/span text and href-based candidates like '/movie/...'.
    """
    if BeautifulSoup is None:
        raise RuntimeError('BeautifulSoup is not available; install beautifulsoup4')

    soup = BeautifulSoup(html, 'html.parser')
    titles = set()

    # Helper to handle class_ values that may be a list or string
    def class_contains(sub: str):
        def _checker(c):
            if not c:
                return False
            if isinstance(c, (list, tuple)):
                s = ' '.join(c)
            else:
                s = c
            return sub in s

        return _checker

    # Find the details credits tables
    tables = soup.find_all('table', class_=class_contains('DetailsCreditsTable_table'))
    for table in tables:
        # Look for title cells
        title_cells = table.find_all('td', class_=class_contains('DetailsCreditsTable_title'))
        for td in title_cells:
            # Prefer anchor > span, then anchor text, then direct span text
            a = td.find('a')
            if a:
                span = a.find('span')
                if span and span.get_text(strip=True):
                    titles.add(span.get_text(strip=True))
                    continue
                if a.get_text(strip=True):
                    titles.add(a.get_text(strip=True))
                    continue
            sp = td.find('span')
            if sp and sp.get_text(strip=True):
                titles.add(sp.get_text(strip=True))

    # Also scan for anchors with movie/show hrefs elsewhere in the HTML
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/movie/') or href.startswith('/show/') or '/title/' in href:
            text = a.get_text(strip=True)
            if text:
                titles.add(text)

    # Normalize titles (strip trailing years)
    year_re = re.compile(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$")
    normalized = sorted({year_re.sub('', t).strip() for t in titles})
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


def get_scorsese_titles(headless: bool = True, timeout: int = 15, debug: bool = False) -> List[str]:
    """Scrape Plex person page for Martin Scorsese and return titles.

    This uses Selenium to run JS; if element scraping yields nothing it falls
    back to parsing page_source with BeautifulSoup.
    """
    options = webdriver.ChromeOptions()
    if headless:
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
        url = "https://watch.plex.tv/person/martin-scorsese"
        if debug:
            print('navigating to', url)
        driver.get(url)

        wait = WebDriverWait(driver, timeout)

        # quick cookie dismissal attempts
        cookie_selectors = [
            "//button[contains(., 'Accept') or contains(., 'I Agree') or contains(., 'Allow') ]",
            "//a[contains(., 'Accept') or contains(., 'Agree') or contains(., 'Allow')]",
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

        driver.execute_script("window.scrollTo(0, 600);")
        time.sleep(0.8)

        try:
            search_root = wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        except Exception:
            try:
                search_root = driver.find_element(By.CSS_SELECTOR, "div.person")
            except Exception:
                search_root = driver.find_element(By.TAG_NAME, "body")

        if debug:
            try:
                print('search_root tag:', search_root.tag_name)
            except Exception:
                print('search_root obtained')

        titles = set()

        candidate_selectors = [
            ".//table[contains(@class,'DetailsCreditsTable_table')]//td[contains(@class,'DetailsCreditsTable_title')]//a//span",
            ".//table[contains(@class,'DetailsCreditsTable_table')]//td[contains(@class,'DetailsCreditsTable_title')]//a",
            ".//a[contains(@href, '/video/') or contains(@href, '/watch/') or contains(@href, '/metadata/')]",
            ".//img[@alt]",
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

        # Normalize
        year_re = re.compile(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$")
        normalized = sorted({year_re.sub('', t).strip() for t in titles})

        if not normalized and BeautifulSoup is not None:
            if debug:
                print('Falling back to BeautifulSoup page parsing')
            bs_titles = extract_titles_from_html(driver.page_source)
            return bs_titles

        return normalized
    finally:
        driver.quit()


if __name__ == "__main__":
    # CLI: --html-file <path> and --out <path>
    out_path = 'titles.csv'
    html_file = None
    if '--html-file' in sys.argv:
        i = sys.argv.index('--html-file')
        if i + 1 < len(sys.argv):
            html_file = sys.argv[i + 1]
    if '--out' in sys.argv:
        i = sys.argv.index('--out')
        if i + 1 < len(sys.argv):
            out_path = sys.argv[i + 1]

    if html_file:
        if BeautifulSoup is None:
            print('BeautifulSoup not installed. Run: pip install beautifulsoup4')
            sys.exit(1)
        with open(html_file, 'rb') as f:
            raw = f.read()
        # Try a list of encodings commonly encountered (including UTF-16 BOM)
        html = None
        for enc in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1'):
            try:
                html = raw.decode(enc)
                break
            except Exception:
                html = None
        if html is None:
            # as last resort, decode latin-1 with replacement
            html = raw.decode('latin-1', errors='replace')
        titles = extract_titles_from_html(html)
    else:
        titles = get_scorsese_titles(headless=True)

    # Filter out titles ending with 'credits'
    filtered = [t for t in titles if not t.strip().lower().endswith('credits')]

    save_titles_csv(filtered, out_path)
    print(f"Found {len(titles)} works (before filter). {len(filtered)} written to {out_path}.")
    for t in filtered:
        print(t)


def extract_titles_from_html(html: str) -> List[str]:
    """Extract titles from Plex DetailsCreditsTable HTML using BeautifulSoup.

    Looks for tables with class containing 'DetailsCreditsTable_table' and
    collects anchor/span text and href-based candidates like '/movie/...'.
    """
    if BeautifulSoup is None:
        raise RuntimeError('BeautifulSoup is not available; install beautifulsoup4')

    soup = BeautifulSoup(html, 'html.parser')
    titles = set()

    # Find the details credits tables
    tables = soup.find_all('table', class_=lambda c: c and 'DetailsCreditsTable_table' in c)
    for table in tables:
        # Look for title cells
        title_cells = table.find_all('td', class_=lambda c: c and 'DetailsCreditsTable_title' in c)
        for td in title_cells:
            # Prefer anchor > span, then anchor text, then direct span text
            a = td.find('a')
            if a:
                # span inside anchor
                span = a.find('span')
                if span and span.get_text(strip=True):
                    titles.add(span.get_text(strip=True))
                    continue
                # fallback to anchor text
                if a.get_text(strip=True):
                    titles.add(a.get_text(strip=True))
                    continue
            # fallback: any span inside td
            sp = td.find('span')
            if sp and sp.get_text(strip=True):
                titles.add(sp.get_text(strip=True))

    # Also scan for anchors with movie/show hrefs elsewhere in the HTML
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/movie/') or href.startswith('/show/') or '/title/' in href:
            text = a.get_text(strip=True)
            if text:
                titles.add(text)

    # Normalize titles (strip trailing years)
    year_re = re.compile(r"\s*\(\s*(?:19|20)\d{2}\s*\)\s*$")
    normalized = sorted({year_re.sub('', t).strip() for t in titles})
    return normalized


def save_titles_csv(titles: List[str], path: str) -> None:
    """Save titles to a CSV file with a single column 'title'."""
    # Ensure directory exists
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['title'])
        for t in titles:
            writer.writerow([t])
