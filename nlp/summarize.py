from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch
import os
from settings import settings

HF_TOKEN = settings.HF_TOKEN

MODEL_NAME_BART_LARGE_CNN = "facebook/bart-large-cnn"
print(f"Loading embedding model: {MODEL_NAME_BART_LARGE_CNN}")
try:
    EMBEDDING_TOKENIZER = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
    EMBEDDING_MODEL = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn")
except Exception as e:
    print(f"Error loading embedding model: {e}")


def add_summaries_to_articles(news_articles):
    model_name = "facebook/bart-large-cnn"
    print(f"Loading summarization model: {model_name}")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    except Exception as e:
        print(f"Error loading summarization model: {e}")
        return

    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    print("Summarizing articles...")
    for i, article in enumerate(news_articles):
        content = article.get("content", "")
        if not content.strip():
            article["summary"] = ""
            continue

        try:
            inputs = tokenizer.batch_encode_plus(
                [content],
                max_length=1024,
                return_tensors="pt",
                truncation=True
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}

            summary_ids = model.generate(
                inputs["input_ids"],
                max_length=130,
                min_length=30,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )

            summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
            article["summary"] = summary
            print(f"Summarized {i+1}/{len(news_articles)} articles.")
        except Exception as e:
            print(f"Failed to summarize article {i+1}: {e}")
            article["summary"] = ""
