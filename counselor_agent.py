"""
Counselor Agent - Provides nudges to counselors during patient conversations
"""

import os
import json
import logging
import re
from typing import List, Dict, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class CounselorAgent:
    def __init__(self, api_key: Optional[str] = None, model: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key is required. Set OPENAI_API_KEY environment variable."
            )
        self.client = OpenAI(api_key=self.api_key)
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1")

    def analyze_conversation(
        self, transcripts: List[Dict[str, str]], previous_nudges: List[str] = None
    ) -> Dict:
        if not transcripts:
            return {"problems": [], "nudges": [], "sentiment": ["neutral"]}
        logger.info("Analyzing conversation with %d messages", len(transcripts))

        conversation_text = transcripts
        if isinstance(transcripts, list):
            conversation_text = ""
            for msg in transcripts:
                for k, v in msg.items():
                    conversation_text = conversation_text + f"{k}: {v} \n"
        print(conversation_text)

        previous_nudges_text = ""
        if previous_nudges:
            previous_nudges_text = (
                "\nPrevious suggestions given to counselor:\n"
                + "\n".join([f"- {nudge}" for nudge in previous_nudges])
                + "\n\nConsider these previous suggestions when providing new nudges. Build upon them or provide new relevant suggestions based on the current conversation state."
            )

        prompt = f"""Analyze this patient-counselor conversation and provide:

        You were given a mixed conversation (counceller and patient),
        identify patient transcripts and counceller transcripts and provide the output as following.

            1. PROBLEMS: List all problems or concerns the patient is expressing. Each problem should be a short, clear statement. Return as a list.

            2. NUDGES: Provide 3-5 actionable suggestions for the counselor. Each nudge should be one short sentence. Return as a list. provide medication also.

            3. SENTIMENT: Identify the main emotional tone using simple words like: positive, negative, anxiety, neutral, sadness, anger, fear, hope, etc. Return as a list of 1-3 emotion words that best describe the conversation.

            4. FOLLOW_UP: Based on the conversation suggest the counceller what to ask.

            5. RISK: Give a risk value based on the patient conversation

            Format your response as JSON with these exact keys:
            {{
            "problems": ["problem1", "problem2", etc],
            "nudges": ["nudge1", "nudge2", "nudge3", etc],
            "sentiment": ["word1", "word2"],
            "follow_up": ""
            "risk": ["low", "medium", "high"]
            }}

            Use simple, clear words. Keep everything short and direct.

            previous nudges: {previous_nudges_text}

            Conversation:
            {conversation_text}
            """

        #   "risk": "Low",
        #   "generative_nudge": "Good choice. Take two deep breaths and text someone you trust.",
        #   "follow_up": "Who could you text right now?"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert counselor assistant. You MUST respond ONLY with valid JSON. No explanations, no markdown, just pure JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )

            result_text = response.choices[0].message.content.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            result = json.loads(result_text)

            if "problems" not in result or not isinstance(result["problems"], list):
                result["problems"] = []
            if "nudges" not in result or not isinstance(result["nudges"], list):
                result["nudges"] = []
            if "sentiment" not in result or not isinstance(result["sentiment"], list):
                result["sentiment"] = ["neutral"]
            if result["sentiment"]:
                result["sentiment"] = [
                    word.lower().strip() for word in result["sentiment"]
                ]
            if "follow_up" not in result:
                result["follow_up"] = ""
            if "risk" not in result:
                result["risk"] = []

            return result
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse JSON response, attempting fallback extraction"
            )
            try:
                json_match = re.search(
                    r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", result_text, re.DOTALL
                )
                if json_match:
                    result = json.loads(json_match.group())
                    if "problems" not in result or not isinstance(
                        result["problems"], list
                    ):
                        result["problems"] = []
                    if "nudges" not in result or not isinstance(result["nudges"], list):
                        result["nudges"] = []
                    if "sentiment" not in result or not isinstance(
                        result["sentiment"], list
                    ):
                        result["sentiment"] = ["neutral"]
                    if "follow_up" not in result:
                        result["follow_up"] = ""
                    if "risk" not in result:
                        result["risk"] = []

                    return result
            except (json.JSONDecodeError, ValueError, AttributeError):
                logger.error("Failed to extract JSON from response", exc_info=True)
            logger.error("Unable to analyze conversation - JSON parsing failed")
            return {
                "problems": ["Unable to analyze"],
                "nudges": ["Review conversation manually"],
                "sentiment": ["neutral"],
                "follow_up": "",
                "risk": [],
            }
        except Exception as e:
            logger.error(
                "Error during conversation analysis: %s", str(e), exc_info=True
            )
            return {
                "problems": ["Error occurred"],
                "nudges": [],
                "sentiment": ["neutral"],
                "follow_up": "",
                "risk": [],
            }
