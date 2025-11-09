from sentence_transformers import SentenceTransformer
import torch

print("Loading SentenceTransformer model: gtr-t5-base")
MODEL_NAME = "sentence-transformers/gtr-t5-base"
MODEL = SentenceTransformer(MODEL_NAME)
MODEL.eval()
print("Model loaded successfully.")

def get_embedding_st(text):
    if not text or not text.strip():
        print("Warning: Empty text provided for embedding.")
        return None

    try:
        embedding = MODEL.encode(text, convert_to_tensor=True, normalize_embeddings=True)
        return embedding.cpu().numpy()
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None
