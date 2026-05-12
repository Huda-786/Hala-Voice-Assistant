from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SessionState:
    service_type: Optional[str] = None        # "lost_replacement" | "renewal" | "new_issuance"
    nationality: Optional[str] = None         # "uae_national" | "gcc_national" | "resident"
    category: Optional[str] = None            # "employee" | "student" | "investor" | etc.
    urgency: Optional[str] = None 
    age: Optional[int] = None            # "urgent" | "standard"

    # Derived metadata filters for ChromaDB
    confirmed_facts: dict = field(default_factory=dict)

    def update(self, **kwargs):
        """Only update fields that aren't already confirmed."""
        for key, value in kwargs.items():
            # if value and getattr(self, key, None) is None:
            #     setattr(self, key, value)
            #     self.confirmed_facts[key] = value
            if not value:
                continue

            current_value = getattr(self, key, None)

            # If empty, set it
            if current_value is None:
                setattr(self, key, value)
                self.confirmed_facts[key] = value
                continue

            # Allow category correction
            if key == "category" and value != current_value:
                setattr(self, key, value)
                self.confirmed_facts[key] = value
                continue

            # Allow topic correction/update
            if key == "topic" and value != current_value:
                setattr(self, key, value)
                self.confirmed_facts[key] = value
                continue

            # Allow urgency correction/update
            if key == "urgency" and value != current_value:
                setattr(self, key, value)
                self.confirmed_facts[key] = value
                continue

    def to_enriched_query(self, raw_user_query: str) -> str:
        """
        Takes the raw user message and prepends confirmed session context.
        This is what gets sent to ChromaDB instead of the raw query.

        Example:
            raw:      "what is the fee?"
            enriched: "Lost ID replacement fee for GCC national student"
        """
        context_parts = []

        if self.service_type:
            label = {
                "lost_replacement": "Lost ID card replacement",
                "renewal": "ID card renewal",
                "new_issuance": "New ID card issuance",
            }.get(self.service_type, self.service_type)
            context_parts.append(label)

        if self.nationality:
            label = {
                "uae_national": "UAE national",
                "gcc_national": "GCC national",
                "resident": "UAE resident",
            }.get(self.nationality, self.nationality)
            context_parts.append(label)

        if self.category:
            context_parts.append(self.category)

        if context_parts:
            prefix = " | ".join(context_parts)
            return f"{prefix} — {raw_user_query}"

        return raw_user_query

    def to_metadata_filter(self) -> Optional[dict]:
        """
        Returns a ChromaDB `where` filter dict based on confirmed facts.
        Only filters on fields that are confirmed to avoid over-constraining.
        Your chunks must have matching metadata keys for this to work.
        """
        filters = []

        if self.service_type:
            filters.append({"service_type": {"$eq": self.service_type}})

        if self.nationality:
            filters.append({
                "$or": [
                    {"nationality": {"$eq": self.nationality}},
                    {"nationality": {"$eq": "all"}},
                ]
            })

        if self.category:
            filters.append({
                "$or": [
                    {"sub_category": {"$eq": self.category}},
                    {"sub_category": {"$eq": "all"}},
                ]
            })

        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]
        return {"$and": filters}

    def summary(self) -> str:
        parts = []
        if self.service_type:
            parts.append(f"service={self.service_type}")
        if self.nationality:
            parts.append(f"nationality={self.nationality}")
        if self.category:
            parts.append(f"category={self.category}")
        if self.age:
            parts.append(f"age={self.age}")
        return " | ".join(parts) if parts else "no confirmed context yet"