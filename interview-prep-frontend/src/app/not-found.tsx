"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Compass } from "lucide-react";

export default function NotFound() {
  return <main className="status-page"><motion.div className="status-code" initial={{ opacity: 0, scale: .7 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: "spring", stiffness: 120 }}>404</motion.div><motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .15 }}><h1>Page not found</h1><p>This page does not exist in your interview workspace.</p></motion.div><motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .3 }}><Link href="/"><ArrowLeft size={14} /> Return to chat</Link></motion.div><motion.div className="status-compass" animate={{ rotate: 360 }} transition={{ duration: 8, repeat: Infinity, ease: "linear" }}><Compass size={20} /></motion.div></main>;
}