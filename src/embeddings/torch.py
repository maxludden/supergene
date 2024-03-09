from transformers import AutoTokenizer, AutoModel
import torch
from supergene.mongo import Mongo
from supergene.v0_0_2 import Version0_0_2
from supergene.v0_0_3 import Version0_0_3

# For this example, let's use the all-MiniLM-L6-v2 model from Sentence Transformers
model_name = "sentence-transformers/all-MiniLM-L6-v2"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

def get_embedding(text):
    # Tokenize the text
    inputs = tokenizer(text, padding=True, truncation=True, max_length=512, return_tensors="pt")
    
    # Generate embeddings
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Extract embeddings
    embeddings = outputs.last_hidden_state.mean(dim=1) # You can experiment with pooling strategies
    return embeddings

def main():
    mongo = Mongo()
    mongo.connect()
    for doc in Version0_0_2.all(sort="chapter"):
        text = doc.text
        embedding = get_embedding(text)
        