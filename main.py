import os
import json
from logger import get_file_logger, get_logger
from parser import ContentParser
from scoring import Scorer
from tokenizer import Tokenizer

# Maybe throw this into a config later?
# Can only be ANALYST or DEV as per instructor data
target = "TEST"

# May need adjustments as the directory structure changes
directory = f"Data/{target}"
    
logger = get_logger(__name__)
scorerlogger = get_file_logger("scorer")

for urlfolder in os.listdir(directory):
    for filename in os.listdir(os.path.join(directory, urlfolder)):
        logger.info(f"(Not) Processing file: {filename}")
        with open(os.path.join(directory, urlfolder, filename), "r") as file:
            obj = json.load(file)
            url = obj.get("url")
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

            scorer = Scorer()
            scores = scorer.score({
                "content": token_counts,
                "title": title_token_counts
            })

            scorerlogger.info(f"URL: {url}")
            scorerlogger.info(f"Scores: {scores}\n\n")
            logger.info(f"Finished processing file: {filename}")


logger.info("Finished processing all files.")