"use client";

import { Copy } from "lucide-react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface CodeBlockProps {
  language: string;
  code: string;
  // any extra props forwarded from ReactMarkdown
  [key: string]: unknown;
}

export function CodeBlock({ language, code, ...props }: CodeBlockProps) {
  return (
    <div className="code-block-container">
      <div className="code-block-header">
        <span className="code-block-language">{language}</span>
        <button className="code-block-copy" onClick={() => navigator.clipboard.writeText(code)}>
          <Copy size={13} /> Copy code
        </button>
      </div>
      <SyntaxHighlighter style={vscDarkPlus as any} language={language} PreTag="div" {...props}>
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
