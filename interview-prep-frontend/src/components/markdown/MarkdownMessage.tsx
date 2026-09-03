"use client";

import { isValidElement, useMemo, useState, type ReactElement, type ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X } from "lucide-react";
import { MermaidDiagram } from "@/components/markdown/MermaidDiagram";
import { CodeBlock } from "@/components/markdown/CodeBlock";
import { ReferenceChip } from "@/components/markdown/ReferenceChip";
import { splitReferences } from "@/lib/normalizers";

export function MarkdownMessage({ content }: { content: string }) {
  const { body, references } = useMemo(() => splitReferences(content), [content]);
  const [modalImage, setModalImage] = useState<{ src: string; alt?: string } | null>(null);

  return (
    <>
      <div className="message-markdown">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            pre({ children }: { children?: ReactNode }) {
              const child = isValidElement(children)
                ? (children as ReactElement<{ className?: string; children?: ReactNode }>)
                : null;
              if (child?.props.className?.includes("language-mermaid")) {
                return <MermaidDiagram code={String(child.props.children ?? "").trim()} />;
              }
              return <pre>{children}</pre>;
            },

            code({ className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || "");
              if (match) {
                const codeString = String(children).replace(/\n$/, "");
                return <CodeBlock language={match[1]} code={codeString} {...props} />;
              }
              return <code className={className} {...props}>{children}</code>;
            },

            img(props) {
              if (!props.src) return null;
              return (
                <img
                  src={props.src as string}
                  alt={props.alt}
                  className="markdown-image"
                  onClick={() => setModalImage({ src: props.src as string, alt: props.alt })}
                />
              );
            },
          }}
        >
          {body}
        </ReactMarkdown>
      </div>

      {!!references.length && (
        <div className="reference-chips" aria-label="References">
          {references.map((ref) => <ReferenceChip key={ref.url} reference={ref} />)}
        </div>
      )}

      <AnimatePresence>
        {modalImage && (
          <motion.div
            className="modal-backdrop"
            onClick={() => setModalImage(null)}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <button className="image-modal-close" onClick={() => setModalImage(null)} aria-label="Close">
              <X size={24} />
            </button>
            <motion.div
              className="image-zoom-container"
              onClick={(e) => e.stopPropagation()}
              initial={{ scale: 0.95 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0.95 }}
            >
              <img
                src={modalImage.src}
                alt={modalImage.alt}
                className="zoomed-image"
                onClick={() => setModalImage(null)}
              />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
