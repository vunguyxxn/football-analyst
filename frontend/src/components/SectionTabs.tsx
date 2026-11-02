/** Buttons keep ordinary Tab/Enter navigation and expose selection to AT. */
export default function SectionTabs<T extends string>({ label, value, items, onChange }: {
  label: string
  value: T
  items: readonly { id: T; label: string }[]
  onChange: (value: T) => void
}) {
  return <div className="section-tabs" role="group" aria-label={label}>
    {items.map(item => <button key={item.id} type="button" aria-pressed={value === item.id} onClick={() => onChange(item.id)}>{item.label}</button>)}
  </div>
}
