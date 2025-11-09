from transformers import AutoTokenizer, AutoModel
import torch
import os
from settings import settings

HF_TOKEN = settings.HF_TOKEN

MODEL_NAME_DARKBERT = "s2w-ai/DarkBERT"
print(f"Loading embedding model: {MODEL_NAME_DARKBERT}")
try:
    EMBEDDING_TOKENIZER = AutoTokenizer.from_pretrained(
        MODEL_NAME_DARKBERT,
        token=HF_TOKEN if HF_TOKEN else None,
        add_prefix_space=True  
    )
    EMBEDDING_MODEL = AutoModel.from_pretrained(MODEL_NAME_DARKBERT, token=HF_TOKEN if HF_TOKEN else None)
    EMBEDDING_MODEL.eval()
    print("Embedding model loaded successfully.")
except Exception as e:
    print(f"Error loading embedding model: {e}")
    EMBEDDING_TOKENIZER = None
    EMBEDDING_MODEL = None


def get_segmented_embedding(text, max_tokens=512, stride=256):
    if not EMBEDDING_TOKENIZER or not EMBEDDING_MODEL:
        print("Embedding model not available.")
        return None

    if not text or not text.strip():
        print("Warning: Empty text provided for embedding. Returning None.")
        return None

    all_tokens = EMBEDDING_TOKENIZER.tokenize(text, add_special_tokens=False)

    if not all_tokens:
        print("Warning: Text resulted in no tokens. Returning None.")
        return None

    embeddings = []

    for i in range(0, len(all_tokens), stride):
        chunk_tokens_list = all_tokens[i : i + max_tokens - 2] # for [CLS] and [SEP]

        inputs = EMBEDDING_TOKENIZER(
            chunk_tokens_list,
            is_split_into_words=True,
            return_tensors="pt",
            truncation=True,
            max_length=max_tokens,
            padding="max_length"
        )

        with torch.no_grad():
            outputs = EMBEDDING_MODEL(**inputs)
        cls_embedding = outputs.last_hidden_state[:, 0, :]
        embeddings.append(cls_embedding)

    if not embeddings:
        print("Warning: No embeddings generated for the text. Returning None.")
        return None
    
    squeezed_embeddings = [emb.squeeze(0) for emb in embeddings]
    if not squeezed_embeddings:
        return None
        
    stacked_embeddings = torch.stack(squeezed_embeddings, dim=0)
    mean_embedding = torch.mean(stacked_embeddings, dim=0)
    
    return mean_embedding.cpu().numpy()