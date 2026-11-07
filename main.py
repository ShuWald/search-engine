import os
import json
from logger import get_file_logger, get_logger
from docuid import DocuID, Url
from parser import ContentParser
from scoring import Scorer
from tokenizer import Tokenizer
from invertedindex import InvertedIndex
from collections import Counter

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
        logger.info(f"Processing file: {filename} under {urlfolder}")
        with open(os.path.join(directory, urlfolder, filename), "r") as file:
            obj = json.load(file)
            docu_id = DocuID(url_string=obj.get("url"))
            content = obj.get("content")

            parser = ContentParser(content) 
            result = parser.parse()
            title = result["title"]
            header = result["header"]
            bold = result["bold"]
            clean_text = result["clean_text"]

            tokenizer = Tokenizer()
            # This includes stemming 
            # Note: Stemming can modify original/root word, see logs
            token_counts = tokenizer.process(clean_text)
            title_token_counts = None if title is None else tokenizer.process(title)
            header_token_counts = None if header is None else tokenizer.process(header)
            bold_token_counts = None if bold is None else tokenizer.process(bold)

            # all above things return a counter object with tokens relevant to their class and their frequency

            # combine it all into a dict of token : str as key and frequency : int as value
            token_dict = dict(token_counts) # dict of all tokens

            def add_to_token_dict(add_counter : Counter, weight : int):
                for token, frequency in add_counter.items():
                    if token in token_dict:
                        token_dict[token] += weight * frequency

            if title_token_counts:
                add_to_token_dict(title_token_counts, 3)
            if header_token_counts:
               add_to_token_dict(header_token_counts, 2) 
            if bold_token_counts:
                add_to_token_dict(bold_token_counts, 1)



            # tokenizer.process_unique does this directly from content
            total_count = list(token_dict.items()) # create a list of tuples(token, frequency)
            ii.add_document(docu_id.doc_id, total_count)
            num_idx_docs += 1

            #scorer = Scorer()
            #scores = scorer.score({
            #    "content": token_counts,
             #   "title": title_token_counts
            #})

            #scorerlogger.info(f"URL: {docu_id.url}")
            #scorerlogger.info(f"Scores: {scores}\n\n")
            # Nothing else is done with scorer
            # tagge out scorer due to general uselessness

            logger.info(f"Finished processing: {docu_id.doc_id}")
    

ii.save_index()

num_unique_tokens = len(ii.index)
total_idx_size = os.path.getsize("inverted_index.json")/1024

print(f"Total number of indexed documents: {num_idx_docs}")
print(f"Total number of unique tokens: {num_unique_tokens}")
print(f"Total index size: {total_idx_size:.2f} KB")

logger.info("Finished processing all files.")