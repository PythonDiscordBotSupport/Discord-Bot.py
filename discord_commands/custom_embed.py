  def parse_colored_text(self, text: str) -> str:
    # ANSI-коды цветов
    ansi_colors = {
        "red": "\u001b[31m",
        "green": "\u001b[32m",
        "yellow": "\u001b[33m",
        "blue": "\u001b[34m",
        "purple": "\u001b[35m",
        "cyan": "\u001b[36m",
    }

    # Ищем слово прямо перед скобкой без пробела: слово[цвет]
    # Группа 1 — само слово, Группа 2 — название цвета
    pattern = re.compile(r"([^\s\[]+)\[(red|green|yellow|blue|purple|cyan)\]", re.IGNORECASE)

    def replace_match(match):
      word = match.group(1)
      color = match.group(2).lower()
      code = ansi_colors.get(color, "")
      # Возвращаем цветное слово, сбрасывая цвет в конце, а [red] полностью стирается!
      return f"{code}{word}\u001b[0m"

    processed_text = pattern.sub(replace_match, text)

    # Если нашли теги, оборачиваем в ansi-блок для активации цветов в Discord
    if "\u001b[" in processed_text:
      return f"```ansi\n{processed_text}\n```"
    
    return text
    
