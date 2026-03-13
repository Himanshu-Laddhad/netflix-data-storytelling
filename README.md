# 🎬 Netflix — Crafting & Articulating a Compelling Story

> **Course:** MGMT 59000V — Visual Analytics
> **Assignment:** Homework 2
> **Author:** Himanshu Laddhad

---

## Overview

This project tells a data-driven story using the **Netflix catalog dataset**, comparing two directors with radically different profiles — **Rajiv Chilaka** (Indian children's animation) and **Martin Scorsese** (Hollywood prestige cinema). It also includes automated **web scraping** pipelines built with Selenium to enrich the dataset by collecting filmography data from streaming platforms.

---

## Dataset

| Property | Details |
|---|---|
| **Source** | [Kaggle – Netflix Movies and TV Shows](https://www.kaggle.com/datasets/shivamb/netflix-shows) |
| **File** | `netflix_data.csv` |
| **Records** | ~8,800 titles |
| **Features** | Title, type (Movie/TV Show), director, cast, country, date added, release year, rating, duration, genre |

---

## Project Structure

```
HW2/
├── netflix_directors_analysis.ipynb       # Main analysis notebook
├── netflix_data.csv                       # Netflix catalog dataset
│
├── MS_Selenium/                           # Martin Scorsese scraper (Plex)
│   ├── MS_Selenium.py                     # Selenium + BeautifulSoup scraper
│   ├── ms_titles.csv                      # Scraped Scorsese filmography
│   └── test_titles.csv
│
├── RC_Selenium/                           # Rajiv Chilaka scraper (Komparify)
│   ├── RC_Selenium.py                     # Selenium + BeautifulSoup scraper
│   ├── rc_titles.csv                      # Scraped Chilaka filmography
│   └── rc_titles_full_from_debug.csv
│
├── Executive_Summary_Netflix.pdf          # Written executive summary
├── Appendix_Figures.pdf                   # Supporting visualizations
├── laddhad_himanshu_assignment2.docx      # Full assignment report
└── README.md
```

---

## Analysis Breakdown

### Part 1 — Data Cleaning & Preparation

- Handled missing values in `director`, `cast`, and `country` columns
- Converted `date_added` to datetime for time-series analysis
- Filtered dataset to isolate titles by Rajiv Chilaka and Martin Scorsese

### Part 2 — Comparative Director Analysis

| Dimension | Rajiv Chilaka | Martin Scorsese |
|---|---|---|
| **Specialty** | Children's animation (Chhota Bheem) | Crime / drama features |
| **Content Type** | Primarily Movies | Primarily Movies |
| **Geographic Reach** | India-centric | Global |
| **Netflix Presence** | High volume, niche | Curated, prestige catalog |

- Compared content-type distribution (Movie vs TV Show)
- Analyzed genre/category spread
- Visualized release-year trends to understand platform addition patterns
- Assessed ratings profiles (TV-Y7, TV-G vs R, PG-13)

### Part 3 — Web Scraping Pipelines

Two custom Selenium scrapers were built to cross-reference external streaming catalogs:

**`MS_Selenium.py` — Plex scraper (Scorsese)**
- Navigates to Scorsese's director page on Plex
- Parses `DetailsCreditsTable` HTML using BeautifulSoup
- Extracts film titles via anchor/span elements
- Exports results to `ms_titles.csv`

**`RC_Selenium.py` — Komparify scraper (Chilaka)**
- Scrapes Rajiv Chilaka's actor/director page on Komparify
- Targets `div.play-tt` elements and entertainment-route anchor hrefs
- Normalizes titles by stripping trailing year annotations
- Exports results to `rc_titles.csv`

---

## Key Story

> *Two directors. One platform. Opposite audiences.*

Rajiv Chilaka dominates Netflix's children's content space with a high-volume, culturally specific catalog, while Martin Scorsese's presence reflects Hollywood's prestige curation strategy. The data reveals that Netflix actively pursues both volume-driven regional creators and globally recognized auteurs — two very different value propositions under one subscription.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3 | Core analysis and scripting |
| Pandas | Data manipulation |
| Matplotlib / Seaborn | Visualizations |
| Selenium | Browser automation for web scraping |
| BeautifulSoup4 | HTML parsing |
| Jupyter Notebook | Interactive analysis environment |

---

## How to Run

### Analysis Notebook
1. Ensure `netflix_data.csv` is in the same directory
2. Install dependencies:
   ```bash
   pip install pandas matplotlib seaborn jupyter
   ```
3. Run the notebook:
   ```bash
   jupyter notebook netflix_directors_analysis.ipynb
   ```

### Web Scrapers
> **Requirements:** Chrome + ChromeDriver installed and in PATH

```bash
pip install selenium beautifulsoup4

# Run Martin Scorsese scraper
python MS_Selenium/MS_Selenium.py

# Run Rajiv Chilaka scraper
python RC_Selenium/RC_Selenium.py
```

---

## Author

**Himanshu Laddhad**
PUID: 039494953
Purdue University — MGMT 59000V Visual Analytics
