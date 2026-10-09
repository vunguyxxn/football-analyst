import { Select as SelectPrimitive } from "@base-ui/react/select"
import { Check, ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

export type SelectOption = {
  value: string
  label: string
}

type SelectFieldProps = {
  label: string
  value: string | null
  options: SelectOption[]
  placeholder: string
  disabled?: boolean
  onValueChange: (value: string | null) => void
}

export function SelectField({
  label,
  value,
  options,
  placeholder,
  disabled,
  onValueChange,
}: SelectFieldProps) {
  return (
    <label className="select-field">
      <span className="field-label">{label}</span>
      <SelectPrimitive.Root
        disabled={disabled}
        items={options}
        onValueChange={onValueChange}
        value={value}
      >
        <SelectPrimitive.Trigger className="select-trigger">
          <SelectPrimitive.Value placeholder={placeholder} />
          <SelectPrimitive.Icon className="select-chevron">
            <ChevronDown aria-hidden="true" size={16} />
          </SelectPrimitive.Icon>
        </SelectPrimitive.Trigger>
        <SelectPrimitive.Portal>
          <SelectPrimitive.Positioner className="select-positioner" sideOffset={6}>
            <SelectPrimitive.Popup className="select-popup">
              <SelectPrimitive.List>
                {options.map((option) => (
                  <SelectPrimitive.Item
                    className={cn("select-option")}
                    key={option.value}
                    value={option.value}
                  >
                    <SelectPrimitive.ItemText>
                      {option.label}
                    </SelectPrimitive.ItemText>
                    <SelectPrimitive.ItemIndicator className="select-check">
                      <Check aria-hidden="true" size={14} />
                    </SelectPrimitive.ItemIndicator>
                  </SelectPrimitive.Item>
                ))}
              </SelectPrimitive.List>
            </SelectPrimitive.Popup>
          </SelectPrimitive.Positioner>
        </SelectPrimitive.Portal>
      </SelectPrimitive.Root>
    </label>
  )
}
