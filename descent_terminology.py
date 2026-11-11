"""
Terminologie française contrôlée pour Descent V2.

Ce glossaire harmonise les traductions des termes
du manuel anglais. Il ne définit aucune règle.
"""

TERMINOLOGY = {
    "defeated": "vaincu",
    "knocked out": "mis hors de combat",
    "stand up": "se relever",
    "revive a hero": "réanimer un héros",
    "rest": "se reposer",
    "fatigue": "fatigue",
}


def format_terminology():
    return "\n".join(
        f"- {english} : {french}"
        for english, french in TERMINOLOGY.items()
    )


if __name__ == "__main__":
    print("=== GLOSSAIRE DESCENT V2 ===")
    print(format_terminology())
