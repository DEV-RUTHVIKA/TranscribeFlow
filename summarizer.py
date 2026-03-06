from transformers import pipeline

# Load once globally
summarizer = pipeline("summarization", model="t5-small")


def generate_summary(text):
    summary = summarizer(
        text,
        max_length=120,
        min_length=40,
        do_sample=False
    )
    return summary[0]['summary_text']
