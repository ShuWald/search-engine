import os
import json
from logger import get_file_logger, get_logger
from docuid import DocuID, Url
from parser import ContentParser
from scoring import Scorer
from tokenizer import Tokenizer
from invertedindex import InvertedIndex

# Maybe throw this into a config later?
# Can only be ANALYST or DEV as per instructor data
target = "TEST"

# May need adjustments as the directory structure changes
directory = f"Data/{target}"
    
logger = get_logger(__name__)
scorerlogger = get_file_logger("scorer")

ii = InvertedIndex()
num_idx_docs = 0 

for urlfolder in os.listdir(directory):
    for filename in os.listdir(os.path.join(directory, urlfolder)):
        logger.info(f"(Not) Processing file: {filename} under {urlfolder}")
        with open(os.path.join(directory, urlfolder, filename), "r") as file:
            obj = json.load(file)
            docu_id = DocuID(url_string=obj.get("url"))
            content = obj.get("content")

            parser = ContentParser(content) 
            result = parser.parse()
            title = result["title"]
            clean_text = result["clean_text"]

            tokenizer = Tokenizer()
            # This includes stemming 
            # Note: Stemming can modify original/root word, see logs
            token_counts = tokenizer.process(clean_text)

            title_token_counts = None if title is None else tokenizer.process(title)

            # tokenizer.process_unique does this directly from content
            ii.add_document(docu_id.doc_id, token_counts)
            num_idx_docs += 1

            scorer = Scorer()
            scores = scorer.score({
                "content": token_counts,
                "title": title_token_counts
            })

            scorerlogger.info(f"URL: {docu_id.url}")
            scorerlogger.info(f"Scores: {scores}\n\n")
            # Nothing else is done with scorer

            logger.info(f"Finished processing: {docu_id.doc_id}")
    

ii.save_index()
num_unique_tokens = len(ii.index)
total_idx_size = os.path.getsize("inverted_index.json")/1024

print(f"Total number of indexed documents: {num_idx_docs}")
print(f"Total number of unique tokens: {num_unique_tokens}")
print(f"Total index size: {total_idx_size:.2f} KB")
logger.info("Finished processing all files.")