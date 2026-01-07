import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Role } from '@/lib/types'
import { ShieldCheck } from '@phosphor-icons/react'

interface RoleSelectProps {
  roles: Role[]
  value?: number
  disabled?: boolean
  placeholder?: string
  onChange: (roleId: number) => void
}

export function RoleSelect({ roles, value, disabled, placeholder = 'Seleccionar rol', onChange }: RoleSelectProps) {
  return (
    <Select
      value={value ? String(value) : undefined}
      onValueChange={(val) => onChange(Number(val))}
      disabled={disabled}
    >
      <SelectTrigger className="min-w-[180px]">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {roles.map((role) => (
          <SelectItem key={role.id} value={role.id.toString()}>
            <div className="flex items-center gap-2">
              <span>{role.name}</span>
              {role.is_system_role && (
                <ShieldCheck className="h-4 w-4 text-primary" />
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
