export function formatDate(updatedAt: string): string {
  const diffDays = Math.floor((Date.now() - new Date(updatedAt).getTime()) / 86_400_000)
  if (diffDays === 0) return '오늘'
  if (diffDays === 1) return '어제'
  return `${diffDays}일 전`
}
