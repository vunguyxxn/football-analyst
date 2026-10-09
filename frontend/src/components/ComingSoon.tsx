import { motion } from "framer-motion"
import type { LucideIcon } from "lucide-react"
import { ArrowUpRight } from "lucide-react"

type ComingSoonProps = {
  icon: LucideIcon
  title: string
}

export function ComingSoon({ icon: Icon, title }: ComingSoonProps) {
  return (
    <motion.section
      animate={{ opacity: 1, y: 0 }}
      className="coming-soon card-surface"
      initial={{ opacity: 0, y: 8 }}
      transition={{ duration: 0.2 }}
    >
      <div className="coming-icon">
        <Icon aria-hidden="true" size={22} strokeWidth={1.7} />
      </div>
      <span className="eyebrow">KHÔNG GIAN PHÂN TÍCH</span>
      <h2>{title}</h2>
      <p>Sắp có</p>
      <span aria-hidden="true" className="coming-accent">
        <ArrowUpRight size={18} />
      </span>
    </motion.section>
  )
}
