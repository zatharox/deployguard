from dataclasses import dataclass, field
from typing import Dict, List, Set


@dataclass
class ChangeNode:
    """Represents a node in the change graph."""

    node_id: str
    node_type: str
    name: str


@dataclass
class ChangeEdge:
    """Represents a relationship between two nodes."""

    source: str
    target: str
    relationship: str


@dataclass
class ChangeGraphResult:
    """Result of change graph and blast-radius analysis."""

    nodes: List[ChangeNode] = field(default_factory=list)
    edges: List[ChangeEdge] = field(default_factory=list)

    changed_files: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    critical_areas: List[str] = field(default_factory=list)

    blast_radius_score: float = 0.0
    blast_radius_level: str = "narrow"
    confidence: str = "low"

    def to_dict(self) -> Dict:
        return {
            "changed_files": self.changed_files,
            "components": self.components,
            "critical_areas": self.critical_areas,
            "blast_radius": {
                "score": round(self.blast_radius_score, 2),
                "level": self.blast_radius_level,
                "confidence": self.confidence,
            },
            "nodes": [
                {
                    "id": node.node_id,
                    "type": node.node_type,
                    "name": node.name,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "relationship": edge.relationship,
                }
                for edge in self.edges
            ],
        }


class ChangeGraphAnalyzer:
    """
    Analyze changed files to estimate structural blast radius.

    This first implementation is deterministic:
    - Files are mapped to top-level components.
    - Files are mapped to known critical areas.
    - A bounded structural blast-radius score is calculated.
    """

    CRITICAL_AREAS = {
        "auth": "authentication",
        "authentication": "authentication",
        "payment": "payment",
        "payments": "payment",
        "billing": "billing",
        "core": "core",
        "kernel": "kernel",
        "database": "database",
        "db": "database",
        "security": "security",
        "api": "api",
    }

    def analyze(self, changed_files: List[str]) -> ChangeGraphResult:
        """
        Analyze a list of changed file paths.

        Args:
            changed_files: File paths changed by a PR.

        Returns:
            ChangeGraphResult containing graph and blast-radius information.
        """

        normalized_files = self._normalize_files(changed_files)

        result = ChangeGraphResult(
            changed_files=normalized_files,
        )

        component_map: Dict[str, Set[str]] = {}
        critical_map: Dict[str, Set[str]] = {}

        for file_path in normalized_files:
            component = self._extract_component(file_path)

            component_map.setdefault(component, set()).add(file_path)

            node_id = f"file:{file_path}"

            result.nodes.append(
                ChangeNode(
                    node_id=node_id,
                    node_type="file",
                    name=file_path,
                )
            )

            component_node_id = f"component:{component}"

            if component_node_id not in {node.node_id for node in result.nodes}:
                result.nodes.append(
                    ChangeNode(
                        node_id=component_node_id,
                        node_type="component",
                        name=component,
                    )
                )

            result.edges.append(
                ChangeEdge(
                    source=node_id,
                    target=component_node_id,
                    relationship="belongs_to",
                )
            )

            critical_area = self._extract_critical_area(file_path)

            if critical_area:
                critical_map.setdefault(
                    critical_area,
                    set(),
                ).add(file_path)

                critical_node_id = f"critical:{critical_area}"

                if critical_node_id not in {node.node_id for node in result.nodes}:
                    result.nodes.append(
                        ChangeNode(
                            node_id=critical_node_id,
                            node_type="critical_area",
                            name=critical_area,
                        )
                    )

                result.edges.append(
                    ChangeEdge(
                        source=node_id,
                        target=critical_node_id,
                        relationship="affects",
                    )
                )

        components = sorted(component_map.keys())

        critical_areas = sorted(critical_map.keys())

        result.components = components
        result.critical_areas = critical_areas

        (
            result.blast_radius_score,
            result.blast_radius_level,
        ) = self._calculate_blast_radius(
            files_changed=len(normalized_files),
            components_changed=len(components),
            critical_areas_changed=len(critical_areas),
        )

        result.confidence = self._calculate_confidence(
            files_changed=len(normalized_files),
            components_changed=len(components),
        )

        return result

    @staticmethod
    def _normalize_files(changed_files: List[str]) -> List[str]:
        """
        Normalize and deduplicate file paths.
        """

        normalized = set()

        for file_path in changed_files:
            if not file_path:
                continue

            path = file_path.strip().replace("\\", "/")

            if not path:
                continue

            while path.startswith("./"):
                path = path[2:]

            path = path.rstrip("/")

            if path:
                normalized.add(path)

        return sorted(normalized)

    @staticmethod
    def _extract_component(file_path: str) -> str:
        """
        Infer a component from the first meaningful path segment.

        Examples:
            api/auth.py -> api
            services/user.py -> services
            src/payment/service.py -> src
            payment/service.py -> payment
        """

        parts = [part for part in file_path.split("/") if part]

        if not parts:
            return "root"

        if len(parts) == 1:
            return "root"

        ignored = {
            "src",
            "lib",
            "app",
            "source",
            "test",
            "tests",
        }

        if parts[0].lower() in ignored and len(parts) > 2:
            return parts[1]

        return parts[0]

    @classmethod
    def _extract_critical_area(
        cls,
        file_path: str,
    ) -> str | None:
        """
        Detect whether a changed file belongs to a critical area.
        """

        parts = [part.lower() for part in file_path.split("/") if part]

        for part in parts:
            normalized = part.replace("-", "_").replace(".", "_")

            if normalized in cls.CRITICAL_AREAS:
                return cls.CRITICAL_AREAS[normalized]

        return None

    @staticmethod
    def _calculate_blast_radius(
        files_changed: int,
        components_changed: int,
        critical_areas_changed: int,
    ) -> tuple[float, str]:
        """
        Calculate bounded structural blast radius.

        Maximum score: 10.
        """

        score = 0.0

        # Change volume: maximum 3 points.
        if files_changed >= 15:
            score += 3.0
        elif files_changed >= 8:
            score += 2.0
        elif files_changed >= 4:
            score += 1.0
        elif files_changed >= 1:
            score += 0.5

        # Cross-component impact: maximum 3 points.
        # Cross-component impact: maximum 3 points.
        if components_changed >= 5:
            score += 3.0
        elif components_changed >= 3:
            score += 2.0
        elif components_changed >= 2:
            score += 1.0

        # Critical areas: maximum 4 points.
        if critical_areas_changed >= 3:
            score += 4.0
        elif critical_areas_changed == 2:
            score += 3.0
        elif critical_areas_changed == 1:
            score += 2.0

        # Multiple critical areas indicate cross-domain impact.
        if critical_areas_changed >= 3 and components_changed >= 3:
            score = max(score, 7.0)

        score = min(score, 10.0)

        if score >= 7.0:
            level = "broad"
        elif score >= 4.0:
            level = "moderate"
        else:
            level = "narrow"

        return score, level

    @staticmethod
    def _calculate_confidence(
        files_changed: int,
        components_changed: int,
    ) -> str:
        """
        Estimate confidence based on available structural information.
        """

        if files_changed >= 5 and components_changed >= 2:
            return "high"

        if files_changed >= 2:
            return "medium"

        return "low"
