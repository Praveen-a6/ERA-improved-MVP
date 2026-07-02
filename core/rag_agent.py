# rag_agent.py
import time
import json
import ssl
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from core.llm_utils import llm_call, MODEL


_SSL_CONTEXT = ssl.create_default_context()
_SSL_CONTEXT.check_hostname = False
_SSL_CONTEXT.verify_mode = ssl.CERT_NONE

# ── ARXIV SEARCH ──────────────────────────────────────
def search_arxiv(query: str, max_results: int = 3) -> list[dict]:
    encoded = urllib.parse.quote(query)
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{encoded}"
        f"&start=0&max_results={max_results}"
        "&sortBy=relevance&sortOrder=descending"
    )

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ERA-Lite/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            xml_data = resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ⚠ arXiv fetch failed: {e}")
        return []

    try:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(xml_data)
    except Exception as e:
        print(f"  ⚠ arXiv XML parse failed: {e}")
        return []

    papers = []
    for entry in root.findall("atom:entry", ns):
        title = entry.find("atom:title", ns)
        summary = entry.find("atom:summary", ns)
        link = entry.find("atom:id", ns)
        authors = entry.findall("atom:author", ns)

        if title is None or summary is None:
            continue

        author_names = []
        for a in authors[:3]:
            name = a.find("atom:name", ns)
            if name is not None and name.text:
                author_names.append(name.text.strip())

        papers.append({
            "title": title.text.strip().replace("\n", " "),
            "abstract": summary.text.strip().replace("\n", " ")[:800],
            "authors": ", ".join(author_names),
            "url": link.text.strip() if link is not None and link.text else ""
        })

    return papers


# ── SEMANTIC SCHOLAR SEARCH ───────────────────────────
def search_semantic_scholar(query: str, max_results: int = 3) -> list[dict]:
    encoded = urllib.parse.quote(query)
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={encoded}"
        f"&limit={max_results}"
        "&fields=title,abstract,year,paperId"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ERA-Lite-Research/1.0"}
    )

    try:
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 429:
            print("  ⚠ Semantic Scholar rate limited — waiting 5s and retrying")
            time.sleep(5)
            try:
                with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as retry_e:
                print(f"  ⚠ Semantic Scholar retry failed: {retry_e}")
                return []
        else:
            print(f"  ⚠ Semantic Scholar fetch failed: {e}")
            return []
    except Exception as e:
        print(f"  ⚠ Semantic Scholar fetch failed: {e}")
        return []

    papers = []
    for p in data.get("data", []):
        abstract = p.get("abstract") or ""
        paper_id = p.get("paperId") or ""
        papers.append({
            "title": p.get("title", "Unknown"),
            "abstract": abstract[:800],
            "year": p.get("year", ""),
            "url": f"https://www.semanticscholar.org/paper/{paper_id}" if paper_id else ""
        })

    return papers


# ── RAG AGENT — SUMMARIZE FOR PROMPT ─────────────────
def build_research_context(problem: str, tags: list[str], max_papers: int = 4) -> str:
    if not tags:
        return ""

    arxiv_query = " ".join(tags[:2]) + " algorithm"
    ss_query = " ".join(tags[:3])

    print(f"  Searching: arXiv='{arxiv_query}' | S2='{ss_query}'")

    arxiv_papers = search_arxiv(arxiv_query, max_results=2)
    ss_papers = search_semantic_scholar(ss_query, max_results=2)
    all_papers = (arxiv_papers + ss_papers)[:max_papers]

    if not all_papers:
        print("  ⚠ No papers found — skipping research context")
        return ""

    print(f"  ✓ Found {len(all_papers)} paper(s)")

    paper_text = ""
    for i, p in enumerate(all_papers, 1):
        paper_text += f"\n[Paper {i}] {p['title']}\n"
        paper_text += f"Abstract: {p['abstract']}\n"

    prompt = f"""You are a research assistant helping a code generator solve a computational problem.

Problem to solve:
{problem}

Relevant research papers:
{paper_text}

Extract 3-5 specific, actionable algorithmic insights from these papers that would help solve the problem above.

Focus on:
- Specific algorithms or data structures mentioned
- Key implementation tricks or optimizations
- Edge cases the papers address
- Performance improvements

Be concrete and specific. Each insight should be directly applicable to writing code.
Format as a numbered list. Maximum 200 words total.
"""

    try:
        response = llm_call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300,
            stream=False
        )
        insights = response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  ⚠ RAG summarization failed: {e}")
        return ""

    return f"""Research insights from {len(all_papers)} relevant paper(s):
{insights}
"""