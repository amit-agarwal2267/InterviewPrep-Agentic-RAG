"use client";

import { useEffect, useRef, useState } from "react";

export function MermaidDiagram({ code }: { code: string }) {
  const [viewport, setViewport] = useState({ x: 0, y: 0, scale: 1 });
  const [rendered, setRendered] = useState<{ svg: string | null; error: string | null }>({
    svg: null,
    error: null,
  });
  const drag = useRef<{ pointerId: number; x: number; y: number } | null>(null);

  useEffect(() => {
    let cancelled = false;

    const renderDiagram = async () => {
      try {
        // Dynamic import to avoid SSR issues with renderMermaidSVG
        const { renderMermaidSVG } = await import("beautiful-mermaid");

        if (cancelled) return;

        setRendered({
          svg: renderMermaidSVG(code, {
            bg: "var(--background)",
            fg: "var(--foreground)",
            accent: "var(--accent)",
            transparent: true,
          }),
          error: null,
        });
      } catch (error) {
        if (cancelled) return;

        setRendered({
          svg: null,
          error: error instanceof Error ? error.message : "Unable to render diagram",
        });
      }
    };

    renderDiagram();

    return () => {
      cancelled = true;
    };
  }, [code]);

  if (rendered.error) {
    return <pre className="mermaid-error"><code>{code}</code></pre>;
  }

  const zoom = (factor: number) =>
    setViewport((v) => ({ ...v, scale: Math.min(4, Math.max(0.5, v.scale * factor)) }));

  return (
    <div className="mermaid-frame">
      <div className="mermaid-controls" aria-label="Diagram controls">
        <button type="button" onClick={() => zoom(1.25)} aria-label="Zoom in">+</button>
        <button type="button" onClick={() => zoom(0.8)} aria-label="Zoom out">−</button>
        <button type="button" onClick={() => setViewport({ x: 0, y: 0, scale: 1 })}>Reset</button>
      </div>
      <div
        className="mermaid-diagram"
        onWheel={(e) => { if (e.ctrlKey) { e.preventDefault(); zoom(e.deltaY < 0 ? 1.1 : 0.9); } }}
        onPointerDown={(e) => {
          drag.current = { pointerId: e.pointerId, x: e.clientX, y: e.clientY };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (!drag.current || drag.current.pointerId !== e.pointerId) return;
          const dx = e.clientX - drag.current.x;
          const dy = e.clientY - drag.current.y;
          drag.current = { pointerId: e.pointerId, x: e.clientX, y: e.clientY };
          setViewport((v) => ({ ...v, x: v.x + dx, y: v.y + dy }));
        }}
        onPointerUp={(e) => {
          if (drag.current?.pointerId === e.pointerId) drag.current = null;
          e.currentTarget.releasePointerCapture(e.pointerId);
        }}
      >
        <div
          className="mermaid-canvas"
          style={{ transform: `translate(${viewport.x}px, ${viewport.y}px) scale(${viewport.scale})` }}
          dangerouslySetInnerHTML={{ __html: rendered.svg ?? "" }}
        />
      </div>
    </div>
  );
}
