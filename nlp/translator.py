from transformers import MarianMTModel, MarianTokenizer
import torch
import os
import argostranslate.package
import glob
from argostranslate import translate

def translate_boannews_with_argos(base_dir, target_source="boannews"):
    from_code = "ko"
    to_code = "en"

    installed_languages = translate.get_installed_languages()
    from_lang = next((lang for lang in installed_languages if lang.code == from_code), None)
    to_lang = next((lang for lang in installed_languages if lang.code == to_code), None)

    if not from_lang or not to_lang:
        print(f"Language pair '{from_code}' → '{to_code}' not found. Please install the required model first.")
        return []

    translator = from_lang.get_translation(to_lang)
    translated_articles = []

    print(f"Translating articles under: {base_dir}/{target_source}/")

    base_target_path = os.path.join(base_dir, target_source)
    article_paths = glob.glob(os.path.join(base_target_path, "*", "*", "article.txt"))

    for article_path in article_paths:
        try:
            with open(article_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                continue

            translated_content = translator.translate(content)

            with open(article_path, "w", encoding="utf-8") as f:
                f.write(translated_content)

            rel_path = os.path.relpath(article_path, base_dir)
            translated_articles.append({
                "source": target_source,
                "path": article_path,
                "rel_path": rel_path,
                "content": translated_content,
                "translated": True
            })

            print(f"Translated and overwritten: {rel_path}")

        except Exception as e:
            print(f"Failed to translate {article_path}: {e}")

    print(f"Translation completed. Total: {len(translated_articles)} articles.")
    return translated_articles
