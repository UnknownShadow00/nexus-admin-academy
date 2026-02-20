import asyncio
import logging
import re
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


async def scrape_examcompass_quiz(url: str) -> dict:
    if "examcompass.com" not in url:
        raise ValueError("URL must be from examcompass.com")

    html = ""
    title = ""

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
            except Exception as exc:
                await browser.close()
                raise ValueError(f"Could not load page: {exc}") from exc

            try:
                await page.wait_for_selector(".question, .quiz-question, [class*='question']", timeout=10000)
            except Exception:
                await asyncio.sleep(3)

            html = await page.content()
            title = await page.title()
            await browser.close()
    except Exception:
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                response.raise_for_status()
                html = response.text
        except Exception as exc:
            raise ValueError(f"Could not load page: {exc}") from exc

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    if not title:
        title = (soup.title.get_text(strip=True) if soup.title else "ExamCompass Quiz").strip()
    questions = _parse_questions(soup)

    if not questions:
        raise ValueError(
            "Could not find questions on this page. "
            "Check that the URL points to a valid ExamCompass quiz page."
        )

    return {
        "title": title.replace(" | ExamCompass", "").replace(" - ExamCompass", "").strip(),
        "questions": questions,
        "source_url": url,
        "question_count": len(questions),
    }


def _parse_questions(soup) -> list[dict]:
    questions = []
    forms = soup.find_all("form") or [soup]
    for container in forms:
        blocks = (
            container.find_all("div", class_=re.compile(r"question", re.I))
            or container.find_all("fieldset")
            or container.find_all("div", class_=re.compile(r"quiz", re.I))
        )
        for block in blocks:
            question = _extract_question_from_block(block)
            if question:
                questions.append(question)

    if not questions:
        questions = _extract_from_radio_groups(soup)
    if not questions:
        questions = _extract_from_text_patterns(soup)
    return questions


def _extract_question_from_block(block) -> Optional[dict]:
    question_text = None
    for tag in ["p", "strong", "h3", "h4", "div"]:
        element = block.find(tag)
        if element and len(element.get_text(strip=True)) > 20:
            question_text = element.get_text(strip=True)
            break
    if not question_text:
        return None

    inputs = block.find_all("input", {"type": "radio"})
    if len(inputs) < 2:
        return None

    options = []
    correct_index = None
    for i, inp in enumerate(inputs[:4]):
        label = None
        inp_id = inp.get("id")
        if inp_id:
            label_el = block.find("label", {"for": inp_id})
            if label_el:
                label = label_el.get_text(strip=True)
        if not label:
            sibling = inp.find_next_sibling()
            if sibling:
                label = sibling.get_text(strip=True)
        if not label:
            label = f"Option {chr(65 + i)}"
        options.append(label)

        if inp.get("data-correct") == "true" or inp.get("correct") == "true":
            correct_index = i
        label_node = block.find("label", {"for": inp.get("id", "")})
        if label_node and "correct" in (label_node.get("class") or []):
            correct_index = i

    if len(options) < 2:
        return None
    while len(options) < 4:
        options.append("")

    return {
        "question_text": question_text,
        "option_a": options[0],
        "option_b": options[1],
        "option_c": options[2],
        "option_d": options[3],
        "correct_answer": chr(65 + correct_index) if correct_index is not None else "A",
        "explanation": "",
    }


def _extract_from_radio_groups(soup) -> list[dict]:
    groups = {}
    for inp in soup.find_all("input", {"type": "radio"}):
        name = inp.get("name", "")
        groups.setdefault(name, []).append(inp)

    questions = []
    for _, inputs in groups.items():
        if len(inputs) < 2:
            continue
        prev = inputs[0].find_previous(["p", "strong", "h3", "h4"])
        question_text = prev.get_text(strip=True) if prev else f"Question {len(questions) + 1}"
        options = []
        for inp in inputs[:4]:
            label = soup.find("label", {"for": inp.get("id", "")})
            options.append(label.get_text(strip=True) if label else inp.get("value", f"Option {len(options) + 1}"))
        while len(options) < 4:
            options.append("")
        questions.append(
            {
                "question_text": question_text,
                "option_a": options[0],
                "option_b": options[1],
                "option_c": options[2],
                "option_d": options[3],
                "correct_answer": "A",
                "explanation": "",
            }
        )
    return questions


def _extract_from_text_patterns(soup) -> list[dict]:
    text = soup.get_text()
    pattern = re.compile(
        r"\d+\.\s+(.+?)\n\s*A\.\s+(.+?)\n\s*B\.\s+(.+?)\n\s*C\.\s+(.+?)\n\s*D\.\s+(.+?)(?=\n\d+\.|\Z)",
        re.DOTALL,
    )
    return [
        {
            "question_text": match.group(1).strip(),
            "option_a": match.group(2).strip(),
            "option_b": match.group(3).strip(),
            "option_c": match.group(4).strip(),
            "option_d": match.group(5).strip(),
            "correct_answer": "A",
            "explanation": "",
        }
        for match in pattern.finditer(text)
    ]
