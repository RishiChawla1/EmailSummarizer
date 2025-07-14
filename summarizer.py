import re
import tempfile
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image
import pytesseract

# Load model
model_name = "google/flan-t5-base"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

# Tesseract path (adjust as needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def clean_text(text):
    text = re.sub(r"[^\x00-\x7F]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()

def deduplicate_lines(text):
    lines = text.splitlines()
    seen = set()
    return " ".join([line.strip() for line in lines if line.strip() and not (line in seen or seen.add(line))])

def filter_noise_lines(text):
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("view image") or "follow image" in line.lower():
            continue
        if re.match(r"^#+\s*[A-Z]{2,}", line):
            continue
        cleaned.append(line)
    return " ".join(cleaned)

def looks_like_garbage(text):
    return (
        len(text) < 10 or
        text.lower().startswith("html") or
        "font-" in text or
        "margin:" in text or
        "background-color" in text
    )

def render_html_to_image(html_content):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=800x2000')
    options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=options)

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as f:
            f.write(html_content.encode("utf-8"))
            temp_html_path = f.name

        driver.get("file://" + temp_html_path)
        screenshot_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
        driver.save_screenshot(screenshot_path)
        return Image.open(screenshot_path)
    finally:
        driver.quit()

def run_ocr_from_html(html_text):
    image = render_html_to_image(html_text)
    extracted_text = pytesseract.image_to_string(image, config="--psm 6")
    return clean_text(extracted_text)

def get_dynamic_lengths(word_count):
    if word_count < 20:
        return 20, 5
    elif word_count < 50:
        return 40, 10
    elif word_count < 100:
        return 80, 20
    elif word_count < 200:
        return 110, 30
    else:
        return 130, 40

def summarize_with_model(text):
    words = text.split()
    if len(words) < 10:
        return text.strip()

    max_len, min_len = get_dynamic_lengths(len(words))

    try:
        summary = summarizer(
            text,
            max_length=max_len,
            min_length=min_len,
            do_sample=False,
            clean_up_tokenization_spaces=True
        )[0]['summary_text'].strip()

        # Avoid summaries longer than input
        if len(summary.split()) >= len(text.split()):
            return text.strip()

        return summary
    except Exception as e:
        print(f"[Summarization Error] {e}")
        return text.strip()

def summarize_email(text, html_fallback=None):
    text = clean_text(text)
    text = deduplicate_lines(text)
    text = filter_noise_lines(text)

    if looks_like_garbage(text):
        if html_fallback:
            soup = BeautifulSoup(html_fallback, "html.parser")
            html_text = clean_text(soup.get_text(separator=" ", strip=True))
            if html_text and len(html_text.split()) > 10 and not looks_like_garbage(html_text):
                return summarize_email(html_text)
            ocr_text = run_ocr_from_html(html_fallback)
            if ocr_text and not looks_like_garbage(ocr_text):
                return summarize_email(ocr_text)
        return "(No meaningful content found)"

    return summarize_with_model(text)
