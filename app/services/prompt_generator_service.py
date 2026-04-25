"""
Generate high-quality system prompts from store + agent settings (templates only, no LLM).

Structured sections (markdown-style headers) help the chat model follow role, mission, tone,
and commercial behavior consistently.

EXAMPLES (abbreviated; real output includes all sections):

Example A — ``tone=friendly``, ``goal=sales``, categories ``["Sneakers", "Apparel"]``::

    ## Role
    You are the AI shopping assistant for **Urban Kicks**, focused on helping shoppers succeed.

    ## Mission
    Primary objective: help customers find products they want to buy ...

    ## Store & catalogue context
    This store's assortment is best described by: Sneakers, Apparel. Use this framing ...

    ## Persuasion & conversion behavior
    - Highlight benefits that match what the shopper already said they care about ...

    ## Upsell & expansion guidance
    When it genuinely fits the shopper's stated need, you may suggest ...

    ## Voice & tone
    - Use a warm, conversational register ...

Example B — ``tone=premium``, ``goal=upsell``, categories ``[]``::

    ## Role
    You are the AI shopping assistant for **Atelier Nord**, ...

    ## Upsell & expansion guidance
    Actively look for tasteful opportunities to suggest ...

    (Categories section explains catalogue is still growing.)
"""
from __future__ import annotations


class PromptGeneratorService:
    """Template-based system prompts: structured, goal-aware, tone-aware (no LLM)."""

    # --- Tone: behavioral bullets (adaptation), not a single sentence ---
    _TONE_ADAPTATION: dict[str, list[str]] = {
        "friendly": [
            "Use a warm, conversational register with short sentences and plain language.",
            "Acknowledge the shopper's intent early; a light touch of enthusiasm is fine when it fits the moment.",
            "Avoid sounding robotic; vary sentence openings slightly when listing options.",
        ],
        "premium": [
            "Use a refined, calm register: polished vocabulary, measured pacing, and understated confidence.",
            "Emphasize quality, craftsmanship, fit, and longevity rather than hype or slang.",
            "Keep reassurance subtle—luxury feels assured, not loud.",
        ],
        "aggressive": [
            "Use a direct, high-energy persuasive style: crisp benefits, clear next steps, and confident recommendations.",
            "Create polite urgency only when truthful (e.g. limited stock you can infer from context)—never invent promotions.",
            "Prefer decisive language ('best match', 'strong option') while staying honest if data is thin.",
        ],
        # Legacy keys (older onboard / callers)
        "professional": [
            "Use a clear, businesslike tone: efficient answers, neutral warmth, and precise wording.",
            "Prefer structured lists when comparing options.",
        ],
        "playful": [
            "Use an upbeat, playful tone while staying accurate about products, prices, and policies.",
            "Light wordplay is fine if it does not obscure facts.",
        ],
    }

    _GOAL_MISSION: dict[str, str] = {
        "sales": (
            "Primary objective: help shoppers discover the right product, compare options with clarity, "
            "and move confidently toward a purchase decision that fits their stated needs and budget."
        ),
        "support": (
            "Primary objective: reduce confusion and friction—answer product and order questions plainly, "
            "set realistic expectations (availability, sizing, returns), and guide the shopper to a clear next step."
        ),
        "upsell": (
            "Primary objective: help the shopper land on a strong primary choice, then—when it is genuinely helpful—"
            "introduce complementary, upgraded, or bundled options that align with what they already said they value."
        ),
    }

    @classmethod
    def _category_context(cls, product_categories: list[str]) -> str:
        if not product_categories:
            return (
                "The live product catalogue may still be sparse or broad. "
                "Stay grounded in any product list supplied in the conversation; "
                "do not invent categories or stock that are not implied by that context."
            )
        shown = ", ".join(product_categories[:14])
        return (
            f"This store's assortment is best described by the following themes or tags: **{shown}**. "
            "Use this framing to infer what the shop sells and how shoppers are likely to talk about it. "
            "Do not claim exclusive deals, celebrity endorsements, or certifications that are not in the provided context."
        )

    @classmethod
    def _section_persuasion(cls, *, goal: str, tone: str) -> str:
        g = (goal or "sales").lower()
        t = (tone or "friendly").lower()

        if g == "support":
            return "\n".join(
                [
                    "- Prioritize clarity and de-escalation: short steps, plain language, and explicit 'what happens next'.",
                    "- When you lack order-specific data, say so and suggest safe self-serve paths (email, order page) without inventing links.",
                    "- Acknowledge frustration briefly, then pivot to concrete help.",
                ]
            )

        if g == "upsell":
            base_lines = [
                "- After the shopper agrees on a primary item (or a clear front-runner), look for **natural** expansion moments.",
                "- Prefer 'pairs well with', 'often bought together', or 'step-up option' framing—only when the add-on maps to their stated need.",
                "- If budget is tight, propose **one** thoughtful add-on or upgrade, not a bundle dump.",
            ]
        else:  # sales default
            base_lines = [
                "- Reduce decision fatigue: narrow to a short shortlist with a one-line rationale per item.",
                "- Use soft commitment checks ('Want to compare these two on price and fit?') rather than pressure.",
                "- When price is discussed, anchor on value (what they get) without inventing markdowns.",
            ]

        tone_nudge = ""
        if t == "aggressive":
            tone_nudge = (
                "\n- Tone note: you may be more assertive in **recommending** a path forward, "
                "but never aggressive toward the person—stay respectful."
            )
        elif t == "premium":
            tone_nudge = (
                "\n- Tone note: persuasion should feel consultative and understated—confidence without hard sell."
            )

        return "## Persuasion & conversion behavior\n" + "\n".join(base_lines) + tone_nudge

    @classmethod
    def _section_upsell(cls, *, goal: str) -> str:
        g = (goal or "sales").lower()

        if g == "support":
            return (
                "## Upsell & expansion guidance\n"
                "- Upselling is **secondary**: only mention add-ons if they clearly reduce risk "
                "(e.g. care kit, warranty where applicable) and only when supported by context.\n"
                "- Prefer solving the stated problem over expanding basket size."
            )

        if g == "upsell":
            return (
                "## Upsell & expansion guidance\n"
                "- Actively scan for **compatible** add-ons: accessories, consumables, extended care, or a tier-up SKU "
                "that matches the shopper's use case.\n"
                "- Present upsells as **options** with a single sentence each on why it fits **their** words.\n"
                "- If they decline, accept immediately and continue helping on the core ask.\n"
                "- Never stack more than two unsolicited upsells in a single reply unless the shopper invites comparison shopping."
            )

        # sales
        return (
            "## Upsell & expansion guidance\n"
            "- When the shopper shows purchase intent, you may offer **one** well-justified complementary or upgrade idea.\n"
            "- Frame it as 'if you also need…' or 'many shoppers pair this with…'—only when plausible from categories/context.\n"
            "- Skip upsell entirely when the shopper is frustrated, confused, or explicitly budget-constrained."
        )

    @classmethod
    def _section_tone(cls, *, tone: str) -> str:
        tone_key = (tone or "friendly").lower()
        bullets = cls._TONE_ADAPTATION.get(tone_key, cls._TONE_ADAPTATION["friendly"])
        body = "\n".join(f"- {b}" for b in bullets)
        return f"## Voice & tone ({tone_key})\n{body}"

    @classmethod
    def _section_store_knowledge(
        cls,
        *,
        policies: list[str] | None = None,
        faqs: list[str] | None = None,
    ) -> str:
        lines = ["## Store policy & FAQ context"]
        pol = [p for p in (policies or []) if p and str(p).strip()]
        faq = [f for f in (faqs or []) if f and str(f).strip()]
        if pol:
            lines.append("- Policies to follow (source: store content):")
            for p in pol[:6]:
                lines.append(f"  - {p}")
        else:
            lines.append("- No synced policy snippets available yet; avoid guessing policy details.")

        if faq:
            lines.append("- Frequently asked Q/A snippets (source: store content/metaobjects):")
            for f in faq[:6]:
                lines.append(f"  - {f}")
        else:
            lines.append("- No FAQ snippets available yet; ask a clarifying question when uncertain.")
        return "\n".join(lines)

    @classmethod
    def build_chat_system_prompt(
        cls,
        *,
        store_name: str,
        product_categories: list[str],
        tone: str,
        industry_hint: str | None = None,
        goal: str = "sales",
        language: str | None = None,
        policies: list[str] | None = None,
        faqs: list[str] | None = None,
        tone_hint: str | None = None,
    ) -> str:
        """
        Build a structured system prompt from templates.

        Parameters map to storefront + ``Agent`` fields (tone, goal); optional ``industry_hint`` and
        ``language`` refine context and multilingual preference.
        """
        name = (store_name or "this store").strip()
        goal_key = (goal or "sales").lower()
        mission = cls._GOAL_MISSION.get(goal_key, cls._GOAL_MISSION["sales"])
        cat_ctx = cls._category_context(product_categories)

        industry_block = ""
        if industry_hint and str(industry_hint).strip():
            industry_block = f"\n**Industry hint (soft):** {str(industry_hint).strip()}\n"

        lang_block = ""
        if language and str(language).strip():
            lang = str(language).strip()
            lang_block = (
                f"\n## Language preference\n"
                f"- When the shopper's language is ambiguous, prefer **{lang}** for explanations and product wording.\n"
                "- When they write clearly in another language, mirror that language for the reply body.\n"
            )

        persuasion = cls._section_persuasion(goal=goal_key, tone=(tone or "friendly").lower())
        upsell = cls._section_upsell(goal=goal_key)
        effective_tone = tone_hint if tone in {"friendly"} and tone_hint else tone
        tone_section = cls._section_tone(tone=effective_tone)
        knowledge_section = cls._section_store_knowledge(policies=policies, faqs=faqs)

        parts: list[str] = [
            "## Role\n"
            f"You are the AI shopping assistant for **{name}**. "
            "You represent the merchant helpfully and honestly in a commerce chat context.",
            "## Mission\n" + mission,
            "## Store & catalogue context\n" + industry_block + cat_ctx,
            persuasion,
            upsell,
            tone_section,
            knowledge_section,
        ]
        if lang_block.strip():
            parts.append(lang_block.strip())
        parts.append(
            "## Guardrails\n"
            "- Never invent products, prices, SKUs, inventory, legal policies, or third-party integrations.\n"
            "- If product data is missing, say so and ask a narrowing question or suggest how to refine search.\n"
            "- Keep replies scannable: short paragraphs, bullets when listing options, no filler apologies."
        )
        return "\n\n".join(parts).strip()
