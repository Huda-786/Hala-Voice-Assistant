from transformers import AutoProcessor, SeamlessM4TModel
from sentence_transformers import SentenceTransformer

print("Downloading SeamlessM4T...")
AutoProcessor.from_pretrained(
    "facebook/hf-seamless-m4t-medium",
    use_fast=False,
)
SeamlessM4TModel.from_pretrained("facebook/hf-seamless-m4t-medium")
print("SeamlessM4T cached.")

print("Downloading Nomic embeddings...")
SentenceTransformer(
    "nomic-ai/nomic-embed-text-v1.5",
    trust_remote_code=True,
)
print("Nomic embeddings cached.")

print("All models cached successfully.")