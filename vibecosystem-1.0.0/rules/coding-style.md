# Coding Style & Patterns

## Immutability (KRITIK)

ASLA mutate etme, yeni obje olustur:
```javascript
// YANLIS
user.name = name

// DOGRU
return { ...user, name }
```

## Dosya Organizasyonu

COK KUCUK DOSYA > AZ BUYUK DOSYA:
- 200-400 satir normal, 800 max
- Feature/domain bazli organize et
- Fonksiyonlar <50 satir
- 4+ seviye nesting yapma

## Error Handling

```typescript
try {
  const result = await riskyOperation()
  return result
} catch (error) {
  console.error('Operation failed:', error)
  throw new Error('Detayli kullanici mesaji')
}
```

## Input Validation

```typescript
import { z } from 'zod'
const schema = z.object({
  email: z.string().email(),
  age: z.number().int().min(0).max(150)
})
const validated = schema.parse(input)
```

## API Response Format

```typescript
interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  meta?: { total: number; page: number; limit: number }
}
```

## Repository Pattern

```typescript
interface Repository<T> {
  findAll(filters?: Filters): Promise<T[]>
  findById(id: string): Promise<T | null>
  create(data: CreateDto): Promise<T>
  update(id: string, data: UpdateDto): Promise<T>
  delete(id: string): Promise<void>
}
```

## Kalite Checklist

- [ ] Okunabilir, iyi isimlendirilmis
- [ ] console.log yok
- [ ] Hardcoded deger yok
- [ ] Mutation yok
- [ ] Hata yakalama var
