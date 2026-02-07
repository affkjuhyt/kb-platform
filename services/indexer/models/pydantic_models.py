from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Node:
    heading: str
    level: int
    text: str = ""
    children: List["Node"] = field(default_factory=list)

    def add_child(self, node: "Node") -> None:
        self.children.append(node)


@dataclass
class Chunk:
    text: str
    heading_path: List[str]
    section_path: str
    index: int
    start: int
    end: int
    source_type: Optional[str] = None
