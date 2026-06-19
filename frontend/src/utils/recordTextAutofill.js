export function recordBodyText(record = {}) {
  return String(
    record.original_text ||
    record.body_clean ||
    record.body_core ||
    ''
  ).trim()
}

export function shouldReplaceOriginalText({
  currentText = '',
  manuallyEdited = false,
  lastAutoFilledText = ''
} = {}) {
  const current = String(currentText)
  return (
    !current.trim() ||
    !manuallyEdited ||
    current === String(lastAutoFilledText)
  )
}
