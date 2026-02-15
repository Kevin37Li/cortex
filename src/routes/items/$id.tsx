import { createFileRoute } from '@tanstack/react-router'
import { ItemDetail } from '@/components/items'

export const Route = createFileRoute('/items/$id')({
  component: ItemDetailPage,
})

function ItemDetailPage() {
  const { id } = Route.useParams()
  return <ItemDetail itemId={id} />
}
