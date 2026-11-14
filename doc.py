from logging import Logger
from collections import Counter
from docuid import DocuID
from parser import ContentParser
from tokenizer import Tokenizer
import json

"""Class representing a document going into the index."""
class Doc:
    url: str
    wordweights: dict[str, int]

    tokenizer = Tokenizer()

    # Create from a deserialized json object from the dataset.
    def __init__(self, obj, logger: Logger):
        docu_id = DocuID(url_string=obj.get("url"))
        content = obj.get("content")

        parser = ContentParser(content)
        result = parser.parse()
        title = result["title"]
        header = result["header"]
        bold = result["bold"]
        clean_text = result["clean_text"]

        tokenizer = self.tokenizer
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

        self.url = docu_id.url.url
        self.wordweights = token_dict

        logger.info(f"Finished processing: {docu_id.url.url}")
