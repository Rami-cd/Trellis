import { useMemo, useRef, useCallback, useState, useEffect } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { X, Search } from 'lucide-react';

const NODE_COLORS = {
  function: '#3fa9f5',
  class: '#ffb020',
  module: '#9aa5ad',
  variable: '#3ddc84',
};

const SEED_COLOR = '#ff4d5e';
const UNRESOLVED_COLOR = '#6b6b6b';

// Edge type -> stroke style. Keys are lowercased at lookup time so backend
// casing (e.g. "Calls" vs "calls") can't silently fall through to default.
const EDGE_STYLES = {
  calls: { color: '#3fa9f5', dash: null },
  defines: { color: '#9aa5ad', dash: null },
  imports: { color: '#3ddc84', dash: [4, 2] },
  inherits: { color: '#ffb020', dash: null },
};
const DEFAULT_EDGE_STYLE = { color: '#5c6570', dash: null };
const UNRESOLVED_EDGE_STYLE = { color: '#6b6b6b', dash: [2, 3] };

function colorForNode(node) {
  if (node.is_seed) return SEED_COLOR;
  return NODE_COLORS[node.type] ?? '#8a8a8a';
}

function styleForEdge(link) {
  if (link.unresolved) return UNRESOLVED_EDGE_STYLE;
  const key = (link.type || '').toLowerCase();
  return EDGE_STYLES[key] ?? DEFAULT_EDGE_STYLE;
}

// Convert a hex color to an rgba string with the given alpha, so dimmed
// states are computed rather than relying on appended-hex-alpha string hacks.
function withAlpha(hex, alpha) {
  const h = hex.replace('#', '');
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function GraphView({ graphData }) {
  const fgRef = useRef();
  const containerRef = useRef();

  const [selectedNode, setSelectedNode] = useState(null);
  const [hoverNode, setHoverNode] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const data = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };

    const nodeIds = new Set(graphData.nodes.map((n) => n.id));

    const degrees = {};
    const neighbors = {};

    graphData.edges.forEach((e) => {
      degrees[e.source_id] = (degrees[e.source_id] || 0) + 1;
      degrees[e.target_id] = (degrees[e.target_id] || 0) + 1;

      if (!neighbors[e.source_id]) neighbors[e.source_id] = new Set();
      if (!neighbors[e.target_id]) neighbors[e.target_id] = new Set();

      neighbors[e.source_id].add(e.target_id);
      neighbors[e.target_id].add(e.source_id);
    });

    return {
      nodes: graphData.nodes.map((n) => ({
        id: n.id,
        label: n.qualified_name,
        type: n.type,
        is_seed: n.is_seed,
        summary: n.summary,
        raw_source: n.raw_source,
        val: Math.sqrt(degrees[n.id] || 0) * 2 + 1.5,
        neighbors: neighbors[n.id] || new Set(),
      })),
      links: graphData.edges.map((e) => ({
        source: e.source_id,
        target: e.target_id,
        type: e.type,
        target_ref: e.target_ref,
        unresolved: !nodeIds.has(e.target_id) || !nodeIds.has(e.source_id),
      })),
    };
  }, [graphData]);

  const handleNodeClick = useCallback((node) => {
    setSelectedNode(node);
  }, []);

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node ? node.id : null);
  }, []);

  // Returns { color, dimmed } so the canvas renderer can decide whether to glow.
  const resolveNodeAppearance = useCallback(
    (node) => {
      const baseColor = colorForNode(node);
      const failsSearch =
        searchQuery && !node.label.toLowerCase().includes(searchQuery.toLowerCase());
      const failsHover = hoverNode && node.id !== hoverNode && !node.neighbors.has(hoverNode);

      if (failsSearch || failsHover) {
        return { color: withAlpha(baseColor, 0.15), dimmed: true };
      }
      return { color: baseColor, dimmed: false };
    },
    [hoverNode, searchQuery]
  );

  const getLinkColor = useCallback(
    (link) => {
      const baseStyle = styleForEdge(link);
      const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
      const targetId = typeof link.target === 'object' ? link.target.id : link.target;

      const isHoverDimmed = hoverNode && sourceId !== hoverNode && targetId !== hoverNode;

      if (isHoverDimmed) {
        return 'rgba(90, 90, 90, 0.12)';
      }
      return baseStyle.color;
    },
    [hoverNode]
  );

  if (!graphData) {
    return (
      <div className="flex-1 flex items-center justify-center text-on-surface-variant text-sm">
        Ask a question to generate a graph
      </div>
    );
  }

  return (
    <div ref={containerRef} className="flex-1 w-full h-full relative overflow-hidden bg-surface-dim">

      {/* Search / Filter Overlay */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 w-[350px]">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-on-surface-variant" />
          <input
            type="text"
            placeholder="Filter nodes by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-surface-container-highest border border-outline-variant rounded-full pl-10 pr-4 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary shadow-lg transition-colors"
          />
        </div>
      </div>

      <ForceGraph2D
        width={dimensions.width}
        height={dimensions.height}
        ref={fgRef}
        graphData={data}
        nodeId="id"
        nodeVal="val"
        nodeLabel={(node) => `${node.label}${node.summary ? `\n${node.summary}` : ''}`}
        nodeRelSize={5}
        linkLabel={(link) =>
          link.unresolved ? `${link.type} (unresolved: ${link.target_ref})` : link.type
        }
        linkColor={getLinkColor}
        linkWidth={(link) => (link.unresolved ? 1 : 1.6)}
        linkLineDash={(link) => styleForEdge(link).dash}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        onNodeClick={handleNodeClick}
        onNodeHover={handleNodeHover}
        onBackgroundClick={() => setSelectedNode(null)}
        backgroundColor="transparent"
        d3Force={{
          charge: -900,
          linkDistance: 140,
        }}
        d3VelocityDecay={0.35}
        cooldownTicks={200}
        onEngineTick={() => {
          const nodes = data.nodes;
          for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
              const a = nodes[i], b = nodes[j];
              if (a.x === undefined || b.x === undefined) continue;
              const dx = b.x - a.x, dy = b.y - a.y;
              const dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
              const minDist = (a.val + b.val) * 1.8 + 6;
              if (dist < minDist) {
                const overlap = (minDist - dist) / 2;
                const nx = dx / dist, ny = dy / dist;
                a.x -= nx * overlap; a.y -= ny * overlap;
                b.x += nx * overlap; b.y += ny * overlap;
              }
            }
          }
        }}
        nodeCanvasObject={(node, ctx) => {
          const { color, dimmed } = resolveNodeAppearance(node);
          const size = node.val * 1.8;

          ctx.save();

          if (!dimmed) {
            // Neon halo: two soft glow passes at increasing radius/blur for
            // a real light-bloom look rather than a single flat shadow.
            ctx.shadowColor = color;
            ctx.shadowBlur = 22;
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();

            ctx.shadowBlur = 10;
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();
          } else {
            ctx.beginPath();
            ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();
          }

          ctx.restore();

          if (!dimmed) {
            // Hot white core = filament of the "neon tube"
            ctx.beginPath();
            ctx.arc(node.x, node.y, size * 0.38, 0, 2 * Math.PI, false);
            ctx.fillStyle = 'rgba(255,255,255,0.9)';
            ctx.fill();
          }

          ctx.beginPath();
          ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
          ctx.lineWidth = 1;
          ctx.strokeStyle = dimmed ? 'rgba(255,255,255,0.04)' : 'rgba(255,255,255,0.5)';
          ctx.stroke();
        }}
      />

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-surface-container-lowest/80 backdrop-blur-md border border-outline-variant rounded-xl px-3 py-2 text-xs text-on-surface space-y-1 pointer-events-none shadow-lg">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full" style={{ background: SEED_COLOR, boxShadow: `0 0 6px ${SEED_COLOR}` }} />
          Seed node
        </div>
        {Object.entries(NODE_COLORS).map(([type, color]) => (
          <div key={type} className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
            {type}
          </div>
        ))}
        <div className="border-t border-outline-variant/50 my-1.5" />
        {Object.entries(EDGE_STYLES).map(([type, style]) => (
          <div key={type} className="flex items-center gap-2">
            <span
              className="w-4 h-0"
              style={{
                borderTop: `2px ${style.dash ? 'dashed' : 'solid'} ${style.color}`,
              }}
            />
            {type}
          </div>
        ))}
        <div className="flex items-center gap-2">
          <span
            className="w-4 h-0"
            style={{ borderTop: `2px dashed ${UNRESOLVED_COLOR}` }}
          />
          unresolved
        </div>
      </div>

      {/* Floating source card */}
      {selectedNode && (
        <div className="absolute top-4 right-4 bottom-4 w-[420px] max-w-[90%] bg-surface-container-lowest border border-outline-variant rounded-2xl shadow-xl flex flex-col overflow-hidden z-10">
          <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant bg-surface-container-highest/50">
            <div className="min-w-0 pr-4">
              <p className="text-sm font-semibold text-on-surface truncate">
                {selectedNode.label}
              </p>
              <p className="text-xs text-on-surface-variant uppercase tracking-wider mt-0.5">{selectedNode.type}</p>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="p-1.5 rounded-md bg-surface-dim text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {selectedNode.summary && (
            <p className="px-4 py-3 text-sm text-on-surface-variant border-b border-outline-variant bg-surface-dim/30">
              {selectedNode.summary}
            </p>
          )}

          <div className="flex-1 overflow-auto p-4 bg-surface-container-lowest">
            {selectedNode.raw_source ? (
              <pre className="text-xs font-mono text-on-surface whitespace-pre-wrap break-words">
                {selectedNode.raw_source}
              </pre>
            ) : (
              <p className="text-sm text-on-surface-variant italic">No raw source available for this node.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}