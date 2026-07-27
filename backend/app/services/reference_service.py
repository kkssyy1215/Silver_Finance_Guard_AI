from app.schemas.common import SourceReference
from app.services.rule_loader import load_rule_file


def references_for(*categories: str) -> list[SourceReference]:
    knowledge_base = load_rule_file("knowledge_base.json")
    selected = []
    wanted = set(categories)

    for source in knowledge_base:
        if source["category"] in wanted:
            selected.append(
                SourceReference(
                    source_id=source["source_id"],
                    title=source["title"],
                    publisher=source["publisher"],
                    url=source["url"],
                    summary=source["summary"],
                )
            )

    return selected
