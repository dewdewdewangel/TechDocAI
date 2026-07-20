export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t px-6 py-4">
      <p className="text-center text-sm text-muted-foreground">
        TechDoc AI - {currentYear}
      </p>
    </footer>
  )
}
