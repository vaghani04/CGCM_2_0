# First import the chunker you want from Chonkie
from chonkie import RecursiveChunker

# Initialize the chunker
chunker = RecursiveChunker()

with open("/Users/maunikvaghani/Developer/pp/CGCM_2_0/src/app/services/path_validation_service.py", "r") as file:
    text = file.read()

# Chunk some text
chunks = chunker(text)

# Access chunks
for chunk in chunks:
    print(f"Chunk: {chunk.text}")
    print(f"Tokens: {chunk.token_count}")