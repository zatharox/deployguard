import React from 'react';

type Node = {
  id: string;
  label?: string;
};

type Edge = {
  source: string;
  target: string;
  relationship?: string;
};

interface ChangeGraphProps {
  nodes: Node[];
  edges: Edge[];
}

type GraphNode = Node & {
  type: 'file' | 'component' | 'other';
};

function getNodeType(node: Node): GraphNode['type'] {
  if (node.id.startsWith('file:')) {
    return 'file';
  }

  if (node.id.startsWith('component:')) {
    return 'component';
  }

  return 'other';
}

function displayName(node: Node): string {
  return node.label || node.id.replace(/^(file|component):/, '');
}

function shorten(text: string, max = 38): string {
  if (text.length <= max) {
    return text;
  }

  return `${text.slice(0, max - 3)}...`;
}

export default function ChangeGraph({
  nodes,
  edges,
}: ChangeGraphProps) {
  if (nodes.length === 0) {
    return (
      <div className="change-graph-empty">
        No change graph data available.
      </div>
    );
  }

  const files = nodes.filter(
    (node) => getNodeType(node) === 'file',
  );

  const components = nodes.filter(
    (node) => getNodeType(node) === 'component',
  );

  const others = nodes.filter(
    (node) => getNodeType(node) === 'other',
  );

  const width = 900;
  const height = 460;

  const fileY = 135;
  const componentY = 340;

  const fileStep =
    files.length > 1
      ? 650 / (files.length - 1)
      : 0;

  const componentStep =
    components.length > 1
      ? 650 / (components.length - 1)
      : 0;

  const positions = new Map<
    string,
    { x: number; y: number }
  >();

  files.forEach((node, index) => {
    positions.set(node.id, {
      x:
        files.length === 1
          ? width / 2
          : 125 + index * fileStep,
      y: fileY,
    });
  });

  components.forEach((node, index) => {
    positions.set(node.id, {
      x:
        components.length === 1
          ? width / 2
          : 125 + index * componentStep,
      y: componentY,
    });
  });

  others.forEach((node, index) => {
    positions.set(node.id, {
      x: 125 + index * 180,
      y: 400,
    });
  });

  return (
    <div className="change-graph-wrapper">
      <svg
        className="change-graph-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="DeployGuard change graph"
      >
        <defs>
          <marker
            id="deployguard-arrow"
            viewBox="0 0 10 10"
            refX="9"
            refY="5"
            markerWidth="7"
            markerHeight="7"
            orient="auto-start-reverse"
          >
            <path
              d="M 0 0 L 10 5 L 0 10 z"
              fill="#64748b"
            />
          </marker>
        </defs>

        <rect
          x="0"
          y="0"
          width={width}
          height={height}
          rx="12"
          fill="#111720"
        />

        <text
          x="32"
          y="36"
          fill="#e5e7eb"
          fontSize="16"
          fontWeight="700"
        >
          Change Graph
        </text>

        <text
          x="32"
          y="58"
          fill="#7f8b9c"
          fontSize="11"
        >
          Files and the components affected by this PR
        </text>

        <text
          x="32"
          y="100"
          fill="#7f8b9c"
          fontSize="11"
          fontWeight="700"
          letterSpacing="1"
        >
          CHANGED FILES
        </text>

        <text
          x="32"
          y="305"
          fill="#7f8b9c"
          fontSize="11"
          fontWeight="700"
          letterSpacing="1"
        >
          COMPONENTS
        </text>

        {edges.map((edge, index) => {
          const source = positions.get(edge.source);
          const target = positions.get(edge.target);

          if (!source || !target) {
            return null;
          }

          const label =
            edge.relationship || 'related';

          const midpointX =
            (source.x + target.x) / 2;

          const midpointY =
            (source.y + target.y) / 2;

          return (
            <g
              key={`${edge.source}-${edge.target}-${index}`}
            >
              <line
                x1={source.x}
                y1={source.y + 30}
                x2={target.x}
                y2={target.y - 30}
                stroke="#64748b"
                strokeWidth="2"
                markerEnd="url(#deployguard-arrow)"
              />

              <text
                x={midpointX}
                y={midpointY}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
              >
                {label}
              </text>
            </g>
          );
        })}

        {[...files, ...components, ...others].map(
          (node) => {
            const position = positions.get(node.id);

            if (!position) {
              return null;
            }

            const type = getNodeType(node);

            const isFile = type === 'file';

            return (
              <g key={node.id}>
                <rect
                  x={position.x - 115}
                  y={position.y - 30}
                  width="230"
                  height="60"
                  rx="10"
                  fill={
                    isFile
                      ? "#17212d"
                      : "#312e81"
                  }
                  stroke={
                    isFile
                      ? "#22d3ee"
                      : "#8b5cf6"
                  }
                  strokeWidth="1.5"
                />

                <text
                  x={position.x}
                  y={position.y - 7}
                  textAnchor="middle"
                  fill={
                    isFile
                      ? "#67e8f9"
                      : "#c4b5fd"
                  }
                  fontSize="9"
                  fontWeight="700"
                  letterSpacing="1"
                >
                  {isFile
                    ? "FILE"
                    : type === "component"
                      ? "COMPONENT"
                      : "NODE"}
                </text>

                <text
                  x={position.x}
                  y={position.y + 14}
                  textAnchor="middle"
                  fill="#f8fafc"
                  fontSize="12"
                >
                  {shorten(displayName(node))}
                </text>
              </g>
            );
          },
        )}

        <g transform="translate(690 405)">
          <rect
            x="0"
            y="0"
            width="180"
            height="35"
            rx="8"
            fill="#151c26"
            stroke="#263241"
          />

          <circle
            cx="18"
            cy="17"
            r="5"
            fill="#22d3ee"
          />

          <text
            x="31"
            y="21"
            fill="#94a3b8"
            fontSize="10"
          >
            Changed file
          </text>

          <circle
            cx="102"
            cy="17"
            r="5"
            fill="#8b5cf6"
          />

          <text
            x="115"
            y="21"
            fill="#94a3b8"
            fontSize="10"
          >
            Component
          </text>
        </g>
      </svg>
    </div>
  );
}
