"""
Martell Pattern Detection — identifies Time Assassin
behaviors and enforces the 1:3:1 Rule.

5 Time Assassins (Dan Martell):
1. The Staller — delays decisions, needs more info
2. The Speed Demon — rushes without systems
3. The Supervisor — micromanages, can't delegate
4. The Saver — hoards tasks, won't let go
5. The Self-Medicator — avoids pain with busy work
"""

import logging
logger = logging.getLogger(__name__)


TIME_ASSASSIN_SIGNALS = {
    'staller': [
        "i need more information", "let me think about it",
        "i'm not sure yet", "maybe later", "not ready",
        "need to research more", "waiting on",
    ],
    'speed_demon': [
        "just do it quickly", "don't worry about the process",
        "we'll figure it out", "ship it", "just get it done",
        "skip the", "forget the system",
    ],
    'supervisor': [
        "i need to check everything", "let me review all",
        "i want to see every", "cc me on everything",
        "don't do anything without", "run it by me first",
    ],
    'saver': [
        "i'll do it myself", "it's easier if i",
        "no one else can", "i have to handle this",
        "i can't delegate", "only i know how",
    ],
    'self_medicator': [
        "let me check email first", "quick social media",
        "just one more thing", "busy", "swamped",
        "so many tasks", "can't focus",
    ],
}


def detect_time_assassin(text: str) -> dict:
    """
    Detect Time Assassin patterns in founder messages.
    Returns detected assassin type and intervention string, or {} if none.
    """
    text_lower = text.lower()
    detected = []

    for assassin, signals in TIME_ASSASSIN_SIGNALS.items():
        if any(signal in text_lower for signal in signals):
            detected.append(assassin)

    if not detected:
        return {}

    assassin = detected[0]
    interventions = {
        'staller': (
            "⚠️ **Time Assassin detected: The Staller**\n"
            "You're delaying a decision. What's the cost of not deciding today?\n"
            "Apply 1:3:1 — give me 3 options and your recommendation."
        ),
        'speed_demon': (
            "⚠️ **Time Assassin detected: The Speed Demon**\n"
            "Moving fast without a system creates rework. "
            "Take 10 minutes to build the playbook first."
        ),
        'supervisor': (
            "⚠️ **Time Assassin detected: The Supervisor**\n"
            "You're micromanaging. Trust the system or fix the system — "
            "don't monitor everything manually."
        ),
        'saver': (
            "⚠️ **Time Assassin detected: The Saver**\n"
            "You're hoarding a task. Is this actually below your Buyback Rate? "
            "If so, delegate it now."
        ),
        'self_medicator': (
            "⚠️ **Time Assassin detected: The Self-Medicator**\n"
            "You're using busy work to avoid something harder. "
            "What are you actually avoiding?"
        ),
    }

    return {
        'assassin': assassin,
        'intervention': interventions.get(assassin, ''),
        'all_detected': detected,
    }


def check_131_rule(text: str) -> bool:
    """
    Check if a problem is presented without options/recommendation.
    The 1:3:1 Rule: 1 problem, 3 options, 1 recommendation.
    Returns True if message presents a problem with no options (violation).
    """
    problem_signals = [
        "problem is", "issue with", "we have a problem",
        "something is wrong", "this isn't working",
        "what should i do", "what do you think",
        "i don't know what to do",
    ]
    option_signals = [
        "option 1", "option 2", "first option", "second option",
        "we could", "one approach", "another approach",
        "recommend", "suggest",
    ]

    text_lower = text.lower()
    has_problem = any(s in text_lower for s in problem_signals)
    has_options = any(s in text_lower for s in option_signals)

    return has_problem and not has_options
