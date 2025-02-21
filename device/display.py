import logging

logger = logging.getLogger(__name__)

class Display:

    def show_text(self, text):
        logger.info(f"Displaying: {text}")