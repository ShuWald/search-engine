import os
import json
from bs4 import BeautifulSoup
import nltk
from logger import get_logger

# Maybe throw this into a config later?
# Can only be ANALYST or DEV as per instructor data
target = "TEST"

# May need adjustments as the directory structure changes
directory = f"Data/{target}"

logger = get_logger(__name__)

for urlfolder in os.listdir(directory):
    for filename in os.listdir(os.path.join(directory, urlfolder)):
        logger.info(f"(Not) Processing file: {filename}")
        with open(os.path.join(directory, urlfolder, filename), "r") as file:
            obj = json.load(file)
            url = obj.get("url")
            content = obj.get("content")
            logger.info(f"URL: {url}")
            # Get a random excerpt for now cuz why not
            logger.info(f"Content excerpt: {content[1000:1250]}")
        logger.info(f"Finished fake processing file: {filename}")
logger.info("Finished processing all files.")