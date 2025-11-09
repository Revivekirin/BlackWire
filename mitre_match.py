import os
import json

from utils.file_loader import load_articles_from_directory, load_mitre_techniques
from nlp.translator import translate_boannews_with_argos
from nlp.summarize import add_summaries_to_articles
from mitre.matcher import calculate_mire_embedding, match_articles_to_mitre
from settings import settings

BASE_NEWS_DIR = settings.BASE_NEWS_DIR
MITRE_XLSX_PATH = settings.MITRE_XLSX_PATH
OUTPUT_DIR = settings.OUTPUT_DIR


def main_workflow():
    os.makedirs(os.path.dirname(OUTPUT_DIR), exist_ok=True)
   
    original_news_articles = load_articles_from_directory(BASE_NEWS_DIR)
    if not original_news_articles :
        print("No articles found. Exiting.")
        return

    translate_boannews_with_argos(BASE_NEWS_DIR, target_source='boannews')
    news_articles = load_articles_from_directory(BASE_NEWS_DIR)

    add_summaries_to_articles(news_articles)
    save_articles_to_json(news_articles, output_path="news_data.json")

    mitre_techniques_info = load_mitre_techniques(MITRE_XLSX_PATH)
    if not mitre_techniques_info:
        print("No MITRE techniques found. Exiting.")
    else:
        mitre_embeddings_array, valid_mitre_techniques = calculate_mire_embedding(mitre_techniques_info)
        if mitre_embeddings_array is None:
            print("No valid MIRE embeddings found. Exiting.")
        else:
            final_articles_with_mitre = match_articles_to_mitre(news_articles, mitre_embeddings_array, valid_mitre_techniques)
    
    existing_data = []
    if os.path.exists(OUTPUT_DIR):
        with open(OUTPUT_DIR, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

    merged_data = existing_data + (final_articles_with_mitre if 'final_articles_with_mitre' in locals() else news_articles)

    with open(OUTPUT_DIR, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=4)

def save_articles_to_json(news_articles, output_path=f"{OUTPUT_DIR}"):
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(news_articles, f, ensure_ascii=False, indent=4)
        print(f"Save path: {output_path}")
    except Exception as e:
        print(f"Error occurs: {e}")


if __name__ == "__main__": main_workflow() 