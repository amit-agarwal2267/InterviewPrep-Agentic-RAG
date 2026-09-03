import { Globe2 } from "lucide-react";
import type { Reference } from "@/types/chat";

export function ReferenceChip({ reference }: { reference: Reference }) {
  const provider = `${reference.source} ${reference.url}`.toLowerCase();
  const isNotion = provider.includes("notion");
  const isGithub = provider.includes("github");

  return (
    <a
      className="reference-chip"
      href={reference.url}
      target="_blank"
      rel="noreferrer"
      title={`${reference.title} — ${reference.source}`}
    >
      <span className={`reference-icon ${isNotion ? "notion" : isGithub ? "github" : ""}`}>
        {isNotion ? <strong>N</strong> : isGithub ? <strong>GH</strong> : <Globe2 size={13} />}
      </span>
      <span>{reference.title}</span>
    </a>
  );
}
