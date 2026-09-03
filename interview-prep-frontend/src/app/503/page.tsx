"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight, RefreshCw } from "lucide-react";

export default function ServiceUnavailable() {
  return <main className="status-page"><motion.div className="status-code" initial={{ opacity: 0, scale: .7 }} animate={{ opacity: 1, scale: 1 }} transition={{ type: "spring", stiffness: 120 }}>503</motion.div><motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .15 }}><h1>Service unavailable</h1><p>The interview assistant is temporarily offline. Please try again shortly.</p></motion.div><motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: .3 }}><Link href="/"><RefreshCw size={14} /> Try again <ArrowRight size={14} /></Link></motion.div><motion.div className="status-loader" animate={{ rotate: 360 }} transition={{ duration: 1.8, repeat: Infinity, ease: "linear" }}><RefreshCw size={20} /></motion.div></main>;
}