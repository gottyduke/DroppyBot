import json
import os

import requests
from discord.ext import commands

from shared import CogBase


class GPTTools(CogBase, commands.Cog):
    def __init__(self):
        self.registered_tools = {"search_web_content": self.search_web_content}

    def process_tool_call(self, tool):
        if tool.function.name in self.registered_tools:
            return self.registered_tools[tool.function.name](
                json.loads(tool.function.arguments)
            )

    @staticmethod
    def search_web_content(arguments):
        """
        bing v7 api for openai gpt tool calling
        """

        params = {
            "q": arguments["query"],
            "mkt": arguments["market"],
            "setLang": arguments["language"],
        }
        headers = {"Ocp-Apim-Subscription-Key": os.environ["ABS_KEY"]}
        endpoint = "https://api.bing.microsoft.com/" + "v7.0/search"

        # make bing request
        response = requests.get(endpoint, headers=headers, params=params)
        response.raise_for_status()

        filtered_result = [
            {"name": webpage["name"], "snippet": webpage["snippet"]}
            for webpage in response.json()["webPages"]["value"]
        ]

        return filtered_result
